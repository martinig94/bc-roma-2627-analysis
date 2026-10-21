"""Opponent analysis before one BC Roma game, using only data from before that game, with a comparison against BC Roma.

    python notebooks/opponent.py --round 5          # analysis of BC Roma's round-5 opponent
    python notebooks/opponent.py --eurocup 2026-10-27   # analysis of the opponent of a EuroCup game (by date)

Runs the existing figure scripts (matchup_report.py, lineups_report.py, standings.py) into
reports/matchup_<home>_vs_<away>_before_<date>/ and writes auto.json there (the BC Roma vs opponent comparison table).
A folder that already exists is a frozen snapshot and is left alone; one with a hand-written README.md keeps it.
Otherwise the page is weekly/games/<date>/analysis.md (created once, see pages.py), with the automatic blocks filled in by build_site.py.
Both teams' figures use their league games (LBA) plus their EuroCup games, for the teams that are in the EuroCup file.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

import pages
import player_photos
import standings as st
import team_games as tgm
import weekly_config
import weekly_report as wr
import weekly_sections as ws

ROOT = Path(__file__).resolve().parent.parent
NB = ROOT / "notebooks"
CFG = weekly_config.load()
TEAM = CFG["team"]
VERSION = 7   # bump when the generated data changes shape: weekly.py regenerates older analyses


def folder_name(home: str, away: str, date: str) -> str:
    return f"matchup_{home.replace(' ', '_')}_vs_{away.replace(' ', '_')}_before_{date}"


def eurocup_teams(data: Path) -> set[str]:
    path = ROOT / CFG["eurocup_file"] if CFG["eurocup_file"] else None
    if not path or not path.exists():
        return set()
    from matchup_report import parse_eurocup
    return set(parse_eurocup(path)[0].team.unique())


def run(script: str, *args: str) -> None:
    r = subprocess.run([sys.executable, str(NB / script), *args], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"{script} failed:\n{r.stderr[-1500:]}")


def comparison(box: pd.DataFrame, games: pd.DataFrame, date: str, team: str, opp: str, comps: tuple = ("LBA", "EC")) -> dict:
    """`games`: the games of the table the positions come from (the LBA games, or the EuroCup group's for a EuroCup game)."""
    tab = st.standings(games, date)
    prof = {t: ws.team_profile(box, t, comps) for t in (team, opp)}
    rows = []
    for k in prof[team]:
        rows.append({"stat": k, "team": prof[team][k], "opp": prof[opp].get(k, "–")})
    return {"rows": rows,
            "team": {"record": prof[team]["Record"], "position": int(tab.loc[team, "pos"]), "form": tab.loc[team, "form"][-5:]},
            "opp": {"record": prof[opp].get("Record", "0-0"), "position": int(tab.loc[opp, "pos"]), "form": tab.loc[opp, "form"][-5:]}}


def write_roster(folder: Path, opp: str, date: str, data: Path) -> list[dict]:
    """The opponent's roster before `date` (league + EuroCup, with photos) as roster.json + photo_<id>.jpg in the folder."""
    player_photos.main_quiet(opp)
    roster = ws.roster_table(ws.load_box_before(data, date, CFG["eurocup_file"]), data, opp, asof=date)
    for r in roster:
        if r["photo"]:
            src = data / "eurocup" / "photos" / f"{str(r['player_id']).removeprefix('ec_')}.jpg" if str(r["player_id"]).startswith("ec_") else data / "photos" / f"{r['player_id']}.jpg"
            shutil.copy(src, folder / f"photo_{r['player_id']}.jpg")
    (folder / "roster.json").write_text(json.dumps(roster, indent=2, ensure_ascii=False), encoding="utf-8")
    return roster


def generate(rnd: int, team: str = TEAM, data: Path = ROOT / "data", force: bool = False) -> Path | None:
    games = pd.read_csv(data / "games.csv")
    g = games[(games["round"] == rnd) & ((games.home_team == team) | (games.away_team == team))]
    if g.empty:
        raise SystemExit(f"{team} has no game in round {rnd}")
    g = g.iloc[0]
    date = g.match_datetime[:10]
    home = g.home_team == team
    opp = g.away_team if home else g.home_team
    folder = ROOT / "reports" / folder_name(g.home_team, g.away_team, date)
    current = tgm.n_before(tgm.team_games(data, team), games, date)
    if folder.exists():
        if (folder / "README.md").exists():          # hand-written page: its text stays; the roster with pictures is added at build time
            write_roster(folder, opp, date, data)
            print(f"opponent analysis with a hand-written README, left alone: {folder.name}")
            return folder
        auto_path = folder / "auto.json"
        old = json.loads(auto_path.read_text(encoding="utf-8")) if auto_path.exists() else {}
        if not force and old.get("n_before") == current and old.get("version") == VERSION:          # nothing new in the data since it was generated
            print(f"opponent analysis up to date: {folder.name}")
            return folder
    if st.finished(games, date).empty:
        raise SystemExit(f"no games before {date}")

    ec_all = eurocup_teams(data)
    ec_teams = sorted({team, opp} & ec_all) if {team, opp} <= ec_all else []   # EuroCup numbers only when both teams play it
    args = ["--home", g.home_team, "--away", g.away_team, "--before", date, "--out", "reports"]
    run("matchup_report.py", *args, *([] if ec_teams else ["--no-eurocup"]))
    run("lineups_report.py", "--team", team, "--team", opp, "--before", date, "--out", str(folder))
    run("standings.py", "--team", team, "--team", opp, "--before", date, "--out", str(folder))

    xbox = ws.load_box_before(data, date, CFG["eurocup_file"])
    roster = write_roster(folder, opp, date, data)
    fin = st.finished(games, date)
    lba_ids = [int(x) for x in fin[(fin.home_team == opp) | (fin.away_team == opp)].game_id]
    pbp = pd.read_csv(data / "pbp.csv")
    pairs = ws.assist_pairs(pbp, lba_ids, opp)
    box_lba = pd.read_csv(data / "box_scores.csv")
    box_ast = int(box_lba[(box_lba.game_id.isin(lba_ids)) & (box_lba.team == opp) & (box_lba.row_type == "total")].ast.sum())
    assist_top = ws.fig_assists(pairs, box_ast, folder, opp) if len(pairs) and box_ast else []
    auto = {
        "kind": "opponent", "version": VERSION, "n_before": current, "round": rnd, "team": team, "opponent": wr.short(opp), "opponent_full": opp, "home": bool(home),
        "home_team": g.home_team, "away_team": g.away_team, "date": date, "time": g.match_datetime[11:16],
        "venue": None if pd.isna(g.venue) else g.venue, "eurocup": bool(ec_teams),
        "eurocup_teams": [wr.short(t) for t in ec_teams], "league": CFG["league"], "roster": roster,
        "comparison": comparison(xbox, games, date, team, opp, ("LBA", "EC") if ec_teams else ("LBA",)),
        "assist_top": assist_top, "turnovers": ws.turnover_table(xbox, opp),
        "standings_md": (folder / "standings.md").read_text(encoding="utf-8"),
    }
    (folder / "auto.json").write_text(json.dumps(auto, indent=2, ensure_ascii=False), encoding="utf-8")
    page, created = pages.ensure("analysis", date, auto, sorted(f.name for f in folder.iterdir()))
    if created:
        print(f"created {page.relative_to(ROOT)} - the page you edit")
    print(f"opponent analysis round {rnd}: {wr.short(team)} vs {wr.short(opp)}  ->  {folder}")
    return folder


def generate_eurocup(date: str, team: str = TEAM, data: Path = ROOT / "data", force: bool = False) -> Path | None:
    """The same analysis for a EuroCup game (the game of `date` in team_games.py), built from the EuroCup data only (box scores, shots and
    play-by-play from the EuroLeague API): the EuroCup group table, the other EuroCup teams as the league."""
    import eurocup
    tg = tgm.team_games(data, team)
    rows = tg[(tg.competition == "EuroCup") & (tg.date == date)]
    if rows.empty:
        raise SystemExit(f"{team} has no EuroCup game on {date}")
    g = rows.iloc[0]
    results = eurocup.load_results(data)
    if results is None:
        raise SystemExit("no EuroCup results yet (data/eurocup/results.csv comes from eurocup_fetch.py)")
    frame = eurocup.games_frame(results, team)
    names = set(frame.home_team) | set(frame.away_team)
    opp = eurocup.find_team(names, g.opponent_full)
    if opp is None:
        raise SystemExit(f"{g.opponent_full} is not in the EuroCup results")
    at_home = True if pd.isna(g.home) else bool(g.home)
    home_team, away_team = (team, opp) if at_home else (opp, team)
    folder = ROOT / "reports" / (g.analysis if isinstance(g.analysis, str) and g.analysis else folder_name(home_team, away_team, date))
    games = pd.read_csv(data / "games.csv")
    current = tgm.n_before(tg, games, date)
    if folder.exists():
        if (folder / "README.md").exists() or (ROOT / "weekly" / "opponent" / folder.name / "document.md").exists():
            print(f"opponent analysis written by hand, left alone: {folder.name}")
            return folder
        auto_path = folder / "auto.json"
        old = json.loads(auto_path.read_text(encoding="utf-8")) if auto_path.exists() else {}
        if not force and old.get("n_before") == current and old.get("version") == VERSION:
            print(f"opponent analysis up to date: {folder.name}")
            return folder
    if st.finished(frame, date).empty:
        raise SystemExit(f"no EuroCup games before {date}")
    run("matchup_report.py", "--home", home_team, "--away", away_team, "--before", date, "--out", "reports", "--competition", "EC")
    run("lineups_report.py", "--team", team, "--team", opp, "--before", date, "--out", str(folder), "--competition", "EC")
    xbox = ws.load_box_before(data, date, CFG["eurocup_file"])
    roster = write_roster(folder, opp, date, data)
    ec_box = xbox[xbox.competition == "EC"]
    ec_ids = sorted(ec_box[(ec_box.team == opp) & (ec_box.row_type == "total")].game_id.unique())
    pairs = ws.assist_pairs(pd.read_csv(data / "eurocup" / "pbp.csv"), ec_ids, opp)
    box_ast = int(ec_box[(ec_box.game_id.isin(ec_ids)) & (ec_box.team == opp) & (ec_box.row_type == "total")].ast.sum())
    assist_top = ws.fig_assists(pairs, box_ast, folder, opp, "EuroCup") if len(pairs) and box_ast else []
    rnd_no = None
    sched = results[(results.date == date) & ((results.home == opp) | (results.away == opp))]
    if len(sched):
        rnd_no = int(sched.iloc[0]["round"])
    auto = {
        "kind": "opponent", "version": VERSION, "n_before": current, "competition": "EuroCup", "round": rnd_no, "team": team,
        "opponent": wr.short(opp), "opponent_full": opp, "home": at_home, "home_team": home_team, "away_team": away_team,
        "date": date, "time": g.time, "venue": None, "eurocup": True, "eurocup_teams": [wr.short(team), wr.short(opp)], "league": "EuroCup",
        "roster": roster, "comparison": comparison(xbox, frame, date, team, opp, ("EC",)),
        "assist_top": assist_top, "turnovers": ws.turnover_table(xbox, opp),
        "standings_md": (folder / "standings.md").read_text(encoding="utf-8"),
    }
    (folder / "auto.json").write_text(json.dumps(auto, indent=2, ensure_ascii=False), encoding="utf-8")
    page, created = pages.ensure("analysis", date, auto, sorted(f.name for f in folder.iterdir()))
    if created:
        print(f"created {page.relative_to(ROOT)} - the page you edit")
    print(f"opponent analysis EuroCup {date}: {wr.short(team)} vs {wr.short(opp)}  ->  {folder}")
    return folder


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int)
    ap.add_argument("--eurocup", metavar="DATE", help="EuroCup game of this date (YYYY-MM-DD) instead of an LBA round")
    ap.add_argument("--team", default=TEAM)
    ap.add_argument("--data", default=str(ROOT / "data"))
    a = ap.parse_args()
    if a.eurocup:
        generate_eurocup(a.eurocup, a.team, Path(a.data), force=True)
    elif a.round:
        generate(a.round, a.team, Path(a.data))
    else:
        ap.error("--round or --eurocup is required")


if __name__ == "__main__":
    main()
