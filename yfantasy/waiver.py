"""Waiver wire assistant — rank free agents and build claims."""

from __future__ import annotations

from yfantasy.models import League, Player
from yfantasy.scoring import ScoringEngine


class WaiverAssistant:
    """Rank and evaluate free agents for waiver claims."""

    def __init__(self, league: League, engine: ScoringEngine):
        self.league = league
        self.engine = engine

    def rank_free_agents(
        self, free_agents: list[Player], position: str | None = None
    ) -> list[tuple[Player, float]]:
        """Rank free agents by projected value. Returns (player, value) pairs."""
        filtered = free_agents
        if position:
            filtered = [p for p in free_agents if position in p.positions]

        ranked = [
            (p, self.engine.projected_value(p))
            for p in filtered
        ]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    def suggest_drops(
        self, roster_players: list[Player],
    ) -> list[tuple[Player, float]]:
        """Rank roster players by value ascending (worst first) for drop candidates."""
        ranked = [
            (p, self.engine.projected_value(p))
            for p in roster_players
        ]
        ranked.sort(key=lambda x: x[1])
        return ranked
