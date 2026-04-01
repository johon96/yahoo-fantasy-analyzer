"""yfantasy league — list, select, and view league info."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from yfantasy.client import YahooClient
from yfantasy.config import Config
from yfantasy.cli.display import print_standings

console = Console()

league_app = typer.Typer(help="League management commands.")


@league_app.command("list")
def list_leagues() -> None:
    """List all your Yahoo Fantasy leagues."""
    config = Config()
    client = YahooClient(config)
    leagues = client.get_leagues()

    if not leagues:
        console.print("No leagues found.")
        return

    default_key = config.get("defaults", "league_key")
    for lg in leagues:
        key = lg.get("league_key", "")
        name = lg.get("name", "Unknown")
        season = lg.get("season", "")
        marker = " [green](active)[/]" if key == default_key else ""
        console.print(f"  {key} — {name} ({season}){marker}")


@league_app.command("select")
def select_league() -> None:
    """Interactively select a default league."""
    config = Config()
    client = YahooClient(config)
    leagues = client.get_leagues()

    if not leagues:
        console.print("No leagues found.")
        return

    for i, lg in enumerate(leagues, 1):
        console.print(f"  {i}. {lg.get('name')} ({lg.get('league_key')})")

    choice = typer.prompt("Select league", type=int, default=1)
    idx = max(0, min(choice - 1, len(leagues) - 1))
    selected = leagues[idx]
    league_key = selected.get("league_key", "")
    config.set("defaults", "league_key", league_key)
    config.save()
    console.print(f"[green]Default league:[/] {selected.get('name')} ({league_key})")


@league_app.command("info")
def league_info(league: Optional[str] = typer.Option(None, "--league", "-l")) -> None:
    """Show league details and standings."""
    config = Config()
    league_key = league or config.get("defaults", "league_key")
    if not league_key:
        console.print("[red]No league selected.[/] Run `yfantasy league select` first.")
        raise typer.Exit(1)

    client = YahooClient(config)
    lg = client.get_league(league_key)
    console.print(f"[bold]{lg.name}[/] ({lg.league_key})")
    console.print(f"  Sport: {lg.sport.upper()} — Season: {lg.season}")
    console.print(f"  Teams: {lg.num_teams} — Scoring: {lg.scoring_type}")
    console.print(f"  Period: {lg.scoring_period} — Week: {lg.current_week}")
    console.print(f"  Positions: {', '.join(lg.roster_positions)}\n")

    teams = client.get_standings(league_key)
    if teams:
        print_standings(teams)
