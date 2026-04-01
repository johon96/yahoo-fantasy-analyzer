"""Scoring engine — calculates fantasy value from stats using league-specific rules."""

from __future__ import annotations

import math
from typing import Optional

from yfantasy.models import League, Player, StatCategory


class ScoringEngine:
    """Calculate fantasy point values using league scoring settings."""

    def __init__(self, league: League):
        self.league = league
        self._scoring_cats = [c for c in league.stat_categories if c.is_scoring]
        self._pool: list[Player] = []
        self._pool_means: dict[str, float] = {}
        self._pool_stds: dict[str, float] = {}

    def set_player_pool(self, players: list[Player]) -> None:
        """Set the player pool for z-score / replacement-level calculations."""
        self._pool = players
        self._compute_pool_stats()

    def player_value(self, player: Player) -> float:
        """Calculate total fantasy value from actual stats."""
        return self._value_from_stats(player.stats)

    def projected_value(self, player: Player) -> float:
        """Calculate total fantasy value from projected stats, falling back to actual."""
        stats = player.projected_stats if player.projected_stats else player.stats
        return self._value_from_stats(stats)

    def value_above_replacement(self, player: Player, position: str) -> float:
        """How much better than a replacement-level player at this position."""
        player_val = self.projected_value(player)
        replacement_val = self._replacement_value(position)
        return player_val - replacement_val

    # -- internals -----------------------------------------------------------

    def _value_from_stats(self, stats: dict[str, float]) -> float:
        if self.league.scoring_type in ("point", "points"):
            return self._points_value(stats)
        else:
            return self._category_value(stats)

    def _points_value(self, stats: dict[str, float]) -> float:
        total = 0.0
        for cat in self._scoring_cats:
            if cat.value is not None:
                total += stats.get(cat.stat_id, 0.0) * cat.value
        return round(total, 2)

    def _category_value(self, stats: dict[str, float]) -> float:
        """Z-score based value for category leagues."""
        if not self._pool_stds:
            return sum(stats.get(c.stat_id, 0.0) for c in self._scoring_cats)

        total_z = 0.0
        for cat in self._scoring_cats:
            val = stats.get(cat.stat_id, 0.0)
            mean = self._pool_means.get(cat.stat_id, 0.0)
            std = self._pool_stds.get(cat.stat_id, 1.0)
            if std > 0:
                z = (val - mean) / std
                if cat.sort_order == "0":
                    z = -z
                total_z += z
        return round(total_z, 4)

    def _replacement_value(self, position: str) -> float:
        """Estimate replacement-level value for a position."""
        eligible = [p for p in self._pool if position in p.positions]
        if not eligible:
            return 0.0

        values = sorted(
            [self.projected_value(p) for p in eligible], reverse=True
        )
        slots = self.league.roster_positions.count(position) * self.league.num_teams
        idx = min(slots, len(values) - 1)
        return values[idx] if idx < len(values) else 0.0

    def _compute_pool_stats(self) -> None:
        """Pre-compute mean and std for each stat category across the player pool."""
        for cat in self._scoring_cats:
            vals = [p.stats.get(cat.stat_id, 0.0) for p in self._pool if p.stats]
            if not vals:
                self._pool_means[cat.stat_id] = 0.0
                self._pool_stds[cat.stat_id] = 1.0
                continue
            mean = sum(vals) / len(vals)
            variance = sum((v - mean) ** 2 for v in vals) / max(len(vals) - 1, 1)
            self._pool_means[cat.stat_id] = mean
            self._pool_stds[cat.stat_id] = math.sqrt(variance) if variance > 0 else 1.0
