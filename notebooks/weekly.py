"""One command for the whole site: generate whatever is new, rebuild docs/.

    python notebooks/weekly.py              # everything that is missing, then build docs/
    python notebooks/weekly.py --collect    # first pull new games from legabasket.it (python -m lba_data.collect)
    python notebooks/weekly.py --round 4    # regenerate everything of LBA round 4 (e.g. after a stats correction); your text is kept
    python notebooks/weekly.py --game 2026-10-20   # regenerate the snapshot of the game on that date (any competition)
    python notebooks/weekly.py --only snapshot,opponent   # a subset of: snapshot, opponent, review
    python notebooks/weekly.py --no-build   # figures and data only

For every game of the team, by round N (settings in weekly/config.json):
  snapshot  the team before the game, data from before it, for every game in every competition (LBA and EuroCup; needs a
            game before it, up to the next game to be played). Folder = the date of the game.
  opponent  analysis of the opponent of an LBA game with the comparison against the team (same data cut); other
            competitions' opponents get a hand-made page (weekly/schedule.csv links it to the game)
  review    post-game review of an LBA round (only once it is finished and collected)
Your text lives in weekly/{snapshot,opponent,review}/.../notes.md, created empty the first time and never overwritten
(a hand-written README.md in a reports/matchup_* folder is used as it is).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from datetime import date

import pandas as pd

import build_site
import opponent
import snapshot_report
import team_games
import weekly_config
import weekly_report

ROOT = Path(__file__).resolve().parent.parent
KINDS = ("snapshot", "opponent", "review")


def has_text(notes: Path) -> bool:
    """Some text of yours in the notes (the `reviewed:` marker alone is not text)."""
    return notes.exists() and any(k != "reviewed" for k in build_site.parse_notes(notes))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--collect", action="store_true", help="pull new games before generating")
    ap.add_argument("--round", type=int, help="regenerate this LBA round (all kinds that apply)")
    ap.add_argument("--game", help="regenerate the snapshot of the game on this date, YYYY-MM-DD")
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
    tg = team_games.team_games(ROOT / "data", team)
    targets = team_games.snapshot_targets(tg, f"{date.today():%Y-%m-%d}")
    rnd_key = {int(r["round"]): r["key"] for _, r in tg[tg.competition == "LBA"].iterrows()}
    games_df = pd.read_csv(ROOT / "data" / "games.csv")

    def snap_done(key: str) -> bool:
        """Generated, and with the data that is available now (a snapshot of a future game goes stale when games are collected)."""
        path = ROOT / "reports" / "snapshot" / key / "auto.json"
        if not path.exists():
            return False
        old = json.loads(path.read_text(encoding="utf-8"))
        return old.get("n_before") == team_games.n_before(tg, games_df, key) and old.get("version") == snapshot_report.VERSION
    lba_targets = [int(r) for r in targets[targets.competition == "LBA"]["round"]]
    rep = lambda kind, r: ROOT / "reports" / kind / f"round-{r:02d}" / "auto.json"
    if a.game:
        snaps = [a.game] if a.game in set(targets.key) else []
    elif a.round:
        snaps = [rnd_key[a.round]] if rnd_key.get(a.round) in set(targets.key) else []
    else:
        snaps = [k for k in targets.key if not snap_done(k)]
    todo = {
        "snapshot": snaps,
        "opponent": [a.round] if a.round in lba_targets else [] if (a.round or a.game) else lba_targets,   # opponent.generate skips existing folders
        "review": [a.round] if a.round in done else [] if (a.round or a.game) else [r for r in done if not rep("review", r).exists()],
    }
    if (a.round or a.game) and not any(todo[k] for k in kinds):
        raise SystemExit(f"nothing to generate for {team} ({a.round or a.game})")
    for k in (todo["snapshot"] if "snapshot" in kinds else []):
        snapshot_report.generate(k, team)
    for r in (todo["opponent"] if "opponent" in kinds else []):
        opponent.generate(r, team, force=bool(a.round))
    for r in (todo["review"] if "review" in kinds else []):
        weekly_report.generate(r, team)
    if not a.no_build:
        build_site.main()

    waiting, to_review = [], []
    today = date.today().isoformat()
    for k in targets.key:
        notes = ROOT / "weekly" / "snapshot" / k / "notes.md"
        if not has_text(notes):
            waiting.append(f"snapshot {k}")
        if k >= today and build_site.page_state(build_site.parse_notes(notes)) != "reviewed":
            to_review.append(f"snapshot {k}")
    for r in done:
        if not has_text(ROOT / "weekly" / "review" / f"round-{r:02d}" / "notes.md"):
            waiting.append(f"review round {r}")
    for notes in sorted((ROOT / "weekly" / "opponent").glob("*/notes.md")):
        folder = notes.parent.name
        if (ROOT / "reports" / folder / "README.md").exists():
            continue
        if not has_text(notes):
            waiting.append(f"opponent {folder.removeprefix('matchup_')}")
        if folder.rsplit("_before_", 1)[1] >= today and build_site.page_state(build_site.parse_notes(notes)) != "reviewed":
            to_review.append(f"opponent {folder.removeprefix('matchup_')}")
    if to_review:
        print("\nUPCOMING GAMES TO REVIEW (flagged as draft on the site until `reviewed: yes` is set in their notes): " + "; ".join(to_review))
    if waiting:
        print("\nno text written yet (optional): " + "; ".join(waiting))


if __name__ == "__main__":
    main()
