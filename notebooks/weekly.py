"""One command for the weekly report: generate whatever is new, rebuild the site.

    python notebooks/weekly.py              # every finished round of the team that has no report yet, then build docs/
    python notebooks/weekly.py --collect    # first pull new games from legabasket.it (python -m lba_data.collect)
    python notebooks/weekly.py --round 4    # regenerate one round (e.g. after a stats correction); your notes are kept
    python notebooks/weekly.py --no-build   # figures and data only

Team, season, author and EuroCup file are set in weekly/config.json. Generated automatically: reports/weekly/round-NN/
(figures + auto.json). Written by you: weekly/round-NN/notes.md, created empty the first time and never overwritten.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

import build_site
import weekly_config
import weekly_report

ROOT = Path(__file__).resolve().parent.parent


def has_text(notes: Path) -> bool:
    return notes.exists() and bool(build_site.parse_notes(notes))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--collect", action="store_true", help="pull new games before generating")
    ap.add_argument("--round", type=int, help="regenerate this round even if it exists")
    ap.add_argument("--no-build", action="store_true")
    a = ap.parse_args()
    cfg = weekly_config.load(); team = cfg["team"]
    if a.collect:
        subprocess.run([sys.executable, "-m", "lba_data.collect"], cwd=ROOT, check=True)
    games = pd.read_csv(ROOT / "data" / "games.csv")
    done = weekly_report.finished_rounds(games, team)
    todo = [a.round] if a.round else [r for r in done if not (ROOT / "reports" / "weekly" / f"round-{r:02d}" / "auto.json").exists()]
    if a.round and a.round not in done:
        raise SystemExit(f"{team} has no finished game in round {a.round}")
    if not todo:
        print(f"nothing new: {team} reports exist for rounds {done[0] if done else '-'}..{done[-1] if done else '-'}")
    for r in todo:
        weekly_report.generate(r, team)
    if not a.no_build:
        build_site.main()
    waiting = [r for r in done if not has_text(ROOT / "weekly" / f"round-{r:02d}" / "notes.md")]
    if waiting:
        print("\nno text written yet for round(s): " + ", ".join(map(str, waiting)) + "  ->  weekly/round-NN/notes.md")


if __name__ == "__main__":
    main()
