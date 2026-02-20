import os
import json
from src.models.state import PipelineState
from src.tools.audit import audit_log
from src.tools.enrich import get_xg_model
from src.tools.secure_db import secure_db_session
from src.models.domain import MatchEnrichedPayload, Match, Event, Team, Player, Location, ShotContext
from pydantic import ValidationError

async def enricher_node(state: PipelineState) -> PipelineState:
    """
    Enricher Agent normalizes the raw data, drops malformed data (via Pydantic),
    and computes advanced metrics like Logistic-Regression xG.
    """
    raw_payload = state.get("raw_event_data")
    if not raw_payload:
        state["pipeline_status"] = "failed"
        state["errors"].append("Enricher called with no raw data")
        return state
        
    match_id = raw_payload["match_id"]
    events = raw_payload["events"]
    
    audit_log("enrichment_started", "EnricherAgent", {"match_id": match_id})
    xg_model = get_xg_model()
    
    valid_events = []
    total_home_xg, total_away_xg = 0.0, 0.0
    
    # Retrieve Match Metadata from State
    raw_match_metadata = state.get("raw_match_metadata", [])
    match_info = next((m for m in raw_match_metadata if m['match_id'] == match_id), None)
    
    from datetime import datetime, timezone
    if match_info:
        # Safely parse date
        match_date_str = match_info.get('match_date', '2026-01-01')
        try:
            match_date = datetime.fromisoformat(match_date_str).replace(tzinfo=timezone.utc)
        except ValueError:
            match_date = datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc)
            
        home_team = Team(team_id=match_info['home_team']['home_team_id'], team_name=match_info['home_team']['home_team_name'])
        away_team = Team(team_id=match_info['away_team']['away_team_id'], team_name=match_info['away_team']['away_team_name'])
        
        # Validates fields securely with Pydantic Match Model
        match = Match(
            match_id=match_id, 
            match_date=match_date, 
            competition_id=match_info.get('competition', {}).get('competition_id', 1), 
            season_id=match_info.get('season', {}).get('season_id', 1),
            home_team=home_team, away_team=away_team,
            home_score=match_info.get('home_score', 0), 
            away_score=match_info.get('away_score', 0), 
            status=match_info.get('match_status', 'finished')
        )
    else:
        # Fallback security if metadata is absolutely missing (e.g direct ad-hoc event inject)
        home_team = Team(team_id=1, team_name="Home Team")
        away_team = Team(team_id=2, team_name="Away Team")
        match = Match(
            match_id=match_id, 
            match_date=datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc), 
            competition_id=1, season_id=1,
            home_team=home_team, away_team=away_team,
            home_score=0, away_score=0, status='finished'
        )
    
    for raw_event in events:
        try:
            # StatsBomb to Our Schema mapper
            player_info = None
            if 'player' in raw_event:
                player_info = Player(player_id=raw_event['player'].get('id', 0), player_name=raw_event['player'].get('name', 'Unknown'))
            
            loc = None
            if 'location' in raw_event and len(raw_event['location']) >= 2:
                loc = Location(x=float(raw_event['location'][0]), y=float(raw_event['location'][1]))
                
            shot_context = None
            if raw_event.get('type', {}).get('name') == 'Shot' and loc:
                # ENRICHMENT: Calculate Logistic xG based on location
                xg_value = xg_model.predict_xg(loc.x, loc.y)
                sb_outcome = raw_event.get('shot', {}).get('outcome', {}).get('name', 'Saved')
                body_part = raw_event.get('shot', {}).get('body_part', {}).get('name', 'Foot')
                
                # Coerce to literal
                if sb_outcome not in ['Goal', 'Saved', 'Off T', 'Post', 'Wayward', 'Blocked']:
                    sb_outcome = 'Saved' 
                    
                shot_context = ShotContext(
                    xg=xg_value,
                    xa=0.0,
                    outcome=sb_outcome,
                    body_part=body_part,
                    distance_to_goal=xg_model._calculate_distance_and_angle(loc.x, loc.y)[0],
                    angle_to_goal=xg_model._calculate_distance_and_angle(loc.x, loc.y)[1]
                )
                
                # Accumulate Team xG
                team_name = raw_event.get('possession_team', {}).get('name')
                if team_name == home_team.team_name:
                    total_home_xg += xg_value
                else:
                    total_away_xg += xg_value

            event = Event(
                event_id=str(raw_event.get('id')),
                match_id=match_id,
                index=int(raw_event.get('index', 1)),
                period=int(raw_event.get('period', 1)),
                timestamp=str(raw_event.get('timestamp')),
                minute=int(raw_event.get('minute', 0)),
                second=int(raw_event.get('second', 0)),
                type_name=str(raw_event.get('type', {}).get('name', 'Unknown')),
                possession_team=Team(team_id=raw_event.get('possession_team', {}).get('id', 0), team_name=raw_event.get('possession_team', {}).get('name', 'Unknown')),
                player=player_info,
                location=loc,
                shot_context=shot_context
            )
            valid_events.append(event)
        except ValidationError as e:
            # Zero-trust means we drop malformed rows loudly in the audit log
            audit_log("validation_drop", "EnricherAgent", {"event_id": raw_event.get('id'), "error": str(e)})
            continue
            
    try:
        enriched = MatchEnrichedPayload(
            match=match,
            events=valid_events,
            total_home_xg=total_home_xg,
            total_away_xg=total_away_xg
        )
        state["enriched_payload"] = enriched
        state["pipeline_status"] = "loading"
        audit_log("enrichment_success", "EnricherAgent", {"match_id": match_id, "valid_events": len(valid_events)})
    except ValidationError as e:
         state["errors"].append(f"Payload validation failed: {str(e)}")
         state["pipeline_status"] = "failed"
         
    return state

async def loader_node(state: PipelineState) -> PipelineState:
    """
    Loader Agent securely stores the Pydantic verified payload into DuckDB,
    then encrypts the output on disk with Fernet.
    """
    payload = state.get("enriched_payload")
    if not payload:
        state["pipeline_status"] = "failed"
        state["errors"].append("Loader called with no enriched payload")
        return state
        
    audit_log("load_started", "LoaderAgent", {"match_id": payload.match.match_id})
    
    with secure_db_session() as db:
        try:
            db.upsert_match_data(payload.model_dump())
            db.flush_to_encrypted_disk()
            state["pipeline_status"] = "validating"
            audit_log("load_success", "LoaderAgent", {"match_id": payload.match.match_id})
        except Exception as e:
            state["errors"].append(f"DB Load failed: {str(e)}")
            state["pipeline_status"] = "failed"
            audit_log("load_failed", "LoaderAgent", {"error": str(e)})
            
    return state
