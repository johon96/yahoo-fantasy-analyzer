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
