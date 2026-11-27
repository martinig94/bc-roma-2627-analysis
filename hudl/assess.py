"""Measure what the Hudl Instat feed covers, from the raw payloads of ``hudl.pull``.

Usage:
    python -m hudl.assess

Prints coverage numbers used by ``reports/hudl_api/hudl_api_assessment.md``:
event inventory, share of shots carrying each tag, shot counts against the LBA
play-by-play, team possessions and points per possession.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from hudl.pull import RAW_DIR

SHOT_ACTIONS = ("2+", "2-", "3+", "3-")
SHOT_TAGS = ("playtype", "hand", "shot_type", "drive", "dribble_move", "contesting")
LBA_PBP_SHOT_EVENTS = ("2 punti segnato", "2 punti sbagliato", "3 punti segnato", "3 punti sbagliato")


def load_events() -> pd.DataFrame:
    """Return every pulled event row with its match id, as one frame."""
    frames = []
    for path in sorted((RAW_DIR / "games").glob("*/events.json")):
        rows = json.loads(path.read_text(encoding="utf-8"))["data"]["row"]
        frame = pd.DataFrame(rows)
        frame["match_id"] = path.parent.name
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def tag_coverage(events: pd.DataFrame) -> pd.DataFrame:
    """Share of field-goal attempts carrying each descriptive tag."""
    shots = events[events.action_name.isin(SHOT_ACTIONS)]
    share = {tag: shots[tag].notna().mean() for tag in SHOT_TAGS}
    share["pos_x"] = shots["pos_x"].notna().mean()
    return pd.Series(share, name="share_of_shots").to_frame()


def team_pace(match_ids: list[str]) -> pd.DataFrame:
    """Possessions and points per possession of every team in every match."""
    records = []
    for match_id in match_ids:
        path = RAW_DIR / "games" / match_id / "teams.json"
        if not path.exists():
            continue
        rows = json.loads(path.read_text(encoding="utf-8"))["data"]["row"]
        per_team: dict[str, dict] = {}
        for row in rows:
            per_team.setdefault(row["team_name"], {"match_id": match_id})[
                row["param_name"]
            ] = float(row["value"])
        records.extend({"team": team, **values} for team, values in per_team.items())
    return pd.DataFrame(records)


def main() -> None:
    """Print the coverage tables."""
    events = load_events()
    print("matches with events:", events.match_id.nunique(), "rows:", len(events))
    print(events.action_name.value_counts().to_string())
    print(tag_coverage(events).round(3).to_string())
    drives = events[events.action_name.isin(SHOT_ACTIONS)]
    print(drives.playtype.value_counts(dropna=False).to_string())
    pace = team_pace(sorted(events.match_id.unique()))
    print(pace.groupby("team")[["Possessions", "Points per possession"]].mean().round(2))


if __name__ == "__main__":
    main()
