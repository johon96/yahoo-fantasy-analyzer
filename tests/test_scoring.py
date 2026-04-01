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
