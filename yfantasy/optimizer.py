"""Week-level lineup and roster optimizer for yfantasy."""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from yfantasy.models import (
    DayPlan,
    League,
    Player,
    Roster,
    RosterPlayer,
    WeekPlan,
    _INACTIVE_POSITIONS,
)
from yfantasy.scoring import ScoringEngine

logger = logging.getLogger(__name__)


class Optimizer:
    """Optimizes lineups and roster moves across a week."""

    def __init__(self, league: League, engine: ScoringEngine):
        self.league = league
        self.engine = engine

    def optimize_lineup(self, roster: Roster) -> WeekPlan:
        """Optimize the lineup for a single day/week (no streaming)."""
        if not roster.players:
            return WeekPlan(
                days=[], transactions_used=0, transactions_remaining=0,
                total_projected_points=0.0, baseline_points=0.0, improvement=0.0,
            )

        baseline = self._score_current_lineup(roster)
        optimal = self._assign_optimal_positions(roster.players)
        optimal_score = sum(
            self.engine.projected_value(rp.player)
            for rp in optimal if rp.is_starting
        )

        day_plan = DayPlan(
            date=date.today(),
            lineup=optimal,
            projected_points=optimal_score,
        )

        return WeekPlan(
            days=[day_plan],
            transactions_used=0,
            transactions_remaining=0,
            total_projected_points=optimal_score,
            baseline_points=baseline,
            improvement=round(optimal_score - baseline, 2),
        )

    def optimize_with_streaming(
        self,
        roster: Roster,
        free_agents: list[Player],
        schedule: dict[date, set[str]],
        remaining_adds: int,
        days: list[date],
    ) -> WeekPlan:
        """Week-level optimization with streaming (add/drops across days)."""
        current_players = {rp.player.player_key: rp.player for rp in roster.players}
        baseline = sum(
            self.engine.projected_value(rp.player)
            for rp in roster.players if rp.is_starting
        ) * len(days)

        day_plans: list[DayPlan] = []
        adds_used = 0

        for d in days:
            playing_today = schedule.get(d, set())
            best_add: Optional[Player] = None
            best_drop: Optional[Player] = None
            best_gain = 0.0

            if adds_used < remaining_adds and free_agents:
                bench_players = sorted(
                    [p for p in current_players.values()],
                    key=lambda p: self.engine.projected_value(p),
                )
                if bench_players:
                    worst = bench_players[0]
                    worst_val = self.engine.projected_value(worst)

                    for fa in free_agents:
                        if fa.player_key in current_players:
                            continue
                        if fa.player_key not in playing_today:
                            continue
                        fa_val = self.engine.projected_value(fa)
                        gain = fa_val - worst_val
                        if gain > best_gain:
                            best_gain = gain
                            best_add = fa
                            best_drop = worst

            adds_today: list[Player] = []
            drops_today: list[Player] = []

            if best_add and best_drop and best_gain > 0:
                adds_today.append(best_add)
                drops_today.append(best_drop)
                del current_players[best_drop.player_key]
                current_players[best_add.player_key] = best_add
                free_agents = [fa for fa in free_agents if fa.player_key != best_add.player_key]
                adds_used += 1

            today_roster_players = [
                RosterPlayer(p, "BN", False) for p in current_players.values()
            ]
            optimal = self._assign_optimal_positions(today_roster_players)
            day_score = sum(
                self.engine.projected_value(rp.player)
                for rp in optimal if rp.is_starting
            )

            day_plans.append(DayPlan(
                date=d,
                lineup=optimal,
                adds=adds_today,
                drops=drops_today,
                projected_points=day_score,
            ))

        total = sum(dp.projected_points for dp in day_plans)
        return WeekPlan(
            days=day_plans,
            transactions_used=adds_used,
            transactions_remaining=remaining_adds - adds_used,
            total_projected_points=round(total, 2),
            baseline_points=round(baseline, 2),
            improvement=round(total - baseline, 2),
        )

    # -- internals -----------------------------------------------------------

    def _score_current_lineup(self, roster: Roster) -> float:
        return sum(
            self.engine.projected_value(rp.player)
            for rp in roster.players if rp.is_starting
        )

    def _assign_optimal_positions(
        self, players: list[RosterPlayer]
    ) -> list[RosterPlayer]:
        """Greedy assignment: highest-value player gets first pick of slots."""
        active_slots = list(self.league.active_positions)
        bench_slots = [
            p for p in self.league.roster_positions if p in _INACTIVE_POSITIONS
        ]

        ranked = sorted(
            players,
            key=lambda rp: self.engine.projected_value(rp.player),
            reverse=True,
        )

        assigned: list[RosterPlayer] = []
        remaining_slots = list(active_slots)

        for rp in ranked:
            placed = False
            for i, slot in enumerate(remaining_slots):
                if slot in rp.player.positions:
                    assigned.append(RosterPlayer(rp.player, slot, True))
                    remaining_slots.pop(i)
                    placed = True
                    break
            if not placed:
                for i, slot in enumerate(remaining_slots):
                    if slot in ("Util", "UTIL", "W/R/T", "FLEX", "F"):
                        assigned.append(RosterPlayer(rp.player, slot, True))
                        remaining_slots.pop(i)
                        placed = True
                        break
            if not placed:
                assigned.append(RosterPlayer(rp.player, "BN", False))

        return assigned
