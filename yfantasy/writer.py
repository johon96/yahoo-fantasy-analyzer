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
        """Change player positions in the lineup."""
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
