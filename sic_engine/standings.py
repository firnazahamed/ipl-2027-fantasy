"""Turn per-match player points + weekly lineups into owner points and standings.

Ported from the 2026 app (get_standings.py) with one deliberate fix:
captain / vice-captain multipliers apply to that owner's own captain only.
(2026 matched a player against every owner's captain list; identical results
while each player has a single owner per week.)
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

from .models import MatchResult, WeeklyLineup
from .rules import LineupRules


def apply_multiplier(points: int, mult: float) -> int:
    """Round up, as in 2026 (np.ceil). Float maths kept identical to 2026."""
    return int(math.ceil(points * mult))


def sub_points(points: int, mult: float) -> int:
    """Bench player subbed in: round half to even, as numpy did in 2026."""
    return int(round(points * mult))


@dataclass
class OwnerMatchLine:
    owner: str
    match_id: str
    week: str
    player_id: str
    role: str        # "C", "VC", "XI" or "SUB"
    raw: int
    points: int


@dataclass
class Standings:
    lines: list[OwnerMatchLine] = field(default_factory=list)

    def owner_match_points(self) -> dict[str, dict[str, int]]:
        out: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for ln in self.lines:
            out[ln.owner][ln.match_id] += ln.points
        return out

    def totals(self) -> dict[str, int]:
        out: dict[str, int] = defaultdict(int)
        for ln in self.lines:
            out[ln.owner] += ln.points
        return dict(out)

    def table(self, owners: list[str] | None = None) -> list[tuple[int, str, int]]:
        """[(rank, owner, points)] best first; ties share the higher rank."""
        totals = self.totals()
        for o in owners or []:
            totals.setdefault(o, 0)
        ordered = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
        table, prev, rank = [], None, 0
        for i, (owner, pts) in enumerate(ordered, start=1):
            if pts != prev:
                rank, prev = i, pts
            table.append((rank, owner, pts))
        return table


def score_owner_match(lineup: WeeklyLineup, result: MatchResult, rules: LineupRules) -> list[OwnerMatchLine]:
    lines: list[OwnerMatchLine] = []
    for i, pid in enumerate(lineup.xi):
        p = result.points.get(pid)
        if p is None:  # did not play in this match
            continue
        raw = p.total
        if i == 0:
            role, pts = "C", apply_multiplier(raw, rules.captain_mult)
        elif i == 1:
            role, pts = "VC", apply_multiplier(raw, rules.vice_captain_mult)
        else:
            role, pts = "XI", raw
        lines.append(OwnerMatchLine(lineup.owner, result.match_id, lineup.week, pid, role, raw, pts))
    for pid in lineup.subs_in:
        p = result.points.get(pid)
        if p is None:
            continue
        lines.append(OwnerMatchLine(lineup.owner, result.match_id, lineup.week, pid, "SUB",
                                    p.total, sub_points(p.total, rules.sub_mult)))
    return lines


def build_standings(
    results: list[MatchResult],
    lineups: list[WeeklyLineup],
    match_week: dict[str, str],
    rules: LineupRules,
) -> Standings:
    by_week: dict[str, list[WeeklyLineup]] = defaultdict(list)
    for lu in lineups:
        by_week[lu.week].append(lu)
    st = Standings()
    for res in results:
        week = match_week[res.match_id]
        for lu in by_week[week]:
            st.lines.extend(score_owner_match(lu, res, rules))
    return st
