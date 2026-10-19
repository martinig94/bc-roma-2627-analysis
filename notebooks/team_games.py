"""Every game of the team in every competition, in date order: the list behind the pre-game snapshots.

    from team_games import team_games
    tg = team_games(data, team)      # one row per game, finished or not

Columns: key (the date, also the folder of the snapshot), date, time, competition ("LBA" or "EuroCup"), round (LBA only),
opponent (short name), opponent_full, home (True/False/None when unknown), finished, pf, pa, win, game_id (LBA int, "EC16" for
the EuroCup file), analysis (opponent-analysis folder, when there is one).

Sources: data/games.csv (LBA, all rounds), the EuroCup file of weekly/config.json (games played, parse_eurocup), and
weekly/schedule.csv for games still to play in other competitions (and any whose data is not in the file yet).
In the EuroCup file the first team listed in a game is the home team.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

import standings as st
import weekly_config

ROOT = Path(__file__).resolve().parent.parent
CFG = weekly_config.load()


def folder_name(home: str, away: str, day: str) -> str:
    return f"matchup_{home.replace(' ', '_')}_vs_{away.replace(' ', '_')}_before_{day}"


def team_games(data: Path, team: str = CFG["team"]) -> pd.DataFrame:
    rows = []
    games = pd.read_csv(data / "games.csv")
    for _, g in games[(games.home_team == team) | (games.away_team == team)].iterrows():
        home = g.home_team == team
        done = str(g.game_status) == "2"
        pf, pa = (g.home_score, g.away_score) if home else (g.away_score, g.home_score)
        day = g.match_datetime[:10]
        rows.append({"date": day, "time": g.match_datetime[11:16], "competition": "LBA", "round": int(g["round"]),
                     "opponent": st.short(g.away_team if home else g.home_team), "opponent_full": g.away_team if home else g.home_team,
                     "home": bool(home), "finished": done, "pf": int(pf) if done else None, "pa": int(pa) if done else None,
                     "game_id": int(g.game_id), "analysis": folder_name(g.home_team, g.away_team, day)})
    ec_file = ROOT / CFG["eurocup_file"] if CFG["eurocup_file"] else None
    if ec_file and ec_file.exists():
        from matchup_report import parse_eurocup
        ec = parse_eurocup(ec_file)[0]
        tot = ec[ec.row_type == "total"]
        first = tot.groupby("game_id", sort=False).team.first()
        for gid in tot[tot.team == team].game_id:
            mine = tot[(tot.game_id == gid) & (tot.team == team)].iloc[0]
            rows.append({"date": mine.date, "time": "", "competition": "EuroCup", "round": None, "opponent": mine.opponent,
                         "opponent_full": mine.opponent, "home": bool(first[gid] == team), "finished": True,
                         "pf": int(mine.pts), "pa": int(mine.opp_pts), "game_id": gid, "analysis": None})
    sched = ROOT / "weekly" / "schedule.csv"
    if sched.exists():
        have = {(r["competition"], r["date"]) for r in rows}
        for r in pd.read_csv(sched, dtype=str, keep_default_na=False).itertuples():
            if (r.competition, r.date) in have:
                continue
            rows.append({"date": r.date, "time": r.time, "competition": r.competition, "round": None, "opponent": r.opponent,
                         "opponent_full": r.opponent, "home": {"1": True, "0": False}.get(r.home), "finished": False,
                         "pf": None, "pa": None, "game_id": None, "analysis": r.analysis or None})
    tg = pd.DataFrame(rows).sort_values(["date", "time"], kind="stable").reset_index(drop=True)
    tg["win"] = tg.pf > tg.pa
    tg["key"] = tg.date
    return tg


def snapshot_targets(tg: pd.DataFrame, today: str) -> pd.DataFrame:
    """Games that get a pre-game snapshot: those with a game of the team before them, up to the next game to be played.
    Games of the past whose data is not collected yet are included (their data cut is complete)."""
    future = tg[(~tg.finished) & (tg.date >= today)]
    cutoff = future.date.min() if len(future) else "9999-12-31"
    t = tg[(tg.date <= cutoff) & (tg.index > 0)]
    return t
