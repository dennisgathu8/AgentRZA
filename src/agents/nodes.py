from src.models.state import PipelineState
from src.tools.audit import audit_log
from src.tools.fetch import SecureFetcher
import asyncio

async def supervisor_node(state: PipelineState) -> PipelineState:
    """
    Supervisor Agent evaluates the target parameters and decides what matches 
    to place into the queue.
    """
    audit_log("supervisor_decision", "SupervisorAgent", {"date": state["target_date"], "competitions": state["target_competitions"]})
    
    # We will dynamically fetch Match IDs for the given competitions.
    # For demo purposes, we will fetch FIFA World Cup 2022 (competition 43, season 106).
    # A real system would have a date-match cross-reference.
    
    if not state.get("matches_to_process"):
        fetcher = SecureFetcher()
        try:
            # StatsBomb WC 2022: comp 43, season 106
            # In a true daily run, we would filter by `state["target_date"]`
            matches_data = await fetcher.fetch_statsbomb_matches(43, 106)
            
            # Select 2 matches for the demo to avoid a massive run
            simulated_matches = []
            for m in matches_data[:2]:
                simulated_matches.append(m['match_id'])
                
            state["matches_to_process"] = simulated_matches
            # Store the raw match metadata in state to avoid mocking in enricher
            if "raw_match_metadata" not in state or state["raw_match_metadata"] is None:
                state["raw_match_metadata"] = matches_data[:2]
            else:
                state["raw_match_metadata"].extend(matches_data[:2])
            
            state["pipeline_status"] = "fetching"
            audit_log("planner_queue_built", "SupervisorAgent", {"len_matches": len(simulated_matches), "queue": simulated_matches})
        except Exception as e:
            state["errors"].append(f"Planner failed to fetch match list: {str(e)}")
            state["pipeline_status"] = "failed"
        finally:
            await fetcher.close()
            
    return state
    
async def fetcher_node(state: PipelineState) -> PipelineState:
    """
    Fetcher Agent securely pulls the match data from StatsBomb with TLS and backoffs.
    """
    if not state["matches_to_process"]:
        state["pipeline_status"] = "done"
        return state
        
    match_id = state["matches_to_process"].pop(0)
    state["current_match_id"] = match_id
    
    fetcher = SecureFetcher()
    try:
        raw_events = await fetcher.fetch_statsbomb_events(match_id)
        state["raw_event_data"] = {"match_id": match_id, "events": raw_events}
        state["pipeline_status"] = "enriching"
    except Exception as e:
        state["errors"].append(f"Fetch failed for {match_id}: {str(e)}")
        state["pipeline_status"] = "supervisor" # fallback to supervisor to decide retry/skip
    finally:
        await fetcher.close()
        
    return state
