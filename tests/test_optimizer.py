"""Tests for yfantasy week-level optimizer."""

from datetime import date
from yfantasy.optimizer import Optimizer
from yfantasy.models import (
    DayPlan, League, Player, Roster, RosterPlayer, StatCategory, WeekPlan,
)
from yfantasy.scoring import ScoringEngine


def _league(scoring_period="daily"):
    return League(
        league_key="465.l.34948",
        name="Test",
        sport="nhl",
        season="2025",
        num_teams=12,
        scoring_type="point",
        scoring_period=scoring_period,
        roster_positions=["C", "LW", "BN"],
        stat_categories=[
            StatCategory("1", "Goals", "G", "1", "P", False, 3.0, False),
            StatCategory("2", "Assists", "A", "1", "P", False, 2.0, False),
        ],
        current_week=20,
    )


def _player(key, name, positions, stats, projected=None):
    return Player(
        player_key=key, name=name, team="TST", positions=positions,
        status="healthy", percent_owned=50.0, current_fantasy_team="465.l.34948.t.1",
        stats=stats, projected_stats=projected or stats,
    )


def test_optimize_lineup_single_day():
    league = _league("weekly")
    engine = ScoringEngine(league)

    p1 = _player("465.p.1", "Star Center", ["C", "LW"], {"1": 30.0, "2": 40.0})
    p2 = _player("465.p.2", "OK Wing", ["LW"], {"1": 10.0, "2": 15.0})
    p3 = _player("465.p.3", "Bench Guy", ["C"], {"1": 5.0, "2": 5.0})

    roster = Roster(
        team_key="465.l.34948.t.1",
        players=[
            RosterPlayer(p1, "BN", False),
            RosterPlayer(p2, "C", True),
            RosterPlayer(p3, "LW", True),
        ],
    )

    optimizer = Optimizer(league, engine)
    plan = optimizer.optimize_lineup(roster)
    assert isinstance(plan, WeekPlan)
    assert plan.total_projected_points >= plan.baseline_points


def test_optimize_with_streaming():
    league = _league("daily")
    engine = ScoringEngine(league)

    p1 = _player("465.p.1", "Star", ["C"], {"1": 30.0, "2": 40.0})
    p2 = _player("465.p.2", "Meh", ["LW"], {"1": 2.0, "2": 3.0})
    p3 = _player("465.p.3", "Bench", ["C", "LW"], {"1": 1.0, "2": 1.0})

    roster = Roster(
        team_key="465.l.34948.t.1",
        players=[
            RosterPlayer(p1, "C", True),
            RosterPlayer(p2, "LW", True),
            RosterPlayer(p3, "BN", False),
        ],
    )

    fa = _player("465.p.99", "Hot FA", ["LW"], {"1": 15.0, "2": 20.0})
    fa.current_fantasy_team = None

    today = date.today()
    schedule = {
        today: {"465.p.1", "465.p.2", "465.p.99"},
    }

    optimizer = Optimizer(league, engine)
    plan = optimizer.optimize_with_streaming(
        roster, free_agents=[fa], schedule=schedule,
        remaining_adds=3, days=[today],
    )
    assert isinstance(plan, WeekPlan)


def test_empty_roster():
    league = _league()
    engine = ScoringEngine(league)
    roster = Roster(team_key="465.l.34948.t.1", players=[])
    optimizer = Optimizer(league, engine)
    plan = optimizer.optimize_lineup(roster)
    assert plan.total_projected_points == 0.0
