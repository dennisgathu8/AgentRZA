import json
from src.models.state import PipelineState
from src.tools.audit import audit_log
from src.models.domain import MatchEnrichedPayload

class QualityValidator:
    """
    Validates statistical integrity of the enriched payloads.
    Functions similarly to Great Expectations for data-quality.
    """
    def generate_report(self, payload: MatchEnrichedPayload) -> dict:
        total_events = len(payload.events)
        total_shots = sum(1 for e in payload.events if e.shot_context is not None)
        
        home_goals = payload.match.home_score
        away_goals = payload.match.away_score
        
        # Anomaly logic: Did a team drastically under/overperform their xG?
        # Or did a match have fewer than expected total events (incomplete data)?
        home_xg = payload.total_home_xg
        away_xg = payload.total_away_xg
        
        anomalies = []
        if total_events < 500: # Typical modern match has >1500 events
            anomalies.append(f"Low event count: {total_events}")
            
        if abs(home_goals - home_xg) > 4.0:
             anomalies.append(f"Severe Home xG anomaly. Goals: {home_goals}, xG: {home_xg:.2f}")
             
        if abs(away_goals - away_xg) > 4.0:
             anomalies.append(f"Severe Away xG anomaly. Goals: {away_goals}, xG: {away_xg:.2f}")
             
        passed = len(anomalies) == 0
        
        report = {
            "match_id": payload.match.match_id,
            "total_events": total_events,
            "total_shots": total_shots,
            "home_xg": round(home_xg, 2),
            "away_xg": round(away_xg, 2),
            "passed": passed,
            "anomalies": anomalies
        }
        return report

async def validator_node(state: PipelineState) -> PipelineState:
    """
    Validator Agent assesses the completed payload.
    If it fails severe statistical checks, it marks it for review or retry.
    """
    payload = state.get("enriched_payload")
    if not payload:
        state["pipeline_status"] = "failed"
        return state
        
    validator = QualityValidator()
    report = validator.generate_report(payload)
    
    audit_log("validation_report", "ValidatorAgent", report)
    
    # Check if pipeline requires self-healing / retry
    if not report["passed"]:
        audit_log("validation_failed", "ValidatorAgent", {"anomalies": report["anomalies"]})
        state["validation_passed"] = False
        # Optional: Direct back to fetcher or raise alert
        state["pipeline_status"] = "supervisor" 
    else:
         state["validation_passed"] = True
         state["pipeline_status"] = "supervisor" # Ask supervisor for the next match
         
    return state
