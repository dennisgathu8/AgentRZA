from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Literal
from datetime import datetime

class StrictModel(BaseModel):
    """Base model enforcing strict configuration for zero-trust data parsing."""
    model_config = ConfigDict(
        extra='forbid',  # Reject any undocumented fields
        validate_assignment=True,
        strict=True
    )

class Player(StrictModel):
    player_id: int
    player_name: str
    position: Optional[str] = None

class Team(StrictModel):
    team_id: int
    team_name: str

class Match(StrictModel):
    match_id: int
    match_date: datetime
    competition_id: int
    season_id: int
    home_team: Team
    away_team: Team
    home_score: int = Field(ge=0, description="Score cannot be negative")
    away_score: int = Field(ge=0, description="Score cannot be negative")
    status: Literal['scheduled', 'finished', 'cancelled', 'available'] = 'finished'

class Location(StrictModel):
    x: float
    y: float

class PassContext(StrictModel):
    length: float = Field(ge=0.0)
    angle: float
    recipient: Optional[Player] = None
    is_progressive: bool = False

class ShotContext(StrictModel):
    xg: Optional[float] = Field(ge=0.0, le=1.0, description="Expected goals strictly bounded between 0 and 1.")
    xa: Optional[float] = Field(ge=0.0, le=1.0, description="Expected assists strictly bounded between 0 and 1.")
    outcome: Literal['Goal', 'Saved', 'Off T', 'Post', 'Wayward', 'Blocked']
    body_part: str
    distance_to_goal: Optional[float] = Field(default=None, ge=0.0)
    angle_to_goal: Optional[float] = Field(default=None)

class TrackingFrame(StrictModel):
    """
    State-of-the-Art representation of a single 30fps optical tracking frame.
    Defines zero-trust bounding logic for X, Y coordinates (normalized 0-1) across both teams.
    """
    frame_id: int
    period: int
    timestamp_ms: int
    ball_location: Optional[Location] = None
    home_players: List[Location] = [] # List of X,Y positions
    away_players: List[Location] = [] # List of X,Y positions
    home_ppda: Optional[float] = None  # Passes Allowed Per Defensive Action at this frame
    away_ppda: Optional[float] = None

class Event(StrictModel):
    event_id: str
    match_id: int
    index: int = Field(ge=1)
    period: int = Field(ge=1, le=5) # 1, 2, 3(ET1), 4(ET2), 5(Pens)
    timestamp: str # ISO string or match clock "MM:SS"
    minute: int = Field(ge=0)
    second: int = Field(ge=0, le=59)
    type_name: str
    possession_team: Team
    player: Optional[Player] = None
    location: Optional[Location] = None
    
    # Specific Contexts (populated based on type_name)
    pass_context: Optional[PassContext] = None
    shot_context: Optional[ShotContext] = None

class MatchEnrichedPayload(StrictModel):
    match: Match
    events: List[Event]
    tracking_frames: List[TrackingFrame] = []
    total_home_xg: float = Field(default=0.0, ge=0.0)
    total_away_xg: float = Field(default=0.0, ge=0.0)
