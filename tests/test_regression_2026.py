"""Phase 0 gate: rescoring every 2026 match must reproduce the 2026 app exactly.

Reads the 2026 app folder (scored scorecard CSVs, weekly squad CSVs, settings.py,
Outputs/). Set SIC_2026_DIR to point elsewhere; skipped if the folder is absent.
"""

import os
from pathlib import Path

import pytest

from sic_engine.adapters import legacy_2026 as legacy
from sic_engine.rules import load_rules
from sic_engine.scoring import score_match
from sic_engine.standings import build_standings

DEFAULT = Path(__file__).resolve().parents[3] / "Summer-2026" / "ipl-2026-fantasy"
ROOT = Path(os.environ.get("SIC_2026_DIR", DEFAULT))

pytestmark = pytest.mark.skipif(not (ROOT / "settings.py").exists(), reason=f"2026 data not found at {ROOT}")

# Fielders the 2026 code could not match either (so they scored 0 in 2026 too).
# Any new entry here means a parsing change: investigate before accepting.
KNOWN_UNMATCHED = {
    # Raghu Sharma's caught-and-bowled; ambiguous with Rohit Sharma. Raghu was in
    # no owner's lineup that week, so no owner's points were affected.
    "1529290": ["RS Sharma (c & b RS Sharma)"],
}

RULES = load_rules("rules_2026")


@pytest.fixture(scope="module")
def season():
    return legacy.load_settings(ROOT)


@pytest.fixture(scope="module")
def scored():
    out = []
    for path in legacy.scorecard_files(ROOT):
        match, stored = legacy.load_match(path)
        out.append((match, stored, score_match(match, RULES)))
    return out


def test_all_74_matches_present(scored):
    assert len(scored) == 74


def test_every_player_score_matches_2026(scored):
    mismatches = []
    for match, stored, result in scored:
        for pid, s in stored.items():
            p = result.points[pid]
            got = (p.batting, p.bowling, p.fielding, p.bonus, p.total)
            exp = (s.batting, s.bowling, s.fielding, s.bonus, s.total)
            if got != exp:
                mismatches.append((match.match_id, p.name, got, exp))
    assert mismatches == []


def test_unmatched_fielders_are_only_the_known_ones(scored):
    found = {m.match_id: r.unmatched_fielders for m, _, r in scored if r.unmatched_fielders}
    assert found == KNOWN_UNMATCHED


@pytest.fixture(scope="module")
def standings(season, scored):
    lineups = legacy.load_lineups(season)
    return build_standings([r for _, _, r in scored], lineups, season.match_week, RULES.lineup)


def test_owner_points_match_2026_for_every_match(standings):
    got = standings.owner_match_points()
    expected = legacy.load_stored_match_points(ROOT)
    diffs = [(o, m, got[o].get(m, 0), v) for o, per in expected.items() for m, v in per.items()
             if got[o].get(m, 0) != v]
    assert diffs == []


def test_final_table_matches_2026(standings, season):
    assert dict((o, p) for _, o, p in standings.table(season.owners)) == legacy.load_stored_standings(ROOT)
    assert standings.table()[0] == (1, "Srini", 11643)
