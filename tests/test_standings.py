from sic_engine.models import MatchResult, PlayerPoints, WeeklyLineup
from sic_engine.rules import load_rules
from sic_engine.standings import apply_multiplier, build_standings, sub_points

L = load_rules("rules_2026").lineup


def result(match_id, pts: dict[str, int]) -> MatchResult:
    return MatchResult(match_id, {pid: PlayerPoints(pid, pid, 1, batting=v) for pid, v in pts.items()})


def test_captain_rounds_up_even_when_negative():
    assert apply_multiplier(15, 1.5) == 23
    assert apply_multiplier(-5, 1.5) == -7


def test_vice_captain():
    assert apply_multiplier(7, 1.2) == 9


def test_sub_rounds_half_to_even_like_2026():
    assert sub_points(15, 0.5) == 8   # 7.5 -> 8
    assert sub_points(13, 0.5) == 6   # 6.5 -> 6


def test_owner_match_points():
    lineup = WeeklyLineup("Firi", "Week1", xi=("c", "vc", "x", "absent"), subs_in=("s",), bench=("b",))
    res = result("m1", {"c": 10, "vc": 10, "x": 10, "s": 10, "b": 50})
    st = build_standings([res], [lineup], {"m1": "Week1"}, L)
    assert st.totals() == {"Firi": 15 + 12 + 10 + 5}   # bench player 'b' scores nothing


def test_multiplier_is_per_owner():
    # 'p' is Srini's captain but an ordinary XI pick for Firi
    a = WeeklyLineup("Srini", "W", xi=("p", "q"))
    b = WeeklyLineup("Firi", "W", xi=("r", "s", "p"))
    st = build_standings([result("m", {"p": 20, "q": 0, "r": 0, "s": 0})], [a, b], {"m": "W"}, L)
    assert st.totals() == {"Srini": 30, "Firi": 20}


def test_table_ties_share_rank():
    st = build_standings(
        [result("m", {"a": 10, "b": 10, "c": 5})],
        [WeeklyLineup("A", "W", xi=("x", "y", "a")), WeeklyLineup("B", "W", xi=("x2", "y2", "b")),
         WeeklyLineup("C", "W", xi=("x3", "y3", "c"))],
        {"m": "W"}, L)
    assert st.table() == [(1, "A", 10), (1, "B", 10), (3, "C", 5)]
