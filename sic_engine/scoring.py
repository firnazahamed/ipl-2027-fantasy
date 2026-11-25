"""Fantasy points for one match. Pure functions: no I/O, no pandas.

Ported from the 2026 app (get_scorecard.py). The 2026 regression test checks
that this reproduces every stored 2026 player score.
"""

from __future__ import annotations

import math
import re

from .models import (
    BattingLine,
    BowlingLine,
    FieldingCredit,
    MatchInput,
    MatchResult,
    PlayerPoints,
    PlayerRef,
)
from .rules import BattingRules, BowlingRules, Rules


# ── Batting ───────────────────────────────────────────────────────────────────

def batting_points(line: BattingLine, r: BattingRules) -> dict[str, int]:
    base = r.run * line.runs
    pace = r.pace_per_run_over_balls * (line.runs - line.balls)
    step = math.floor(line.runs / r.milestone_step)
    milestone = r.milestones[min(step, len(r.milestones) - 1)]
    duck = r.duck if (line.runs == 0 and line.dismissal not in r.duck_exempt) else 0
    impact = r.four * line.fours + r.six * line.sixes + duck
    return {
        "bat_base": base,
        "bat_pace": pace,
        "bat_milestone": milestone,
        "bat_impact": impact,
        "batting": base + pace + milestone + impact,
    }


# ── Bowling ───────────────────────────────────────────────────────────────────

def economy(line: BowlingLine) -> float:
    if line.economy is not None:
        return line.economy
    return line.runs * 6 / line.balls if line.balls else 0.0


def bowling_points(line: BowlingLine, r: BowlingRules) -> dict[str, int]:
    base = r.wicket * line.wickets
    econ = economy(line)
    if econ < r.tight_econ:
        pace = round(r.tight_mult * (line.balls * r.tight_runs_per_ball - line.runs))
    elif econ <= r.loose_econ:
        pace = 0
    else:
        pace = round(line.balls * r.loose_runs_per_ball - line.runs)
    milestone = r.milestones[min(line.wickets, len(r.milestones) - 1)]
    impact = round(r.dot * line.dots + r.maiden * line.maidens)
    return {
        "bowl_base": base,
        "bowl_pace": int(pace),
        "bowl_milestone": milestone,
        "bowl_impact": int(impact),
        "bowling": int(base + pace + milestone + impact),
    }


# ── Fielding (parsed from dismissal text when a source gives no credits) ──────

_NON_WORD = re.compile(r"\W+")


def _clean(name: str) -> str:
    return _NON_WORD.sub(" ", name).strip()


def parse_dismissal_fielders(dismissal: str) -> list[tuple[str, str]]:
    """Return [(kind, fielder name)] named in one dismissal, e.g.
    "c †Buttler b Archer" -> [("catch", "Buttler")]. Substitutes are ignored."""
    found: list[tuple[str, str]] = []
    d = dismissal
    if d.startswith("c & b"):
        found.append(("catch", d.split("c & b")[1].strip()))
    elif d.startswith("c "):
        found.append(("catch", d.split("c ")[1].split(" b ")[0].strip()))
    if d.startswith("st "):
        found.append(("stumping", d.split("st ")[1].split(" b ")[0].strip()))
    if d.startswith("run out"):
        inner = d.split("run out")[1].replace("(", "").replace(")", "")
        found.extend(("run_out", x.strip()) for x in inner.split("/"))
    found = [(k, f) for k, f in found if "sub (" not in f and "sub [" not in f]
    return [(k, _clean(f)) for k, f in found if _clean(f)]


def resolve_fielder(players: list[PlayerRef], fielder: str, fielding_team: int) -> PlayerRef | None:
    """Match a scorecard fielder name to a player, using the 2026 fallbacks:
    1. full name within the fielding team's names
    2. second word matches exactly one player (either team)
    3. second word + first initial matches exactly one player
    4. first word matches exactly one player
    """
    parts = fielder.split()
    if not parts:
        return None
    for p in players:
        if p.team == fielding_team and fielder in p.name:
            return p
    if len(parts) < 2:
        return None
    second = parts[1]
    hits = [p for p in players if second in p.name]
    if len(hits) == 1:
        return hits[0]
    hits = [p for p in players if second in p.name and p.name[:1] == parts[0][:1]]
    if len(hits) == 1:
        return hits[0]
    hits = [p for p in players if parts[0] in p.name]
    if len(hits) == 1:
        return hits[0]
    return None


def fielding_credits_from_dismissals(match: MatchInput) -> tuple[list[FieldingCredit], list[str]]:
    team_of = {p.player_id: p.team for p in match.players}
    credits: list[FieldingCredit] = []
    unmatched: list[str] = []
    for line in match.batting:
        batting_team = team_of.get(line.player_id)
        if batting_team is None:
            continue
        fielding_team = 2 if batting_team == 1 else 1
        for kind, name in parse_dismissal_fielders(line.dismissal):
            p = resolve_fielder(match.players, name, fielding_team)
            if p is None:
                unmatched.append(f"{name} ({line.dismissal})")
            else:
                credits.append(FieldingCredit(p.player_id, kind))
    return credits, unmatched


# ── Whole match ───────────────────────────────────────────────────────────────

def score_match(match: MatchInput, rules: Rules) -> MatchResult:
    pts = {p.player_id: PlayerPoints(p.player_id, p.name, p.team) for p in match.players}

    for line in match.batting:
        if line.player_id in pts:
            b = batting_points(line, rules.batting)
            pts[line.player_id].batting += b["batting"]
            pts[line.player_id].breakdown.update(b)

    for line in match.bowling:
        if line.player_id in pts and line.balls > 0:
            b = bowling_points(line, rules.bowling)
            pts[line.player_id].bowling += b["bowling"]
            pts[line.player_id].breakdown.update(b)

    unmatched: list[str] = []
    credits = match.fielding
    if credits is None:
        credits, unmatched = fielding_credits_from_dismissals(match)
    value = {"catch": rules.fielding.catch, "stumping": rules.fielding.stumping,
             "run_out": rules.fielding.run_out}
    for c in credits:
        if c.player_id in pts:
            pts[c.player_id].fielding += value[c.kind]

    if match.player_of_match_id in pts:
        pts[match.player_of_match_id].bonus += rules.bonus.player_of_match
    if match.winner_team:
        for p in pts.values():
            if p.team == match.winner_team:
                p.bonus += rules.bonus.winning_team

    return MatchResult(match.match_id, pts, unmatched)
