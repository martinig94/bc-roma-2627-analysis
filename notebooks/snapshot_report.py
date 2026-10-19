"""BC Roma pre-game snapshot: the team's situation before one game, using only data from before that game.

    python notebooks/snapshot_report.py --round 5          # the situation before BC Roma's round-5 game

The game can be finished or still to play. Writes reports/snapshot/round-05/ (figures, auto.json) and creates
weekly/snapshot/round-05/notes.md from weekly/template/notes_snapshot.md if it does not exist yet.
`build_site.py` merges them through weekly/template/snapshot.md.j2 into docs/snapshot/round-05/.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pandas as pd

import lba_style
import player_photos
import standings as st
import weekly_config
import weekly_report as wr
import weekly_sections as ws

ROOT = Path(__file__).resolve().parent.parent
CFG = weekly_config.load()
TEAM = CFG["team"]


def team_game(games: pd.DataFrame, team: str, rnd: int) -> pd.Series:
    g = games[(games["round"] == rnd) & ((games.home_team == team) | (games.away_team == team))]
    if g.empty:
        raise SystemExit(f"{team} has no game in round {rnd}")
    return g.iloc[0]


def standings_md(games: pd.DataFrame, before: str, team: str, opp: str) -> str:
    t = st.standings(games, before)
    rows = [[x.pos, f"**{wr.short(tm)}**" if tm in (team, opp) else wr.short(tm), x.pts, f"{x.w}-{x.l}", f"{x['diff']:+d}", x.form]
            for tm, x in t.iterrows()]
    return wr.md_table(["#", "Team", "Pts", "W-L", "Diff", "Results"], rows, ["---:", "---", "---:", ":---:", "---:", ":---:"])


def last_results_md(games: pd.DataFrame, before: str, team: str, n: int = 5) -> str:
    g = st.finished(games, before)
    g = g[(g.home_team == team) | (g.away_team == team)].tail(n)
    items = []
    for _, x in g.iterrows():
        home = x.home_team == team
        pf, pa = (x.home_score, x.away_score) if home else (x.away_score, x.home_score)
        items.append(f"- Round {x['round']}: **{'W' if pf > pa else 'L'}** {pf}-{pa} {'vs' if home else 'at'} {wr.short(x.away_team if home else x.home_team)}")
    return "\n".join(items)


def generate(rnd: int, team: str = TEAM, data: Path = ROOT / "data") -> Path:
    lba_style.AUTHOR = CFG["author"] or lba_style.AUTHOR
    games = pd.read_csv(data / "games.csv")
    pbp = pd.read_csv(data / "pbp.csv")
    g = team_game(games, team, rnd)
    date = g.match_datetime[:10]
    home = g.home_team == team
    opp = g.away_team if home else g.home_team
    done = st.finished(games, date)
    mine = done[(done.home_team == team) | (done.away_team == team)]
    if mine.empty:
        raise SystemExit(f"no {team} game before {date}: nothing to snapshot")

    out = ROOT / "reports" / "snapshot" / f"round-{rnd:02d}"
    out.mkdir(parents=True, exist_ok=True)
    lba_style.STAMP_NOTE = f"games before {pd.Timestamp(date):%d %b %Y} (pre-game snapshot)"

    player_photos.main_quiet(team)
    xbox = ws.load_box_before(data, date, CFG["eurocup_file"])
    lba_games = [int(x) for x in mine.game_id]
    last = mine.iloc[-1]
    last_home = last.home_team == team
    lpf, lpa = (last.home_score, last.away_score) if last_home else (last.away_score, last.home_score)

    st.fig_standings(games, date, [team, opp], out)
    (out / "00_standings.png").replace(out / "standings.png")
    wr.fig_season(games, team, int(last["round"]), out)
    box_lba = pd.read_csv(data / "box_scores.csv")
    box_ast = int(box_lba[(box_lba.game_id.isin(lba_games)) & (box_lba.team == team) & (box_lba.row_type == "total")].ast.sum())
    roster = ws.roster_table(xbox, data, team)
    for r in roster:
        if r["photo"]:
            shutil.copy(data / "photos" / f"{r['player_id']}.jpg", out / f"photo_{r['player_id']}.jpg")

    tab = st.standings(games, date)
    auto = {
        "kind": "snapshot", "round": rnd, "team": team, "opponent": wr.short(opp), "opponent_full": opp, "home": bool(home),
        "date": date, "time": g.match_datetime[11:16], "venue": None if pd.isna(g.venue) else g.venue,
        "played": str(g.game_status) == "2",
        "record": f"{int(tab.loc[team, 'w'])}-{int(tab.loc[team, 'l'])}", "position": int(tab.loc[team, "pos"]),
        "points": int(tab.loc[team, "pts"]), "form": tab.loc[team, "form"][-5:],
        "last_game": {"round": int(last["round"]), "opponent": wr.short(last.away_team if last_home else last.home_team),
                      "home": bool(last_home), "score_for": int(lpf), "score_against": int(lpa), "win": bool(lpf > lpa), "date": last.match_datetime[:10]},
        "playing_time": ws.playing_time_flags(xbox, str(last.game_id), last.match_datetime[:10]),
        "profile": ws.team_profile(xbox, team),
        "roster": roster,
        "assist_top": ws.fig_assists(ws.assist_pairs(pbp, lba_games, team), box_ast, out, team),
        "zone_share": ws.fig_zones(pbp, lba_games, None, out, team),
        "ts_pir_lba": ws.fig_ts_pir(xbox, "LBA", out, team=team),
        "ts_pir_ec": ws.fig_ts_pir(xbox, "EC", out, team=team) if ((xbox.competition == "EC") & (xbox.team == team)).any() else None,
        "md": {"standings": standings_md(games, date, team, opp), "last_results": last_results_md(games, date, team)},
    }
    (out / "auto.json").write_text(json.dumps(auto, indent=2, ensure_ascii=False), encoding="utf-8")

    notes_dir = ROOT / "weekly" / "snapshot" / f"round-{rnd:02d}"
    if not (notes_dir / "notes.md").exists():
        notes_dir.mkdir(parents=True, exist_ok=True)
        (notes_dir / "notes.md").write_text((ROOT / "weekly" / "template" / "notes_snapshot.md").read_text(encoding="utf-8"), encoding="utf-8")
        print(f"created {notes_dir / 'notes.md'} - write your text there")
    print(f"snapshot before round {rnd}: {wr.short(team)} {auto['record']} (#{auto['position']}) vs {wr.short(opp)}  ->  {out}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--team", default=TEAM)
    ap.add_argument("--data", default=str(ROOT / "data"))
    a = ap.parse_args()
    generate(a.round, a.team, Path(a.data))


if __name__ == "__main__":
    main()
