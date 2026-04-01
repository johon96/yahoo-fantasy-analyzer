"""yfantasy optimize — lineup and roster optimization."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import typer
from rich.console import Console

from yfantasy.cli.display import confirm, print_week_plan, print_write_result
from yfantasy.client import YahooClient
from yfantasy.config import Config
from yfantasy.optimizer import Optimizer
from yfantasy.scoring import ScoringEngine
from yfantasy.writer import YahooWriter

console = Console()

optimize_app = typer.Typer(help="Optimize your lineup and roster.")


@optimize_app.callback(invoke_without_command=True)
def optimize_command(
    ctx: typer.Context = None,
    league: Optional[str] = typer.Option(None, "--league", "-l"),
    days: int = typer.Option(7, "--days", "-d", help="Days to plan ahead"),
    no_stream: bool = typer.Option(False, "--no-stream", help="Lineup only, no add/drops"),
    budget: Optional[int] = typer.Option(None, "--budget", "-b", help="Override transaction budget"),
    execute_today: bool = typer.Option(False, "--execute-today", help="Apply only today's moves"),
    auto: bool = typer.Option(False, "--auto", help="Skip confirmations"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Force fresh data"),
) -> None:
    """Generate an optimal week plan for your roster."""
    if ctx and ctx.invoked_subcommand is not None:
        return

    config = Config()
    league_key = league or config.get("defaults", "league_key")
    if not league_key:
        console.print("[red]No league selected.[/] Run `yfantasy league select`.")
        raise typer.Exit(1)

    client = YahooClient(config, use_cache=not no_cache)
    lg = client.get_league(league_key)
    engine = ScoringEngine(lg)

    team_key = client.get_my_team_key(league_key)
    if not team_key:
        console.print("[red]Could not find your team.[/]")
        raise typer.Exit(1)

    roster = client.get_roster(team_key)

    optimizer = Optimizer(lg, engine)

    if no_stream or not lg.is_daily:
        plan = optimizer.optimize_lineup(roster)
    else:
        console.print(f"Optimizing for the next {days} days...")
        today = date.today()
        plan_days = [today + timedelta(days=i) for i in range(days)]

        schedule: dict[date, set[str]] = {}
        for d in plan_days:
            day_roster = client.get_roster(team_key, date=d.isoformat())
            playing = {
                rp.player.player_key
                for rp in day_roster.players
            }
            schedule[d] = playing

        free_agents = client.get_free_agents(league_key, count=50)
        remaining_adds = budget if budget is not None else 7

        plan = optimizer.optimize_with_streaming(
            roster, free_agents, schedule, remaining_adds, plan_days,
        )

    print_week_plan(plan)

    if plan.improvement <= 0:
        console.print("[green]Your lineup is already optimal![/]")
        return

    if execute_today and plan.days:
        day = plan.days[0]
        if day.adds or day.drops:
            console.print(f"\n[bold]Executing today's moves ({day.date}):[/]")
            if confirm("Apply?", auto=auto):
                writer = YahooWriter(config)
                for add_p, drop_p in zip(day.adds, day.drops):
                    result = writer.add_player(
                        league_key, add_p.player_key, drop_player_key=drop_p.player_key
                    )
                    print_write_result(result)

        moves = [
            (rp.player.player_key, rp.selected_position)
            for rp in day.lineup if rp.is_starting
        ]
        if moves and confirm("Set today's lineup?", auto=auto):
            writer = YahooWriter(config)
            result = writer.set_lineup(team_key, moves)
            print_write_result(result)
