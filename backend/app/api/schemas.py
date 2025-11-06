"""Pydantic schemas for API request/response validation."""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class LeagueBase(BaseModel):
    league_key: str
    name: Optional[str] = None
    season: Optional[int] = None


class LeagueResponse(LeagueBase):
    id: int
    game_code: str
    league_type: Optional[str] = None
    
    class Config:
        from_attributes = True


class TeamBase(BaseModel):
    team_key: str
    name: Optional[str] = None


class TeamResponse(TeamBase):
    id: int
    manager: Optional[str] = None
    wins: int
    losses: int
    ties: int
    points_for: float
    points_against: float
    standing: Optional[int] = None
    
    class Config:
        from_attributes = True


class PlayerBase(BaseModel):
    player_key: str
    name: Optional[str] = None
    position: Optional[str] = None


class PlayerResponse(PlayerBase):
    id: int
    team: Optional[str] = None
    status: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class TradeAnalysisResponse(BaseModel):
    overperformers: List[Dict[str, Any]]
    underperformers: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]


class DraftAnalysisResponse(BaseModel):
    best_picks: List[Dict[str, Any]]
    worst_picks: List[Dict[str, Any]]
    draft_grades: Dict[str, Any]
    total_picks: int


class PerformanceAnalysisResponse(BaseModel):
    player_key: str
    projected_points: float
    actual_points: float
    differential: float
    percentage_diff: float


class HistoricalDataResponse(BaseModel):
    season: int
    teams: List[Dict[str, Any]]
    league_stats: Dict[str, Any]


class ErrorResponse(BaseModel):
    detail: str

