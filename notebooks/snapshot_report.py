"""Pre-game snapshot: the team's situation before one game, in either competition, using only data from before that game.

    python notebooks/snapshot_report.py --game 2026-10-20          # the game is identified by its date

The game can be finished or still to play (the list of games is team_games.py: LBA, EuroCup, weekly/schedule.csv).
Writes reports/snapshot/<date>/ (figures, auto.json) and, once, the page you edit: weekly/games/<date>/snapshot.md (see pages.py).
`build_site.py` fills its automatic blocks into docs/snapshot/<date>/.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

import eurocup
import lba_style
import pages
import player_photos
import standings as st
import team_games as tgm
import weekly_config
import weekly_report as wr
import weekly_sections as ws

ROOT = weekly_config.ROOT
CFG = weekly_config.load()
TEAM = CFG["team"]
VERSION = 8   # bump when the generated data changes shape: weekly.py regenerates older snapshots
LBA = "LBA"                                  # competition label of the LBA games in team_games
EUROCUP = eurocup.COMPETITION                # competition label of the EuroCup games in team_games
EUROCUP_BOX = "EC"                           # competition code of EuroCup rows in the box-score frame
EL_SOURCE_NOTE = "EuroLeague live API"       # chart stamp for figures drawn from EuroCup data
LBA_SOURCE_NOTE = lba_style.SOURCE_NOTE      # chart stamp default (restored after the EuroCup figures)
LAST_RESULTS = 5                             # games listed under "last results" and in the form string
STANDINGS_PNG = "standings.png"              # name of the standings figure inside the snapshot folder


def standings_md(games: pd.DataFrame, before: str, team: str, opp: str) -> str:
    """Return the standings as a markdown table, with `team` and `opp` in bold."""
    t = st.standings(games, before)
    rows = [[x.pos, f"**{wr.short(tm)}**" if tm in (team, opp) else wr.short(tm), x.pts, f"{x.w}-{x.l}", f"{x['diff']:+d}", x.form]
            for tm, x in t.iterrows()]
    return wr.md_table(["#", "Team", "Pts", "W-L", "Diff", "Results"], rows, ["---:", "---", "---:", ":---:", "---:", ":---:"])


def nn(x: Any) -> Any:
    """Return None for missing values (NaN from the data frame), else the value."""
    return None if x is None or (not isinstance(x, (str, bool)) and pd.isna(x)) else x


def where(home: bool | None) -> str:
    """Return "at" for an away game and "vs" otherwise (home or unknown)."""
    return "at" if nn(home) is False else "vs"


def last_results_md(before: pd.DataFrame, n: int = LAST_RESULTS) -> str:
    """Return the last `n` finished games as a markdown list."""
    items = []
    for _, x in before.tail(n).iterrows():
        label = f"round {int(x['round'])}" if x.competition == LBA else x.competition
        items.append(f"- {x.date[5:]} · {label}: **{'W' if x.win else 'L'}** {int(x.pf)}-{int(x.pa)} {where(x.home)} {x.opponent}")
    return "\n".join(items)


def game_label(x: Any) -> str:
    """Short label of a finished game for the availability table: "LBA 24 Oct", "EuroCup 27 Oct"."""
    return f"{x.competition} {pd.Timestamp(x.date):%d %b}".replace(" 0", " ")


def lba_style_shots(pbp: pd.DataFrame, games: list[Any], team: str) -> pd.DataFrame:
    """The team's field-goal attempts with a position in those games (empty when there are none)."""
    s = lba_style.shots_cm(pbp[pbp.game_id.isin(games)])
    return s[s.team == team]


def generate(key: str, team: str = TEAM, data: Path = ROOT / "data") -> Path:
    """Build reports/snapshot/<key>/ (figures, auto.json) and the editable page for the game on `key`; return the folder.

    Args:
        key: Date of the game, YYYY-MM-DD.
        team: Team the snapshot is about.
        data: Folder with the LBA and EuroCup CSVs.

    Raises:
        SystemExit: If the team has no game on `key` or no earlier finished game.
    """
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
    lba_before = before[before.competition == LBA]
    ec_before = before[before.competition == EUROCUP]
    is_lba = g.competition == LBA
    opp = g.opponent_full

    out = ROOT / "reports" / "snapshot" / key
    out.mkdir(parents=True, exist_ok=True)
    lba_style.STAMP_NOTE = f"games before {pd.Timestamp(date):%d %b %Y} (pre-game snapshot)"

    player_photos.main_quiet(team)
    xbox = ws.load_box_before(data, date, CFG["eurocup_file"])
    lba_games = [int(x) for x in lba_before.game_id]
    last = before.iloc[-1]

    # standings: the table of the competition of the game (EuroCup group for a EuroCup game, never the LBA one)
    table = {"kind": g.competition, "available": True, "position": None, "teams": None}
    if is_lba:
        st.fig_standings(games, date, [team, opp], out)
        (out / st.STANDINGS_PNG).replace(out / STANDINGS_PNG)
        standings_table = standings_md(games, date, team, opp)
    else:
        results = eurocup.load_results(data)
        frame = eurocup.games_frame(results, team) if results is not None and team in set(results.home) | set(results.away) else None
        if frame is None or st.finished(frame, date).empty:
            table["available"] = False       # no EuroCup results yet (data/eurocup/results.csv comes from eurocup_fetch.py)
            standings_table = ""
        else:
            opp_feed = eurocup.find_team(set(frame.home_team) | set(frame.away_team), opp)
            lba_style.SOURCE_NOTE = EL_SOURCE_NOTE
            st.fig_standings(frame, date, [team] + ([opp_feed] if opp_feed else []), out, title_label=f"{EUROCUP} {CFG['season']}")
            lba_style.SOURCE_NOTE = LBA_SOURCE_NOTE
            (out / st.STANDINGS_PNG).replace(out / STANDINGS_PNG)
            standings_table = standings_md(frame, date, team, opp_feed or "")
            tab_ec = st.standings(frame, date)
            table.update(position=int(tab_ec.loc[team, "pos"]), teams=len(tab_ec),
                         record=f"{int(tab_ec.loc[team, 'w'])}-{int(tab_ec.loc[team, 'l'])}")
    ws.fig_form(before, out, team)
    box_lba = pd.read_csv(data / "box_scores.csv")
    box_ast = int(box_lba[(box_lba.game_id.isin(lba_games)) & (box_lba.team == team) & (box_lba.row_type == "total")].ast.sum())
    roster = ws.roster_table(xbox, data, team, asof=date)      # photos stay in data/photos/; build_site.py copies them into the site

    ec_ids = [str(x) for x in ec_before.game_id]
    ec_pbp_path = data / "eurocup" / "pbp.csv"
    assist_ec, zone_ec = [], None
    if ec_ids and ec_pbp_path.exists():                       # the same two figures from the EuroCup play-by-play
        pbp_ec = pd.read_csv(ec_pbp_path)
        ec_tot = xbox[(xbox.competition == EUROCUP_BOX) & (xbox.team == team) & (xbox.row_type == "total") & xbox.game_id.isin(ec_ids)]
        lba_style.SOURCE_NOTE = EL_SOURCE_NOTE
        pairs_ec = ws.assist_pairs(pbp_ec, ec_ids, team)
        if len(pairs_ec) and int(ec_tot.ast.sum()):
            assist_ec = ws.fig_assists(pairs_ec, int(ec_tot.ast.sum()), out, team, EUROCUP, "assists_eurocup")
        if len(lba_style_shots(pbp_ec, ec_ids, team)):
            zone_ec = ws.fig_zones(pbp_ec, ec_ids, None, out, team, EUROCUP, "_eurocup")
        lba_style.SOURCE_NOTE = LBA_SOURCE_NOTE

    tab = st.standings(games, date)
    venue = games[games.game_id == g.game_id].venue
    auto = {
        "kind": "snapshot", "key": key, "competition": g.competition, "round": None if pd.isna(g["round"]) else int(g["round"]),
        "team": team, "opponent": g.opponent, "opponent_full": opp, "home": None if nn(g.home) is None else bool(g.home),
        "date": date, "time": g.time, "venue": (None if venue.empty or pd.isna(venue.iloc[0]) else venue.iloc[0]) if is_lba else None,
        "played": bool(g.finished), "version": VERSION, "n_before": tgm.n_before(tg, games, date), "opponent_analysis": nn(g.analysis),
        "record": f"{int(tab.loc[team, 'w'])}-{int(tab.loc[team, 'l'])}", "position": int(tab.loc[team, "pos"]), "points": int(tab.loc[team, "pts"]),
        "record_ec": f"{int(ec_before.win.sum())}-{int(len(ec_before) - ec_before.win.sum())}" if len(ec_before) else None,
        "form": "".join("W" if w else "L" for w in before.win.tail(LAST_RESULTS)),
        "last_game": {"competition": last.competition, "round": None if pd.isna(last["round"]) else int(last["round"]),
                      "opponent": last.opponent, "home": None if nn(last.home) is None else bool(last.home), "score_for": int(last.pf), "score_against": int(last.pa),
                      "win": bool(last.win), "date": last.date},
        "playing_time": ws.playing_time_flags(xbox, str(last.game_id), last.date),
        "availability": ws.availability(xbox, [(str(x.game_id), x.date, game_label(x)) for x in before.itertuples()], team),
        "profile": {LBA: ws.team_profile(xbox, team, (LBA,)), EUROCUP: ws.team_profile(xbox, team, (EUROCUP_BOX,))},
        "roster": roster,
        "assist_top": ws.fig_assists(ws.assist_pairs(pbp, lba_games, team), box_ast, out, team),
        "zone_share": ws.fig_zones(pbp, lba_games, None, out, team),
        "assist_top_ec": assist_ec, "zone_share_ec": zone_ec,
        "ts_pir_lba": ws.fig_ts_pir(xbox, LBA, out, team=team),
        "ts_pir_ec": ws.fig_ts_pir(xbox, EUROCUP_BOX, out, team=team) if ((xbox.competition == EUROCUP_BOX) & (xbox.team == team)).any() else None,
        "standings_table": table,
        "md": {"standings": standings_table, "last_results": last_results_md(before)},
    }
    (out / "auto.json").write_text(json.dumps(auto, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    page, created = pages.ensure("snapshot", key, auto, sorted(f.name for f in out.iterdir()))
    if created:
        print(f"created {page.relative_to(ROOT)} - the page you edit")
    print(f"snapshot before {g.competition} game {key}: {wr.short(team)} {where(auto['home'])} {g.opponent}  ->  {out}")
    return out


def main() -> None:
    """Command-line entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--game", required=True, help="date of the game, YYYY-MM-DD")
    ap.add_argument("--team", default=TEAM)
    ap.add_argument("--data", default=str(ROOT / "data"))
    a = ap.parse_args()
    generate(a.game, a.team, Path(a.data))


if __name__ == "__main__":
    main()
