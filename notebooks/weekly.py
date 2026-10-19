"""One command for the whole site: generate whatever is new, rebuild docs/.

    python notebooks/weekly.py              # everything that is missing, then build docs/
    python notebooks/weekly.py --collect    # first pull new games from legabasket.it (python -m lba_data.collect)
    python notebooks/weekly.py --round 4    # regenerate everything of round 4 (e.g. after a stats correction); your text is kept
    python notebooks/weekly.py --only snapshot,opponent   # a subset of: snapshot, opponent, review
    python notebooks/weekly.py --no-build   # figures and data only

For every game of the team, by round N (settings in weekly/config.json):
  snapshot  the team before game N, data from before it (needs a finished game before it, so N >= 2, up to the next game)
  opponent  analysis of the opponent of game N with the comparison against the team (same data cut)
  review    post-game review of game N (only once it is finished and collected)
Your text lives in weekly/{snapshot,opponent,review}/.../notes.md, created empty the first time and never overwritten
(a hand-written README.md in a reports/matchup_* folder is used as it is).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

import build_site
import opponent
import snapshot_report
import weekly_config
import weekly_report

ROOT = Path(__file__).resolve().parent.parent
KINDS = ("snapshot", "opponent", "review")


def has_text(notes: Path) -> bool:
    return notes.exists() and bool(build_site.parse_notes(notes))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--collect", action="store_true", help="pull new games before generating")
    ap.add_argument("--round", type=int, help="regenerate this round (all kinds that apply)")
    ap.add_argument("--only", default=",".join(KINDS), help="comma-separated subset of snapshot,opponent,review")
    ap.add_argument("--no-build", action="store_true")
    a = ap.parse_args()
    kinds = [k for k in a.only.split(",") if k in KINDS]
    cfg = weekly_config.load(); team = cfg["team"]
    if a.collect:
        subprocess.run([sys.executable, "-m", "lba_data.collect"], cwd=ROOT, check=True)
    games = pd.read_csv(ROOT / "data" / "games.csv")
    done = weekly_report.finished_rounds(games, team)
    if not done:
        raise SystemExit(f"no finished {team} game yet")
    mine = set(int(r) for r in games[(games.home_team == team) | (games.away_team == team)]["round"])
    # snapshot/opponent: every game with a finished game before it, up to the next one
    upcoming = [r for r in range(2, max(done) + 2) if r in mine]
    rep = lambda kind, r: ROOT / "reports" / kind / f"round-{r:02d}" / "auto.json"
    todo = {
        "snapshot": [a.round] if a.round in upcoming else [] if a.round else [r for r in upcoming if not rep("snapshot", r).exists()],
        "opponent": [a.round] if a.round in upcoming else [] if a.round else upcoming,   # opponent.generate skips existing folders
        "review": [a.round] if a.round in done else [] if a.round else [r for r in done if not rep("review", r).exists()],
    }
    if a.round and not any(todo[k] for k in kinds):
        raise SystemExit(f"round {a.round}: nothing to generate for {team}")
    for r in (todo["snapshot"] if "snapshot" in kinds else []):
        snapshot_report.generate(r, team)
    for r in (todo["opponent"] if "opponent" in kinds else []):
        opponent.generate(r, team, force=bool(a.round))
    for r in (todo["review"] if "review" in kinds else []):
        weekly_report.generate(r, team)
    if not a.no_build:
        build_site.main()

    waiting = []
    for r in upcoming:
        if not has_text(ROOT / "weekly" / "snapshot" / f"round-{r:02d}" / "notes.md"):
            waiting.append(f"snapshot round {r}")
    for r in done:
        if not has_text(ROOT / "weekly" / "review" / f"round-{r:02d}" / "notes.md"):
            waiting.append(f"review round {r}")
    for notes in sorted((ROOT / "weekly" / "opponent").glob("*/notes.md")):
        if not (ROOT / "reports" / notes.parent.name / "README.md").exists() and not has_text(notes):
            waiting.append(f"opponent {notes.parent.name.removeprefix('matchup_')}")
    if waiting:
        print("\nno text written yet (optional): " + "; ".join(waiting))


if __name__ == "__main__":
    main()
