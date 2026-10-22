"""Quick look at the two Rome teams vs the league. Run after at least one collection.

    python notebooks/roma_quicklook.py

Prints the league's four factors, per-game player averages of the Rome teams and their shot types.
"""
from __future__ import annotations

import pandas as pd

import weekly_config

ROOT = weekly_config.ROOT
DATA = ROOT / "data"
RIVAL_ROME_TEAM = "Maxima Roma"   # the other Rome club in Serie A; the configured team is the first one
ROMA = [weekly_config.load()["team"], RIVAL_ROME_TEAM]
GAME_FINISHED = 2                 # games.csv `game_status` of a finished game
FTA_POSSESSION_WEIGHT = 0.44      # share of free-throw attempts that end a possession
THREE_POINT_WEIGHT = 0.5          # extra weight of a made three in effective FG%
PER_100 = 100                     # ratings are points per 100 possessions
SECONDS_PER_MINUTE = 60
FACTOR_COLS = ["ortg", "drtg", "efg", "tov_pct", "oreb_pct", "ftr", "poss"]


def team_four_factors(box: pd.DataFrame) -> pd.DataFrame:
    """Return per-game mean ratings and four factors of every team, with a ``net`` column.

    Args:
        box: Box-score rows; only ``row_type == "total"`` rows are used.

    Returns:
        One row per team (index ``team``), columns ``FACTOR_COLS`` plus ``net``.
    """
    tot = box[box.row_type == "total"].copy()
    tot["fga"] = tot.fg2a + tot.fg3a
    tot["fgm"] = tot.fg2m + tot.fg3m
    opp = tot[["game_id", "team_id", "oreb", "dreb", "pts"]].rename(
        columns={"team_id": "opponent_id", "oreb": "opp_oreb", "dreb": "opp_dreb", "pts": "opp_pts"})
    tot = tot.merge(opp, on=["game_id", "opponent_id"])
    tot["poss"] = tot.fga - tot.oreb + tot.tov + FTA_POSSESSION_WEIGHT * tot.fta
    tot["ortg"] = PER_100 * tot.pts / tot.poss
    tot["drtg"] = PER_100 * tot.opp_pts / tot.poss
    tot["efg"] = (tot.fgm + THREE_POINT_WEIGHT * tot.fg3m) / tot.fga
    tot["tov_pct"] = tot.tov / tot.poss
    tot["oreb_pct"] = tot.oreb / (tot.oreb + tot.opp_dreb)
    tot["ftr"] = tot.fta / tot.fga
    team = tot.groupby("team")[FACTOR_COLS].mean()
    team["net"] = team.ortg - team.drtg
    return team


def player_averages(box: pd.DataFrame, teams: list[str]) -> pd.DataFrame:
    """Return per-game averages of the players of ``teams`` who played (``sec > 0``)."""
    pl = box[(box.row_type == "player") & box.team.isin(teams) & (box.sec > 0)].copy()
    pl["mp"] = pl.sec / SECONDS_PER_MINUTE
    per = pl.groupby(["team", "player_surname"]).agg(
        g=("game_id", "nunique"), mpg=("mp", "mean"), pts=("pts", "mean"), reb=("reb", "mean"),
        ast=("ast", "mean"), val=("val", "mean"), pm=("plus_minus", "mean"),
        fg3m=("fg3m", "sum"), fg3a=("fg3a", "sum"))
    per["fg3_pct"] = per.fg3m / per.fg3a.replace(0, pd.NA)
    return per


def shot_profile(pbp: pd.DataFrame, teams: list[str]) -> pd.DataFrame:
    """Return attempts, makes and percentage by shot type (pbp qualifier) for ``teams``."""
    shots = pbp[pbp.event.str.contains(r"^\d punti", regex=True, na=False) & pbp.team.isin(teams)].copy()
    shots["made"] = shots.event.str.contains("segnato")
    shots["three"] = shots.event.str.startswith("3")
    prof = shots.groupby(["team", "qualifier_1"]).agg(att=("made", "size"), made=("made", "sum"))
    prof["pct"] = prof.made / prof.att
    return prof


def main() -> None:
    """Print the league four factors, the Rome players' averages and their shot profile."""
    games = pd.read_csv(DATA / "games.csv")
    box = pd.read_csv(DATA / "box_scores.csv")
    pbp = pd.read_csv(DATA / "pbp.csv")

    played = games[games.game_status == GAME_FINISHED]
    print(f"{len(played)} games played of {len(games)}\n")

    team = team_four_factors(box)
    print("Team four factors (per-game means), league sorted by net rating:")
    print(team.sort_values("net", ascending=False).round(3).to_string(), "\n")

    per = player_averages(box, ROMA)
    print("Rome teams, per-game player averages:")
    print(per.sort_values(["team", "mpg"], ascending=[True, False]).round(2).to_string(), "\n")

    prof = shot_profile(pbp, ROMA)
    print("Rome teams, shot attempts by shot type (pbp qualifier):")
    print(prof.sort_values(["team", "att"], ascending=[True, False]).round(3).to_string())


if __name__ == "__main__":
    main()
