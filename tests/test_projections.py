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
