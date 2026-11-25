#!/usr/bin/env python3
"""Rescore the whole 2026 season with the new engine and compare with the 2026 app.

No dependencies beyond Python 3.11+. Usage:
    python3 scripts/rescore_2026.py [path/to/ipl-2026-fantasy]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sic_engine.adapters import legacy_2026 as legacy  # noqa: E402
from sic_engine.rules import load_rules  # noqa: E402
from sic_engine.scoring import score_match  # noqa: E402
from sic_engine.standings import build_standings  # noqa: E402

default = Path(__file__).resolve().parents[3] / "Summer-2026" / "ipl-2026-fantasy"
root = Path(sys.argv[1]) if len(sys.argv) > 1 else default

rules = load_rules("rules_2026")
season = legacy.load_settings(root)

results, player_rows, player_diffs = [], 0, 0
for path in legacy.scorecard_files(root):
    match, stored = legacy.load_match(path)
    res = score_match(match, rules)
    results.append(res)
    for pid, s in stored.items():
        player_rows += 1
        player_diffs += res.points[pid].total != s.total
    for miss in res.unmatched_fielders:
        print(f"  unmatched fielder in {match.match_id}: {miss}")

standings = build_standings(results, legacy.load_lineups(season), season.match_week, rules.lineup)
stored_table = legacy.load_stored_standings(root)

print(f"\n{len(results)} matches, {player_rows} player scores, {player_diffs} differ from 2026\n")
print(f"{'#':>2}  {'Owner':<8}{'New':>8}{'2026':>8}")
ok = True
for rank, owner, pts in standings.table(season.owners):
    old = stored_table.get(owner)
    ok &= pts == old
    print(f"{rank:>2}  {owner:<8}{pts:>8}{old:>8}{'' if pts == old else '  <-- differs'}")
print("\nPASS: new engine reproduces 2026 exactly" if ok and not player_diffs else "\nFAIL")
sys.exit(0 if ok and not player_diffs else 1)
