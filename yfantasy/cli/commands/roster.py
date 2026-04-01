"""yfantasy roster / lineup — view and manage your roster."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from yfantasy.client import YahooClient
from yfantasy.config import Config
from yfantasy.cli.display import print_roster, print_write_result, confirm
from yfantasy.writer import YahooWriter

console = Console()

roster_app = typer.Typer(help="View and manage your roster.")


@roster_app.callback(invoke_without_command=True)
def show_roster(
    ctx: typer.Context,
    league: Optional[str] = typer.Option(None, "--league", "-l"),
    week: Optional[int] = typer.Option(None, "--week", "-w"),
    date: Optional[str] = typer.Option(None, "--date", "-d"),
) -> None:
    """Show current roster (default action)."""
    if ctx.invoked_subcommand is not None:
        return
    config = Config()
    league_key = league or config.get("defaults", "league_key")
    if not league_key:
        console.print("[red]No league selected.[/] Run `yfantasy league select`.")
        raise typer.Exit(1)

    client = YahooClient(config)
    team_key = client.get_my_team_key(league_key)
    if not team_key:
        console.print("[red]Could not find your team.[/]")
        raise typer.Exit(1)

    lg = client.get_league(league_key)
    roster = client.get_roster(team_key, week=week, date=date)
    print_roster(roster, lg)


lineup_app = typer.Typer(help="View and set your lineup.")


@lineup_app.callback(invoke_without_command=True)
def show_lineup(
    ctx: typer.Context,
    league: Optional[str] = typer.Option(None, "--league", "-l"),
    week: Optional[int] = typer.Option(None, "--week", "-w"),
    date: Optional[str] = typer.Option(None, "--date", "-d"),
) -> None:
    """Show current lineup (default action)."""
    if ctx.invoked_subcommand is not None:
        return
    show_roster(ctx, league=league, week=week, date=date)


@lineup_app.command("set")
def set_lineup(
    player: str = typer.Argument(..., help="Player name"),
    position: str = typer.Argument(..., help="Position to move to"),
    league: Optional[str] = typer.Option(None, "--league", "-l"),
    auto: bool = typer.Option(False, "--auto", help="Skip confirmation"),
) -> None:
    """Move a player to a specific position."""
    config = Config()
    league_key = league or config.get("defaults", "league_key")
    if not league_key:
        console.print("[red]No league selected.[/]")
        raise typer.Exit(1)

    client = YahooClient(config)
    team_key = client.get_my_team_key(league_key)
    if not team_key:
        console.print("[red]Could not find your team.[/]")
        raise typer.Exit(1)

    roster = client.get_roster(team_key)

    from difflib import get_close_matches

    names = {rp.player.name: rp for rp in roster.players}
    matches = get_close_matches(player, names.keys(), n=1, cutoff=0.4)
    if not matches:
        console.print(f"[red]Player not found:[/] {player}")
        console.print("Available players:")
        for rp in roster.players:
            console.print(f"  {rp.player.name} ({rp.selected_position})")
        raise typer.Exit(1)

    matched_name = matches[0]
    rp = names[matched_name]
    console.print(f"Move [bold]{rp.player.name}[/] from {rp.selected_position} to {position}?")

    if confirm("Proceed?", auto=auto):
        writer = YahooWriter(config)
        result = writer.set_lineup(team_key, [(rp.player.player_key, position)])
        print_write_result(result)


@lineup_app.command("auto")
def auto_lineup(
    league: Optional[str] = typer.Option(None, "--league", "-l"),
    auto: bool = typer.Option(False, "--auto", help="Skip confirmation"),
) -> None:
    """Automatically set optimal lineup (alias for optimize lineup)."""
    from yfantasy.cli.commands.optimize import optimize_command
    optimize_command(league=league, no_stream=True, auto=auto)
