"""Opponent analysis before one BC Roma game, using only data from before that game, with a comparison against BC Roma.

    python notebooks/opponent.py --round 5          # analysis of BC Roma's round-5 opponent

Runs the existing figure scripts (matchup_report.py, lineups_report.py, standings.py) into
reports/matchup_<home>_vs_<away>_before_<date>/ and writes auto.json there (the BC Roma vs opponent comparison table).
A folder that already exists is a frozen snapshot and is left alone; one with a hand-written README.md keeps it.
Otherwise the page is rendered from weekly/template/opponent.md.j2 plus weekly/opponent/<folder>/notes.md (created empty).
EuroCup games enter the figures only when both teams are in the EuroCup file (the matchup report mixes them in).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

import standings as st
import weekly_config
import weekly_report as wr
import weekly_sections as ws

ROOT = Path(__file__).resolve().parent.parent
NB = ROOT / "notebooks"
CFG = weekly_config.load()
TEAM = CFG["team"]


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


def comparison(box: pd.DataFrame, games: pd.DataFrame, date: str, team: str, opp: str) -> dict:
    tab = st.standings(games, date)
    prof = {t: ws.team_profile(box, t) for t in (team, opp)}
    rows = []
    for k in prof[team]:
        rows.append({"stat": k, "team": prof[team][k], "opp": prof[opp].get(k, "–")})
    return {"rows": rows,
            "team": {"record": prof[team]["Record"], "position": int(tab.loc[team, "pos"]), "form": tab.loc[team, "form"][-5:]},
            "opp": {"record": prof[opp].get("Record", "0-0"), "position": int(tab.loc[opp, "pos"]), "form": tab.loc[opp, "form"][-5:]}}


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
    if folder.exists() and (not force or (folder / "README.md").exists()):   # frozen snapshot / hand-written page
        print(f"opponent analysis exists, left alone: {folder.name}")
        return folder
    if st.finished(games, date).empty:
        raise SystemExit(f"no games before {date}")

    both_ec = {team, opp} <= eurocup_teams(data)
    args = ["--home", g.home_team, "--away", g.away_team, "--before", date, "--out", "reports"]
    run("matchup_report.py", *args, *([] if both_ec else ["--no-eurocup"]))
    run("lineups_report.py", "--team", team, "--team", opp, "--before", date, "--out", str(folder))
    run("standings.py", "--team", team, "--team", opp, "--before", date, "--out", str(folder))

    xbox = ws.load_box_before(data, date, "")
    auto = {
        "kind": "opponent", "round": rnd, "team": team, "opponent": wr.short(opp), "opponent_full": opp, "home": bool(home),
        "home_team": g.home_team, "away_team": g.away_team, "date": date, "time": g.match_datetime[11:16],
        "venue": None if pd.isna(g.venue) else g.venue, "eurocup": bool(both_ec),
        "comparison": comparison(xbox, games, date, team, opp),
        "standings_md": (folder / "standings.md").read_text(encoding="utf-8"),
    }
    (folder / "auto.json").write_text(json.dumps(auto, indent=2, ensure_ascii=False), encoding="utf-8")
    notes_dir = ROOT / "weekly" / "opponent" / folder.name
    notes_dir.mkdir(parents=True, exist_ok=True)
    if not (notes_dir / "notes.md").exists():
        (notes_dir / "notes.md").write_text((ROOT / "weekly" / "template" / "notes_opponent.md").read_text(encoding="utf-8"), encoding="utf-8")
        print(f"created {notes_dir / 'notes.md'} - write your text there")
    print(f"opponent analysis round {rnd}: {wr.short(team)} vs {wr.short(opp)}  ->  {folder}")
    return folder


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--team", default=TEAM)
    ap.add_argument("--data", default=str(ROOT / "data"))
    a = ap.parse_args()
    generate(a.round, a.team, Path(a.data))


if __name__ == "__main__":
    main()
