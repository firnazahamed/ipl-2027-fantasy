# Summer is Coming 2027

The rebuild of the SIC fantasy cricket app. Plan: "Summer is Coming 2027: Audit & Rebuild Plan" doc.

This repo starts with the **scoring and standings engine**. It is pure Python with no dependencies, and later the Cloud Run ingestion job will use it. The web app (Next.js) and database (Supabase) come in Phases 1–2.

```
config/            scoring + lineup rules as TOML (rules_2027 = rules_2026, unchanged)
sic_engine/
  models.py        source-independent match, lineup and points shapes
  scoring.py       fantasy points per player per match (ported from get_scorecard.py)
  standings.py     owner points: captain 1.5x, VC 1.2x (rounded up), subs 0.5x
  adapters/
    legacy_2026.py reads the 2026 app's CSVs: regression test + history import
scripts/
  rescore_2026.py      rescore 2026 and compare with the old app (no deps)
  probe_cricketdata.py check what CricketData.org's free plan returns
tests/             unit tests per rule + the 2026 regression gate
```

## Run

```bash
python3 scripts/rescore_2026.py            # expects ../../Summer-2026/ipl-2026-fantasy
pip install pytest && python3 -m pytest    # 46 tests
```

## Phase 0 status

| Item | Status |
| --- | --- |
| Scoring engine extracted, rules in config | Done |
| Regression gate: all 74 matches and 1,767 player scores rescored, matching 2026 exactly; final table reproduced (Srini 11,643) | Passing |
| Captain/VC multiplier applies to the owner's own captain only (2026 matched any owner's captain) | Fixed; no 2026 points changed |
| New repo with no secrets in code; `.gitignore` blocks keys | Done; run the git commands below |
| **Rotate the ScraperAPI key** (old one is in the 2026 git history) | **You**: ScraperAPI dashboard, then delete the old secret version in Secret Manager |
| Delete the old `ipl-daily-update` Cloud Scheduler job (keeps us within 3 free jobs) | **You**, or ask Claude once gcloud access is set up |
| CricketData.org free plan returns full scorecards? | **You**: sign up, then `scripts/probe_cricketdata.py` |

### Known 2026 data quirk

Match 1529290: a caught-and-bowled credited to "RS Sharma" could not be matched (Rohit vs Raghu Sharma), so Raghu Sharma missed 10 fielding points in 2026. He was in no owner's lineup that week, so no owner's points changed. From 2027, structured API data gives fielder IDs, and any unmatched fielder is flagged for the commissioner.

## First commit

```bash
cd ~/Documents/CT/Summer-2027/sic-2027
git init -b main && git add . && git commit -m "Phase 0: scoring engine + 2026 regression gate"
# then create an empty private GitHub repo and:
git remote add origin git@github.com:<you>/sic-2027.git && git push -u origin main
```
