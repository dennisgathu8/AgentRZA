import asyncio
from langgraph.graph import StateGraph, END
from src.models.state import PipelineState
from src.agents.nodes import supervisor_node, fetcher_node
from src.agents.enrich_load import enricher_node, loader_node
from src.agents.validator import validator_node
from src.tools.audit import audit_log

def route_from_supervisor(state: PipelineState):
    """Router dictates next step from Supervisor."""
    if state["pipeline_status"] == "fetching" and state["matches_to_process"]:
        return "fetcher"
    elif state["pipeline_status"] == "done":
        return END
    else:
        # Fallback security routing
        return END

def route_from_fetcher(state: PipelineState):
    """Router dictates next step from Fetcher."""
    if state["pipeline_status"] == "enriching":
        return "enricher"
    elif state["pipeline_status"] == "supervisor":
       return "supervisor" # Handle retry
    else:
        return END

def build_graph():
    """
    Constructs the strictly-typed zero-trust LangGraph pipeline.
    State transitions are explicitly routed and audited.
    """
    workflow = StateGraph(PipelineState)
    
    # Add Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("fetcher", fetcher_node)
    workflow.add_node("enricher", enricher_node)
    workflow.add_node("loader", loader_node)
    workflow.add_node("validator", validator_node)

    # Secure Routing Edges
    workflow.set_entry_point("supervisor")
    
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {"fetcher": "fetcher", END: END}
    )
    
    workflow.add_conditional_edges(
        "fetcher",
        route_from_fetcher,
        {"enricher": "enricher", "supervisor": "supervisor", END: END}
    )
    
    # Deterministic happy path handles payload directly
    workflow.add_edge("enricher", "loader")
    workflow.add_edge("loader", "validator")
    
    # Validator feeds heavily filtered result back to orchestrator for next run
    workflow.add_edge("validator", "supervisor")
    
    return workflow.compile()

async def run_pipeline(target_date: str):
    """Main execution point for the LangGraph."""
    audit_log("pipeline_start", "System", {"release": "2026-v1", "date": target_date})
    graph = build_graph()
    
    initial_state = PipelineState(
        target_date=target_date,
        target_competitions=[43], # Example: FIFA World Cup etc
        matches_to_process=[],
        current_match_id=None,
        raw_event_data=None,
        enriched_payload=None,
        errors=[],
        validation_passed=False,
        pipeline_status="planning"
    )
    
    final_state = await graph.ainvoke(initial_state)
    audit_log("pipeline_complete", "System", {"final_status": final_state["pipeline_status"], "errors": len(final_state["errors"])})
    return final_state
