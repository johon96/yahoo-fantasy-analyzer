"""yfantasy CLI entry point."""

from __future__ import annotations

import logging
from typing import Optional

import typer

from yfantasy import __version__

app = typer.Typer(
    name="yfantasy",
    help="Yahoo Fantasy Sports CLI — roster optimizer, waiver wire, trade analyzer",
    no_args_is_help=True,
)


def _setup_logging(verbose: bool = False, debug: bool = False) -> None:
    level = logging.WARNING
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )


@app.callback()
def main_callback(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show info-level logs"),
    debug: bool = typer.Option(False, "--debug", help="Show debug-level logs"),
) -> None:
    _setup_logging(verbose=verbose, debug=debug)


@app.command()
def version() -> None:
    """Show version."""
    typer.echo(f"yfantasy {__version__}")


@app.command()
def init() -> None:
    """Set up Yahoo API credentials and authenticate."""
    from yfantasy.cli.commands.init_cmd import init_command

    init_command()


@app.command()
def shell() -> None:
    """Start interactive shell mode."""
    from yfantasy.cli.shell import shell_command

    shell_command()


# Register sub-command groups
from yfantasy.cli.commands.league import league_app
from yfantasy.cli.commands.roster import roster_app, lineup_app
from yfantasy.cli.commands.optimize import optimize_app
from yfantasy.cli.commands.waiver import waiver_app
from yfantasy.cli.commands.trade import trade_app

app.add_typer(league_app, name="league")
app.add_typer(roster_app, name="roster")
app.add_typer(lineup_app, name="lineup")
app.add_typer(optimize_app, name="optimize")
app.add_typer(waiver_app, name="waiver")
app.add_typer(trade_app, name="trade")

from yfantasy.cli.commands.dashboard import dashboard_command
app.command(name="dashboard")(dashboard_command)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
