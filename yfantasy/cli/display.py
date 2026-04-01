"""Rich display helpers for yfantasy CLI."""

from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from yfantasy.models import (
    DayPlan,
    League,
    Matchup,
    Player,
    Roster,
    RosterPlayer,
    Team,
    WeekPlan,
    WriteResult,
)

console = Console()


def print_roster(roster: Roster, league: Optional[League] = None) -> None:
    table = Table(title="Roster", show_lines=True)
    table.add_column("Pos", style="bold cyan", width=5)
    table.add_column("Player", min_width=20)
    table.add_column("Team", width=5)
    table.add_column("Status", width=8)
    table.add_column("Eligible", width=15)

    for rp in sorted(roster.players, key=lambda r: (not r.is_starting, r.selected_position)):
        status_style = "green" if rp.player.status == "healthy" else "red"
        table.add_row(
            rp.selected_position,
            rp.player.name,
            rp.player.team,
            Text(rp.player.status, style=status_style),
            ", ".join(rp.player.positions),
        )
    console.print(table)


def print_standings(teams: list[Team]) -> None:
    table = Table(title="Standings")
    table.add_column("#", width=3)
    table.add_column("Team", min_width=20)
    table.add_column("Manager", min_width=12)
    table.add_column("W", width=4, justify="right")
    table.add_column("L", width=4, justify="right")
    table.add_column("T", width=4, justify="right")
    table.add_column("PF", width=8, justify="right")

    for t in sorted(teams, key=lambda x: x.standing):
        table.add_row(
            str(t.standing),
            t.name,
            t.manager,
            str(t.wins),
            str(t.losses),
            str(t.ties),
            f"{t.points_for:.1f}",
        )
    console.print(table)


def print_free_agents(players: list[Player], title: str = "Free Agents") -> None:
    table = Table(title=title)
    table.add_column("#", width=3)
    table.add_column("Player", min_width=20)
    table.add_column("Team", width=5)
    table.add_column("Pos", width=10)
    table.add_column("% Owned", width=8, justify="right")
    table.add_column("Status", width=8)

    for i, p in enumerate(players, 1):
        status_style = "green" if p.status == "healthy" else "red"
        table.add_row(
            str(i),
            p.name,
            p.team,
            ", ".join(p.positions),
            f"{p.percent_owned:.0f}%",
            Text(p.status, style=status_style),
        )
    console.print(table)


def print_week_plan(plan: WeekPlan) -> None:
    console.print(
        Panel(
            f"Projected: [bold green]{plan.total_projected_points:.1f}[/] pts "
            f"(baseline {plan.baseline_points:.1f}, "
            f"[bold green]+{plan.improvement:.1f}[/] improvement)\n"
            f"Transactions: {plan.transactions_used} used, "
            f"{plan.transactions_remaining} remaining",
            title="Week Optimization Plan",
        )
    )

    for day in plan.days:
        table = Table(title=day.date.strftime("%a %b %d"), show_lines=False)
        table.add_column("Pos", width=5)
        table.add_column("Player", min_width=20)

        for rp in day.lineup:
            if rp.is_starting:
                table.add_row(rp.selected_position, rp.player.name)

        if day.adds or day.drops:
            table.add_section()
            for p in day.adds:
                table.add_row("[green]+ADD[/]", f"[green]{p.name}[/]")
            for p in day.drops:
                table.add_row("[red]-DROP[/]", f"[red]{p.name}[/]")

        console.print(table)
        console.print(f"  Projected: {day.projected_points:.1f} pts\n")


def print_write_result(result: WriteResult) -> None:
    if result.success:
        console.print(f"[green]Success:[/] {result.message}")
    else:
        console.print(f"[red]Failed:[/] {result.message}")


def confirm(message: str, auto: bool = False) -> bool:
    if auto:
        return True
    return console.input(f"{message} [y/N] ").strip().lower() in ("y", "yes")
