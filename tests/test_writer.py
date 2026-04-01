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
