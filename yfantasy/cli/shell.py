"""yfantasy shell — interactive REPL mode."""

from __future__ import annotations

import shlex
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from rich.console import Console

from yfantasy.cli.app import app
from yfantasy.config import Config

console = Console()

_COMMANDS = [
    "dashboard", "roster", "lineup", "optimize", "waiver", "trade",
    "league", "version", "help", "quit", "exit",
    "league list", "league select", "league info",
    "waiver scan", "waiver add",
    "lineup set", "lineup auto",
    "trade analyze", "trade suggest",
    "optimize",
]


def shell_command() -> None:
    """Start an interactive yfantasy session."""
    config = Config()
    history_path = config.config_dir / "history"
    session: PromptSession = PromptSession(
        history=FileHistory(str(history_path)),
        completer=WordCompleter(_COMMANDS, sentence=True),
    )

    league_name = config.get("defaults", "league_key") or "no league"
    console.print("[bold]yfantasy shell[/] — type commands without the `yfantasy` prefix. `quit` to exit.\n")

    while True:
        try:
            text = session.prompt(f"yfantasy ({league_name}) > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not text:
            continue
        if text in ("quit", "exit"):
            break
        if text == "help":
            console.print("Commands: " + ", ".join(sorted(set(c.split()[0] for c in _COMMANDS if c not in ("quit", "exit", "help")))))
            continue

        try:
            args = shlex.split(text)
            app(args, standalone_mode=False)
        except SystemExit:
            pass
        except Exception as e:
            console.print(f"[red]Error:[/] {e}")

        # Refresh league name in prompt
        config_fresh = Config()
        league_name = config_fresh.get("defaults", "league_key") or "no league"
