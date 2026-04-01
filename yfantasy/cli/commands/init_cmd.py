"""yfantasy init — first-time setup and OAuth flow."""

from __future__ import annotations

import typer
from rich.console import Console

from yfantasy.auth import YahooAuth
from yfantasy.config import Config

console = Console()


def init_command() -> None:
    """Set up Yahoo API credentials and authenticate."""
    config = Config()

    console.print("[bold]yfantasy init[/] — first-time setup\n")

    if config.has_credentials():
        console.print(f"Existing credentials found (client_id: {config.get('auth', 'client_id')[:8]}...)")
        if not typer.confirm("Re-enter credentials?", default=False):
            pass
        else:
            _prompt_credentials(config)
    else:
        console.print("Register an app at https://developer.yahoo.com/apps/ to get credentials.")
        console.print("Required: Fantasy Sports read/write scope.\n")
        _prompt_credentials(config)

    console.print("\n[bold]Authenticating with Yahoo...[/]")
    auth = YahooAuth(config)
    try:
        auth.run_oauth_flow()
        console.print("[green]Authenticated successfully![/]\n")
    except Exception as e:
        console.print(f"[red]Authentication failed:[/] {e}")
        raise typer.Exit(1)

    from yfantasy.client import YahooClient

    client = YahooClient(config, use_cache=False)
    leagues = client.get_leagues()

    if not leagues:
        console.print("No leagues found. You may need to join a league on Yahoo Fantasy.")
        return

    console.print("[bold]Your leagues:[/]")
    for i, lg in enumerate(leagues, 1):
        name = lg.get("name", "Unknown")
        key = lg.get("league_key", "")
        season = lg.get("season", "")
        console.print(f"  {i}. {name} ({key}) — {season}")

    choice = typer.prompt(
        "\nSelect default league (number)", type=int, default=1
    )
    idx = max(0, min(choice - 1, len(leagues) - 1))
    selected = leagues[idx]
    league_key = selected.get("league_key", "")
    config.set("defaults", "league_key", league_key)
    config.save()

    console.print(f"\n[green]Default league set to:[/] {selected.get('name')} ({league_key})")
    console.print("Run [bold]yfantasy dashboard[/] to get started!")


def _prompt_credentials(config: Config) -> None:
    client_id = typer.prompt("Yahoo Client ID")
    client_secret = typer.prompt("Yahoo Client Secret", hide_input=True)
    config.set("auth", "client_id", client_id)
    config.set("auth", "client_secret", client_secret)
    config.save()
