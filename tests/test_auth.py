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
