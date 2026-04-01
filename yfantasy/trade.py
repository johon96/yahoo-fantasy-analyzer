"""Trade analysis — evaluate and suggest trades."""

from __future__ import annotations

from dataclasses import dataclass

from yfantasy.models import League, Player
from yfantasy.scoring import ScoringEngine


@dataclass
class TradeEvaluation:
    give_players: list[Player]
    get_players: list[Player]
    give_value: float
    get_value: float
    net_value: float
    verdict: str  # "win", "lose", "fair"


class TradeAnalyzer:
    """Evaluate and suggest trades."""

    def __init__(self, league: League, engine: ScoringEngine):
        self.league = league
        self.engine = engine

    def evaluate(
        self, give: list[Player], get: list[Player]
    ) -> TradeEvaluation:
        """Evaluate a trade proposal."""
        give_val = sum(self.engine.projected_value(p) for p in give)
        get_val = sum(self.engine.projected_value(p) for p in get)
        net = get_val - give_val

        if net > 5:
            verdict = "win"
        elif net < -5:
            verdict = "lose"
        else:
            verdict = "fair"

        return TradeEvaluation(
            give_players=give,
            get_players=get,
            give_value=round(give_val, 2),
            get_value=round(get_val, 2),
            net_value=round(net, 2),
            verdict=verdict,
        )

    def find_sell_high(self, players: list[Player]) -> list[tuple[Player, float]]:
        """Find players performing above projections (sell-high candidates)."""
        candidates = []
        for p in players:
            actual = self.engine.player_value(p)
            projected = self.engine.projected_value(p)
            if projected > 0 and actual > projected * 1.15:
                candidates.append((p, actual - projected))
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates

    def find_buy_low(self, players: list[Player]) -> list[tuple[Player, float]]:
        """Find players performing below projections (buy-low candidates)."""
        candidates = []
        for p in players:
            actual = self.engine.player_value(p)
            projected = self.engine.projected_value(p)
            if projected > 0 and actual < projected * 0.85:
                candidates.append((p, projected - actual))
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates
