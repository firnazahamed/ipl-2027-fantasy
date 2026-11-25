"""Source-independent match and lineup data.

Every data source (CricketData.org, the ESPNcricinfo scraper, the 2026 CSVs) is
converted into these shapes by an adapter. The scoring engine never sees raw
source data.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlayerRef:
    player_id: str
    name: str
    team: int  # 1 = team batting first, 2 = team batting second


@dataclass(frozen=True)
class BattingLine:
    player_id: str
    runs: int
    balls: int
    fours: int
    sixes: int
    dismissal: str  # "not out", "DNB", "absent hurt", or text such as "c Salt b Duffy"


@dataclass(frozen=True)
class BowlingLine:
    player_id: str
    balls: int
    runs: int
    wickets: int
    dots: int
    maidens: int
    economy: float | None = None  # as published; computed from runs/balls if None


@dataclass(frozen=True)
class FieldingCredit:
    player_id: str
    kind: str  # "catch" | "stumping" | "run_out"


@dataclass
class MatchInput:
    match_id: str
    players: list[PlayerRef]
    batting: list[BattingLine]
    bowling: list[BowlingLine]
    # Either give fielding credits directly (structured APIs), or leave as None
    # and they are parsed from the batting dismissal text (scraped scorecards).
    fielding: list[FieldingCredit] | None = None
    player_of_match_id: str | None = None
    winner_team: int | None = None


@dataclass
class PlayerPoints:
    player_id: str
    name: str
    team: int
    batting: int = 0
    bowling: int = 0
    fielding: int = 0
    bonus: int = 0
    breakdown: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return self.batting + self.bowling + self.fielding + self.bonus


@dataclass
class MatchResult:
    match_id: str
    points: dict[str, PlayerPoints]          # by player_id
    unmatched_fielders: list[str] = field(default_factory=list)  # flag for review


@dataclass(frozen=True)
class WeeklyLineup:
    """One owner's selection for one gameweek."""

    owner: str
    week: str
    xi: tuple[str, ...]          # player ids; xi[0] = captain, xi[1] = vice-captain
    subs_in: tuple[str, ...] = ()  # bench players subbed in this week (score sub_mult)
    bench: tuple[str, ...] = ()    # remaining bench, scores nothing

    @property
    def captain(self) -> str | None:
        return self.xi[0] if self.xi else None

    @property
    def vice_captain(self) -> str | None:
        return self.xi[1] if len(self.xi) > 1 else None
