"""Dashboard data assembly for yfantasy."""

from __future__ import annotations

from dataclasses import dataclass, field

from yfantasy.models import Matchup, Player, Roster, Team


@dataclass
class DashboardData:
    standings: list[Team]
    my_team: Team | None
    matchup: Matchup | None
    roster_alerts: list[str]
    top_free_agents: list[tuple[Player, float]]


def build_dashboard(
    standings: list[Team],
    my_team_key: str,
    matchup: Matchup | None,
    roster: Roster,
    top_fa: list[tuple[Player, float]],
) -> DashboardData:
    my_team = next((t for t in standings if t.team_key == my_team_key), None)

    alerts: list[str] = []
    for rp in roster.players:
        if rp.is_starting and rp.player.status not in ("healthy", ""):
            alerts.append(f"{rp.player.name} is {rp.player.status} — consider benching")

    return DashboardData(
        standings=standings,
        my_team=my_team,
        matchup=matchup,
        roster_alerts=alerts,
        top_free_agents=top_fa[:5],
    )
