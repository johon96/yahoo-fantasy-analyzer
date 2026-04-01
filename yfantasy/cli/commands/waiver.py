"""yfantasy waiver — free agent scanning and waiver claims."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from yfantasy.cli.display import confirm, print_write_result
from yfantasy.client import YahooClient
from yfantasy.config import Config
from yfantasy.scoring import ScoringEngine
from yfantasy.waiver import WaiverAssistant
from yfantasy.writer import YahooWriter

console = Console()

waiver_app = typer.Typer(help="Waiver wire assistant.")


@waiver_app.command("scan")
def scan(
    position: Optional[str] = typer.Option(None, "--position", "-p", help="Filter by position"),
    count: int = typer.Option(20, "--count", "-n", help="Number of results"),
    league: Optional[str] = typer.Option(None, "--league", "-l"),
    no_cache: bool = typer.Option(False, "--no-cache"),
) -> None:
    """Scan and rank available free agents."""
    config = Config()
    league_key = league or config.get("defaults", "league_key")
    if not league_key:
        console.print("[red]No league selected.[/]")
        raise typer.Exit(1)

    client = YahooClient(config, use_cache=not no_cache)
    lg = client.get_league(league_key)
    engine = ScoringEngine(lg)
    assistant = WaiverAssistant(lg, engine)

    free_agents = client.get_free_agents(league_key, position=position, count=count)
    ranked = assistant.rank_free_agents(free_agents, position=position)

    table = Table(title=f"Top Free Agents{f' ({position})' if position else ''}")
    table.add_column("#", width=3)
    table.add_column("Player", min_width=20)
    table.add_column("Team", width=5)
    table.add_column("Pos", width=10)
    table.add_column("Value", width=8, justify="right")
    table.add_column("% Owned", width=8, justify="right")
    table.add_column("Status", width=8)

    for i, (p, val) in enumerate(ranked[:count], 1):
        table.add_row(
            str(i), p.name, p.team, ", ".join(p.positions),
            f"{val:.1f}", f"{p.percent_owned:.0f}%", p.status,
        )
    console.print(table)


@waiver_app.command("add")
def add_player(
    player_name: str = typer.Argument(..., help="Player to add"),
    drop: Optional[str] = typer.Option(None, "--drop", help="Player to drop"),
    league: Optional[str] = typer.Option(None, "--league", "-l"),
    auto: bool = typer.Option(False, "--auto"),
) -> None:
    """Add a free agent to your roster."""
    config = Config()
    league_key = league or config.get("defaults", "league_key")
    if not league_key:
        console.print("[red]No league selected.[/]")
        raise typer.Exit(1)

    client = YahooClient(config)
    lg = client.get_league(league_key)

    from difflib import get_close_matches

    free_agents = client.get_free_agents(league_key, count=100)
    fa_names = {p.name: p for p in free_agents}
    matches = get_close_matches(player_name, fa_names.keys(), n=1, cutoff=0.4)
    if not matches:
        console.print(f"[red]Player not found:[/] {player_name}")
        raise typer.Exit(1)

    add_p = fa_names[matches[0]]

    drop_key = None
    if drop:
        team_key = client.get_my_team_key(league_key)
        roster = client.get_roster(team_key)
        roster_names = {rp.player.name: rp.player for rp in roster.players}
        drop_matches = get_close_matches(drop, roster_names.keys(), n=1, cutoff=0.4)
        if drop_matches:
            drop_key = roster_names[drop_matches[0]].player_key
            console.print(f"Add [green]{add_p.name}[/], drop [red]{drop_matches[0]}[/]?")
        else:
            console.print(f"[red]Drop player not found:[/] {drop}")
            raise typer.Exit(1)
    else:
        console.print(f"Add [green]{add_p.name}[/]?")

    if confirm("Proceed?", auto=auto):
        writer = YahooWriter(config)
        result = writer.add_player(league_key, add_p.player_key, drop_player_key=drop_key)
        print_write_result(result)
