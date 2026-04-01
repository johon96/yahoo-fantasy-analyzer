"""Tests for yfantasy data models."""

from yfantasy.models import (
    Player,
    RosterPlayer,
    Roster,
    StatCategory,
    League,
    Team,
    Standing,
    Matchup,
    DayPlan,
    WeekPlan,
    WriteResult,
)
from datetime import date


def test_player_creation():
    player = Player(
        player_key="465.p.6619",
        name="Connor McDavid",
        team="EDM",
        positions=["C", "LW"],
        status="healthy",
        percent_owned=99.9,
        current_fantasy_team="465.l.34948.t.1",
        stats={"1": 30.0, "2": 50.0},
        projected_stats={"1": 35.0, "2": 55.0},
    )
    assert player.player_key == "465.p.6619"
    assert player.name == "Connor McDavid"
    assert "C" in player.positions
    assert player.stats["1"] == 30.0


def test_player_is_available():
    free_agent = Player(
        player_key="465.p.1234",
        name="Free Agent",
        team="NYR",
        positions=["D"],
        status="healthy",
        percent_owned=10.0,
        current_fantasy_team=None,
        stats={},
        projected_stats=None,
    )
    assert free_agent.is_available is True

    rostered = Player(
        player_key="465.p.5678",
        name="Rostered Player",
        team="TOR",
        positions=["C"],
        status="healthy",
        percent_owned=90.0,
        current_fantasy_team="465.l.34948.t.1",
        stats={},
        projected_stats=None,
    )
    assert rostered.is_available is False


def test_roster_player():
    player = Player(
        player_key="465.p.6619",
        name="Connor McDavid",
        team="EDM",
        positions=["C", "LW"],
        status="healthy",
        percent_owned=99.9,
        current_fantasy_team=None,
        stats={},
        projected_stats=None,
    )
    rp = RosterPlayer(player=player, selected_position="C", is_starting=True)
    assert rp.is_starting is True
    assert rp.selected_position == "C"


def test_stat_category_is_scoring():
    scoring_cat = StatCategory(
        stat_id="1",
        name="Goals",
        display_name="G",
        sort_order="1",
        position_type="P",
        is_only_display=False,
        value=3.0,
        is_category=True,
    )
    assert scoring_cat.is_scoring is True

    display_cat = StatCategory(
        stat_id="99",
        name="Games Played",
        display_name="GP",
        sort_order="1",
        position_type="P",
        is_only_display=True,
        value=None,
        is_category=False,
    )
    assert display_cat.is_scoring is False


def test_league_is_daily():
    daily_league = League(
        league_key="465.l.34948",
        name="Test Hockey League",
        sport="nhl",
        season="2025",
        num_teams=12,
        scoring_type="head",
        scoring_period="daily",
        roster_positions=["C", "C", "LW", "RW", "D", "D", "G", "BN", "BN", "IR"],
        stat_categories=[],
        current_week=20,
    )
    assert daily_league.is_daily is True

    weekly_league = League(
        league_key="461.l.12345",
        name="Test Football League",
        sport="nfl",
        season="2025",
        num_teams=10,
        scoring_type="head",
        scoring_period="weekly",
        roster_positions=["QB", "RB", "WR", "TE", "K", "DEF", "BN"],
        stat_categories=[],
        current_week=10,
    )
    assert weekly_league.is_daily is False


def test_league_active_positions():
    league = League(
        league_key="465.l.34948",
        name="Test League",
        sport="nhl",
        season="2025",
        num_teams=12,
        scoring_type="head",
        scoring_period="daily",
        roster_positions=["C", "C", "LW", "RW", "D", "D", "G", "BN", "BN", "IR"],
        stat_categories=[],
        current_week=20,
    )
    active = league.active_positions
    assert "C" in active
    assert "BN" not in active
    assert "IR" not in active


def test_week_plan_improvement():
    plan = WeekPlan(
        days=[],
        transactions_used=2,
        transactions_remaining=3,
        total_projected_points=185.5,
        baseline_points=170.0,
        improvement=15.5,
    )
    assert plan.improvement == 15.5


def test_write_result():
    success = WriteResult(success=True, message="Player added successfully")
    assert success.success is True

    failure = WriteResult(success=False, message="Roster is full")
    assert failure.success is False
