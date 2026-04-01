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
