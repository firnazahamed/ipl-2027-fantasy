"""Hand-checked cases for every 2026 scoring rule."""

import pytest

from sic_engine.models import BattingLine, BowlingLine, MatchInput, PlayerRef
from sic_engine.rules import load_rules
from sic_engine.scoring import (
    batting_points,
    bowling_points,
    parse_dismissal_fielders,
    resolve_fielder,
    score_match,
)

R = load_rules("rules_2026")


def bat(runs, balls, fours=0, sixes=0, how="c X b Y"):
    return batting_points(BattingLine("1", runs, balls, fours, sixes, how), R.batting)["batting"]


def bowl(balls, runs, wkts=0, dots=0, maidens=0, econ=None):
    return bowling_points(BowlingLine("1", balls, runs, wkts, dots, maidens, econ), R.bowling)["bowling"]


class TestBatting:
    def test_century(self):
        # 100 base + (100-50) pace + 50 milestone + 10 fours + 5x2 sixes
        assert bat(100, 50, fours=10, sixes=5) == 100 + 50 + 50 + 10 + 10

    @pytest.mark.parametrize("runs,milestone", [(24, 0), (25, 10), (49, 10), (50, 20), (75, 30), (99, 30), (150, 50)])
    def test_milestones(self, runs, milestone):
        assert bat(runs, runs) == runs + milestone  # pace 0, no boundaries

    def test_duck_costs_five(self):
        assert bat(0, 3, how="b Bumrah") == 0 - 3 - 5

    @pytest.mark.parametrize("how", ["not out", "DNB", "absent hurt"])
    def test_no_duck_penalty_when_not_dismissed(self, how):
        assert bat(0, 0, how=how) == 0

    def test_slow_innings_loses_pace_points(self):
        assert bat(20, 30) == 20 - 10


class TestBowling:
    def test_tight_spell(self):
        # econ 5: 50 wkts + 3*(36-20)=48 pace + 10 (2 wkts) + 12 dots*1.5=18
        assert bowl(24, 20, wkts=2, dots=12) == 50 + 48 + 10 + 18

    def test_middle_economy_band_scores_no_pace(self):
        assert bowl(24, 40, econ=10.0) == 0

    def test_expensive_spell_is_negative(self):
        assert bowl(24, 54, econ=13.5) == 48 - 54

    def test_economy_exactly_nine_is_neutral(self):
        assert bowl(24, 36, econ=9.0) == 0

    @pytest.mark.parametrize("wkts,milestone", [(1, 0), (2, 10), (3, 20), (4, 30), (5, 50), (6, 50)])
    def test_wicket_milestones(self, wkts, milestone):
        assert bowl(24, 36, wkts=wkts, econ=9.0) == 25 * wkts + milestone

    def test_maiden(self):
        assert bowl(6, 0, dots=6, maidens=1) == round(3 * 9) + 9 + 30

    def test_economy_computed_when_missing(self):
        assert bowl(24, 20) == bowl(24, 20, econ=5.0)


class TestFielding:
    @pytest.mark.parametrize("text,expected", [
        ("c †Buttler b Archer", [("catch", "Buttler")]),
        ("c & b Rashid Khan", [("catch", "Rashid Khan")]),
        ("st †Pant b Bishnoi", [("stumping", "Pant")]),
        ("run out (Jadeja/†Dhoni)", [("run_out", "Jadeja"), ("run_out", "Dhoni")]),
        ("c sub (Ashwin) b Chahal", []),
        ("lbw b Bumrah", []),
        ("not out", []),
    ])
    def test_parse(self, text, expected):
        assert parse_dismissal_fielders(text) == expected

    def test_resolve_prefers_fielding_team(self):
        players = [PlayerRef("1", "Abhishek Sharma", 1), PlayerRef("2", "Rohit Sharma", 2)]
        assert resolve_fielder(players, "Sharma", 2).player_id == "2"

    def test_ambiguous_initials_stay_unmatched(self):
        players = [PlayerRef("1", "Rohit Sharma", 2), PlayerRef("2", "Raghu Sharma", 2)]
        assert resolve_fielder(players, "RS Sharma", 2) is None


def test_score_match_bonuses_and_flags():
    players = [PlayerRef("a", "Virat Kohli", 1), PlayerRef("b", "Rohit Sharma", 2)]
    m = MatchInput(
        "m1", players,
        batting=[BattingLine("a", 50, 40, 5, 1, "c Rohit Sharma b X"),
                 BattingLine("b", 10, 10, 0, 0, "c Nobody b Y")],
        bowling=[], player_of_match_id="a", winner_team=1,
    )
    r = score_match(m, R)
    assert r.points["b"].fielding == 10                 # catch credited by name
    assert r.points["a"].bonus == 25 + 5                # MoM + winning side
    assert r.points["b"].bonus == 0
    assert r.unmatched_fielders == ["Nobody (c Nobody b Y)"]
