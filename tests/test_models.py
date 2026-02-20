import pytest
from pydantic import ValidationError
from datetime import datetime, timezone
from src.models.domain import Match, Team

def test_pydantic_forbid_extra():
    """
    Zero-trust validation must reject injected API keys or arbitrary JSON payloads.
    """
    home = Team(team_id=1, team_name="Home")
    away = Team(team_id=2, team_name="Away")
    
    with pytest.raises(ValidationError):
        # Adding a malicious hidden field should trigger pure rejection
        Match(
            match_id=1,
            match_date=datetime.now(timezone.utc),
            competition_id=1, season_id=1,
            home_team=home, away_team=away,
            home_score=0, away_score=0, status='finished',
            injected_malicious_script="<script>alert(1)</script>"
        )

def test_score_bounds():
    """
    Football scores cannot be logically negative.
    """
    home = Team(team_id=1, team_name="Home")
    away = Team(team_id=2, team_name="Away")
    
    with pytest.raises(ValidationError):
        Match(
            match_id=1,
            match_date=datetime.now(timezone.utc),
            competition_id=1, season_id=1,
            home_team=home, away_team=away,
            home_score=-1, away_score=0, status='finished'
        )
