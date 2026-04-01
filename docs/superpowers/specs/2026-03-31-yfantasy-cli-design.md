# yfantasy CLI — Design Spec

## Overview

Transform the existing `yahoo-fantasy-analyzer` project from a half-built web app into a focused CLI tool called `yfantasy`. Clean rewrite of the core, keeping the proven Yahoo API and OAuth code, dropping FastAPI/SQLAlchemy/React.

Multi-sport (NHL, NBA, NFL, MLB), supports both daily and weekly scoring sports, with a week-level optimizer as the headline feature.

## Project Structure

```
yahoo-fantasy-analyzer/
├── yfantasy/
│   ├── __init__.py              # Version, package metadata
│   ├── client.py                # YahooClient — all API reads (from yahoo_api.py)
│   ├── writer.py                # YahooWriter — all API writes (PUT/POST/DELETE)
│   ├── auth.py                  # OAuth2 flow, token storage/refresh
│   ├── config.py                # ~/.yfantasy/config.toml management
│   ├── models.py                # Dataclasses: Player, Team, League, Roster, etc.
│   ├── projections.py           # ProjectionProvider interface + YahooProvider
│   ├── scoring.py               # League scoring rules → value calculations
│   ├── optimizer.py             # Lineup + roster optimization, week-level planning
│   ├── waiver.py                # Free agent ranking, waiver claim building
│   ├── trade.py                 # Trade value model, trade evaluation
│   ├── dashboard.py             # Assemble weekly dashboard data
│   └── cli/
│       ├── __init__.py
│       ├── app.py               # Typer app, top-level entry point
│       ├── commands/
│       │   ├── init.py          # `yfantasy init` — OAuth setup
│       │   ├── league.py        # `yfantasy league` — list/select/info
│       │   ├── roster.py        # `yfantasy roster` — view, lineup changes
│       │   ├── optimize.py      # `yfantasy optimize` — lineup + roster optimizer
│       │   ├── waiver.py        # `yfantasy waiver` — scan, rank, claim
│       │   ├── trade.py         # `yfantasy trade` — analyze, propose
│       │   ├── dashboard.py     # `yfantasy dashboard` — weekly overview
│       │   └── export.py        # `yfantasy export` — CSV export (from export_players.py)
│       ├── shell.py             # `yfantasy shell` — interactive REPL
│       └── display.py           # Rich tables, formatting helpers
├── tests/
│   ├── test_client.py
│   ├── test_optimizer.py
│   ├── test_scoring.py
│   └── ...
├── pyproject.toml               # Build config, entry point, deps
└── README.md
```

## Dependencies

**Keep:**
- `yfpy` — Yahoo Fantasy API wrapper
- `requests` — HTTP client for direct API calls

**Add:**
- `typer[all]` — CLI framework (includes rich, shellingham)
- `rich` — Pretty tables, progress bars, panels
- `prompt_toolkit` — Interactive shell mode (autocomplete, history)

**Drop:**
- FastAPI, uvicorn (web server)
- SQLAlchemy (ORM)
- React/TypeScript/Vite (frontend)
- SQLite database

## Auth & Config

### `yfantasy init`

1. Prompt for `client_id` and `client_secret` (from Yahoo Developer Apps)
2. Run OAuth2 browser flow — open browser, local callback server on `localhost:8765`
3. Store in `~/.yfantasy/config.toml`:

```toml
[auth]
client_id = "dj0yJm..."
client_secret = "abc123..."
access_token = "eyJ..."
refresh_token = "APr..."
token_expiry = 2026-04-01T12:00:00

[defaults]
league_key = ""
sport = ""
```

4. Show user's leagues, prompt to pick a default

### Token Lifecycle

- Check `token_expiry` before every API call
- Auto-refresh using `refresh_token` if expired
- If refresh fails: prompt to re-run `yfantasy init`

### League Selection

- `yfantasy league list` — all leagues across sports
- `yfantasy league select` — interactive picker, saves to defaults
- Most commands use default league; `--league <key>` overrides

## Core Data Models

Plain dataclasses, no ORM.

```python
@dataclass
class Player:
    player_key: str          # "465.p.6619"
    name: str
    team: str                # Real-world team abbreviation
    positions: list[str]     # ["C", "LW"] — eligible positions
    status: str              # "healthy", "IR", "DTD", "O"
    percent_owned: float
    current_fantasy_team: str | None
    stats: dict[str, float]  # stat_id → value
    projected_stats: dict[str, float] | None

@dataclass
class RosterPlayer:
    player: Player
    selected_position: str   # Current slot: "C", "LW", "BN", "IR"
    is_starting: bool

@dataclass
class Roster:
    team_key: str
    players: list[RosterPlayer]

@dataclass
class StatCategory:
    stat_id: str
    name: str                # "Goals", "Assists"
    display_name: str        # "G", "A"
    sort_order: str          # "1" = higher is better
    position_type: str       # "P" (skater/player) or "G" (goalie)
    is_only_display: bool    # Shown but doesn't count for scoring
    value: float | None      # Points per stat (points leagues)
    is_category: bool        # True if this is a H2H scoring category

@dataclass
class League:
    league_key: str
    name: str
    sport: str               # "nhl", "nfl", "nba", "mlb"
    season: str
    num_teams: int
    scoring_type: str        # "head", "roto", "points"
    scoring_period: str      # "daily" or "weekly"
    roster_positions: list[str]
    stat_categories: list[StatCategory]
    current_week: int
```

## API Layer

### `client.py` — Reads

Cleaned up from existing `yahoo_api.py`. Hybrid approach (direct REST + YFPY). Returns dataclasses instead of raw dicts. Proper `logging` module instead of print statements.

Methods: `get_leagues()`, `get_roster()`, `get_free_agents()`, `get_player_stats()`, `get_projections()`, `get_standings()`, `get_scoreboard()`, `get_matchups()`

**Schedule data for daily sports:** Yahoo's roster endpoint accepts a date parameter. When fetched for a specific date, it indicates which players have games that day (they're eligible to start). The optimizer calls `get_roster(team_key, date=d)` for each remaining day in the week to build the schedule matrix. Free agent schedules are obtained by fetching free agents per date similarly.

### `writer.py` — Writes (new)

All mutations via Yahoo API with XML payloads:

- `set_lineup(team_key, moves)` — PUT to roster resource
- `add_player(league_key, player_key, drop_player_key=None)` — POST transaction
- `propose_trade(league_key, trader_players, tradee_players, tradee_team_key)` — POST trade
- `cancel_transaction(league_key, transaction_key)` — DELETE
- `edit_waiver_priority(league_key, team_key, priority)` — PUT
- `edit_faab_bid(league_key, claim_key, amount)` — PUT

All return `success: bool` + `message: str`.

## Scoring Engine

`scoring.py` — calculates fantasy value from stats using league-specific weights.

```python
class ScoringEngine:
    def __init__(self, league: League): ...
    def player_value(self, player: Player) -> float
    def value_above_replacement(self, player: Player, position: str) -> float
    def projected_value(self, player: Player) -> float
```

Three scoring type strategies:
- **Points leagues** — `sum(stat * weight)` for each category
- **H2H category leagues** — z-score each category against league population, sum
- **Roto** — rank-based, similar to z-score approach

## Projections

`projections.py` — pluggable interface for projection data sources.

```python
class ProjectionProvider(Protocol):
    def get_projections(self, player_keys: list[str], league: League) -> dict[str, dict[str, float]]: ...
```

Ship with `YahooProjectionProvider` (uses Yahoo stats sub-resource). Interface allows adding FantasyPros, ESPN, or custom model providers later without changing consuming code.

## The Five Features

### 1. Roster Optimizer (`yfantasy optimize`)

The headline feature. Detects daily vs weekly from league settings.

**For daily sports (NHL, NBA, MLB) — week-level optimization:**

Solves a multi-day scheduling problem. Inputs: roster, free agent pool, game schedules for remaining days this week, roster slot constraints, weekly transaction limits.

Produces a `WeekPlan`:

```python
@dataclass
class DayPlan:
    date: date
    lineup: list[RosterPlayer]
    adds: list[Player]
    drops: list[Player]
    projected_points: float

@dataclass
class WeekPlan:
    days: list[DayPlan]
    transactions_used: int
    transactions_remaining: int
    total_projected_points: float
    baseline_points: float
    improvement: float
```

Algorithm: greedy with lookahead. For each remaining day, set optimal lineup from current roster. Then evaluate streaming swaps: "is there a free agent whose total remaining-week value minus the dropped player's value worth spending a transaction?" Pick highest-value swap, commit, repeat until no profitable swaps or transaction budget exhausted.

**For weekly sports (NFL):** same code path, single-day plan.

**Flags:**
- `--days 3` — only plan next 3 days
- `--no-stream` — optimize lineup only, no add/drops
- `--budget 2` — override transaction budget
- `--execute today` — apply only today's moves
- `--auto` — unattended, no confirmation

### 2. Lineup Setter (`yfantasy lineup`)

Direct roster management:
- `yfantasy lineup` — show current lineup
- `yfantasy lineup set <player> <position>` — move a specific player
- `yfantasy lineup auto` — alias for optimize lineup
- `yfantasy lineup --week 15` / `--date 2026-04-03` — view/set for future

### 3. Waiver Wire Assistant (`yfantasy waiver`)

- `yfantasy waiver scan` — rank free agents by projected value, Rich table
- `yfantasy waiver scan --position C` — filter by position
- `yfantasy waiver add <player>` — add free agent; if roster full, prompts who to drop
- `yfantasy waiver claim <player> --drop <player> --priority <n>` — submit waiver claim
- `yfantasy waiver --faab <amount>` — FAAB bid for auction waivers

### 4. Trade Analyzer (`yfantasy trade`)

- `yfantasy trade analyze <player1> for <player2>` — compare value, stats, projections, schedule
- `yfantasy trade team <team>` — show roster values, sell-high/buy-low candidates
- `yfantasy trade suggest` — scan all teams for mutually beneficial trades
- `yfantasy trade propose <their_player> for <your_player> --to <team>` — submit via API

### 5. Weekly Dashboard (`yfantasy dashboard`)

Rich panel overview: standings, this week's matchup (projected score), roster alerts (injuries, bye weeks, no game today), waiver wire gems (top available pickups).

Daily sports version shows today's games, week-so-far score, streaming opportunities.

- `yfantasy dashboard` — full overview
- `yfantasy dashboard --week 15` — future week preview

## Interactive Shell

`yfantasy shell` — REPL powered by `prompt_toolkit`.

- Tab-completion for commands, player names, team names
- Command history persisted to `~/.yfantasy/history`
- Active league shown in prompt, switchable mid-session
- Same commands as CLI subcommands — no separate codepath

## Cross-cutting Concerns

### Caching

File-based JSON cache in `~/.yfantasy/cache/`. Time-based expiry:
- Player data: 1 hour
- Roster/lineup: 5 minutes
- League settings/scoring: 24 hours
- Free agents: 30 minutes
- `--no-cache` flag on any command

### Write Safety

- Default: confirm every write operation with prompt
- `--auto` flag: execute without confirmation (for cron/scripting)
- Batch confirmation available: show all moves, approve/pick/cancel

### Error Handling

- Auth expired → auto-refresh, fallback to "run `yfantasy init`"
- Rate limited → retry with backoff, show "retrying in 5s..."
- Player not found → fuzzy match with difflib: "Did you mean...?"
- Transaction rejected → display Yahoo's error reason

### Logging

- Default: errors only
- `-v` / `--verbose`: info-level (API calls, cache hits)
- `--debug`: full request/response
- Goes to stderr (stdout stays clean for piping)

### Output Formats

- Default: Rich tables/panels
- `--json`: machine-readable JSON on any command

## Migration from Existing Code

**Keep and refactor:**
- `yahoo_api.py` → `client.py` (remove ORM deps, print debugging → logging, return dataclasses)
- `auth.py` → `auth.py` (remove JSON file storage, use TOML config)
- `export_players.py` → `cli/commands/export.py` (fold into CLI)

**Drop:**
- `app/main.py` (FastAPI)
- `app/api/routes.py`, `app/api/schemas.py` (web endpoints)
- `app/database.py`, `app/models.py` (SQLAlchemy ORM)
- `app/analyzers/` (placeholder implementations)
- `app/config.py` (Pydantic settings → simple TOML)
- `frontend/` (entire React app)
