"""Weekly report of one team (weekly/config.json): the automatic part (plots + tables) for one round.

Normally run through `python notebooks/weekly.py`, which finds the new rounds by itself. Directly:

    python notebooks/weekly_report.py --round 4            # the team's game of round 4 (regenerates it)
    python notebooks/weekly_report.py --round 4 --team "Maxima Roma"

Writes reports/weekly/round-04/:
  standings.png, margin.png, players.png, season.png   figures
  auto.json                                            numbers and markdown snippets used by the page template
and creates weekly/round-04/notes.md from weekly/template/notes.md if it does not exist yet (the hand-written part).
`build_site.py` merges the two through weekly/template/page.md.j2 into docs/weekly/round-04/.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import lba_style
import standings as st
import weekly_sections as ws
import player_photos
import weekly_config
from lba_style import GREEN, LEAGUE, RED, SUP_KW, TEXT, TEXT2, TITLE_KW, save_fig, style_axes, team_color

ROOT = Path(__file__).resolve().parent.parent
CFG = weekly_config.load()
TEAM = CFG["team"]
FOES = "#4a7fc1"


def short(t: str) -> str:
    return st.short(t)


# ── data ────────────────────────────────────────────────────────────────────────
def find_game(games: pd.DataFrame, team: str, rnd: int) -> pd.Series:
    g = games[(games["round"] == rnd) & ((games.home_team == team) | (games.away_team == team))]
    if g.empty:
        raise SystemExit(f"{team} has no game in round {rnd}")
    g = g.iloc[0]
    if str(g.game_status) != "2":
        raise SystemExit(f"{team}'s round {rnd} game is not finished/collected yet (run `python -m lba_data.collect`)")
    return g


def quarter_scores(g: pd.Series, pbp: pd.DataFrame) -> list[tuple[int, int]]:
    """(home, away) points per period; from games.csv when present, else rebuilt from the play-by-play."""
    cols = [("q1_home", "q1_away"), ("q2_home", "q2_away"), ("q3_home", "q3_away"), ("q4_home", "q4_away"), ("ot_home", "ot_away")]
    out = [(int(g[h]), int(g[a])) for h, a in cols if pd.notna(g[h]) and pd.notna(g[a])]
    if len(out) >= 4:
        return out
    p = pbp[pbp.game_id == g.game_id].dropna(subset=["score_home", "score_away"]).sort_values("seq")
    out, prev = [], (0, 0)
    for _, x in p.groupby("period"):
        end = (int(x.score_home.iloc[-1]), int(x.score_away.iloc[-1]))
        out.append((end[0] - prev[0], end[1] - prev[1])); prev = end
    return out


def team_totals(box: pd.DataFrame, gid: int, team: str) -> pd.Series:
    return box[(box.game_id == gid) & (box.team == team) & (box.row_type == "total")].iloc[0]


def four_factors(t: pd.Series, o: pd.Series) -> dict:
    fga = t.fg2a + t.fg3a
    poss = fga - t.oreb + t.tov + 0.44 * t.fta
    return {
        "Points": int(t.pts), "Possessions": round(poss, 1), "Off. rating": round(100 * t.pts / poss, 1),
        "eFG%": round(100 * (t.fg2m + 1.5 * t.fg3m) / fga, 1),
        "TOV%": round(100 * t.tov / poss, 1),
        "OREB%": round(100 * t.oreb / (t.oreb + o.dreb), 1),
        "FT rate (FTA/FGA)": round(100 * t.fta / fga, 1),
        "3P": f"{int(t.fg3m)}/{int(t.fg3a)}", "2P": f"{int(t.fg2m)}/{int(t.fg2a)}", "FT": f"{int(t.ftm)}/{int(t.fta)}",
        "Assists": int(t.ast), "Turnovers": int(t.tov), "Rebounds": int(t.reb),
    }


# ── figures ─────────────────────────────────────────────────────────────────────
def fig_margin(g, pbp, team, out: Path) -> dict:
    p = pbp[pbp.game_id == g.game_id].dropna(subset=["score_home", "score_away"]).sort_values("seq")
    GOLD, GOLD_EDGE = team_color(team)
    home = g.home_team == team
    m = (p.score_home - p.score_away) * (1 if home else -1)
    # elapsed_sec restarts every period: 10' quarters, 5' overtimes
    start = p.period.map(lambda k: 10 * (k - 1) if k <= 4 else 40 + 5 * (k - 5))
    t = (start + p.elapsed_sec / 60).values
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.fill_between(t, 0, m, where=m >= 0, color=GOLD, alpha=0.85, step="post", linewidth=0)
    ax.fill_between(t, 0, m, where=m < 0, color=LEAGUE, alpha=0.7, step="post", linewidth=0)
    ax.step(t, m, where="post", color=GOLD_EDGE, linewidth=1)
    ax.axhline(0, color=TEXT2, linewidth=0.8)
    for q in range(10, int(t.max()) + 1, 10):
        ax.axvline(q, color=lba_style.GRID, linewidth=0.8, zorder=0)
    ax.set_xlabel("minute"); ax.set_ylabel(f"{short(team)} lead (points)")
    style_axes(ax, "y")
    ax.set_title(f"Score margin: biggest lead {int(m.max()):+d}, biggest deficit {int(m.min()):+d}", loc="left", **TITLE_KW)
    save_fig(fig, out / "margin.png"); plt.close(fig)
    return {"max_lead": int(m.max()), "max_deficit": int(m.min())}


def fig_players(box, g, team, out: Path) -> pd.DataFrame:
    b = box[(box.row_type == "player") & (box.team == team) & (box.sec > 0)].copy()
    cur = b[b.game_id == g.game_id].set_index("player_surname")
    prev = b[(b.game_id != g.game_id) & (b["round"] < g["round"])].groupby("player_surname").val.mean()
    d = cur[["sec", "val", "pts"]].join(prev.rename("avg_before"))
    GOLD, GOLD_EDGE = team_color(team)
    d = d[d.sec >= 300].sort_values("val")
    d.index = d.index.str.title()
    fig, ax = plt.subplots(figsize=(10, 0.45 * len(d) + 1.8))
    y = np.arange(len(d))
    ax.barh(y, d.val, 0.6, color=GOLD, edgecolor=GOLD_EDGE, linewidth=0.6, zorder=2)
    ax.scatter(d.avg_before, y, color=TEXT, marker="|", s=260, zorder=3, label="season average before this game")
    for yi, (_, x) in zip(y, d.iterrows()):
        ax.text(max(x.val, 0) + 0.4, yi, f"{int(x.val)} PIR · {int(x.pts)} pts · {x.sec / 60:.0f}'", va="center", fontsize=9, color=TEXT2)
    ax.set_yticks(y); ax.set_yticklabels(d.index)
    ax.set_xlabel("PIR (LBA efficiency)"); ax.legend(loc="lower right", fontsize=8)
    style_axes(ax, "x")
    ax.set_title("Players with 5+ minutes: PIR in the game vs their average before", loc="left", **TITLE_KW)
    save_fig(fig, out / "players.png"); plt.close(fig)
    return d


def fig_season(games, team, upto: int, out: Path) -> None:
    gg = st.finished(games); gg = gg[gg["round"] <= upto]
    lg = st._long(gg.assign(date=gg.date))
    gg = gg.assign(r=gg["round"])
    rows = []
    for _, x in gg.iterrows():
        rows.append((x.r, x.home_team, x.home_score, x.away_score)); rows.append((x.r, x.away_team, x.away_score, x.home_score))
    d = pd.DataFrame(rows, columns=["round", "team", "pf", "pa"])
    GOLD, GOLD_EDGE = team_color(team)
    lgavg = d.groupby("round")[["pf"]].mean()
    me = d[d.team == team].set_index("round")
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(lgavg.index, lgavg.pf, color=LEAGUE, linewidth=2, linestyle="--", label="league average scored")
    ax.plot(me.index, me.pf, color=GOLD_EDGE, marker="o", linewidth=2.4, markerfacecolor=GOLD, markersize=9, label=f"{short(team)} scored")
    ax.plot(me.index, me.pa, color=FOES, marker="o", linewidth=2.4, markersize=7, label=f"{short(team)} conceded")
    for r, x in me.iterrows():
        ax.text(r, x.pf + 2.2, int(x.pf), ha="center", fontsize=9, color=TEXT)
        ax.text(r, x.pa - 4.5, int(x.pa), ha="center", fontsize=9, color=FOES)
    ax.set_xticks(me.index); ax.set_xlabel("round"); ax.set_ylabel("points per game")
    ax.legend(loc="upper left", ncol=3, fontsize=8)
    style_axes(ax, "y")
    ax.set_title("Season so far: points scored and conceded by round", loc="left", **TITLE_KW)
    save_fig(fig, out / "season.png"); plt.close(fig)


# ── markdown snippets ───────────────────────────────────────────────────────────
def md_table(headers, rows, align=None) -> str:
    align = align or ["---"] * len(headers)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(align) + " |"]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def box_md(box, g, team) -> str:
    b = box[(box.game_id == g.game_id) & (box.team == team) & (box.row_type == "player") & (box.sec > 0)].sort_values("sec", ascending=False)
    rows = []
    for _, x in b.iterrows():
        rows.append([f"{'**' if x.starter else ''}{x.player_surname.title()}{'**' if x.starter else ''}", f"{x.sec / 60:.0f}", int(x.pts),
                     f"{int(x.fg2m)}/{int(x.fg2a)}", f"{int(x.fg3m)}/{int(x.fg3a)}", f"{int(x.ftm)}/{int(x.fta)}",
                     int(x.reb), int(x.ast), int(x.tov), int(x.stl), int(x.val), f"{int(x.plus_minus):+d}"])
    return md_table(["Player", "Min", "Pts", "2P", "3P", "FT", "Reb", "Ast", "TOV", "Stl", "PIR", "+/-"], rows,
                    ["---"] + ["---:"] * 11) + "\n\nBold = starter."


def results_md(games, rnd, highlight) -> str:
    res = st.results_by_round(games); res = res[res["round"] == rnd]
    items = []
    for _, x in res.iterrows():
        txt = f"{short(x.home_team)} {x.home_score}-{x.away_score} {short(x.away_team)}"
        items.append(f"- **{txt}**" if (x.home_team == highlight or x.away_team == highlight) else f"- {txt}")
    return "\n".join(items)


def standings_table_md(games, rnd, highlight) -> str:
    t = st.standings(games.assign(), None)
    g = games[games["round"] <= rnd]
    t = st.standings(g, None)
    rows = [[x.pos, f"**{short(tm)}**" if tm == highlight else short(tm), x.pts, f"{x.w}-{x.l}", f"{x['diff']:+d}", x.form] for tm, x in t.iterrows()]
    return md_table(["#", "Team", "Pts", "W-L", "Diff", "Results"], rows, ["---:", "---", "---:", ":---:", "---:", ":---:"])


def next_game(games, team, rnd) -> dict | None:
    n = games[(games["round"] > rnd) & ((games.home_team == team) | (games.away_team == team))].sort_values("round")
    if n.empty:
        return None
    x = n.iloc[0]; home = x.home_team == team
    return {"round": int(x["round"]), "opponent": short(x.away_team if home else x.home_team), "home": bool(home),
            "date": x.match_datetime[:10], "time": x.match_datetime[11:16], "venue": None if pd.isna(x.venue) else x.venue}


# ── main ────────────────────────────────────────────────────────────────────────
def finished_rounds(games: pd.DataFrame, team: str) -> list[int]:
    g = games[((games.home_team == team) | (games.away_team == team)) & (games.game_status.astype(str) == "2")]
    return sorted(int(r) for r in g["round"].unique())


def generate(rnd: int, team: str = TEAM, data: Path = ROOT / "data") -> Path:
    """Write reports/weekly/round-NN/ (figures + auto.json) and, once, weekly/round-NN/notes.md. Returns the output folder."""
    lba_style.AUTHOR = CFG["author"] or lba_style.AUTHOR
    games = pd.read_csv(data / "games.csv")
    box = pd.read_csv(data / "box_scores.csv")
    pbp = pd.read_csv(data / "pbp.csv")
    g = find_game(games, team, rnd)
    home = g.home_team == team
    opp = g.away_team if home else g.home_team
    pf, pa = (g.home_score, g.away_score) if home else (g.away_score, g.home_score)

    out = ROOT / "reports" / "weekly" / f"round-{rnd:02d}"
    out.mkdir(parents=True, exist_ok=True)
    lba_style.STAMP_NOTE = f"through round {rnd}"

    gr = games[games["round"] <= rnd]
    st.fig_standings(gr, None, [team, opp], out)
    (out / "00_standings.png").replace(out / "standings.png")
    margin = fig_margin(g, pbp, team, out)
    fig_players(box, g, team, out)
    fig_season(games, team, rnd, out)

    # extra sections: roster, playing time, assists, zones, TS% vs PIR
    date = g.match_datetime[:10]
    player_photos.main_quiet(team)
    xbox = ws.load_box(data, rnd, date, CFG["eurocup_file"])
    lba_games = [int(x) for x in games[(games["round"] <= rnd) & (games.game_status.astype(str) == "2") &
                                       ((games.home_team == team) | (games.away_team == team))].game_id]
    pairs = ws.assist_pairs(pbp, lba_games, team)
    box_ast = int(box[(box.game_id.isin(lba_games)) & (box.team == team) & (box.row_type == "total")].ast.sum())
    extra = {
        "roster": ws.roster_table(xbox, data),
        "playing_time": ws.playing_time_flags(xbox, str(g.game_id), date),
        "assist_top": ws.fig_assists(pairs, box_ast, out, team),
        "zone_share": ws.fig_zones(pbp, lba_games, int(g.game_id), out, team),
        "ts_pir_lba": ws.fig_ts_pir(xbox, "LBA", out, team=team),
        "ts_pir_ec": ws.fig_ts_pir(xbox, "EC", out, team=team) if ((xbox.competition == "EC") & (xbox.team == team)).any() else None,
    }
    photos = {r["player_id"] for r in extra["roster"] if r["photo"]}
    for pid in photos:
        shutil.copy(data / "photos" / f"{pid}.jpg", out / f"photo_{pid}.jpg")

    q = quarter_scores(g, pbp)
    qs = [(h, aw) if home else (aw, h) for h, aw in q]
    t, o = team_totals(box, g.game_id, team), team_totals(box, g.game_id, opp)
    ff_t, ff_o = four_factors(t, o), four_factors(o, t)
    ff_md = md_table(["", short(team), short(opp)], [[k, ff_t[k], ff_o[k]] for k in ff_t], ["---", "---:", "---:"])

    tab = st.standings(gr, None)
    auto = {
        "round": rnd, "game_id": int(g.game_id), "team": team, "opponent": short(opp), "opponent_full": opp,
        "home": bool(home), "win": bool(pf > pa), "score_for": int(pf), "score_against": int(pa),
        "date": g.match_datetime[:10], "time": g.match_datetime[11:16],
        "venue": None if pd.isna(g.venue) else g.venue, "town": None if pd.isna(g.town) else g.town,
        "spectators": None if pd.isna(g.spectators) else int(g.spectators),
        "coach": g.home_coach if home else g.away_coach, "coach_opp": g.away_coach if home else g.home_coach,
        "quarters": [{"for": int(f), "against": int(ag)} for f, ag in qs],
        "record": f"{int(tab.loc[team, 'w'])}-{int(tab.loc[team, 'l'])}", "position": int(tab.loc[team, "pos"]),
        "margin": margin, "four_factors": ff_t, "four_factors_opp": ff_o,
        "md": {"four_factors": ff_md, "box": box_md(box, g, team), "box_opp": box_md(box, g, opp),
               "results": results_md(games, rnd, team), "standings": standings_table_md(games, rnd, team)},
        "next": next_game(games, team, rnd),
        **extra,
    }
    (out / "auto.json").write_text(json.dumps(auto, indent=2, ensure_ascii=False), encoding="utf-8")

    notes_dir = ROOT / "weekly" / f"round-{rnd:02d}"
    if not (notes_dir / "notes.md").exists():
        notes_dir.mkdir(parents=True, exist_ok=True)
        text = (ROOT / "weekly" / "template" / "notes.md").read_text(encoding="utf-8").replace("{{round}}", str(rnd))
        (notes_dir / "notes.md").write_text(text, encoding="utf-8")
        print(f"created {notes_dir / 'notes.md'} - write your text there")
    print(f"round {rnd}: {short(team)} {pf}-{pa} {short(opp)}  ->  {out}")
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
