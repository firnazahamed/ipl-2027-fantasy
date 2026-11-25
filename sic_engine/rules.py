"""Scoring and league rules, loaded from TOML so rule changes are config, not code."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@dataclass(frozen=True)
class BattingRules:
    run: int = 1                       # base points per run
    pace_per_run_over_balls: int = 1   # (runs - balls)
    four: int = 1
    six: int = 2
    duck: int = -5
    duck_exempt: tuple[str, ...] = ("not out", "DNB", "absent hurt")
    milestone_step: int = 25           # runs per milestone step
    milestones: tuple[int, ...] = (0, 10, 20, 30, 50)  # bonus at 0, 25, 50, 75, 100+ runs


@dataclass(frozen=True)
class BowlingRules:
    wicket: int = 25
    dot: float = 1.5
    maiden: int = 30
    # Economy bands: econ < tight_econ -> tight_mult * (tight_balls_per_run * balls - runs)
    # tight_econ <= econ <= loose_econ -> 0
    # econ > loose_econ -> (loose_balls_per_run * balls - runs)  (negative)
    tight_econ: float = 9.0
    tight_mult: float = 3.0
    tight_runs_per_ball: float = 1.5
    loose_econ: float = 12.0
    loose_runs_per_ball: float = 2.0
    milestones: tuple[int, ...] = (0, 0, 10, 20, 30, 50)  # bonus at 0,1,2,3,4,5+ wickets


@dataclass(frozen=True)
class FieldingRules:
    catch: int = 10
    stumping: int = 10
    run_out: int = 10        # each fielder named in the run out


@dataclass(frozen=True)
class BonusRules:
    player_of_match: int = 25
    winning_team: int = 5


@dataclass(frozen=True)
class LineupRules:
    xi_size: int = 11
    bench_size: int = 4
    captain_mult: float = 1.5
    vice_captain_mult: float = 1.2
    sub_mult: float = 0.5            # bench player subbed in for the week
    max_overseas: int = 4
    min_batters: int = 6             # batters incl. WK and all-rounders
    min_bowlers: int = 5             # bowlers incl. all-rounders
    min_wicketkeepers: int = 1


@dataclass(frozen=True)
class Rules:
    season: int
    batting: BattingRules = field(default_factory=BattingRules)
    bowling: BowlingRules = field(default_factory=BowlingRules)
    fielding: FieldingRules = field(default_factory=FieldingRules)
    bonus: BonusRules = field(default_factory=BonusRules)
    lineup: LineupRules = field(default_factory=LineupRules)


def _section(cls, raw: dict):
    data = {}
    for k, v in raw.items():
        data[k] = tuple(v) if isinstance(v, list) else v
    return cls(**data)


def load_rules(name: str = "rules_2026", config_dir: Path = CONFIG_DIR) -> Rules:
    """Load rules from config/<name>.toml."""
    with open(config_dir / f"{name}.toml", "rb") as fh:
        raw = tomllib.load(fh)
    return Rules(
        season=raw["season"],
        batting=_section(BattingRules, raw.get("batting", {})),
        bowling=_section(BowlingRules, raw.get("bowling", {})),
        fielding=_section(FieldingRules, raw.get("fielding", {})),
        bonus=_section(BonusRules, raw.get("bonus", {})),
        lineup=_section(LineupRules, raw.get("lineup", {})),
    )
