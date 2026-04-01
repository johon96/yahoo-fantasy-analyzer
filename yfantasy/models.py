"""Data models for yfantasy — plain dataclasses, no ORM."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

# Bench / inactive position names across all sports
_INACTIVE_POSITIONS = {"BN", "IR", "IR+", "IL", "IL+", "DL", "NA", "Bench"}


@dataclass
class Player:
    player_key: str
    name: str
    team: str
    positions: list[str]
    status: str
    percent_owned: float
    current_fantasy_team: Optional[str]
    stats: dict[str, float]
    projected_stats: Optional[dict[str, float]]

    @property
    def is_available(self) -> bool:
        return self.current_fantasy_team is None


@dataclass
class RosterPlayer:
    player: Player
    selected_position: str
    is_starting: bool


@dataclass
class Roster:
    team_key: str
    players: list[RosterPlayer]


@dataclass
class StatCategory:
    stat_id: str
    name: str
    display_name: str
    sort_order: str
    position_type: str
    is_only_display: bool
    value: Optional[float]
    is_category: bool

    @property
    def is_scoring(self) -> bool:
        return not self.is_only_display and (self.value is not None or self.is_category)


@dataclass
class League:
    league_key: str
    name: str
    sport: str
    season: str
    num_teams: int
    scoring_type: str
    scoring_period: str
    roster_positions: list[str]
    stat_categories: list[StatCategory]
    current_week: int

    @property
    def is_daily(self) -> bool:
        return self.scoring_period == "daily"

    @property
    def active_positions(self) -> list[str]:
        return [p for p in self.roster_positions if p not in _INACTIVE_POSITIONS]


@dataclass
class Team:
    team_key: str
    name: str
    manager: str
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points_for: float = 0.0
    points_against: float = 0.0
    standing: int = 0


@dataclass
class Standing:
    teams: list[Team]


@dataclass
class Matchup:
    week: int
    team_key: str
    opponent_key: str
    team_projected: float = 0.0
    opponent_projected: float = 0.0
    team_score: float = 0.0
    opponent_score: float = 0.0


@dataclass
class DayPlan:
    date: date
    lineup: list[RosterPlayer]
    adds: list[Player] = field(default_factory=list)
    drops: list[Player] = field(default_factory=list)
    projected_points: float = 0.0


@dataclass
class WeekPlan:
    days: list[DayPlan]
    transactions_used: int
    transactions_remaining: int
    total_projected_points: float
    baseline_points: float
    improvement: float


@dataclass
class WriteResult:
    success: bool
    message: str
