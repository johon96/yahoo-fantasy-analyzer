# yfantasy CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform yahoo-fantasy-analyzer from a half-built web app into a focused CLI tool called `yfantasy` with multi-sport support, week-level optimization, and full roster management.

**Architecture:** Clean Python package (`yfantasy/`) with dataclass models, hybrid Yahoo API client (direct REST + YFPY), pluggable scoring engine, and typer-based CLI. Config stored in `~/.yfantasy/config.toml`. File-based JSON caching.

**Tech Stack:** Python 3.9+, typer[all], rich, prompt_toolkit, yfpy, requests

**Existing code base:** `/Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer/` on branch `johnathan.vangorp/yfantasy-cli`

**Existing code to reference:**
- `backend/app/auth.py` — OAuth2 flow, token refresh, User class
- `backend/app/yahoo_api.py` — YahooAPIClient with direct REST + YFPY hybrid
- `backend/export_players.py` — Batch player fetching, XML parsing, stat ID mapping
- `backend/app/config.py` — Pydantic settings (will replace with TOML)

---

## Task 1: Project Scaffolding & pyproject.toml

**Files:**
- Create: `pyproject.toml`
- Create: `yfantasy/__init__.py`
- Create: `yfantasy/cli/__init__.py`
- Create: `yfantasy/cli/app.py`
- Create: `yfantasy/cli/commands/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "yfantasy"
version = "0.1.0"
description = "Yahoo Fantasy Sports CLI — roster optimizer, waiver wire, trade analyzer"
requires-python = ">=3.9"
dependencies = [
    "typer[all]>=0.9.0",
    "rich>=13.0.0",
    "prompt-toolkit>=3.0.0",
    "yfpy>=17.0.0",
    "requests>=2.28.0",
    "requests-oauthlib>=1.3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
]

[project.scripts]
yfantasy = "yfantasy.cli.app:main"

[tool.setuptools.packages.find]
include = ["yfantasy*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create yfantasy/__init__.py**

```python
"""yfantasy — Yahoo Fantasy Sports CLI."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Create yfantasy/cli/__init__.py**

```python
"""CLI package for yfantasy."""
```

- [ ] **Step 4: Create yfantasy/cli/app.py with minimal entry point**

```python
"""yfantasy CLI entry point."""

import typer

app = typer.Typer(
    name="yfantasy",
    help="Yahoo Fantasy Sports CLI — roster optimizer, waiver wire, trade analyzer",
    no_args_is_help=True,
)


@app.command()
def version():
    """Show version."""
    from yfantasy import __version__
    typer.echo(f"yfantasy {__version__}")


def main():
    app()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Create yfantasy/cli/commands/__init__.py**

```python
"""CLI command modules."""
```

- [ ] **Step 6: Create tests/__init__.py and tests/conftest.py**

`tests/__init__.py`:
```python
```

`tests/conftest.py`:
```python
"""Shared test fixtures for yfantasy."""
```

- [ ] **Step 7: Verify CLI installs and runs**

Run:
```bash
cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer
pip install -e ".[dev]"
yfantasy version
```
Expected: `yfantasy 0.1.0`

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml yfantasy/ tests/
git commit -m "feat: scaffold yfantasy package with CLI entry point"
```

---

## Task 2: Data Models

**Files:**
- Create: `yfantasy/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write tests for models**

```python
"""Tests for yfantasy data models."""

from yfantasy.models import (
    Player,
    RosterPlayer,
    Roster,
    StatCategory,
    League,
    Team,
    Standing,
    Matchup,
    DayPlan,
    WeekPlan,
    WriteResult,
)
from datetime import date


def test_player_creation():
    player = Player(
        player_key="465.p.6619",
        name="Connor McDavid",
        team="EDM",
        positions=["C", "LW"],
        status="healthy",
        percent_owned=99.9,
        current_fantasy_team="465.l.34948.t.1",
        stats={"1": 30.0, "2": 50.0},
        projected_stats={"1": 35.0, "2": 55.0},
    )
    assert player.player_key == "465.p.6619"
    assert player.name == "Connor McDavid"
    assert "C" in player.positions
    assert player.stats["1"] == 30.0


def test_player_is_available():
    free_agent = Player(
        player_key="465.p.1234",
        name="Free Agent",
        team="NYR",
        positions=["D"],
        status="healthy",
        percent_owned=10.0,
        current_fantasy_team=None,
        stats={},
        projected_stats=None,
    )
    assert free_agent.is_available is True

    rostered = Player(
        player_key="465.p.5678",
        name="Rostered Player",
        team="TOR",
        positions=["C"],
        status="healthy",
        percent_owned=90.0,
        current_fantasy_team="465.l.34948.t.1",
        stats={},
        projected_stats=None,
    )
    assert rostered.is_available is False


def test_roster_player():
    player = Player(
        player_key="465.p.6619",
        name="Connor McDavid",
        team="EDM",
        positions=["C", "LW"],
        status="healthy",
        percent_owned=99.9,
        current_fantasy_team=None,
        stats={},
        projected_stats=None,
    )
    rp = RosterPlayer(player=player, selected_position="C", is_starting=True)
    assert rp.is_starting is True
    assert rp.selected_position == "C"


def test_stat_category_is_scoring():
    scoring_cat = StatCategory(
        stat_id="1",
        name="Goals",
        display_name="G",
        sort_order="1",
        position_type="P",
        is_only_display=False,
        value=3.0,
        is_category=True,
    )
    assert scoring_cat.is_scoring is True

    display_cat = StatCategory(
        stat_id="99",
        name="Games Played",
        display_name="GP",
        sort_order="1",
        position_type="P",
        is_only_display=True,
        value=None,
        is_category=False,
    )
    assert display_cat.is_scoring is False


def test_league_is_daily():
    daily_league = League(
        league_key="465.l.34948",
        name="Test Hockey League",
        sport="nhl",
        season="2025",
        num_teams=12,
        scoring_type="head",
        scoring_period="daily",
        roster_positions=["C", "C", "LW", "RW", "D", "D", "G", "BN", "BN", "IR"],
        stat_categories=[],
        current_week=20,
    )
    assert daily_league.is_daily is True

    weekly_league = League(
        league_key="461.l.12345",
        name="Test Football League",
        sport="nfl",
        season="2025",
        num_teams=10,
        scoring_type="head",
        scoring_period="weekly",
        roster_positions=["QB", "RB", "WR", "TE", "K", "DEF", "BN"],
        stat_categories=[],
        current_week=10,
    )
    assert weekly_league.is_daily is False


def test_league_active_positions():
    league = League(
        league_key="465.l.34948",
        name="Test League",
        sport="nhl",
        season="2025",
        num_teams=12,
        scoring_type="head",
        scoring_period="daily",
        roster_positions=["C", "C", "LW", "RW", "D", "D", "G", "BN", "BN", "IR"],
        stat_categories=[],
        current_week=20,
    )
    active = league.active_positions
    assert "C" in active
    assert "BN" not in active
    assert "IR" not in active


def test_week_plan_improvement():
    plan = WeekPlan(
        days=[],
        transactions_used=2,
        transactions_remaining=3,
        total_projected_points=185.5,
        baseline_points=170.0,
        improvement=15.5,
    )
    assert plan.improvement == 15.5


def test_write_result():
    success = WriteResult(success=True, message="Player added successfully")
    assert success.success is True

    failure = WriteResult(success=False, message="Roster is full")
    assert failure.success is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer && python -m pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yfantasy.models'`

- [ ] **Step 3: Implement models.py**

```python
"""Data models for yfantasy — plain dataclasses, no ORM."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

# Bench / inactive position names across all sports
_INACTIVE_POSITIONS = {"BN", "IR", "IR+", "IL", "IL+", "DL", "NA", "Bench"}


@dataclass
class Player:
    player_key: str
    name: str
    team: str
    positions: list[str]
    status: str
    percent_owned: float
    current_fantasy_team: Optional[str]
    stats: dict[str, float]
    projected_stats: Optional[dict[str, float]]

    @property
    def is_available(self) -> bool:
        return self.current_fantasy_team is None


@dataclass
class RosterPlayer:
    player: Player
    selected_position: str
    is_starting: bool


@dataclass
class Roster:
    team_key: str
    players: list[RosterPlayer]


@dataclass
class StatCategory:
    stat_id: str
    name: str
    display_name: str
    sort_order: str
    position_type: str
    is_only_display: bool
    value: Optional[float]
    is_category: bool

    @property
    def is_scoring(self) -> bool:
        return not self.is_only_display and (self.value is not None or self.is_category)


@dataclass
class League:
    league_key: str
    name: str
    sport: str
    season: str
    num_teams: int
    scoring_type: str
    scoring_period: str
    roster_positions: list[str]
    stat_categories: list[StatCategory]
    current_week: int

    @property
    def is_daily(self) -> bool:
        return self.scoring_period == "daily"

    @property
    def active_positions(self) -> list[str]:
        return [p for p in self.roster_positions if p not in _INACTIVE_POSITIONS]


@dataclass
class Team:
    team_key: str
    name: str
    manager: str
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points_for: float = 0.0
    points_against: float = 0.0
    standing: int = 0


@dataclass
class Standing:
    teams: list[Team]


@dataclass
class Matchup:
    week: int
    team_key: str
    opponent_key: str
    team_projected: float = 0.0
    opponent_projected: float = 0.0
    team_score: float = 0.0
    opponent_score: float = 0.0


@dataclass
class DayPlan:
    date: date
    lineup: list[RosterPlayer]
    adds: list[Player] = field(default_factory=list)
    drops: list[Player] = field(default_factory=list)
    projected_points: float = 0.0


@dataclass
class WeekPlan:
    days: list[DayPlan]
    transactions_used: int
    transactions_remaining: int
    total_projected_points: float
    baseline_points: float
    improvement: float


@dataclass
class WriteResult:
    success: bool
    message: str
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer && python -m pytest tests/test_models.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add yfantasy/models.py tests/test_models.py
git commit -m "feat: add core data models (Player, League, Roster, WeekPlan, etc.)"
```

---

## Task 3: Config Management

**Files:**
- Create: `yfantasy/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write tests for config**

```python
"""Tests for yfantasy config management."""

import json
from pathlib import Path
from datetime import datetime
from yfantasy.config import Config, _DEFAULT_CONFIG


def test_default_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config = Config(config_dir=tmp_path / ".yfantasy")
    assert config.get("defaults", "league_key") == ""
    assert config.get("defaults", "sport") == ""


def test_set_and_get(tmp_path):
    config = Config(config_dir=tmp_path / ".yfantasy")
    config.set("defaults", "league_key", "465.l.34948")
    assert config.get("defaults", "league_key") == "465.l.34948"


def test_save_and_reload(tmp_path):
    config = Config(config_dir=tmp_path / ".yfantasy")
    config.set("auth", "client_id", "test_id")
    config.set("auth", "client_secret", "test_secret")
    config.save()

    config2 = Config(config_dir=tmp_path / ".yfantasy")
    assert config2.get("auth", "client_id") == "test_id"
    assert config2.get("auth", "client_secret") == "test_secret"


def test_has_credentials(tmp_path):
    config = Config(config_dir=tmp_path / ".yfantasy")
    assert config.has_credentials() is False

    config.set("auth", "client_id", "test_id")
    config.set("auth", "client_secret", "test_secret")
    assert config.has_credentials() is True


def test_has_token(tmp_path):
    config = Config(config_dir=tmp_path / ".yfantasy")
    assert config.has_token() is False

    config.set("auth", "access_token", "tok123")
    config.set("auth", "refresh_token", "ref456")
    config.set("auth", "token_expiry", "2099-01-01T00:00:00")
    assert config.has_token() is True


def test_is_token_expired(tmp_path):
    config = Config(config_dir=tmp_path / ".yfantasy")
    config.set("auth", "token_expiry", "2000-01-01T00:00:00")
    assert config.is_token_expired() is True

    config.set("auth", "token_expiry", "2099-01-01T00:00:00")
    assert config.is_token_expired() is False


def test_config_dir_created(tmp_path):
    config_dir = tmp_path / ".yfantasy"
    assert not config_dir.exists()
    Config(config_dir=config_dir)
    assert config_dir.exists()


def test_cache_dir(tmp_path):
    config = Config(config_dir=tmp_path / ".yfantasy")
    cache_dir = config.cache_dir
    assert cache_dir == tmp_path / ".yfantasy" / "cache"
    assert cache_dir.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer && python -m pytest tests/test_config.py -v`
Expected: FAIL

- [ ] **Step 3: Implement config.py**

```python
"""Config management for yfantasy — TOML-based, stored in ~/.yfantasy/."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Use tomllib (stdlib 3.11+) with fallback
try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]

_DEFAULT_CONFIG: dict[str, dict[str, str]] = {
    "auth": {
        "client_id": "",
        "client_secret": "",
        "access_token": "",
        "refresh_token": "",
        "token_expiry": "",
    },
    "defaults": {
        "league_key": "",
        "sport": "",
    },
}

_DEFAULT_DIR = Path.home() / ".yfantasy"


class Config:
    """Manages yfantasy configuration stored in ~/.yfantasy/config.toml."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or _DEFAULT_DIR
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.config_dir / "config.toml"
        self._data: dict[str, dict[str, str]] = {}
        self._load()

    # -- public API ----------------------------------------------------------

    def get(self, section: str, key: str, default: str = "") -> str:
        return self._data.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: str) -> None:
        self._data.setdefault(section, {})[key] = value

    def save(self) -> None:
        lines: list[str] = []
        for section, kvs in self._data.items():
            lines.append(f"[{section}]")
            for k, v in kvs.items():
                lines.append(f'{k} = "{v}"')
            lines.append("")
        self._path.write_text("\n".join(lines))

    def has_credentials(self) -> bool:
        return bool(self.get("auth", "client_id") and self.get("auth", "client_secret"))

    def has_token(self) -> bool:
        return bool(
            self.get("auth", "access_token")
            and self.get("auth", "refresh_token")
            and self.get("auth", "token_expiry")
        )

    def is_token_expired(self) -> bool:
        expiry = self.get("auth", "token_expiry")
        if not expiry:
            return True
        try:
            return datetime.fromisoformat(expiry) < datetime.now()
        except ValueError:
            return True

    @property
    def cache_dir(self) -> Path:
        d = self.config_dir / "cache"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # -- internal ------------------------------------------------------------

    def _load(self) -> None:
        if self._path.exists() and tomllib is not None:
            with open(self._path, "rb") as f:
                self._data = tomllib.load(f)
        elif self._path.exists():
            # Minimal fallback parser for simple key = "value" TOML
            self._data = self._parse_simple_toml(self._path.read_text())
        else:
            self._data = {s: dict(kvs) for s, kvs in _DEFAULT_CONFIG.items()}

    @staticmethod
    def _parse_simple_toml(text: str) -> dict[str, dict[str, str]]:
        data: dict[str, dict[str, str]] = {}
        section = ""
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1]
                data.setdefault(section, {})
            elif "=" in line and section:
                k, v = line.split("=", 1)
                v = v.strip().strip('"')
                data[section][k.strip()] = v
        return data
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer && python -m pytest tests/test_config.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add yfantasy/config.py tests/test_config.py
git commit -m "feat: add TOML-based config management (~/.yfantasy/config.toml)"
```

---

## Task 4: Auth Module

**Files:**
- Create: `yfantasy/auth.py`
- Create: `tests/test_auth.py`

Reference: `backend/app/auth.py` for OAuth flow, token refresh logic.

- [ ] **Step 1: Write tests for auth**

```python
"""Tests for yfantasy auth module."""

from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from yfantasy.auth import YahooAuth
from yfantasy.config import Config


def test_auth_needs_init_without_credentials(tmp_path):
    config = Config(config_dir=tmp_path / ".yfantasy")
    auth = YahooAuth(config)
    assert auth.needs_init() is True


def test_auth_needs_init_with_credentials(tmp_path):
    config = Config(config_dir=tmp_path / ".yfantasy")
    config.set("auth", "client_id", "test_id")
    config.set("auth", "client_secret", "test_secret")
    config.set("auth", "access_token", "tok")
    config.set("auth", "refresh_token", "ref")
    config.set("auth", "token_expiry", "2099-01-01T00:00:00")
    auth = YahooAuth(config)
    assert auth.needs_init() is False


def test_get_access_token_valid(tmp_path):
    config = Config(config_dir=tmp_path / ".yfantasy")
    future = (datetime.now() + timedelta(hours=1)).isoformat()
    config.set("auth", "client_id", "test_id")
    config.set("auth", "client_secret", "test_secret")
    config.set("auth", "access_token", "valid_token")
    config.set("auth", "refresh_token", "ref")
    config.set("auth", "token_expiry", future)
    auth = YahooAuth(config)

    token = auth.get_access_token()
    assert token == "valid_token"


@patch("yfantasy.auth.requests.post")
def test_get_access_token_refreshes_when_expired(mock_post, tmp_path):
    config = Config(config_dir=tmp_path / ".yfantasy")
    past = (datetime.now() - timedelta(hours=1)).isoformat()
    config.set("auth", "client_id", "test_id")
    config.set("auth", "client_secret", "test_secret")
    config.set("auth", "access_token", "expired_token")
    config.set("auth", "refresh_token", "ref_token")
    config.set("auth", "token_expiry", past)

    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "access_token": "new_token",
        "refresh_token": "new_ref",
        "expires_in": 3600,
    }
    mock_post.return_value = mock_response

    auth = YahooAuth(config)
    token = auth.get_access_token()
    assert token == "new_token"
    assert config.get("auth", "access_token") == "new_token"


@patch("yfantasy.auth.requests.post")
def test_refresh_failure_raises(mock_post, tmp_path):
    config = Config(config_dir=tmp_path / ".yfantasy")
    past = (datetime.now() - timedelta(hours=1)).isoformat()
    config.set("auth", "client_id", "test_id")
    config.set("auth", "client_secret", "test_secret")
    config.set("auth", "access_token", "expired")
    config.set("auth", "refresh_token", "bad_ref")
    config.set("auth", "token_expiry", past)

    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status_code = 401
    mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
    mock_post.return_value = mock_response

    auth = YahooAuth(config)
    try:
        auth.get_access_token()
        assert False, "Should have raised"
    except Exception as e:
        assert "401" in str(e) or "refresh" in str(e).lower() or "init" in str(e).lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer && python -m pytest tests/test_auth.py -v`
Expected: FAIL

- [ ] **Step 3: Implement auth.py**

```python
"""OAuth2 authentication for Yahoo Fantasy Sports API."""

from __future__ import annotations

import base64
import logging
import threading
import webbrowser
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional
from urllib.parse import parse_qs, urlparse

import requests

from yfantasy.config import Config

logger = logging.getLogger(__name__)

_AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
_USERINFO_URL = "https://api.login.yahoo.com/openid/v1/userinfo"
_CALLBACK_PORT = 8765


class YahooAuth:
    """Handles Yahoo OAuth2 flow and token management."""

    def __init__(self, config: Config):
        self.config = config

    def needs_init(self) -> bool:
        return not self.config.has_credentials() or not self.config.has_token()

    def get_access_token(self) -> str:
        """Return a valid access token, refreshing if necessary."""
        if not self.config.is_token_expired():
            return self.config.get("auth", "access_token")

        # Try refresh
        refresh_token = self.config.get("auth", "refresh_token")
        if not refresh_token:
            raise RuntimeError("No refresh token. Run `yfantasy init` to authenticate.")

        logger.info("Access token expired, refreshing...")
        token_data = self._refresh(refresh_token)
        self._store_token(token_data)
        return token_data["access_token"]

    def run_oauth_flow(self) -> dict:
        """Run full OAuth2 browser flow. Returns token data dict."""
        client_id = self.config.get("auth", "client_id")
        redirect_uri = f"http://localhost:{_CALLBACK_PORT}"

        auth_url = (
            f"{_AUTH_URL}?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
        )

        code = self._capture_auth_code(auth_url, redirect_uri)
        token_data = self._exchange_code(code, redirect_uri)
        self._store_token(token_data)
        return token_data

    def get_user_info(self) -> dict:
        """Fetch Yahoo user profile (guid, email, name)."""
        token = self.get_access_token()
        resp = requests.get(
            _USERINFO_URL, headers={"Authorization": f"Bearer {token}"}
        )
        resp.raise_for_status()
        return resp.json()

    # -- internal ------------------------------------------------------------

    def _exchange_code(self, code: str, redirect_uri: str) -> dict:
        client_id = self.config.get("auth", "client_id")
        client_secret = self.config.get("auth", "client_secret")

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        resp = requests.post(
            _TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # Fallback to Basic auth if POST body creds fail
        if not resp.ok and resp.status_code == 401:
            logger.debug("Retrying token exchange with Basic auth header")
            creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            resp = requests.post(
                _TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {creds}",
                },
            )

        resp.raise_for_status()
        return resp.json()

    def _refresh(self, refresh_token: str) -> dict:
        client_id = self.config.get("auth", "client_id")
        client_secret = self.config.get("auth", "client_secret")

        resp = requests.post(
            _TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if not resp.ok:
            raise RuntimeError(
                f"Token refresh failed ({resp.status_code}). Run `yfantasy init` to re-authenticate."
            )
        return resp.json()

    def _store_token(self, token_data: dict) -> None:
        expiry = datetime.now() + timedelta(seconds=token_data.get("expires_in", 3600))
        self.config.set("auth", "access_token", token_data["access_token"])
        self.config.set(
            "auth",
            "refresh_token",
            token_data.get("refresh_token", self.config.get("auth", "refresh_token")),
        )
        self.config.set("auth", "token_expiry", expiry.isoformat())
        self.config.save()

    def _capture_auth_code(self, auth_url: str, redirect_uri: str) -> str:
        """Open browser for auth, capture the callback code."""
        code_holder: dict[str, Optional[str]] = {"code": None}

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                qs = parse_qs(urlparse(self.path).query)
                code_holder["code"] = qs.get("code", [None])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h2>Authenticated! You can close this tab.</h2></body></html>"
                )

            def log_message(self, format, *args):
                pass  # Suppress request logs

        server = HTTPServer(("localhost", _CALLBACK_PORT), CallbackHandler)
        webbrowser.open(auth_url)
        server.handle_request()
        server.server_close()

        if not code_holder["code"]:
            raise RuntimeError("Did not receive authorization code from Yahoo.")
        return code_holder["code"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer && python -m pytest tests/test_auth.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add yfantasy/auth.py tests/test_auth.py
git commit -m "feat: add Yahoo OAuth2 auth module with token refresh"
```

---

## Task 5: Cache Module

**Files:**
- Create: `yfantasy/cache.py`
- Create: `tests/test_cache.py`

- [ ] **Step 1: Write tests for cache**

```python
"""Tests for yfantasy file-based cache."""

import json
import time
from yfantasy.cache import FileCache


def test_cache_miss(tmp_path):
    cache = FileCache(cache_dir=tmp_path)
    assert cache.get("nonexistent", ttl_seconds=60) is None


def test_cache_set_and_get(tmp_path):
    cache = FileCache(cache_dir=tmp_path)
    cache.set("my_key", {"hello": "world"})
    result = cache.get("my_key", ttl_seconds=60)
    assert result == {"hello": "world"}


def test_cache_expired(tmp_path):
    cache = FileCache(cache_dir=tmp_path)
    cache.set("old_key", {"stale": True})
    # Manually backdate the file
    cache_file = tmp_path / "old_key.json"
    data = json.loads(cache_file.read_text())
    data["timestamp"] = time.time() - 120
    cache_file.write_text(json.dumps(data))

    assert cache.get("old_key", ttl_seconds=60) is None


def test_cache_invalidate(tmp_path):
    cache = FileCache(cache_dir=tmp_path)
    cache.set("deleteme", {"bye": True})
    assert cache.get("deleteme", ttl_seconds=60) is not None
    cache.invalidate("deleteme")
    assert cache.get("deleteme", ttl_seconds=60) is None


def test_cache_clear(tmp_path):
    cache = FileCache(cache_dir=tmp_path)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert cache.get("a", ttl_seconds=60) is None
    assert cache.get("b", ttl_seconds=60) is None


def test_cache_key_sanitization(tmp_path):
    cache = FileCache(cache_dir=tmp_path)
    cache.set("league/465.l.34948/roster;week=5", {"data": True})
    result = cache.get("league/465.l.34948/roster;week=5", ttl_seconds=60)
    assert result == {"data": True}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer && python -m pytest tests/test_cache.py -v`
Expected: FAIL

- [ ] **Step 3: Implement cache.py**

```python
"""File-based JSON cache for yfantasy."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Default TTLs in seconds
TTL_ROSTER = 300        # 5 minutes
TTL_FREE_AGENTS = 1800  # 30 minutes
TTL_PLAYERS = 3600      # 1 hour
TTL_LEAGUE = 86400      # 24 hours


class FileCache:
    """Simple file-based JSON cache with TTL expiry."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str, ttl_seconds: int) -> Optional[Any]:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            if time.time() - data["timestamp"] > ttl_seconds:
                logger.debug("Cache expired: %s", key)
                return None
            logger.debug("Cache hit: %s", key)
            return data["value"]
        except (json.JSONDecodeError, KeyError):
            return None

    def set(self, key: str, value: Any) -> None:
        path = self._path(key)
        path.write_text(json.dumps({"timestamp": time.time(), "value": value}))
        logger.debug("Cache set: %s", key)

    def invalidate(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def clear(self) -> None:
        for f in self.cache_dir.glob("*.json"):
            f.unlink()

    def _path(self, key: str) -> Path:
        safe = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self.cache_dir / f"{safe}.json"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer && python -m pytest tests/test_cache.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add yfantasy/cache.py tests/test_cache.py
git commit -m "feat: add file-based JSON cache with TTL expiry"
```

---

## Task 6: Yahoo API Client (Reads)

**Files:**
- Create: `yfantasy/client.py`
- Create: `tests/test_client.py`

Reference: `backend/app/yahoo_api.py` for parsing patterns, `backend/export_players.py` for XML stat parsing.

- [ ] **Step 1: Write tests for client**

```python
"""Tests for yfantasy Yahoo API client."""

from unittest.mock import patch, MagicMock
from yfantasy.client import YahooClient
from yfantasy.config import Config
from yfantasy.models import League, Player


def _make_client(tmp_path):
    """Create a client with mock auth."""
    config = Config(config_dir=tmp_path / ".yfantasy")
    config.set("auth", "client_id", "test_id")
    config.set("auth", "client_secret", "test_secret")
    config.set("auth", "access_token", "test_token")
    config.set("auth", "refresh_token", "test_ref")
    config.set("auth", "token_expiry", "2099-01-01T00:00:00")
    config.set("defaults", "league_key", "465.l.34948")
    return YahooClient(config)


@patch("yfantasy.client.requests.get")
def test_make_request_adds_json_format(mock_get, tmp_path):
    client = _make_client(tmp_path)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"fantasy_content": {}}
    mock_get.return_value = mock_resp

    client._request("league/465.l.34948")
    called_url = mock_get.call_args[0][0]
    assert "format=json" in called_url


@patch("yfantasy.client.requests.get")
def test_make_request_auth_header(mock_get, tmp_path):
    client = _make_client(tmp_path)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"fantasy_content": {}}
    mock_get.return_value = mock_resp

    client._request("league/465.l.34948")
    headers = mock_get.call_args[1]["headers"]
    assert headers["Authorization"] == "Bearer test_token"


def test_parse_league_key():
    game_id, league_id = YahooClient.parse_league_key("465.l.34948")
    assert game_id == "465"
    assert league_id == "34948"


def test_game_code_from_id():
    assert YahooClient.game_code_from_id("465") == "nhl"
    assert YahooClient.game_code_from_id("461") == "nfl"
    assert YahooClient.game_code_from_id("404") == "mlb"
    assert YahooClient.game_code_from_id("428") == "nba"
    assert YahooClient.game_code_from_id("999") == "nhl"  # fallback
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer && python -m pytest tests/test_client.py -v`
Expected: FAIL

- [ ] **Step 3: Implement client.py**

```python
"""Yahoo Fantasy Sports API client — read operations."""

from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from typing import Any, Optional

import requests

from yfantasy.auth import YahooAuth
from yfantasy.cache import FileCache, TTL_LEAGUE, TTL_PLAYERS, TTL_ROSTER, TTL_FREE_AGENTS
from yfantasy.config import Config
from yfantasy.models import (
    League,
    Matchup,
    Player,
    Roster,
    RosterPlayer,
    StatCategory,
    Team,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://fantasysports.yahooapis.com/fantasy/v2"

# Map Yahoo game IDs → sport codes
_GAME_CODE_MAP: dict[str, str] = {
    "449": "nfl", "461": "nfl", "458": "nfl",
    "465": "nhl", "427": "nhl", "453": "nhl",
    "404": "mlb", "412": "mlb", "454": "mlb",
    "428": "nba", "431": "nba",
}

# Yahoo Fantasy XML namespace
_NS = {"f": "http://fantasysports.yahooapis.com/fantasy/v2/base.rng"}


class YahooClient:
    """Read-only Yahoo Fantasy Sports API client."""

    def __init__(self, config: Config, *, use_cache: bool = True):
        self.config = config
        self.auth = YahooAuth(config)
        self._cache = FileCache(config.cache_dir) if use_cache else None

    # -- public API ----------------------------------------------------------

    def get_leagues(self) -> list[dict[str, Any]]:
        """Get all leagues for the authenticated user."""
        resp = self._request("users;use_login=1/games/leagues")
        return self._parse_leagues_response(resp)

    def get_league(self, league_key: str) -> League:
        """Get full league info including settings, scoring, and roster positions."""
        cache_key = f"league:{league_key}:settings"
        if self._cache:
            cached = self._cache.get(cache_key, TTL_LEAGUE)
            if cached:
                return self._dict_to_league(cached)

        # Fetch league info + settings in one call
        resp = self._request(f"league/{league_key}/settings")
        league = self._parse_league_settings(resp, league_key)

        if self._cache:
            self._cache.set(cache_key, self._league_to_dict(league))
        return league

    def get_roster(
        self, team_key: str, *, week: Optional[int] = None, date: Optional[str] = None
    ) -> Roster:
        """Get team roster. Optionally for a specific week or date."""
        extra = ""
        if week is not None:
            extra = f";week={week}"
        elif date is not None:
            extra = f";date={date}"

        cache_key = f"roster:{team_key}{extra}"
        if self._cache:
            cached = self._cache.get(cache_key, TTL_ROSTER)
            if cached:
                return self._dict_to_roster(cached)

        resp = self._request(f"team/{team_key}/roster{extra}")
        roster = self._parse_roster_response(resp, team_key)

        if self._cache:
            self._cache.set(cache_key, self._roster_to_dict(roster))
        return roster

    def get_free_agents(
        self, league_key: str, *, position: Optional[str] = None, count: int = 50
    ) -> list[Player]:
        """Get available free agents, optionally filtered by position."""
        filters = f";status=FA;sort=AR;count={count}"
        if position:
            filters += f";position={position}"

        cache_key = f"fa:{league_key}{filters}"
        if self._cache:
            cached = self._cache.get(cache_key, TTL_FREE_AGENTS)
            if cached:
                return [self._dict_to_player(p) for p in cached]

        resp = self._request(f"league/{league_key}/players{filters}/stats")
        players = self._parse_players_response(resp)

        if self._cache:
            self._cache.set(cache_key, [self._player_to_dict(p) for p in players])
        return players

    def get_standings(self, league_key: str) -> list[Team]:
        """Get league standings."""
        resp = self._request(f"league/{league_key}/standings")
        return self._parse_standings_response(resp)

    def get_scoreboard(self, league_key: str, week: int) -> list[Matchup]:
        """Get matchups for a specific week."""
        resp = self._request(f"league/{league_key}/scoreboard;week={week}")
        return self._parse_scoreboard_response(resp)

    def get_my_team_key(self, league_key: str) -> Optional[str]:
        """Find the authenticated user's team key in a league."""
        resp = self._request(f"league/{league_key}/teams")
        teams = self._parse_teams_list(resp)
        # The user's team is identified by is_owned_by_current_login
        for t in teams:
            if t.get("is_owned_by_current_login"):
                return t.get("team_key")
        return teams[0].get("team_key") if teams else None

    # -- static helpers ------------------------------------------------------

    @staticmethod
    def parse_league_key(league_key: str) -> tuple[str, str]:
        parts = league_key.split(".")
        return parts[0], parts[-1]

    @staticmethod
    def game_code_from_id(game_id: str) -> str:
        return _GAME_CODE_MAP.get(game_id, "nhl")

    # -- HTTP ----------------------------------------------------------------

    def _request(self, endpoint: str) -> dict:
        token = self.auth.get_access_token()
        sep = "&" if "?" in endpoint else "?"
        url = f"{_BASE_URL}/{endpoint}{sep}format=json"
        logger.info("GET %s", url)

        resp = requests.get(
            url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}
        )

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "5"))
            logger.warning("Rate limited. Retrying in %ds...", retry_after)
            time.sleep(retry_after)
            return self._request(endpoint)

        if resp.status_code == 401:
            # Force token refresh and retry once
            logger.warning("401 — forcing token refresh")
            self.config.set("auth", "token_expiry", "2000-01-01T00:00:00")
            token = self.auth.get_access_token()
            resp = requests.get(
                url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}
            )

        resp.raise_for_status()
        return resp.json()

    # -- response parsers ----------------------------------------------------

    def _parse_leagues_response(self, resp: dict) -> list[dict[str, Any]]:
        """Parse the deeply nested Yahoo leagues response."""
        leagues: list[dict[str, Any]] = []
        try:
            fc = resp.get("fantasy_content", {})
            users = fc.get("users", {})
            user_arr = users.get("0", {}).get("user", [])
            if len(user_arr) < 2:
                return []
            games_obj = user_arr[1].get("games", {})
            for key in games_obj:
                if key == "count":
                    continue
                game = games_obj[key].get("game")
                if not game:
                    continue
                leagues_obj = {}
                if isinstance(game, list) and len(game) > 1 and isinstance(game[1], dict):
                    leagues_obj = game[1].get("leagues", {})
                elif isinstance(game, dict):
                    leagues_obj = game.get("leagues", {})
                for lk in leagues_obj:
                    if lk == "count":
                        continue
                    league_entry = leagues_obj[lk].get("league")
                    if isinstance(league_entry, list):
                        for item in league_entry:
                            if isinstance(item, dict):
                                leagues.append(item)
                    elif isinstance(league_entry, dict):
                        leagues.append(league_entry)
        except Exception:
            logger.exception("Failed to parse leagues response")
        return leagues

    def _parse_league_settings(self, resp: dict, league_key: str) -> League:
        """Parse league + settings response into a League model."""
        fc = resp.get("fantasy_content", {})
        league_arr = fc.get("league", [])

        info = league_arr[0] if isinstance(league_arr, list) and league_arr else {}
        settings_obj = league_arr[1] if isinstance(league_arr, list) and len(league_arr) > 1 else {}
        settings = settings_obj.get("settings", [{}])
        settings_data = settings[0] if isinstance(settings, list) and settings else {}

        # Parse stat categories
        stat_cats: list[StatCategory] = []
        for cat_entry in settings_data.get("stat_categories", {}).get("stats", []):
            s = cat_entry.get("stat", {})
            stat_cats.append(
                StatCategory(
                    stat_id=str(s.get("stat_id", "")),
                    name=s.get("name", ""),
                    display_name=s.get("display_name", s.get("abbr", "")),
                    sort_order=str(s.get("sort_order", "1")),
                    position_type=s.get("position_type", "P"),
                    is_only_display=bool(int(s.get("is_only_display_stat", "0"))),
                    value=self._parse_stat_value(settings_data, str(s.get("stat_id", ""))),
                    is_category=not bool(int(s.get("is_only_display_stat", "0"))),
                )
            )

        # Parse roster positions
        roster_positions: list[str] = []
        for rp in settings_data.get("roster_positions", []):
            pos = rp.get("roster_position", {})
            pos_name = pos.get("position", "")
            count = int(pos.get("count", 1))
            roster_positions.extend([pos_name] * count)

        game_id, _ = self.parse_league_key(league_key)
        sport = self.game_code_from_id(game_id)

        # Determine scoring period: NFL is weekly, most others are daily
        scoring_period = "weekly" if sport == "nfl" else "daily"

        return League(
            league_key=league_key,
            name=info.get("name", ""),
            sport=sport,
            season=str(info.get("season", "")),
            num_teams=int(info.get("num_teams", 0)),
            scoring_type=info.get("scoring_type", "head"),
            scoring_period=scoring_period,
            roster_positions=roster_positions,
            stat_categories=stat_cats,
            current_week=int(info.get("current_week", 1)),
        )

    def _parse_stat_value(self, settings_data: dict, stat_id: str) -> Optional[float]:
        """Find the point value for a stat in league modifier settings."""
        for mod in settings_data.get("stat_modifiers", {}).get("stats", []):
            s = mod.get("stat", {})
            if str(s.get("stat_id", "")) == stat_id:
                try:
                    return float(s.get("value", 0))
                except (ValueError, TypeError):
                    return None
        return None

    def _parse_roster_response(self, resp: dict, team_key: str) -> Roster:
        """Parse roster response into Roster model."""
        fc = resp.get("fantasy_content", {})
        team_arr = fc.get("team", [])
        roster_obj = team_arr[1] if isinstance(team_arr, list) and len(team_arr) > 1 else {}
        roster_data = roster_obj.get("roster", {})
        players_obj = {}
        if isinstance(roster_data, dict):
            coverage = roster_data.get("0", roster_data)
            players_obj = coverage.get("players", {}) if isinstance(coverage, dict) else {}
        elif isinstance(roster_data, list) and roster_data:
            players_obj = roster_data[0].get("players", {}) if isinstance(roster_data[0], dict) else {}

        roster_players: list[RosterPlayer] = []
        for key in players_obj:
            if key == "count":
                continue
            player_data = players_obj[key].get("player", [])
            if not isinstance(player_data, list) or len(player_data) < 2:
                continue
            player = self._parse_player_from_json(player_data[0] if isinstance(player_data[0], list) else [player_data[0]])
            pos_obj = player_data[1].get("selected_position", [{}])
            selected_pos = pos_obj[0].get("position", "BN") if isinstance(pos_obj, list) and pos_obj else "BN"

            roster_players.append(
                RosterPlayer(
                    player=player,
                    selected_position=selected_pos,
                    is_starting=selected_pos not in {"BN", "IR", "IR+", "IL", "IL+", "DL", "NA"},
                )
            )

        return Roster(team_key=team_key, players=roster_players)

    def _parse_players_response(self, resp: dict) -> list[Player]:
        """Parse a players collection response."""
        players: list[Player] = []
        fc = resp.get("fantasy_content", {})
        league_arr = fc.get("league", [])
        if not isinstance(league_arr, list) or len(league_arr) < 2:
            return []
        players_obj = league_arr[1].get("players", {})
        for key in players_obj:
            if key == "count":
                continue
            pdata = players_obj[key].get("player", [])
            if not isinstance(pdata, list) or not pdata:
                continue
            attrs = pdata[0] if isinstance(pdata[0], list) else [pdata[0]]
            player = self._parse_player_from_json(attrs)
            # Parse stats if present
            if len(pdata) > 1 and isinstance(pdata[1], dict):
                stats_obj = pdata[1].get("player_stats", {})
                player.stats = self._parse_stats_from_json(stats_obj)
            players.append(player)
        return players

    def _parse_player_from_json(self, attrs: list) -> Player:
        """Parse player attributes from Yahoo's JSON array format."""
        name = ""
        player_key = ""
        team_abbr = ""
        positions: list[str] = []
        status = "healthy"
        percent_owned = 0.0
        fantasy_team = None

        for attr in attrs:
            if not isinstance(attr, dict):
                continue
            if "player_key" in attr:
                player_key = attr["player_key"]
            if "name" in attr:
                n = attr["name"]
                name = f"{n.get('first', '')} {n.get('last', '')}".strip()
            if "editorial_team_abbr" in attr:
                team_abbr = attr["editorial_team_abbr"]
            if "display_position" in attr:
                positions = [p.strip() for p in attr["display_position"].split(",")]
            if "status" in attr:
                status = attr["status"] or "healthy"
            if "percent_owned" in attr:
                po = attr["percent_owned"]
                if isinstance(po, dict):
                    percent_owned = float(po.get("value", 0))
                elif isinstance(po, list):
                    for item in po:
                        if isinstance(item, dict) and "value" in item:
                            percent_owned = float(item["value"])
            if "ownership" in attr:
                own = attr["ownership"]
                if isinstance(own, dict) and own.get("ownership_type") == "team":
                    fantasy_team = own.get("owner_team_key")

        return Player(
            player_key=player_key,
            name=name,
            team=team_abbr,
            positions=positions,
            status=status,
            percent_owned=percent_owned,
            current_fantasy_team=fantasy_team,
            stats={},
            projected_stats=None,
        )

    def _parse_stats_from_json(self, stats_obj: dict) -> dict[str, float]:
        """Parse player stats from Yahoo JSON stats object."""
        result: dict[str, float] = {}
        if not isinstance(stats_obj, dict):
            return result
        stats_wrapper = stats_obj.get("stats", [])
        for entry in stats_wrapper:
            if not isinstance(entry, dict):
                continue
            stat = entry.get("stat", {})
            sid = str(stat.get("stat_id", ""))
            val = stat.get("value", "0")
            try:
                result[sid] = float(val) if val else 0.0
            except (ValueError, TypeError):
                result[sid] = 0.0
        return result

    def _parse_standings_response(self, resp: dict) -> list[Team]:
        """Parse standings response into list of Team."""
        teams: list[Team] = []
        fc = resp.get("fantasy_content", {})
        league_arr = fc.get("league", [])
        if not isinstance(league_arr, list) or len(league_arr) < 2:
            return []
        standings_obj = league_arr[1].get("standings", [])
        if not isinstance(standings_obj, list) or not standings_obj:
            return []
        teams_data = standings_obj[0].get("teams", {}) if isinstance(standings_obj[0], dict) else {}

        for key, value in teams_data.items():
            if key == "count" or not isinstance(value, dict):
                continue
            team_info = value.get("team", [])
            if not isinstance(team_info, list) or len(team_info) < 3:
                continue
            attrs = team_info[0] if isinstance(team_info[0], list) else [team_info[0]]
            standings_data = team_info[2] if len(team_info) > 2 else {}

            name = ""
            team_key = ""
            manager = ""
            for attr in attrs:
                if not isinstance(attr, dict):
                    continue
                if "name" in attr:
                    name = attr["name"]
                if "team_key" in attr:
                    team_key = attr["team_key"]
                if "managers" in attr:
                    mgrs = attr["managers"]
                    if isinstance(mgrs, list) and mgrs:
                        manager = mgrs[0].get("manager", {}).get("nickname", "")

            ts = standings_data.get("team_standings", {})
            ot = ts.get("outcome_totals", {})
            teams.append(
                Team(
                    team_key=team_key,
                    name=name,
                    manager=manager,
                    wins=int(ot.get("wins", 0)),
                    losses=int(ot.get("losses", 0)),
                    ties=int(ot.get("ties", 0)),
                    points_for=float(ts.get("points_for", 0)),
                    points_against=float(ts.get("points_against", 0)),
                    standing=int(ts.get("rank", 0)),
                )
            )
        return teams

    def _parse_scoreboard_response(self, resp: dict) -> list[Matchup]:
        """Parse scoreboard into Matchup list."""
        matchups: list[Matchup] = []
        fc = resp.get("fantasy_content", {})
        league_arr = fc.get("league", [])
        if not isinstance(league_arr, list) or len(league_arr) < 2:
            return []
        sb = league_arr[1].get("scoreboard", {})
        ms = sb.get("0", sb).get("matchups", {}) if isinstance(sb, dict) else {}
        for key in ms:
            if key == "count":
                continue
            m = ms[key].get("matchup", {})
            teams_in_matchup = m.get("0", m).get("teams", {}) if isinstance(m, dict) else {}
            team_keys: list[str] = []
            for tk in teams_in_matchup:
                if tk == "count":
                    continue
                t = teams_in_matchup[tk].get("team", [[]])
                for attr in (t[0] if isinstance(t[0], list) else [t[0]]):
                    if isinstance(attr, dict) and "team_key" in attr:
                        team_keys.append(attr["team_key"])
            if len(team_keys) >= 2:
                matchups.append(
                    Matchup(
                        week=int(m.get("week", 0)),
                        team_key=team_keys[0],
                        opponent_key=team_keys[1],
                    )
                )
        return matchups

    def _parse_teams_list(self, resp: dict) -> list[dict]:
        """Parse teams response for ownership detection."""
        result: list[dict] = []
        fc = resp.get("fantasy_content", {})
        league_arr = fc.get("league", [])
        if not isinstance(league_arr, list) or len(league_arr) < 2:
            return []
        teams_obj = league_arr[1].get("teams", {})
        for key in teams_obj:
            if key == "count":
                continue
            t = teams_obj[key].get("team", [])
            attrs = t[0] if isinstance(t, list) and t and isinstance(t[0], list) else (t[0:1] if isinstance(t, list) else [])
            info: dict[str, Any] = {}
            for attr in (attrs if isinstance(attrs, list) else [attrs]):
                if isinstance(attr, dict):
                    info.update(attr)
            result.append(info)
        return result

    # -- serialization helpers for caching -----------------------------------

    def _player_to_dict(self, p: Player) -> dict:
        return {
            "player_key": p.player_key, "name": p.name, "team": p.team,
            "positions": p.positions, "status": p.status,
            "percent_owned": p.percent_owned,
            "current_fantasy_team": p.current_fantasy_team,
            "stats": p.stats, "projected_stats": p.projected_stats,
        }

    def _dict_to_player(self, d: dict) -> Player:
        return Player(**d)

    def _roster_to_dict(self, r: Roster) -> dict:
        return {
            "team_key": r.team_key,
            "players": [
                {"player": self._player_to_dict(rp.player),
                 "selected_position": rp.selected_position,
                 "is_starting": rp.is_starting}
                for rp in r.players
            ],
        }

    def _dict_to_roster(self, d: dict) -> Roster:
        return Roster(
            team_key=d["team_key"],
            players=[
                RosterPlayer(
                    player=self._dict_to_player(rp["player"]),
                    selected_position=rp["selected_position"],
                    is_starting=rp["is_starting"],
                )
                for rp in d["players"]
            ],
        )

    def _league_to_dict(self, lg: League) -> dict:
        return {
            "league_key": lg.league_key, "name": lg.name, "sport": lg.sport,
            "season": lg.season, "num_teams": lg.num_teams,
            "scoring_type": lg.scoring_type, "scoring_period": lg.scoring_period,
            "roster_positions": lg.roster_positions,
            "stat_categories": [
                {"stat_id": sc.stat_id, "name": sc.name,
                 "display_name": sc.display_name, "sort_order": sc.sort_order,
                 "position_type": sc.position_type,
                 "is_only_display": sc.is_only_display,
                 "value": sc.value, "is_category": sc.is_category}
                for sc in lg.stat_categories
            ],
            "current_week": lg.current_week,
        }

    def _dict_to_league(self, d: dict) -> League:
        return League(
            league_key=d["league_key"], name=d["name"], sport=d["sport"],
            season=d["season"], num_teams=d["num_teams"],
            scoring_type=d["scoring_type"], scoring_period=d["scoring_period"],
            roster_positions=d["roster_positions"],
            stat_categories=[StatCategory(**sc) for sc in d["stat_categories"]],
            current_week=d["current_week"],
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer && python -m pytest tests/test_client.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add yfantasy/client.py tests/test_client.py
git commit -m "feat: add Yahoo API client with caching and response parsing"
```

---

## Task 7: Scoring Engine

**Files:**
- Create: `yfantasy/scoring.py`
- Create: `tests/test_scoring.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for yfantasy scoring engine."""

from yfantasy.scoring import ScoringEngine
from yfantasy.models import League, Player, StatCategory


def _points_league():
    return League(
        league_key="461.l.12345",
        name="Points League",
        sport="nfl",
        season="2025",
        num_teams=10,
        scoring_type="point",
        scoring_period="weekly",
        roster_positions=["QB", "RB", "WR", "BN"],
        stat_categories=[
            StatCategory("4", "Passing Yards", "PaYd", "1", "P", False, 0.04, False),
            StatCategory("5", "Passing TDs", "PaTD", "1", "P", False, 4.0, False),
            StatCategory("9", "Rushing Yards", "RuYd", "1", "P", False, 0.1, False),
        ],
        current_week=5,
    )


def _category_league():
    return League(
        league_key="465.l.34948",
        name="Category League",
        sport="nhl",
        season="2025",
        num_teams=12,
        scoring_type="head",
        scoring_period="daily",
        roster_positions=["C", "LW", "D", "G", "BN"],
        stat_categories=[
            StatCategory("1", "Goals", "G", "1", "P", False, None, True),
            StatCategory("2", "Assists", "A", "1", "P", False, None, True),
            StatCategory("14", "SOG", "SOG", "1", "P", False, None, True),
        ],
        current_week=20,
    )


def _player(stats, projected=None):
    return Player(
        player_key="465.p.1",
        name="Test Player",
        team="TST",
        positions=["C"],
        status="healthy",
        percent_owned=50.0,
        current_fantasy_team=None,
        stats=stats,
        projected_stats=projected,
    )


def test_points_league_value():
    engine = ScoringEngine(_points_league())
    # 300 passing yards * 0.04 = 12, 2 passing TDs * 4 = 8, 50 rush yards * 0.1 = 5
    p = _player({"4": 300.0, "5": 2.0, "9": 50.0})
    assert engine.player_value(p) == 25.0


def test_points_league_projected_value():
    engine = ScoringEngine(_points_league())
    p = _player({"4": 100.0}, projected={"4": 300.0, "5": 2.0, "9": 50.0})
    assert engine.projected_value(p) == 25.0


def test_points_league_projected_value_falls_back_to_actual():
    engine = ScoringEngine(_points_league())
    p = _player({"4": 300.0, "5": 2.0, "9": 50.0})
    assert engine.projected_value(p) == 25.0


def test_category_league_value():
    engine = ScoringEngine(_category_league())
    p = _player({"1": 30.0, "2": 40.0, "14": 200.0})
    # Category leagues use z-scores; with one player, z-scores are 0
    # Just verify it returns a float without error
    val = engine.player_value(p)
    assert isinstance(val, float)


def test_value_above_replacement():
    league = _points_league()
    engine = ScoringEngine(league)
    star = _player({"4": 300.0, "5": 3.0, "9": 80.0})
    bench = _player({"4": 150.0, "5": 1.0, "9": 30.0})
    engine.set_player_pool([star, bench])
    var = engine.value_above_replacement(star, "QB")
    assert var > 0


def test_empty_stats_returns_zero():
    engine = ScoringEngine(_points_league())
    p = _player({})
    assert engine.player_value(p) == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer && python -m pytest tests/test_scoring.py -v`
Expected: FAIL

- [ ] **Step 3: Implement scoring.py**

```python
"""Scoring engine — calculates fantasy value from stats using league-specific rules."""

from __future__ import annotations

import math
from typing import Optional

from yfantasy.models import League, Player, StatCategory


class ScoringEngine:
    """Calculate fantasy point values using league scoring settings."""

    def __init__(self, league: League):
        self.league = league
        self._scoring_cats = [c for c in league.stat_categories if c.is_scoring]
        self._pool: list[Player] = []
        self._pool_means: dict[str, float] = {}
        self._pool_stds: dict[str, float] = {}

    def set_player_pool(self, players: list[Player]) -> None:
        """Set the player pool for z-score / replacement-level calculations."""
        self._pool = players
        self._compute_pool_stats()

    def player_value(self, player: Player) -> float:
        """Calculate total fantasy value from actual stats."""
        return self._value_from_stats(player.stats)

    def projected_value(self, player: Player) -> float:
        """Calculate total fantasy value from projected stats, falling back to actual."""
        stats = player.projected_stats if player.projected_stats else player.stats
        return self._value_from_stats(stats)

    def value_above_replacement(self, player: Player, position: str) -> float:
        """How much better than a replacement-level player at this position."""
        player_val = self.projected_value(player)
        replacement_val = self._replacement_value(position)
        return player_val - replacement_val

    # -- internals -----------------------------------------------------------

    def _value_from_stats(self, stats: dict[str, float]) -> float:
        if self.league.scoring_type in ("point", "points"):
            return self._points_value(stats)
        else:
            return self._category_value(stats)

    def _points_value(self, stats: dict[str, float]) -> float:
        total = 0.0
        for cat in self._scoring_cats:
            if cat.value is not None:
                total += stats.get(cat.stat_id, 0.0) * cat.value
        return round(total, 2)

    def _category_value(self, stats: dict[str, float]) -> float:
        """Z-score based value for category leagues."""
        if not self._pool_stds:
            # Without a pool, just sum raw stats (basic fallback)
            return sum(stats.get(c.stat_id, 0.0) for c in self._scoring_cats)

        total_z = 0.0
        for cat in self._scoring_cats:
            val = stats.get(cat.stat_id, 0.0)
            mean = self._pool_means.get(cat.stat_id, 0.0)
            std = self._pool_stds.get(cat.stat_id, 1.0)
            if std > 0:
                z = (val - mean) / std
                # Invert z-score for stats where lower is better
                if cat.sort_order == "0":
                    z = -z
                total_z += z
        return round(total_z, 4)

    def _replacement_value(self, position: str) -> float:
        """Estimate replacement-level value for a position."""
        eligible = [
            p for p in self._pool if position in p.positions
        ]
        if not eligible:
            return 0.0

        values = sorted(
            [self.projected_value(p) for p in eligible], reverse=True
        )
        # Replacement level = value at the edge of startable players
        # Roughly: number of teams * slots for this position
        slots = self.league.roster_positions.count(position) * self.league.num_teams
        idx = min(slots, len(values) - 1)
        return values[idx] if idx < len(values) else 0.0

    def _compute_pool_stats(self) -> None:
        """Pre-compute mean and std for each stat category across the player pool."""
        for cat in self._scoring_cats:
            vals = [p.stats.get(cat.stat_id, 0.0) for p in self._pool if p.stats]
            if not vals:
                self._pool_means[cat.stat_id] = 0.0
                self._pool_stds[cat.stat_id] = 1.0
                continue
            mean = sum(vals) / len(vals)
            variance = sum((v - mean) ** 2 for v in vals) / max(len(vals) - 1, 1)
            self._pool_means[cat.stat_id] = mean
            self._pool_stds[cat.stat_id] = math.sqrt(variance) if variance > 0 else 1.0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer && python -m pytest tests/test_scoring.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add yfantasy/scoring.py tests/test_scoring.py
git commit -m "feat: add scoring engine (points + category z-score + replacement value)"
```

---

## Task 8: Projections Module

**Files:**
- Create: `yfantasy/projections.py`
- Create: `tests/test_projections.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for yfantasy projections module."""

from unittest.mock import MagicMock
from yfantasy.projections import YahooProjectionProvider, ProjectionProvider
from yfantasy.models import League, StatCategory


def _league():
    return League(
        league_key="465.l.34948",
        name="Test",
        sport="nhl",
        season="2025",
        num_teams=12,
        scoring_type="head",
        scoring_period="daily",
        roster_positions=["C"],
        stat_categories=[StatCategory("1", "Goals", "G", "1", "P", False, None, True)],
        current_week=20,
    )


def test_yahoo_provider_satisfies_protocol():
    mock_client = MagicMock()
    provider = YahooProjectionProvider(mock_client)
    # Verify it matches the Protocol
    assert hasattr(provider, "get_projections")


def test_yahoo_provider_returns_dict():
    mock_client = MagicMock()
    mock_client._request.return_value = {
        "fantasy_content": {
            "league": [
                {},
                {
                    "players": {
                        "0": {
                            "player": [
                                [{"player_key": "465.p.1"}],
                                {"player_stats": {"stats": [{"stat": {"stat_id": "1", "value": "25"}}]}},
                            ]
                        },
                        "count": 1,
                    }
                },
            ]
        }
    }
    provider = YahooProjectionProvider(mock_client)
    result = provider.get_projections(["465.p.1"], _league())
    assert isinstance(result, dict)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer && python -m pytest tests/test_projections.py -v`
Expected: FAIL

- [ ] **Step 3: Implement projections.py**

```python
"""Projection providers for yfantasy — pluggable interface."""

from __future__ import annotations

import logging
from typing import Protocol, TYPE_CHECKING

from yfantasy.models import League

if TYPE_CHECKING:
    from yfantasy.client import YahooClient

logger = logging.getLogger(__name__)


class ProjectionProvider(Protocol):
    """Interface for projection data sources."""

    def get_projections(
        self, player_keys: list[str], league: League
    ) -> dict[str, dict[str, float]]:
        """Return {player_key: {stat_id: projected_value}} for given players."""
        ...


class YahooProjectionProvider:
    """Fetch projections from Yahoo's season stats endpoint."""

    def __init__(self, client: "YahooClient"):
        self._client = client

    def get_projections(
        self, player_keys: list[str], league: League
    ) -> dict[str, dict[str, float]]:
        """Fetch projected stats from Yahoo for the given players."""
        result: dict[str, dict[str, float]] = {}

        # Batch in groups of 25 (Yahoo API limit)
        for i in range(0, len(player_keys), 25):
            batch = player_keys[i : i + 25]
            keys_param = ",".join(batch)
            try:
                resp = self._client._request(
                    f"players;player_keys={keys_param}/stats;type=season"
                )
                fc = resp.get("fantasy_content", {})
                players_obj = fc.get("players", {})
                for key in players_obj:
                    if key == "count":
                        continue
                    pdata = players_obj[key].get("player", [])
                    if not isinstance(pdata, list) or len(pdata) < 2:
                        continue
                    # Extract player_key
                    attrs = pdata[0] if isinstance(pdata[0], list) else [pdata[0]]
                    pk = ""
                    for attr in attrs:
                        if isinstance(attr, dict) and "player_key" in attr:
                            pk = attr["player_key"]
                    if pk:
                        stats_obj = pdata[1].get("player_stats", {}) if isinstance(pdata[1], dict) else {}
                        result[pk] = self._client._parse_stats_from_json(stats_obj)
            except Exception:
                logger.warning("Failed to fetch projections for batch starting at %d", i)

        return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer && python -m pytest tests/test_projections.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add yfantasy/projections.py tests/test_projections.py
git commit -m "feat: add pluggable projection provider with Yahoo implementation"
```

---

## Task 9: Writer Module (API Writes)

**Files:**
- Create: `yfantasy/writer.py`
- Create: `tests/test_writer.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for yfantasy writer module."""

from unittest.mock import patch, MagicMock
from yfantasy.writer import YahooWriter
from yfantasy.config import Config
from yfantasy.models import WriteResult


def _make_writer(tmp_path):
    config = Config(config_dir=tmp_path / ".yfantasy")
    config.set("auth", "client_id", "test_id")
    config.set("auth", "client_secret", "test_secret")
    config.set("auth", "access_token", "test_token")
    config.set("auth", "refresh_token", "test_ref")
    config.set("auth", "token_expiry", "2099-01-01T00:00:00")
    return YahooWriter(config)


@patch("yfantasy.writer.requests.put")
def test_set_lineup(mock_put, tmp_path):
    writer = _make_writer(tmp_path)
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_put.return_value = mock_resp

    result = writer.set_lineup("465.l.34948.t.1", [("465.p.6619", "C")])
    assert isinstance(result, WriteResult)
    assert result.success is True
    assert mock_put.called
    # Verify XML was sent
    call_kwargs = mock_put.call_args
    assert "application/xml" in str(call_kwargs)


@patch("yfantasy.writer.requests.post")
def test_add_player(mock_post, tmp_path):
    writer = _make_writer(tmp_path)
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 201
    mock_post.return_value = mock_resp

    result = writer.add_player("465.l.34948", "465.p.9999")
    assert result.success is True


@patch("yfantasy.writer.requests.post")
def test_add_drop_player(mock_post, tmp_path):
    writer = _make_writer(tmp_path)
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 201
    mock_post.return_value = mock_resp

    result = writer.add_player("465.l.34948", "465.p.9999", drop_player_key="465.p.1111")
    assert result.success is True
    body = mock_post.call_args[1].get("data", "")
    assert "465.p.9999" in body
    assert "465.p.1111" in body


@patch("yfantasy.writer.requests.put")
def test_set_lineup_failure(mock_put, tmp_path):
    writer = _make_writer(tmp_path)
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 400
    mock_resp.text = "Invalid roster position"
    mock_put.return_value = mock_resp

    result = writer.set_lineup("465.l.34948.t.1", [("465.p.6619", "INVALID")])
    assert result.success is False
    assert "Invalid" in result.message or "400" in result.message
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer && python -m pytest tests/test_writer.py -v`
Expected: FAIL

- [ ] **Step 3: Implement writer.py**

```python
"""Yahoo Fantasy Sports API writer — all mutation operations."""

from __future__ import annotations

import logging
from typing import Optional

import requests

from yfantasy.auth import YahooAuth
from yfantasy.config import Config
from yfantasy.models import WriteResult

logger = logging.getLogger(__name__)

_BASE_URL = "https://fantasysports.yahooapis.com/fantasy/v2"


class YahooWriter:
    """Write operations for Yahoo Fantasy Sports API."""

    def __init__(self, config: Config):
        self.config = config
        self.auth = YahooAuth(config)

    def set_lineup(
        self, team_key: str, moves: list[tuple[str, str]]
    ) -> WriteResult:
        """Change player positions in the lineup.

        Args:
            team_key: e.g. "465.l.34948.t.1"
            moves: list of (player_key, new_position) tuples
        """
        players_xml = ""
        for player_key, position in moves:
            players_xml += (
                f"<player>"
                f"<player_key>{player_key}</player_key>"
                f"<position>{position}</position>"
                f"</player>"
            )

        xml = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f"<fantasy_content>"
            f"<roster>"
            f"<coverage_type>date</coverage_type>"
            f"<players>{players_xml}</players>"
            f"</roster>"
            f"</fantasy_content>"
        )

        return self._put(f"team/{team_key}/roster", xml)

    def add_player(
        self,
        league_key: str,
        player_key: str,
        drop_player_key: Optional[str] = None,
    ) -> WriteResult:
        """Add a player (optionally dropping another)."""
        if drop_player_key:
            xml = (
                f'<?xml version="1.0" encoding="UTF-8"?>'
                f"<fantasy_content>"
                f"<transaction>"
                f"<type>add/drop</type>"
                f"<players>"
                f"<player>"
                f"<player_key>{player_key}</player_key>"
                f"<transaction_data><type>add</type></transaction_data>"
                f"</player>"
                f"<player>"
                f"<player_key>{drop_player_key}</player_key>"
                f"<transaction_data><type>drop</type></transaction_data>"
                f"</player>"
                f"</players>"
                f"</transaction>"
                f"</fantasy_content>"
            )
        else:
            xml = (
                f'<?xml version="1.0" encoding="UTF-8"?>'
                f"<fantasy_content>"
                f"<transaction>"
                f"<type>add</type>"
                f"<players>"
                f"<player>"
                f"<player_key>{player_key}</player_key>"
                f"<transaction_data><type>add</type></transaction_data>"
                f"</player>"
                f"</players>"
                f"</transaction>"
                f"</fantasy_content>"
            )

        return self._post(f"league/{league_key}/transactions", xml)

    def propose_trade(
        self,
        league_key: str,
        my_team_key: str,
        my_player_keys: list[str],
        their_player_keys: list[str],
        their_team_key: str,
    ) -> WriteResult:
        """Propose a trade to another team."""
        players_xml = ""
        for pk in my_player_keys:
            players_xml += (
                f"<player>"
                f"<player_key>{pk}</player_key>"
                f"<transaction_data>"
                f"<type>pending_trade</type>"
                f"<source_team_key>{my_team_key}</source_team_key>"
                f"<destination_team_key>{their_team_key}</destination_team_key>"
                f"</transaction_data>"
                f"</player>"
            )
        for pk in their_player_keys:
            players_xml += (
                f"<player>"
                f"<player_key>{pk}</player_key>"
                f"<transaction_data>"
                f"<type>pending_trade</type>"
                f"<source_team_key>{their_team_key}</source_team_key>"
                f"<destination_team_key>{my_team_key}</destination_team_key>"
                f"</transaction_data>"
                f"</player>"
            )

        xml = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f"<fantasy_content>"
            f"<transaction>"
            f"<type>trade</type>"
            f"<trader_team_key>{my_team_key}</trader_team_key>"
            f"<tradee_team_key>{their_team_key}</tradee_team_key>"
            f"<players>{players_xml}</players>"
            f"</transaction>"
            f"</fantasy_content>"
        )

        return self._post(f"league/{league_key}/transactions", xml)

    def cancel_transaction(
        self, league_key: str, transaction_key: str
    ) -> WriteResult:
        """Cancel a pending transaction."""
        return self._delete(
            f"league/{league_key}/transactions/{transaction_key}"
        )

    # -- HTTP helpers --------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        token = self.auth.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/xml",
        }

    def _put(self, endpoint: str, xml_body: str) -> WriteResult:
        url = f"{_BASE_URL}/{endpoint}"
        logger.info("PUT %s", url)
        logger.debug("Body: %s", xml_body)
        resp = requests.put(url, data=xml_body, headers=self._headers())
        if resp.ok:
            return WriteResult(success=True, message="OK")
        return WriteResult(success=False, message=f"{resp.status_code}: {resp.text[:200]}")

    def _post(self, endpoint: str, xml_body: str) -> WriteResult:
        url = f"{_BASE_URL}/{endpoint}"
        logger.info("POST %s", url)
        logger.debug("Body: %s", xml_body)
        resp = requests.post(url, data=xml_body, headers=self._headers())
        if resp.ok:
            return WriteResult(success=True, message="OK")
        return WriteResult(success=False, message=f"{resp.status_code}: {resp.text[:200]}")

    def _delete(self, endpoint: str) -> WriteResult:
        url = f"{_BASE_URL}/{endpoint}"
        logger.info("DELETE %s", url)
        resp = requests.delete(url, headers=self._headers())
        if resp.ok:
            return WriteResult(success=True, message="OK")
        return WriteResult(success=False, message=f"{resp.status_code}: {resp.text[:200]}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer && python -m pytest tests/test_writer.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add yfantasy/writer.py tests/test_writer.py
git commit -m "feat: add Yahoo API writer for roster moves, add/drop, trades"
```

---

## Task 10: CLI Display Helpers

**Files:**
- Create: `yfantasy/cli/display.py`

- [ ] **Step 1: Implement display.py**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add yfantasy/cli/display.py
git commit -m "feat: add Rich display helpers for roster, standings, week plan"
```

---

## Task 11: CLI Init & League Commands

**Files:**
- Create: `yfantasy/cli/commands/init_cmd.py`
- Create: `yfantasy/cli/commands/league.py`
- Create: `yfantasy/cli/commands/__init__.py`
- Modify: `yfantasy/cli/app.py`

Note: The init command file is named `init_cmd.py` to avoid shadowing Python's built-in `init`.

- [ ] **Step 1: Implement init_cmd.py**

```python
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

    # Step 1: Get API credentials
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

    # Step 2: OAuth flow
    console.print("\n[bold]Authenticating with Yahoo...[/]")
    auth = YahooAuth(config)
    try:
        auth.run_oauth_flow()
        console.print("[green]Authenticated successfully![/]\n")
    except Exception as e:
        console.print(f"[red]Authentication failed:[/] {e}")
        raise typer.Exit(1)

    # Step 3: Show leagues and pick default
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
```

- [ ] **Step 2: Implement league.py**

```python
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
```

- [ ] **Step 3: Update yfantasy/cli/commands/__init__.py**

```python
"""CLI command modules."""
```

- [ ] **Step 4: Update yfantasy/cli/app.py to wire in commands**

```python
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


# Register sub-command groups
from yfantasy.cli.commands.league import league_app

app.add_typer(league_app, name="league")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Test manually**

Run:
```bash
cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer
pip install -e ".[dev]"
yfantasy --help
yfantasy version
yfantasy league --help
```
Expected: Help text shows init, version, league commands

- [ ] **Step 6: Commit**

```bash
git add yfantasy/cli/
git commit -m "feat: add init and league CLI commands with Rich output"
```

---

## Task 12: Roster & Lineup Commands

**Files:**
- Create: `yfantasy/cli/commands/roster.py`
- Modify: `yfantasy/cli/app.py`

- [ ] **Step 1: Implement roster.py**

```python
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

    # Find player by fuzzy name match
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
```

- [ ] **Step 2: Register in app.py**

Add to `yfantasy/cli/app.py` after the league import:

```python
from yfantasy.cli.commands.roster import roster_app, lineup_app

app.add_typer(roster_app, name="roster")
app.add_typer(lineup_app, name="lineup")
```

- [ ] **Step 3: Commit**

```bash
git add yfantasy/cli/commands/roster.py yfantasy/cli/app.py
git commit -m "feat: add roster and lineup CLI commands"
```

---

## Task 13: Optimizer (Week-Level)

**Files:**
- Create: `yfantasy/optimizer.py`
- Create: `tests/test_optimizer.py`
- Create: `yfantasy/cli/commands/optimize.py`
- Modify: `yfantasy/cli/app.py`

- [ ] **Step 1: Write optimizer tests**

```python
"""Tests for yfantasy week-level optimizer."""

from datetime import date
from yfantasy.optimizer import Optimizer
from yfantasy.models import (
    DayPlan, League, Player, Roster, RosterPlayer, StatCategory, WeekPlan,
)
from yfantasy.scoring import ScoringEngine


def _league(scoring_period="daily"):
    return League(
        league_key="465.l.34948",
        name="Test",
        sport="nhl",
        season="2025",
        num_teams=12,
        scoring_type="point",
        scoring_period=scoring_period,
        roster_positions=["C", "LW", "BN"],
        stat_categories=[
            StatCategory("1", "Goals", "G", "1", "P", False, 3.0, False),
            StatCategory("2", "Assists", "A", "1", "P", False, 2.0, False),
        ],
        current_week=20,
    )


def _player(key, name, positions, stats, projected=None):
    return Player(
        player_key=key, name=name, team="TST", positions=positions,
        status="healthy", percent_owned=50.0, current_fantasy_team="465.l.34948.t.1",
        stats=stats, projected_stats=projected or stats,
    )


def test_optimize_lineup_single_day():
    league = _league("weekly")
    engine = ScoringEngine(league)

    p1 = _player("465.p.1", "Star Center", ["C", "LW"], {"1": 30.0, "2": 40.0})
    p2 = _player("465.p.2", "OK Wing", ["LW"], {"1": 10.0, "2": 15.0})
    p3 = _player("465.p.3", "Bench Guy", ["C"], {"1": 5.0, "2": 5.0})

    roster = Roster(
        team_key="465.l.34948.t.1",
        players=[
            RosterPlayer(p1, "BN", False),
            RosterPlayer(p2, "C", True),  # Misplaced wing at C
            RosterPlayer(p3, "LW", True),  # Bench guy starting
        ],
    )

    optimizer = Optimizer(league, engine)
    plan = optimizer.optimize_lineup(roster)
    assert isinstance(plan, WeekPlan)
    assert plan.total_projected_points >= plan.baseline_points


def test_optimize_with_streaming():
    league = _league("daily")
    engine = ScoringEngine(league)

    p1 = _player("465.p.1", "Star", ["C"], {"1": 30.0, "2": 40.0})
    p2 = _player("465.p.2", "Meh", ["LW"], {"1": 2.0, "2": 3.0})
    p3 = _player("465.p.3", "Bench", ["C", "LW"], {"1": 1.0, "2": 1.0})

    roster = Roster(
        team_key="465.l.34948.t.1",
        players=[
            RosterPlayer(p1, "C", True),
            RosterPlayer(p2, "LW", True),
            RosterPlayer(p3, "BN", False),
        ],
    )

    fa = _player("465.p.99", "Hot FA", ["LW"], {"1": 15.0, "2": 20.0})
    fa.current_fantasy_team = None

    today = date.today()
    schedule = {
        today: {"465.p.1", "465.p.2", "465.p.99"},
    }

    optimizer = Optimizer(league, engine)
    plan = optimizer.optimize_with_streaming(
        roster, free_agents=[fa], schedule=schedule,
        remaining_adds=3, days=[today],
    )
    assert isinstance(plan, WeekPlan)


def test_empty_roster():
    league = _league()
    engine = ScoringEngine(league)
    roster = Roster(team_key="465.l.34948.t.1", players=[])
    optimizer = Optimizer(league, engine)
    plan = optimizer.optimize_lineup(roster)
    assert plan.total_projected_points == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer && python -m pytest tests/test_optimizer.py -v`
Expected: FAIL

- [ ] **Step 3: Implement optimizer.py**

```python
"""Week-level lineup and roster optimizer for yfantasy."""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from yfantasy.models import (
    DayPlan,
    League,
    Player,
    Roster,
    RosterPlayer,
    WeekPlan,
    _INACTIVE_POSITIONS,
)
from yfantasy.scoring import ScoringEngine

logger = logging.getLogger(__name__)


class Optimizer:
    """Optimizes lineups and roster moves across a week."""

    def __init__(self, league: League, engine: ScoringEngine):
        self.league = league
        self.engine = engine

    def optimize_lineup(self, roster: Roster) -> WeekPlan:
        """Optimize the lineup for a single day/week (no streaming)."""
        if not roster.players:
            return WeekPlan(
                days=[], transactions_used=0, transactions_remaining=0,
                total_projected_points=0.0, baseline_points=0.0, improvement=0.0,
            )

        baseline = self._score_current_lineup(roster)
        optimal = self._assign_optimal_positions(roster.players)
        optimal_score = sum(
            self.engine.projected_value(rp.player)
            for rp in optimal if rp.is_starting
        )

        day_plan = DayPlan(
            date=date.today(),
            lineup=optimal,
            projected_points=optimal_score,
        )

        return WeekPlan(
            days=[day_plan],
            transactions_used=0,
            transactions_remaining=0,
            total_projected_points=optimal_score,
            baseline_points=baseline,
            improvement=round(optimal_score - baseline, 2),
        )

    def optimize_with_streaming(
        self,
        roster: Roster,
        free_agents: list[Player],
        schedule: dict[date, set[str]],
        remaining_adds: int,
        days: list[date],
    ) -> WeekPlan:
        """Week-level optimization with streaming (add/drops across days).

        Args:
            roster: Current roster
            free_agents: Available free agents
            schedule: {date: set of player_keys with games that day}
            remaining_adds: Transaction budget for the rest of the week
            days: Dates to optimize across
        """
        current_players = {rp.player.player_key: rp.player for rp in roster.players}
        baseline = sum(
            self.engine.projected_value(rp.player)
            for rp in roster.players if rp.is_starting
        ) * len(days)

        day_plans: list[DayPlan] = []
        adds_used = 0

        for d in days:
            playing_today = schedule.get(d, set())

            # Score current roster players who are playing
            roster_playing = [
                p for pk, p in current_players.items() if pk in playing_today
            ]

            # Find best streaming candidate if budget allows
            best_add: Optional[Player] = None
            best_drop: Optional[Player] = None
            best_gain = 0.0

            if adds_used < remaining_adds and free_agents:
                # Find worst bench player
                bench_players = sorted(
                    [p for p in current_players.values()],
                    key=lambda p: self.engine.projected_value(p),
                )
                if bench_players:
                    worst = bench_players[0]
                    worst_val = self.engine.projected_value(worst)

                    for fa in free_agents:
                        if fa.player_key in current_players:
                            continue
                        if fa.player_key not in playing_today:
                            continue
                        fa_val = self.engine.projected_value(fa)
                        gain = fa_val - worst_val
                        if gain > best_gain:
                            best_gain = gain
                            best_add = fa
                            best_drop = worst

            adds_today: list[Player] = []
            drops_today: list[Player] = []

            if best_add and best_drop and best_gain > 0:
                adds_today.append(best_add)
                drops_today.append(best_drop)
                # Update current players
                del current_players[best_drop.player_key]
                current_players[best_add.player_key] = best_add
                # Remove from FA pool
                free_agents = [fa for fa in free_agents if fa.player_key != best_add.player_key]
                adds_used += 1

            # Build optimal lineup for this day
            today_roster_players = [
                RosterPlayer(p, "BN", False) for p in current_players.values()
            ]
            optimal = self._assign_optimal_positions(today_roster_players)
            day_score = sum(
                self.engine.projected_value(rp.player)
                for rp in optimal if rp.is_starting
            )

            day_plans.append(DayPlan(
                date=d,
                lineup=optimal,
                adds=adds_today,
                drops=drops_today,
                projected_points=day_score,
            ))

        total = sum(dp.projected_points for dp in day_plans)
        return WeekPlan(
            days=day_plans,
            transactions_used=adds_used,
            transactions_remaining=remaining_adds - adds_used,
            total_projected_points=round(total, 2),
            baseline_points=round(baseline, 2),
            improvement=round(total - baseline, 2),
        )

    # -- internals -----------------------------------------------------------

    def _score_current_lineup(self, roster: Roster) -> float:
        return sum(
            self.engine.projected_value(rp.player)
            for rp in roster.players if rp.is_starting
        )

    def _assign_optimal_positions(
        self, players: list[RosterPlayer]
    ) -> list[RosterPlayer]:
        """Greedy assignment: highest-value player gets first pick of slots."""
        active_slots = list(self.league.active_positions)
        bench_slots = [
            p for p in self.league.roster_positions if p in _INACTIVE_POSITIONS
        ]

        # Sort by projected value descending
        ranked = sorted(
            players,
            key=lambda rp: self.engine.projected_value(rp.player),
            reverse=True,
        )

        assigned: list[RosterPlayer] = []
        remaining_slots = list(active_slots)

        for rp in ranked:
            placed = False
            for i, slot in enumerate(remaining_slots):
                if slot in rp.player.positions:
                    assigned.append(RosterPlayer(rp.player, slot, True))
                    remaining_slots.pop(i)
                    placed = True
                    break
            if not placed:
                # Check for utility/flex slots (common in NFL)
                for i, slot in enumerate(remaining_slots):
                    if slot in ("Util", "UTIL", "W/R/T", "FLEX", "F"):
                        assigned.append(RosterPlayer(rp.player, slot, True))
                        remaining_slots.pop(i)
                        placed = True
                        break
            if not placed:
                assigned.append(RosterPlayer(rp.player, "BN", False))

        return assigned
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer && python -m pytest tests/test_optimizer.py -v`
Expected: All PASS

- [ ] **Step 5: Implement CLI command optimize.py**

```python
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
        # Simple lineup optimization
        plan = optimizer.optimize_lineup(roster)
    else:
        # Week-level optimization with streaming
        console.print(f"Optimizing for the next {days} days...")
        today = date.today()
        plan_days = [today + timedelta(days=i) for i in range(days)]

        # Build schedule by fetching roster for each day
        schedule: dict[date, set[str]] = {}
        for d in plan_days:
            day_roster = client.get_roster(team_key, date=d.isoformat())
            playing = {
                rp.player.player_key
                for rp in day_roster.players
                # Players with games show as startable on that date
            }
            schedule[d] = playing

        # Get free agents
        free_agents = client.get_free_agents(league_key, count=50)
        remaining_adds = budget if budget is not None else 7  # Default fallback

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

        # Set today's lineup
        moves = [
            (rp.player.player_key, rp.selected_position)
            for rp in day.lineup if rp.is_starting
        ]
        if moves and confirm("Set today's lineup?", auto=auto):
            writer = YahooWriter(config)
            result = writer.set_lineup(team_key, moves)
            print_write_result(result)
```

- [ ] **Step 6: Register in app.py**

Add to `yfantasy/cli/app.py`:

```python
from yfantasy.cli.commands.optimize import optimize_app

app.add_typer(optimize_app, name="optimize")
```

- [ ] **Step 7: Commit**

```bash
git add yfantasy/optimizer.py yfantasy/cli/commands/optimize.py tests/test_optimizer.py yfantasy/cli/app.py
git commit -m "feat: add week-level optimizer with streaming support"
```

---

## Task 14: Waiver Wire Command

**Files:**
- Create: `yfantasy/waiver.py`
- Create: `yfantasy/cli/commands/waiver.py`
- Modify: `yfantasy/cli/app.py`

- [ ] **Step 1: Implement waiver.py**

```python
"""Waiver wire assistant — rank free agents and build claims."""

from __future__ import annotations

from yfantasy.models import League, Player
from yfantasy.scoring import ScoringEngine


class WaiverAssistant:
    """Rank and evaluate free agents for waiver claims."""

    def __init__(self, league: League, engine: ScoringEngine):
        self.league = league
        self.engine = engine

    def rank_free_agents(
        self, free_agents: list[Player], position: str | None = None
    ) -> list[tuple[Player, float]]:
        """Rank free agents by projected value. Returns (player, value) pairs."""
        filtered = free_agents
        if position:
            filtered = [p for p in free_agents if position in p.positions]

        ranked = [
            (p, self.engine.projected_value(p))
            for p in filtered
        ]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    def suggest_drops(
        self, roster_players: list[Player],
    ) -> list[tuple[Player, float]]:
        """Rank roster players by value ascending (worst first) for drop candidates."""
        ranked = [
            (p, self.engine.projected_value(p))
            for p in roster_players
        ]
        ranked.sort(key=lambda x: x[1])
        return ranked
```

- [ ] **Step 2: Implement CLI waiver.py**

```python
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

    # Find the player in free agents
    from difflib import get_close_matches

    free_agents = client.get_free_agents(league_key, count=100)
    fa_names = {p.name: p for p in free_agents}
    matches = get_close_matches(player_name, fa_names.keys(), n=1, cutoff=0.4)
    if not matches:
        console.print(f"[red]Player not found:[/] {player_name}")
        raise typer.Exit(1)

    add_p = fa_names[matches[0]]

    # Find drop candidate if specified
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
```

- [ ] **Step 3: Register in app.py**

Add to `yfantasy/cli/app.py`:

```python
from yfantasy.cli.commands.waiver import waiver_app

app.add_typer(waiver_app, name="waiver")
```

- [ ] **Step 4: Commit**

```bash
git add yfantasy/waiver.py yfantasy/cli/commands/waiver.py yfantasy/cli/app.py
git commit -m "feat: add waiver wire scan and add commands"
```

---

## Task 15: Trade Analyzer Command

**Files:**
- Create: `yfantasy/trade.py`
- Create: `yfantasy/cli/commands/trade.py`
- Modify: `yfantasy/cli/app.py`

- [ ] **Step 1: Implement trade.py**

```python
"""Trade analysis — evaluate and suggest trades."""

from __future__ import annotations

from dataclasses import dataclass

from yfantasy.models import League, Player
from yfantasy.scoring import ScoringEngine


@dataclass
class TradeEvaluation:
    give_players: list[Player]
    get_players: list[Player]
    give_value: float
    get_value: float
    net_value: float
    verdict: str  # "win", "lose", "fair"


class TradeAnalyzer:
    """Evaluate and suggest trades."""

    def __init__(self, league: League, engine: ScoringEngine):
        self.league = league
        self.engine = engine

    def evaluate(
        self, give: list[Player], get: list[Player]
    ) -> TradeEvaluation:
        """Evaluate a trade proposal."""
        give_val = sum(self.engine.projected_value(p) for p in give)
        get_val = sum(self.engine.projected_value(p) for p in get)
        net = get_val - give_val

        if net > 5:
            verdict = "win"
        elif net < -5:
            verdict = "lose"
        else:
            verdict = "fair"

        return TradeEvaluation(
            give_players=give,
            get_players=get,
            give_value=round(give_val, 2),
            get_value=round(get_val, 2),
            net_value=round(net, 2),
            verdict=verdict,
        )

    def find_sell_high(self, players: list[Player]) -> list[tuple[Player, float]]:
        """Find players performing above projections (sell-high candidates)."""
        candidates = []
        for p in players:
            actual = self.engine.player_value(p)
            projected = self.engine.projected_value(p)
            if projected > 0 and actual > projected * 1.15:
                candidates.append((p, actual - projected))
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates

    def find_buy_low(self, players: list[Player]) -> list[tuple[Player, float]]:
        """Find players performing below projections (buy-low candidates)."""
        candidates = []
        for p in players:
            actual = self.engine.player_value(p)
            projected = self.engine.projected_value(p)
            if projected > 0 and actual < projected * 0.85:
                candidates.append((p, projected - actual))
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates
```

- [ ] **Step 2: Implement CLI trade.py**

```python
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

    # Find players by name across all league players
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
```

- [ ] **Step 3: Register in app.py**

Add to `yfantasy/cli/app.py`:

```python
from yfantasy.cli.commands.trade import trade_app

app.add_typer(trade_app, name="trade")
```

- [ ] **Step 4: Commit**

```bash
git add yfantasy/trade.py yfantasy/cli/commands/trade.py yfantasy/cli/app.py
git commit -m "feat: add trade analyzer with sell-high/buy-low detection"
```

---

## Task 16: Dashboard Command

**Files:**
- Create: `yfantasy/dashboard.py`
- Create: `yfantasy/cli/commands/dashboard.py`
- Modify: `yfantasy/cli/app.py`

- [ ] **Step 1: Implement dashboard.py**

```python
"""Dashboard data assembly for yfantasy."""

from __future__ import annotations

from dataclasses import dataclass, field

from yfantasy.models import Matchup, Player, Roster, Team


@dataclass
class DashboardData:
    standings: list[Team]
    my_team: Team | None
    matchup: Matchup | None
    roster_alerts: list[str]
    top_free_agents: list[tuple[Player, float]]


def build_dashboard(
    standings: list[Team],
    my_team_key: str,
    matchup: Matchup | None,
    roster: Roster,
    top_fa: list[tuple[Player, float]],
) -> DashboardData:
    my_team = next((t for t in standings if t.team_key == my_team_key), None)

    alerts: list[str] = []
    for rp in roster.players:
        if rp.is_starting and rp.player.status not in ("healthy", ""):
            alerts.append(f"{rp.player.name} is {rp.player.status} — consider benching")

    return DashboardData(
        standings=standings,
        my_team=my_team,
        matchup=matchup,
        roster_alerts=alerts,
        top_free_agents=top_fa[:5],
    )
```

- [ ] **Step 2: Implement CLI dashboard.py**

```python
"""yfantasy dashboard — weekly overview."""

from __future__ import annotations

from typing import Optional

import typer
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from yfantasy.cli.display import print_standings
from yfantasy.client import YahooClient
from yfantasy.config import Config
from yfantasy.dashboard import build_dashboard
from yfantasy.scoring import ScoringEngine
from yfantasy.waiver import WaiverAssistant

console = Console()


def dashboard_command(
    week: Optional[int] = typer.Option(None, "--week", "-w"),
    league: Optional[str] = typer.Option(None, "--league", "-l"),
    no_cache: bool = typer.Option(False, "--no-cache"),
) -> None:
    """Show weekly dashboard — standings, matchup, alerts, waiver gems."""
    config = Config()
    league_key = league or config.get("defaults", "league_key")
    if not league_key:
        console.print("[red]No league selected.[/] Run `yfantasy league select`.")
        raise typer.Exit(1)

    client = YahooClient(config, use_cache=not no_cache)
    lg = client.get_league(league_key)
    engine = ScoringEngine(lg)

    team_key = client.get_my_team_key(league_key)
    current_week = week or lg.current_week

    # Fetch data
    standings = client.get_standings(league_key)
    roster = client.get_roster(team_key) if team_key else None

    matchups = client.get_scoreboard(league_key, current_week)
    my_matchup = next((m for m in matchups if team_key and team_key in (m.team_key, m.opponent_key)), None)

    # Top free agents
    assistant = WaiverAssistant(lg, engine)
    free_agents = client.get_free_agents(league_key, count=10)
    ranked_fa = assistant.rank_free_agents(free_agents)

    data = build_dashboard(
        standings=standings,
        my_team_key=team_key or "",
        matchup=my_matchup,
        roster=roster if roster else __import__("yfantasy.models", fromlist=["Roster"]).Roster(team_key="", players=[]),
        top_fa=ranked_fa,
    )

    # Render
    console.print(f"\n[bold]{lg.name}[/] — Week {current_week}\n")

    print_standings(data.standings)

    if data.matchup:
        opp_name = next(
            (t.name for t in standings if t.team_key == data.matchup.opponent_key),
            "Unknown",
        )
        my_name = data.my_team.name if data.my_team else "You"
        console.print(Panel(
            f"{my_name} vs {opp_name}",
            title="This Week's Matchup",
        ))

    if data.roster_alerts:
        alerts = "\n".join(f"  [yellow]![/] {a}" for a in data.roster_alerts)
        console.print(Panel(alerts, title="Roster Alerts"))

    if data.top_free_agents:
        table = Table(title="Waiver Wire Gems")
        table.add_column("Player", min_width=18)
        table.add_column("Pos", width=8)
        table.add_column("Value", width=8, justify="right")
        for p, val in data.top_free_agents:
            table.add_row(p.name, ", ".join(p.positions), f"{val:.1f}")
        console.print(table)
```

- [ ] **Step 3: Register in app.py**

Add to `yfantasy/cli/app.py`:

```python
from yfantasy.cli.commands.dashboard import dashboard_command

app.command(name="dashboard")(dashboard_command)
```

- [ ] **Step 4: Commit**

```bash
git add yfantasy/dashboard.py yfantasy/cli/commands/dashboard.py yfantasy/cli/app.py
git commit -m "feat: add dashboard command with standings, matchup, alerts, waiver gems"
```

---

## Task 17: Interactive Shell

**Files:**
- Create: `yfantasy/cli/shell.py`
- Modify: `yfantasy/cli/app.py`

- [ ] **Step 1: Implement shell.py**

```python
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
```

- [ ] **Step 2: Register in app.py**

Add to `yfantasy/cli/app.py`:

```python
@app.command()
def shell() -> None:
    """Start interactive shell mode."""
    from yfantasy.cli.shell import shell_command

    shell_command()
```

- [ ] **Step 3: Commit**

```bash
git add yfantasy/cli/shell.py yfantasy/cli/app.py
git commit -m "feat: add interactive shell with tab-completion and history"
```

---

## Task 18: Final Integration & README

**Files:**
- Modify: `yfantasy/cli/app.py` (final version with all imports)
- Modify: `README.md`

- [ ] **Step 1: Write final app.py with all commands registered**

Verify `yfantasy/cli/app.py` has all command imports:

```python
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
from yfantasy.cli.commands.dashboard import dashboard_command

app.add_typer(league_app, name="league")
app.add_typer(roster_app, name="roster")
app.add_typer(lineup_app, name="lineup")
app.add_typer(optimize_app, name="optimize")
app.add_typer(waiver_app, name="waiver")
app.add_typer(trade_app, name="trade")
app.command(name="dashboard")(dashboard_command)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run all tests**

Run: `cd /Users/johnathan.vangorp/personal/yahoo-fantasy-analyzer && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 3: Test CLI end-to-end**

Run:
```bash
pip install -e ".[dev]"
yfantasy --help
yfantasy version
yfantasy league --help
yfantasy roster --help
yfantasy optimize --help
yfantasy waiver --help
yfantasy trade --help
yfantasy dashboard --help
yfantasy shell --help
```
Expected: All show help text without errors

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: finalize yfantasy CLI with all commands integrated"
```
