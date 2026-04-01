"""yfantasy dashboard — weekly overview."""

from __future__ import annotations

from typing import Optional

import typer
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from yfantasy.cli.display import print_standings
from yfantasy.client import YahooClient
from yfantasy.config import Config
from yfantasy.dashboard import build_dashboard
from yfantasy.scoring import ScoringEngine
from yfantasy.waiver import WaiverAssistant

console = Console()


def dashboard_command(
    week: Optional[int] = typer.Option(None, "--week", "-w"),
    league: Optional[str] = typer.Option(None, "--league", "-l"),
    no_cache: bool = typer.Option(False, "--no-cache"),
) -> None:
    """Show weekly dashboard — standings, matchup, alerts, waiver gems."""
    config = Config()
    league_key = league or config.get("defaults", "league_key")
    if not league_key:
        console.print("[red]No league selected.[/] Run `yfantasy league select`.")
        raise typer.Exit(1)

    client = YahooClient(config, use_cache=not no_cache)
    lg = client.get_league(league_key)
    engine = ScoringEngine(lg)

    team_key = client.get_my_team_key(league_key)
    current_week = week or lg.current_week

    standings = client.get_standings(league_key)
    roster = client.get_roster(team_key) if team_key else None

    matchups = client.get_scoreboard(league_key, current_week)
    my_matchup = next((m for m in matchups if team_key and team_key in (m.team_key, m.opponent_key)), None)

    assistant = WaiverAssistant(lg, engine)
    free_agents = client.get_free_agents(league_key, count=10)
    ranked_fa = assistant.rank_free_agents(free_agents)

    from yfantasy.models import Roster as RosterModel
    data = build_dashboard(
        standings=standings,
        my_team_key=team_key or "",
        matchup=my_matchup,
        roster=roster if roster else RosterModel(team_key="", players=[]),
        top_fa=ranked_fa,
    )

    console.print(f"\n[bold]{lg.name}[/] — Week {current_week}\n")

    print_standings(data.standings)

    if data.matchup:
        opp_name = next(
            (t.name for t in standings if t.team_key == data.matchup.opponent_key),
            "Unknown",
        )
        my_name = data.my_team.name if data.my_team else "You"
        console.print(Panel(
            f"{my_name} vs {opp_name}",
            title="This Week's Matchup",
        ))

    if data.roster_alerts:
        alerts = "\n".join(f"  [yellow]![/] {a}" for a in data.roster_alerts)
        console.print(Panel(alerts, title="Roster Alerts"))

    if data.top_free_agents:
        table = Table(title="Waiver Wire Gems")
        table.add_column("Player", min_width=18)
        table.add_column("Pos", width=8)
        table.add_column("Value", width=8, justify="right")
        for p, val in data.top_free_agents:
            table.add_row(p.name, ", ".join(p.positions), f"{val:.1f}")
        console.print(table)
