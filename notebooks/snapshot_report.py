"""Pre-game snapshot: the team's situation before one game, in either competition, using only data from before that game.

    python notebooks/snapshot_report.py --game 2026-10-20          # the game is identified by its date

The game can be finished or still to play (the list of games is team_games.py: LBA, EuroCup, weekly/schedule.csv).
Writes reports/snapshot/<date>/ (figures, auto.json) and creates weekly/snapshot/<date>/notes.md from
weekly/template/notes_snapshot.md if it does not exist yet. `build_site.py` merges them through
weekly/template/snapshot.md.j2 into docs/snapshot/<date>/.
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
import team_games as tgm
import weekly_config
import weekly_report as wr
import weekly_sections as ws

ROOT = Path(__file__).resolve().parent.parent
CFG = weekly_config.load()
TEAM = CFG["team"]


def standings_md(games: pd.DataFrame, before: str, team: str, opp: str) -> str:
    t = st.standings(games, before)
    rows = [[x.pos, f"**{wr.short(tm)}**" if tm in (team, opp) else wr.short(tm), x.pts, f"{x.w}-{x.l}", f"{x['diff']:+d}", x.form]
            for tm, x in t.iterrows()]
    return wr.md_table(["#", "Team", "Pts", "W-L", "Diff", "Results"], rows, ["---:", "---", "---:", ":---:", "---:", ":---:"])


def nn(x):
    """None for missing values (NaN from the data frame), else the value."""
    return None if x is None or (not isinstance(x, (str, bool)) and pd.isna(x)) else x


def where(home) -> str:
    return "at" if nn(home) is False else "vs"


def last_results_md(before: pd.DataFrame, n: int = 5) -> str:
    items = []
    for _, x in before.tail(n).iterrows():
        label = f"round {int(x['round'])}" if x.competition == "LBA" else x.competition
        items.append(f"- {x.date[5:]} · {label}: **{'W' if x.win else 'L'}** {int(x.pf)}-{int(x.pa)} {where(x.home)} {x.opponent}")
    return "\n".join(items)


def generate(key: str, team: str = TEAM, data: Path = ROOT / "data") -> Path:
    lba_style.AUTHOR = CFG["author"] or lba_style.AUTHOR
    games = pd.read_csv(data / "games.csv")
    pbp = pd.read_csv(data / "pbp.csv")
    tg = tgm.team_games(data, team)
    rows = tg[tg.key == key]
    if rows.empty:
        raise SystemExit(f"{team} has no game on {key}")
    g = rows.iloc[0]
    date = g.date
    before = tg[(tg.date < date) & tg.finished]
    if before.empty:
        raise SystemExit(f"no {team} game before {date}: nothing to snapshot")
    lba_before = before[before.competition == "LBA"]
    ec_before = before[before.competition == "EuroCup"]
    is_lba = g.competition == "LBA"
    opp = g.opponent_full

    out = ROOT / "reports" / "snapshot" / key
    out.mkdir(parents=True, exist_ok=True)
    lba_style.STAMP_NOTE = f"games before {pd.Timestamp(date):%d %b %Y} (pre-game snapshot)"

    player_photos.main_quiet(team)
    xbox = ws.load_box_before(data, date, CFG["eurocup_file"])
    lba_games = [int(x) for x in lba_before.game_id]
    last = before.iloc[-1]

    st.fig_standings(games, date, [team, opp] if is_lba else [team], out)
    (out / "00_standings.png").replace(out / "standings.png")
    ws.fig_form(before, out, team)
    box_lba = pd.read_csv(data / "box_scores.csv")
    box_ast = int(box_lba[(box_lba.game_id.isin(lba_games)) & (box_lba.team == team) & (box_lba.row_type == "total")].ast.sum())
    roster = ws.roster_table(xbox, data, team)
    for r in roster:
        if r["photo"]:
            shutil.copy(data / "photos" / f"{r['player_id']}.jpg", out / f"photo_{r['player_id']}.jpg")

    tab = st.standings(games, date)
    venue = games[games.game_id == g.game_id].venue
    auto = {
        "kind": "snapshot", "key": key, "competition": g.competition, "round": None if pd.isna(g["round"]) else int(g["round"]),
        "team": team, "opponent": g.opponent, "opponent_full": opp, "home": None if nn(g.home) is None else bool(g.home),
        "date": date, "time": g.time, "venue": (None if venue.empty or pd.isna(venue.iloc[0]) else venue.iloc[0]) if is_lba else None,
        "played": bool(g.finished), "opponent_analysis": nn(g.analysis),
        "record": f"{int(tab.loc[team, 'w'])}-{int(tab.loc[team, 'l'])}", "position": int(tab.loc[team, "pos"]), "points": int(tab.loc[team, "pts"]),
        "record_ec": f"{int(ec_before.win.sum())}-{int(len(ec_before) - ec_before.win.sum())}" if len(ec_before) else None,
        "form": "".join("W" if w else "L" for w in before.win.tail(5)),
        "last_game": {"competition": last.competition, "round": None if pd.isna(last["round"]) else int(last["round"]),
                      "opponent": last.opponent, "home": None if nn(last.home) is None else bool(last.home), "score_for": int(last.pf), "score_against": int(last.pa),
                      "win": bool(last.win), "date": last.date},
        "missing": [f"{x.date} · {x.competition}{' round ' + str(int(x['round'])) if x.competition == 'LBA' else ''} {where(x.home)} {x.opponent}"
                    for _, x in tg[(tg.date < date) & ~tg.finished].iterrows()],
        "playing_time": ws.playing_time_flags(xbox, str(last.game_id), last.date),
        "profile": {"LBA": ws.team_profile(xbox, team, ("LBA",)), "EuroCup": ws.team_profile(xbox, team, ("EC",))},
        "roster": roster,
        "assist_top": ws.fig_assists(ws.assist_pairs(pbp, lba_games, team), box_ast, out, team),
        "zone_share": ws.fig_zones(pbp, lba_games, None, out, team),
        "ts_pir_lba": ws.fig_ts_pir(xbox, "LBA", out, team=team),
        "ts_pir_ec": ws.fig_ts_pir(xbox, "EC", out, team=team) if ((xbox.competition == "EC") & (xbox.team == team)).any() else None,
        "md": {"standings": standings_md(games, date, team, opp if is_lba else ""), "last_results": last_results_md(before)},
    }
    (out / "auto.json").write_text(json.dumps(auto, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    notes_dir = ROOT / "weekly" / "snapshot" / key
    if not (notes_dir / "notes.md").exists():
        notes_dir.mkdir(parents=True, exist_ok=True)
        (notes_dir / "notes.md").write_text((ROOT / "weekly" / "template" / "notes_snapshot.md").read_text(encoding="utf-8"), encoding="utf-8")
        print(f"created {notes_dir / 'notes.md'} - write your text there")
    print(f"snapshot before {g.competition} game {key}: {wr.short(team)} {where(auto['home'])} {g.opponent}  ->  {out}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True, help="date of the game, YYYY-MM-DD")
    ap.add_argument("--team", default=TEAM)
    ap.add_argument("--data", default=str(ROOT / "data"))
    a = ap.parse_args()
    generate(a.game, a.team, Path(a.data))


if __name__ == "__main__":
    main()
