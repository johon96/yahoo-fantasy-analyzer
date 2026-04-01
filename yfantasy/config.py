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
