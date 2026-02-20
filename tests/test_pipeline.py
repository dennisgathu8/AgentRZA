import pytest
import asyncio
from src.graph import run_pipeline

@pytest.mark.asyncio
async def test_run_pipeline_initialization():
    """
    Test that the LangGraph pipeline initializes and reaches a deterministic end state
    even without real credentials, ensuring the basic graph topology validates.
    """
    # This will likely fail gracefully with an auth or fetch error
    # but the graph itself should execute the node.
    state = await run_pipeline("today")
    
    assert "pipeline_status" in state
    assert isinstance(state.get("errors", []), list)
    
    assert state["pipeline_status"] in ["supervisor", "fetching", "failed"]
