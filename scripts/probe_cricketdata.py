#!/usr/bin/env python3
"""Phase 0 check: does CricketData.org's FREE plan give us full IPL scorecards?

Needs a free API key from https://cricketdata.org (sign up, copy the key).
Uses about 3-4 of the free plan's 100 daily hits.

    export CRICKETDATA_API_KEY=...        # never commit this
    python3 scripts/probe_cricketdata.py

What we need from a scorecard, per player: runs, balls, 4s, 6s, dismissal text
(or fielder ids), overs, runs conceded, wickets, maidens, and ideally dots,
plus player of the match and the winner. Dots are the field most likely to be
missing; the report below says which fields came back.

Endpoint names follow CricketData.org's public docs as of late 2026; if a call
404s, check https://cricketdata.org/how-to-use-cricket-data-api.aspx.
"""

import json
import os
import sys
import urllib.parse
import urllib.request

BASE = "https://api.cricapi.com/v1"
KEY = os.environ.get("CRICKETDATA_API_KEY")
if not KEY:
    sys.exit("Set CRICKETDATA_API_KEY first.")


def call(endpoint: str, **params) -> dict:
    q = urllib.parse.urlencode({"apikey": KEY, **params})
    with urllib.request.urlopen(f"{BASE}/{endpoint}?{q}", timeout=30) as resp:
        data = json.load(resp)
    info = data.get("info", {})
    print(f"  {endpoint}: status={data.get('status')} hits today={info.get('hitsToday')}/{info.get('hitsLimit')}")
    return data


def keys_in(obj, prefix="", out=None):
    out = set() if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(prefix + k)
            keys_in(v, prefix + k + ".", out)
    elif isinstance(obj, list) and obj:
        keys_in(obj[0], prefix, out)
    return out


print("1. Find the IPL 2026 series")
series = call("series", search="Indian Premier League 2026")
ipl = next((s for s in series.get("data", []) if "2026" in s.get("name", "")), None)
if not ipl:
    sys.exit("  IPL 2026 not found in /series. Check the search term.")
print(f"  -> {ipl['name']} ({ipl['id']})")

print("2. List its matches")
info = call("series_info", id=ipl["id"])
matches = [m for m in info.get("data", {}).get("matchList", []) if m.get("matchEnded")]
print(f"  -> {len(matches)} finished matches")
if not matches:
    sys.exit("  No finished matches returned.")

print("3. Fetch one full scorecard")
card = call("match_scorecard", id=matches[0]["id"])
found = keys_in(card.get("data", {}))
want = {
    "batting runs/balls": ["scorecard.batting.r", "scorecard.batting.b"],
    "4s and 6s": ["scorecard.batting.4s", "scorecard.batting.6s"],
    "dismissal text": ["scorecard.batting.dismissal-text"],
    "fielder ids": ["scorecard.batting.catcher.id"],
    "bowling overs/runs/wickets": ["scorecard.bowling.o", "scorecard.bowling.r", "scorecard.bowling.w"],
    "maidens": ["scorecard.bowling.m"],
    "dots": ["scorecard.bowling.0s", "scorecard.bowling.dots"],
    "winner": ["matchWinner"],
}
print("\nField check:")
for label, paths in want.items():
    hit = [p for p in paths if p in found]
    print(f"  {'OK ' if hit else 'MISSING'}  {label}{'  (' + hit[0] + ')' if hit else ''}")
print("\nAll keys returned (for the adapter):")
print("  " + "\n  ".join(sorted(found)))
