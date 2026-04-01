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
