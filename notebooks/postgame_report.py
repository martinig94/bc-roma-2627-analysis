"""Post-game report: one game compared with what the two teams and their players had done before it.

    python notebooks/postgame_report.py --game 25378 --out reports/
    python notebooks/postgame_report.py --game 25378 --no-eurocup

"Before" = every game (LBA + EuroCup when the EuroCup file is present) each team played before this one.
Per-game figures are per-game averages; shooting splits are pooled.

Figures:
  pg_01_margin          score margin through the game, quarter scores, biggest runs
  pg_02_team            team numbers: before (average) -> this game, both teams, one dumbbell per stat
  pg_03_players         players (>=10' in the game): PIR and points in the game vs their average before
  pg_04_zones           FG% by zone, pre-game LBA games vs this game, both teams
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import lba_style
from lba_style import (GREEN, LEAGUE, RED, SUP_KW, TEXT, TEXT2, TITLE_KW, draw_half_court, draw_zone_fill, save_fig,
                       shots_cm, style_axes, team_color, ZONE_LABEL_POS)
from matchup_report import PAINT_CM, load_lba, parse_eurocup, scoring_sources, short, starters_bench, zone_stats

BEFORE = "#b9bdd0"   # "before" marker colour (neutral), the team colour marks the game


# ── data ────────────────────────────────────────────────────────────────────────
def team_lines(box, pbp, ec_zones, team, game_id):
    """One row per game: points, paint, threes, FT, assists, TOV, OREB, fouls drawn, bench points, pace."""
    src = scoring_sources(box, pbp, ec_zones, team); src.index = src.game_id.astype(str)
    sb = starters_bench(box, team); sb.index = sb.game_id.astype(str)
    tot = box[(box.row_type == "total") & (box.team == team)].copy(); tot.index = tot.game_id.astype(str)
    d = pd.DataFrame({
        "points": tot.pts, "points allowed": src.opp_pts,
        "paint points": src.paint, "3PA": tot.fg3a, "3P%": 100 * tot.fg3m / tot.fg3a, "2P%": 100 * tot.fg2m / tot.fg2a,
        "FTA": tot.fta, "FT%": 100 * tot.ftm / tot.fta, "assists": tot.ast, "turnovers": tot.tov, "off. rebounds": tot.oreb,
        "def. rebounds": tot.dreb, "fouls drawn": tot.pf_drawn, "bench points": sb.bench,
        "possessions": tot.fg2a + tot.fg3a - tot.oreb + tot.tov + 0.44 * tot.fta,
    })
    d["date"] = src.date; d["competition"] = src.competition; d["opponent"] = src.opponent
    d["this"] = d.index.astype(str) == str(game_id)
    return d


def player_lines(box, team, game_id):
    b = box[(box.row_type == "player") & (box.team == team) & (box.sec > 0)].copy()
    b["fga"] = b.fg2a + b.fg3a; b["mn"] = b.sec / 60
    b["this"] = b.game_id.astype(str) == str(game_id)
    prev = b[~b.this].groupby("player_surname").agg(g=("game_id", "nunique"), mn=("mn", "mean"), pts=("pts", "mean"), val=("val", "mean"),
                                                     pm=("plus_minus", "mean"), ptsS=("pts", "sum"), fga=("fga", "sum"), fta=("fta", "sum"))
    prev["ts"] = prev.ptsS / (2 * (prev.fga + 0.44 * prev.fta))
    cur = b[b.this].set_index("player_surname")
    cur["ts"] = cur.pts / (2 * (cur.fga + 0.44 * cur.fta)).replace(0, np.nan)
    j = cur[["mn", "pts", "val", "plus_minus", "ts", "ast", "reb", "tov", "fg2m", "fg2a", "fg3m", "fg3a", "ftm", "fta"]].join(prev, rsuffix="_prev")
    j.index = j.index.str.title()
    return j.sort_values("mn", ascending=False)


# ── figures ─────────────────────────────────────────────────────────────────────
def fig_margin(pbp, games, game_id, out):
    g = games[games.game_id == game_id].iloc[0]
    p = pbp[pbp.game_id == game_id].sort_values("seq")
    p = p[p.score_home.notna()].copy()
    p["t"] = (p.period - 1) * 600 + p.elapsed_sec
    p["margin"] = p.score_home - p.score_away
    home, away = g.home_team, g.away_team
    ch, _ = team_color(home); ca, _ = team_color(away, 1)
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.step(p.t / 60, p.margin, where="post", color=TEXT, lw=1.6, zorder=3)
    ax.fill_between(p.t / 60, p.margin, 0, where=p.margin >= 0, step="post", color=ch, alpha=0.6, zorder=2)
    ax.fill_between(p.t / 60, p.margin, 0, where=p.margin < 0, step="post", color=ca, alpha=0.6, zorder=2)
    ax.axhline(0, color=TEXT2, lw=0.8)
    qs = [(g.q1_home, g.q1_away), (g.q2_home, g.q2_away), (g.q3_home, g.q3_away), (g.q4_home, g.q4_away)]
    ymax = max(abs(p.margin).max() + 4, 10)
    for i, (h, a) in enumerate(qs):
        ax.axvline(10 * (i + 1), color=LEAGUE, lw=0.8, ls="--")
        ax.text(10 * i + 5, ymax - 1.2, f"Q{i + 1}: {int(h)}–{int(a)}", ha="center", va="top", fontsize=9.5, color=TEXT2, fontweight="bold")
    # biggest runs: longest stretches without the other team scoring
    runs = []
    for side, sign in (("home", 1), ("away", -1)):
        sc = p[["t", "score_home", "score_away"]].drop_duplicates()
        own = sc.score_home if side == "home" else sc.score_away; oth = sc.score_away if side == "home" else sc.score_home
        start = 0
        for k in range(1, len(sc)):
            if oth.iloc[k] > oth.iloc[k - 1]:
                start = k
            pts = own.iloc[k] - own.iloc[start]
            runs.append((pts, sign, sc.t.iloc[start], sc.t.iloc[k], side))
    for pts, sign, t0, t1, side in sorted(runs, reverse=True)[:1] + sorted([r for r in runs if r[1] == -sorted(runs, reverse=True)[0][1]], reverse=True)[:1]:
        if pts >= 6:
            tm = home if side == "home" else away
            ax.annotate(f"{tm} {pts}–0 run", xy=((t0 + t1) / 120, p[p.t <= t1].margin.iloc[-1]), xytext=((t0 + t1) / 120, (-ymax + 3) if side == "away" else (ymax - 5)),
                        ha="center", fontsize=8.5, color=TEXT2, arrowprops=dict(arrowstyle="-", color=TEXT2, lw=0.7))
    ax.set_xlim(0, 40); ax.set_ylim(-ymax, ymax); ax.set_xticks([0, 10, 20, 30, 40]); ax.set_xlabel("minutes played")
    ax.set_ylabel(f"← {away} ahead   |   {home} ahead →", fontsize=9)
    style_axes(ax, "y")
    ax.set_title(f"{home} {int(g.home_score)}–{int(g.away_score)} {away}  ·  {str(g.match_datetime)[:10]}  ·  {g.venue}", **TITLE_KW)
    fig.suptitle("Score margin through the game", **SUP_KW)
    save_fig(fig, out / "pg_01_margin.png"); plt.close(fig)


TEAM_STATS = ["points", "points allowed", "paint points", "3PA", "3P%", "2P%", "FTA", "FT%", "assists", "turnovers", "off. rebounds", "fouls drawn", "bench points", "possessions"]


def fig_team(lines: dict, game_id, out):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.4), sharey=True)
    y = np.arange(len(TEAM_STATS))[::-1]
    for ax, (team, d) in zip(axes, lines.items()):
        fill, edge = team_color(team, list(lines).index(team))
        before, this = d[~d.this], d[d.this].iloc[0]
        for yi, st in zip(y, TEAM_STATS):
            b, t = before[st].mean(), this[st]
            lo, hi = before[st].min(), before[st].max()
            scale = max(hi, t, 1)
            ax.plot([0, 0], [yi, yi], alpha=0)
            # normalise each stat to its own row: draw on a 0..1 axis with text values
            xb, xt = b / scale, t / scale
            ax.plot([lo / scale, hi / scale], [yi, yi], color=BEFORE, lw=6, alpha=0.6, solid_capstyle="round", zorder=1)
            ax.plot([xb, xt], [yi, yi], color=TEXT2, lw=1, zorder=2)
            ax.scatter([xb], [yi], s=70, color=BEFORE, edgecolor=TEXT2, zorder=3)
            ax.scatter([xt], [yi], s=110, color=fill, edgecolor=edge, zorder=4)
            fmt = (lambda v: f"{v:.0f}%") if "%" in st else (lambda v: f"{v:.1f}" if st == "possessions" else f"{v:.0f}")
            neutral = st in ("3PA", "possessions")
            better = (t < b) if st in ("points allowed", "turnovers") else (t > b)
            ax.text(1.04, yi, f"{fmt(b)} → {fmt(t)}", va="center", fontsize=9, color=TEXT2 if neutral else (GREEN if better else RED), fontweight="bold")
        ax.set_yticks(y); ax.set_yticklabels(TEAM_STATS, fontsize=10); ax.set_xlim(0, 1.3); ax.set_xticks([])
        style_axes(ax); ax.grid(axis="y", color="#eeeef2")
        ax.set_title(f"{team}\naverage of {len(before)} previous games → this game", **TITLE_KW)
    fig.suptitle("Team numbers: before the game vs in the game (grey bar = range of the previous games)", **SUP_KW)
    fig.text(0.01, -0.06, "Green = better than the previous average, red = worse (lower is better for points allowed and turnovers), grey = neutral. "
             "Previous games include EuroCup where available; paint points = made field goals within 4.5 m.", fontsize=8, color=TEXT2)
    save_fig(fig, out / "pg_02_team.png"); plt.close(fig)


def fig_players(players: dict, out, min_minutes=10):
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.8))
    for ax, (team, j) in zip(axes, players.items()):
        fill, edge = team_color(team, list(players).index(team))
        d = j[j.mn >= min_minutes].copy()
        y = np.arange(len(d))[::-1]; h = 0.38
        ax.barh(y + h / 2, d.val_prev.fillna(0), h, color=BEFORE, edgecolor=TEXT2, linewidth=0.4, label="PIR, average before")
        ax.barh(y - h / 2, d.val, h, color=fill, edgecolor=edge, linewidth=0.6, label="PIR, this game")
        xmax = max(d.val.max(), d.val_prev.max()) + 14
        for yi, (name, r) in zip(y, d.iterrows()):
            pb = "" if np.isnan(r.pts_prev) else f"{r.pts_prev:.0f}"
            line = f"{r.pts:.0f} pts ({pb} before) · {r.mn:.0f}' · {int(r.plus_minus):+d}"
            ax.text(max(r.val, r.val_prev if not np.isnan(r.val_prev) else 0) + 0.6, yi, line, va="center", fontsize=8.5, color=TEXT2)
        ax.axvline(0, color=TEXT2, lw=0.8)
        ax.set_yticks(y); ax.set_yticklabels(d.index, fontsize=10); ax.set_xlim(min(0, d.val.min() - 2), xmax); ax.set_xlabel("PIR (league efficiency rating)")
        style_axes(ax, "x"); ax.legend(fontsize=8.5, loc="lower right")
        ax.set_title(f"{team} — players with ≥{min_minutes}' in the game", **TITLE_KW)
    fig.suptitle("Players: this game vs their average before it (points, minutes and +/- are from this game)", **SUP_KW)
    save_fig(fig, out / "pg_03_players.png"); plt.close(fig)


def fig_zones(pbp, teams, game_id, out):
    s = shots_cm(pbp)
    fig, axes = plt.subplots(2, 2, figsize=(13, 13))
    cmap = plt.cm.RdYlGn.copy()
    for row, team in zip(axes, teams):
        for ax, (label, st) in zip(row, (("LBA games before", s[(s.team == team) & (s.game_id != game_id)]), ("this game", s[(s.team == team) & (s.game_id == game_id)]))):
            z = zone_stats(st)
            draw_zone_fill(ax, {k: p for k, (_, _, p) in z.items()}, cmap)
            draw_half_court(ax, color="#3a3d52", lw=1.6)
            for k, (cx, cy) in ZONE_LABEL_POS.items():
                mk, att, p = z.get(k, (0, 0, 0.0))
                lab, col = ("0/0\n—", "#8a8d9c") if att == 0 else (f"{mk}/{att}\n{p:.0f}%", "black" if 25 < p < 75 else "white")
                ax.text(cx, cy, lab, ha="center", va="center", color=col, fontsize=9, fontweight="bold", zorder=5)
            ax.set_title(f"{team} — {label}: {int(st.made.sum())}/{len(st)} FG", **TITLE_KW)
    fig.suptitle("FG% by zone: before vs this game (LBA play-by-play only)", **SUP_KW)
    save_fig(fig, out / "pg_04_zones.png"); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", type=int, required=True)
    ap.add_argument("--data", default=str(Path(__file__).resolve().parent.parent / "data"))
    ap.add_argument("--eurocup", default=None); ap.add_argument("--no-eurocup", action="store_true")
    ap.add_argument("--out", default="reports")
    a = ap.parse_args()
    data = Path(a.data)
    games, box, pbp = load_lba(data)
    g = games[games.game_id == a.game].iloc[0]
    teams = [g.home_team, g.away_team]
    ec_zones = pd.DataFrame(columns=["game_id", "team", "zone", "action", "n"])
    ec_path = Path(a.eurocup) if a.eurocup else data / "eurocup_2026_raw.txt"
    if not a.no_eurocup and ec_path.exists():
        ec_box, ec_zones = parse_eurocup(ec_path)
        ec_box = ec_box[ec_box.team.isin(teams)]
        box = pd.concat([box, ec_box], ignore_index=True)
    # only games before this one count as "before"
    gdate = str(g.match_datetime)[:10]
    box = box[(box.date <= gdate)]
    out = Path(a.out) / f"postgame_{a.game}_{teams[0].replace(' ', '_')}_vs_{teams[1].replace(' ', '_')}"; out.mkdir(parents=True, exist_ok=True)
    lines = {t: team_lines(box, pbp, ec_zones, t, a.game) for t in teams}
    players = {t: player_lines(box, t, a.game) for t in teams}
    fig_margin(pbp, games, a.game, out)
    fig_team(lines, a.game, out)
    fig_players(players, out)
    fig_zones(pbp[pbp.game_id.isin(box.game_id)], teams, a.game, out)
    pd.set_option("display.width", 250)
    for t in teams:
        print(f"\n== {t} ==\n", lines[t][TEAM_STATS + ["opponent", "this"]].round(1).to_string())
        print(players[t].round(2).to_string())
    print("\nfigures in", out)


if __name__ == "__main__":
    main()
