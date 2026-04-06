"""Yahoo Fantasy Sports API client -- read operations."""

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

# Map Yahoo game IDs -> sport codes
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
            logger.warning("401 -- forcing token refresh")
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
            selected_pos = "BN"
            if isinstance(pos_obj, list):
                for entry in pos_obj:
                    if isinstance(entry, dict) and "position" in entry:
                        selected_pos = entry["position"]
                        break

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
