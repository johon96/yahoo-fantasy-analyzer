"""yfantasy trade — analyze trades and find opportunities."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from yfantasy.cli.display import confirm, print_write_result
from yfantasy.client import YahooClient
from yfantasy.config import Config
from yfantasy.scoring import ScoringEngine
from yfantasy.trade import TradeAnalyzer
from yfantasy.writer import YahooWriter

console = Console()

trade_app = typer.Typer(help="Trade analysis and proposals.")


@trade_app.command("analyze")
def analyze(
    give_name: str = typer.Argument(..., help="Player you'd give"),
    for_: str = typer.Argument("for", hidden=True),
    get_name: str = typer.Argument(..., help="Player you'd get"),
    league: Optional[str] = typer.Option(None, "--league", "-l"),
) -> None:
    """Analyze a trade: yfantasy trade analyze 'Player A' for 'Player B'."""
    config = Config()
    league_key = league or config.get("defaults", "league_key")
    if not league_key:
        console.print("[red]No league selected.[/]")
        raise typer.Exit(1)

    client = YahooClient(config)
    lg = client.get_league(league_key)
    engine = ScoringEngine(lg)
    analyzer = TradeAnalyzer(lg, engine)

    from difflib import get_close_matches

    standings = client.get_standings(league_key)
    all_players: dict[str, object] = {}

    for team in standings:
        try:
            roster = client.get_roster(team.team_key)
            for rp in roster.players:
                all_players[rp.player.name] = rp.player
        except Exception:
            pass

    give_matches = get_close_matches(give_name, all_players.keys(), n=1, cutoff=0.4)
    get_matches = get_close_matches(get_name, all_players.keys(), n=1, cutoff=0.4)

    if not give_matches:
        console.print(f"[red]Player not found:[/] {give_name}")
        raise typer.Exit(1)
    if not get_matches:
        console.print(f"[red]Player not found:[/] {get_name}")
        raise typer.Exit(1)

    give_player = all_players[give_matches[0]]
    get_player = all_players[get_matches[0]]

    evaluation = analyzer.evaluate([give_player], [get_player])

    color = {"win": "green", "lose": "red", "fair": "yellow"}[evaluation.verdict]
    console.print(Panel(
        f"Give: [bold]{give_matches[0]}[/] (value: {evaluation.give_value:.1f})\n"
        f"Get:  [bold]{get_matches[0]}[/] (value: {evaluation.get_value:.1f})\n"
        f"Net:  [{color}]{evaluation.net_value:+.1f}[/{color}]\n"
        f"Verdict: [{color}]{evaluation.verdict.upper()}[/{color}]",
        title="Trade Analysis",
    ))


@trade_app.command("suggest")
def suggest(
    league: Optional[str] = typer.Option(None, "--league", "-l"),
) -> None:
    """Find sell-high and buy-low candidates across the league."""
    config = Config()
    league_key = league or config.get("defaults", "league_key")
    if not league_key:
        console.print("[red]No league selected.[/]")
        raise typer.Exit(1)

    client = YahooClient(config)
    lg = client.get_league(league_key)
    engine = ScoringEngine(lg)
    analyzer = TradeAnalyzer(lg, engine)

    team_key = client.get_my_team_key(league_key)
    if not team_key:
        console.print("[red]Could not find your team.[/]")
        raise typer.Exit(1)

    roster = client.get_roster(team_key)
    my_players = [rp.player for rp in roster.players]

    sell_high = analyzer.find_sell_high(my_players)
    buy_low = analyzer.find_buy_low(my_players)

    if sell_high:
        table = Table(title="Sell High (overperforming)")
        table.add_column("Player", min_width=20)
        table.add_column("Surplus", width=10, justify="right")
        for p, surplus in sell_high[:5]:
            table.add_row(p.name, f"+{surplus:.1f}")
        console.print(table)

    if buy_low:
        table = Table(title="Buy Low (underperforming)")
        table.add_column("Player", min_width=20)
        table.add_column("Deficit", width=10, justify="right")
        for p, deficit in buy_low[:5]:
            table.add_row(p.name, f"-{deficit:.1f}")
        console.print(table)

    if not sell_high and not buy_low:
        console.print("No clear sell-high or buy-low candidates found.")
