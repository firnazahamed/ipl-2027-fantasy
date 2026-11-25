"""Adapter for the 2026 app's files: scored scorecard CSVs, weekly squad CSVs and
settings.py. Used for the 2026 regression test and the one-time history import.

The 2026 CSVs hold the raw stats (runs, balls, overs, dots...) next to the
points the old code computed, so we can rescore from the raw stats and compare.
"""

from __future__ import annotations

import csv
import runpy
from dataclasses import dataclass
from pathlib import Path

from ..models import BattingLine, BowlingLine, MatchInput, PlayerRef, WeeklyLineup

NO_LINE = {"0", "0.0", ""}


def _i(v: str) -> int:
    return int(float(v)) if v not in ("", None) else 0


def _overs_to_balls(overs: str) -> int:
    whole, _, part = str(overs).partition(".")
    return int(whole) * 6 + (int(part) if part else 0)


@dataclass
class StoredPoints:
    """Points the 2026 code stored for one player in one match."""

    batting: int
    bowling: int
    fielding: int
    bonus: int
    total: int


@dataclass
class LegacySeason:
    root: Path
    weeks: dict[str, list[str]]          # week -> match ids
    player_ids: dict[str, str]           # name -> ESPN id
    owners: list[str]
    team_names: dict[str, str]

    @property
    def match_week(self) -> dict[str, str]:
        return {m: w for w, ms in self.weeks.items() for m in ms}


def load_settings(root: Path) -> LegacySeason:
    ns = runpy.run_path(str(root / "settings.py"))
    weeks = {w: [str(m) for m in cfg["matches"]] for w, cfg in ns["weeks"].items()}
    ids = {k.strip(): str(v) for k, v in ns["player_id_dict"].items()}
    owners = list(ns["owner_team_dict"].keys())
    return LegacySeason(root, weeks, ids, owners, dict(ns["owner_team_dict"]))


def scorecard_files(root: Path) -> list[Path]:
    return sorted(p for p in (root / "Scorecards").glob("*_scorecard.csv"))


def load_match(path: Path) -> tuple[MatchInput, dict[str, StoredPoints]]:
    match_id = path.name.split("_")[0]
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    players, batting, bowling, stored = [], [], [], {}
    mom, winner = None, None
    for r in rows:
        pid = str(_i(r["Player_id"]))
        team = _i(r["Team"])
        players.append(PlayerRef(pid, r["Name"], team))
        if r["Desc"] not in NO_LINE:
            batting.append(BattingLine(pid, _i(r["Runs_batting"]), _i(r["Balls_batting"]),
                                       _i(r["4s"]), _i(r["6s"]), r["Desc"]))
        if r["Overs"] not in NO_LINE:
            bowling.append(BowlingLine(pid, _overs_to_balls(r["Overs"]), _i(r["Runs_bowling"]),
                                       _i(r["Wickets"]), _i(r["Dots"]), _i(r["Maidens"]),
                                       float(r["Econ"])))
        bonus = _i(r["bonus_points"])
        if bonus in (25, 30):
            mom = pid
        if bonus in (5, 30):
            winner = team
        stored[pid] = StoredPoints(_i(r["batting_points"]), _i(r["bowling_points"]),
                                   _i(r["fielding_points"]), bonus, _i(r["total_points"]))
    match = MatchInput(match_id, players, batting, bowling, None, mom, winner)
    return match, stored


def load_lineups(season: LegacySeason) -> list[WeeklyLineup]:
    """2026 sheet layout per owner column: rows 0-10 XI (0 = C, 1 = VC),
    rows 11-14 bench players subbed in that week, rows 15-18 bench."""
    lineups = []
    for path in sorted((season.root / "Squads").glob("Week*.csv")):
        week = path.stem
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            header = next(reader)
            grid = list(reader)

        def ids(owner_col: int, start: int, stop: int) -> tuple[str, ...]:
            out = []
            for row in grid[start:stop]:
                name = row[owner_col].strip() if owner_col < len(row) else ""
                if name:
                    if name not in season.player_ids:
                        raise KeyError(f"{week}: no player id for '{name}'")
                    out.append(season.player_ids[name])
            return tuple(out)

        for col, owner in enumerate(header):
            lineups.append(WeeklyLineup(owner, week, ids(col, 0, 11), ids(col, 11, 15), ids(col, 15, 19)))
    return lineups


def load_stored_standings(root: Path) -> dict[str, int]:
    with open(root / "Outputs" / "standings_df.csv", newline="") as fh:
        return {r["Owner"]: _i(r["Points"]) for r in csv.DictReader(fh)}


def load_stored_match_points(root: Path) -> dict[str, dict[str, int]]:
    """Owner -> match id -> points, from Outputs/sum_df.csv (Match_N columns
    follow the sorted scorecard file order)."""
    match_ids = [p.name.split("_")[0] for p in scorecard_files(root)]
    with open(root / "Outputs" / "sum_df.csv", newline="") as fh:
        out = {}
        for r in csv.DictReader(fh):
            out[r["Owner"]] = {m: _i(r[f"Match_{i + 1}"]) for i, m in enumerate(match_ids)}
    return out
