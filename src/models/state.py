from typing import TypedDict, Annotated, List, Dict, Any
from operator import add
from src.models.domain import MatchEnrichedPayload

class PipelineState(TypedDict):
    """
    The central LangGraph state.
    Messages and active lists use operators to determine how state is updated.
    """
    # Orchestration Data
    target_date: str
    target_competitions: List[int]
    
    # Execution Tracking
    matches_to_process: List[int]
    current_match_id: int | None
    
    # Working payloads
    raw_match_metadata: List[Dict[str, Any]] | None
    raw_event_data: Dict[str, Any] | None
    raw_tracking_home: str | None
    raw_tracking_away: str | None
    enriched_payload: MatchEnrichedPayload | None
    
    # Status and Audit
    errors: Annotated[List[str], add]
    validation_passed: bool
    pipeline_status: str # "planning", "fetching", "enriching", "loading", "validating", "done", "failed"
