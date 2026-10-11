"""Season-to-date team report in the basketball_analytics style (white background, team in gold).

    python notebooks/team_report.py --team "BC Roma" --out reports/

Every figure compares the team with the rest of the league from the same collected games.
Player charts print minutes played next to each name. Works from round 1 onwards and
just gets more meaningful as data/ grows.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from lba_style import (save_fig, draw_zone_fill, BLUE, DPI, GOLD, GOLD_EDGE, GREEN, LEAGUE, ORANGE, RED, SUP_KW, TEXT, TEXT2, TITLE_KW,
                       ZONE_LABEL_POS as _ZONE_LABEL_POS, ZONE_LABELS, assign_zone_arr, draw_half_court, mins,
                       shots_cm, style_axes, team_bar_kw)


# ── data ────────────────────────────────────────────────────────────────────────
def load(data: Path):
    games = pd.read_csv(data / "games.csv")
    box = pd.read_csv(data / "box_scores.csv")
    pbp = pd.read_csv(data / "pbp.csv")
    return games, box, pbp


def player_table(box: pd.DataFrame) -> pd.DataFrame:
    p = box[(box.row_type == "player")].copy()
    g = p.groupby(["team", "player_surname"], as_index=False).agg(
        GP=("game_id", "nunique"), sec=("sec", "sum"), pts=("pts", "sum"), ast=("ast", "sum"), reb=("reb", "sum"),
        tov=("tov", "sum"), val=("val", "sum"), fg2m=("fg2m", "sum"), fg2a=("fg2a", "sum"), fg3m=("fg3m", "sum"),
        fg3a=("fg3a", "sum"), ftm=("ftm", "sum"), fta=("fta", "sum"), pm=("plus_minus", "sum"))
    g["Player"] = g.player_surname.str.title()
    g["MIN"] = g.sec / 60
    g["MPG"] = g.MIN / g.GP
    g["PPG"], g["APG"], g["PIR"] = g.pts / g.GP, g.ast / g.GP, g.val / g.GP
    g["fga"], g["fgm"] = g.fg2a + g.fg3a, g.fg2m + g.fg3m
    g["eFG%"] = 100 * (g.fgm + 0.5 * g.fg3m) / g.fga.replace(0, np.nan)
    g["FT%"] = 100 * g.ftm / g.fta.replace(0, np.nan)
    g["TS%"] = 100 * g.pts / (2 * (g.fga + 0.44 * g.fta)).replace(0, np.nan)
    g["TO_per40"] = 40 * g.tov / g.MIN.replace(0, np.nan)
    return g


def league_line(box: pd.DataFrame) -> dict:
    t = box[box.row_type == "total"]
    fga, fgm, f3m, ftm, fta, pts = (t.fg2a + t.fg3a).sum(), (t.fg2m + t.fg3m).sum(), t.fg3m.sum(), t.ftm.sum(), t.fta.sum(), t.pts.sum()
    return {"eFG%": 100 * (fgm + 0.5 * f3m) / fga, "FT%": 100 * ftm / fta, "TS%": 100 * pts / (2 * (fga + 0.44 * fta)),
            "TO_per40": 36 * t.tov.sum() / (t.sec.sum() / 60) * 5}   # per player-36 min: team TOV over 5 players


# ── figures ─────────────────────────────────────────────────────────────────────
def zone_stats(s: pd.DataFrame) -> dict[str, tuple[int, int, float]]:
    agg = s.groupby("zone").agg(att=("made", "size"), mk=("made", "sum"))
    return {z: (int(r.mk), int(r.att), 100 * r.mk / r.att) for z, r in agg.iterrows()}


def plot_zone_heatmap(ax, s, title, ref: dict | None = None, colorbar=True, fontsize=8.5):
    st = zone_stats(s)
    cmap = plt.cm.RdYlGn.copy()
    draw_zone_fill(ax, {z: p for z, (_, _, p) in st.items()}, cmap)
    mesh = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 100)); mesh.set_array([])
    draw_half_court(ax, color="#3a3d52", lw=1.6)
    for z, (cx, cy) in _ZONE_LABEL_POS.items():
        mk, att, p = st.get(z, (0, 0, 0.0))
        if att == 0:
            lab, col = "0/0\n—", "#8a8d9c"
        else:
            lab, col = f"{mk}/{att}\n{p:.0f}%", "black" if 25 < p < 75 else "white"
            if ref and z in ref and ref[z][1] > 0:
                lab += f"\nleague {ref[z][2]:.0f}%"
        ax.text(cx, cy, lab, ha="center", va="center", color=col, fontsize=fontsize, fontweight="bold", zorder=5)
    if colorbar:
        cb = plt.colorbar(mesh, ax=ax, fraction=0.025, pad=0.02)
        cb.set_ticks([0, 25, 50, 75, 100]); cb.set_label("FG%", color=TEXT, fontsize=8)
        cb.ax.yaxis.set_tick_params(color=TEXT)
    ax.set_title(title, **TITLE_KW)
    return mesh


def fig_zone_heatmaps(s_team, s_league, team, label, out):
    fig, axes = plt.subplots(1, 2, figsize=(15, 8))
    ref = zone_stats(s_league)
    plot_zone_heatmap(axes[0], s_team, f"{team} — Shot Zone Heatmap", ref=ref, colorbar=False)
    mesh = plot_zone_heatmap(axes[1], s_league, "League (all other teams) — Shot Zone Heatmap", colorbar=False)
    cb = fig.colorbar(mesh, ax=axes, fraction=0.02, pad=0.02)
    cb.set_ticks([0, 25, 50, 75, 100]); cb.set_label("FG%", color=TEXT, fontsize=8)
    cb.ax.yaxis.set_tick_params(color=TEXT)
    fig.suptitle(f"{team} — LBA 2026-27 {label}  |  FG% by zone vs league", **SUP_KW)
    fig.text(0.01, 0.01, "Third line in each zone = FG% of all other LBA teams in that zone, from the collected games.",
             color=TEXT2, fontsize=8)
    save_fig(fig, out / "zone_heatmap_team.png"); plt.close(fig)


def fig_zone_heatmap_players(s_team, pt, team, label, out, n=8):
    top = pt.sort_values("MIN", ascending=False).head(n)
    cols = 4; rows = int(np.ceil(len(top) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(5.0 * cols, 5.4 * rows))
    for ax, (_, r) in zip(axes.ravel(), top.iterrows()):
        sp = s_team[s_team.player.str.upper() == r.player_surname.upper()]
        plot_zone_heatmap(ax, sp, f"{r.Player}  ({mins(r.MIN)}, {int(sp.made.sum())}/{len(sp)} FG)", colorbar=False, fontsize=7.5)
    for ax in axes.ravel()[len(top):]:
        ax.axis("off")
    fig.suptitle(f"{team} — LBA 2026-27 {label}  |  Player Shot Zones (top {len(top)} by minutes)", **SUP_KW)
    save_fig(fig, out / "zone_heatmap_players.png"); plt.close(fig)


def fig_shot_chart(s_team, team, label, out):
    fig, ax = plt.subplots(figsize=(8, 8))
    draw_half_court(ax)
    miss, make = s_team[~s_team.made], s_team[s_team.made]
    ax.scatter(miss.cx, miss.cy, s=55, facecolors="none", edgecolors=RED, linewidths=1.3, label=f"Miss ({len(miss)})", zorder=3)
    ax.scatter(make.cx, make.cy, s=55, c=GOLD, edgecolors=GOLD_EDGE, linewidths=0.7, label=f"Make ({len(make)})", zorder=4)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=2, fontsize=9)
    ax.set_title(f"Shot Chart — all {team} field goal attempts", **TITLE_KW)
    fig.suptitle(f"{team} — LBA 2026-27 {label}", **SUP_KW)
    save_fig(fig, out / "shot_chart.png"); plt.close(fig)


def fig_player_offense(pt_team, lg, team, label, out):
    d = pt_team[pt_team.MIN > 0].sort_values("PIR")
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(19, 7.5), gridspec_kw={"wspace": 0.35})
    y = np.arange(len(d))
    ax0.barh(y, d.PPG, label="PPG", **team_bar_kw())
    ax0.barh(y, d.APG, left=d.PPG, color=BLUE, label="APG", alpha=0.9)
    ax0.set_yticks(y); ax0.set_yticklabels([f"{p}  ({mins(m)})" for p, m in zip(d.Player, d.MIN)], fontsize=9)
    for i, (ppg, apg, pir) in enumerate(zip(d.PPG, d.APG, d.PIR)):
        ax0.text(ppg + apg + 0.3, i, f"PIR {pir:.1f}", va="center", color=TEXT2, fontsize=8)
    ax0.set_title("Offensive Players — sorted by PIR (LBA val.)\n(PPG + APG stacked, minutes in brackets)", **TITLE_KW)
    ax0.legend(fontsize=9, loc="lower right"); style_axes(ax0)

    e = d[d.fga > 0].sort_values("TS%", ascending=False)
    x = np.arange(len(e)); w = 0.25
    ax1.bar(x - w, e["eFG%"], w, label="eFG%", **team_bar_kw())
    ax1.bar(x, e["FT%"].fillna(0), w, color=BLUE, label="FT%", alpha=0.9)
    ax1.bar(x + w, e["TS%"], w, color=GREEN, label="TS%", alpha=0.9)
    for key, col, off in (("eFG%", GOLD, -w), ("FT%", BLUE, 0), ("TS%", GREEN, w)):
        ax1.axhline(lg[key], color=col, lw=1, ls="--", alpha=0.7)
    ax1.text(len(e) - 0.4, lg["TS%"] + 1, f"league TS% {lg['TS%']:.0f}", color=TEXT2, fontsize=8, ha="right")
    ax1.text(len(e) - 0.4, lg["eFG%"] - 3.5, f"league eFG% {lg['eFG%']:.0f}", color=TEXT2, fontsize=8, ha="right")
    ax1.text(len(e) - 0.4, lg["FT%"] + 1, f"league FT% {lg['FT%']:.0f}", color=TEXT2, fontsize=8, ha="right")
    ax1.set_xticks(x); ax1.set_xticklabels([f"{p} ({mins(m)})" for p, m in zip(e.Player, e.MIN)], rotation=35, ha="right", fontsize=8)
    ax1.set_ylim(0, 105); ax1.set_ylabel("Percentage", fontsize=9)
    ax1.set_title("Shooting Efficiency: eFG% / FT% / TS%\n(dashed = league average, same colour)", **TITLE_KW)
    ax1.legend(fontsize=9, loc="upper right"); style_axes(ax1, "y")
    fig.suptitle(f"{team} — LBA 2026-27 {label}  |  Player Offensive Overview", **SUP_KW)
    save_fig(fig, out / "player_PIR.png"); plt.close(fig)


def fig_pir_ts(pt, team, label, out, min_minutes=10):
    d = pt[(pt.MIN >= min_minutes) & (pt.fga > 0)].copy()
    tm, lg = d[d.team == team], d[d.team != team]
    fig, ax = plt.subplots(figsize=(13, 9))
    size = lambda mpg: mpg / d.MPG.max() * 400 + 40
    ax.scatter(lg.PIR, lg["TS%"], s=size(lg.MPG), c=LEAGUE, alpha=0.45, edgecolors="none", zorder=2, label="other LBA players")
    ax.scatter(tm.PIR, tm["TS%"], s=size(tm.MPG), c=GOLD, alpha=0.95, edgecolors=GOLD_EDGE, linewidths=0.8, zorder=3, label=team)
    for i, (_, r) in enumerate(tm.sort_values("PIR").iterrows()):
        ax.annotate(f"{r.Player} ({mins(r.MIN)})", (r.PIR, r["TS%"]), xytext=(6, 6 if i % 2 else -12),
                    textcoords="offset points", color=TEXT, fontsize=8, zorder=4)
    ax.axvline(lg.PIR.median(), color=TEXT, lw=0.7, ls="--", alpha=0.35)
    ax.axhline(lg["TS%"].median(), color=TEXT, lw=0.7, ls="--", alpha=0.35)
    ax.text(lg.PIR.median() + 0.2, ax.get_ylim()[0] + 2, "league median PIR", color=TEXT2, fontsize=8)
    ax.text(ax.get_xlim()[0] + 0.3, lg["TS%"].median() + 0.8, "league median TS%", color=TEXT2, fontsize=8)
    ax.set_xlabel("PIR per game (LBA valutazione)", fontsize=9); ax.set_ylabel("TS% (True Shooting %)", fontsize=9)
    ax.set_title(f"PIR vs True Shooting%  —  dot size = MPG, min {min_minutes} minutes", **TITLE_KW)
    ax.legend(fontsize=9, loc="lower right"); style_axes(ax)
    fig.suptitle(f"{team} — LBA 2026-27 {label}  |  PIR vs True Shooting%", **SUP_KW)
    save_fig(fig, out / "player_pir_ts.png"); plt.close(fig)


def fig_turnovers(pt_team, pt_league, team, label, out, min_minutes=5):
    d = pt_team[pt_team.MIN >= min_minutes].sort_values("TO_per40", ascending=False)
    lg_med = pt_league[pt_league.MIN >= min_minutes].TO_per40.median()
    fig, ax = plt.subplots(figsize=(9, 6))
    cols = [RED if v > 3.5 else ORANGE if v > 2.5 else GOLD for v in d.TO_per40]
    ax.barh([f"{p}  ({mins(m)})" for p, m in zip(d.Player, d.MIN)], d.TO_per40, color=cols, edgecolor=GOLD_EDGE, linewidth=0.5)
    for i, (v, t) in enumerate(zip(d.TO_per40, d.tov)):
        ax.text(v + 0.08, i, f"{v:.2f}  ({int(t)} TO)", va="center", color=TEXT, fontsize=9)
    ax.axvline(3.5, color=RED, lw=0.8, ls="--", alpha=0.6)
    ax.axvline(lg_med, color=LEAGUE, lw=1.2, ls="--"); ax.text(lg_med, len(d) - 0.4, f" league median {lg_med:.1f}", color=LEAGUE, fontsize=8)
    ax.set_title(f"Turnovers per 40 min  (red > 3.5, min {min_minutes} minutes)", **TITLE_KW)
    style_axes(ax)
    fig.suptitle(f"{team} — LBA 2026-27 {label}", **SUP_KW)
    save_fig(fig, out / "player_turnovers.png"); plt.close(fig)


def fig_zone_shares(s_team, s_league, team, label, out):
    """Where the shots come from and what they are worth, team vs league, by the 9 zones."""
    def tab(s):
        g = s.groupby("zone").agg(att=("made", "size"), pts=("pts", lambda p: 0))
        g["pts"] = s.assign(p=s.made * s.pts).groupby("zone").p.sum()
        g["share"] = 100 * g.att / g.att.sum(); g["ppa"] = g.pts / g.att
        return g.reindex(list(ZONE_LABELS)).fillna(0)
    t, l = tab(s_team), tab(s_league)
    fig, axes = plt.subplots(1, 2, figsize=(16, 5.5), gridspec_kw={"wspace": 0.25})
    x = np.arange(9); w = 0.38
    axes[0].bar(x - w / 2, t.share, w, label=team, **team_bar_kw()); axes[0].bar(x + w / 2, l.share, w, color=LEAGUE, label="league")
    for xi, (a, sh) in enumerate(zip(t.att, t.share)):
        axes[0].text(xi - w / 2, sh + 0.6, f"{int(a)}", ha="center", fontsize=8, color=TEXT2)
    axes[0].set_ylabel("% of FGA"); axes[0].set_title("Shot distribution by zone (n on team bars)", **TITLE_KW)
    axes[1].bar(x - w / 2, t.ppa, w, label=team, **team_bar_kw()); axes[1].bar(x + w / 2, l.ppa, w, color=LEAGUE, label="league")
    axes[1].axhline(1.0, color=TEXT, lw=0.8, ls="--", alpha=0.4); axes[1].set_ylabel("points per attempt")
    axes[1].set_title("Points per attempt by zone", **TITLE_KW)
    for ax in axes:
        ax.set_xticks(x); ax.set_xticklabels([f"{z}\n" + ZONE_LABELS[z].replace(" ", "\n") for z in ZONE_LABELS], fontsize=8)
        ax.legend(fontsize=9); style_axes(ax, "y")
    fig.suptitle(f"{team} — LBA 2026-27 {label}  |  Shot profile vs league", **SUP_KW)
    save_fig(fig, out / "zone_profile_vs_league.png"); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", default="BC Roma")
    ap.add_argument("--data", default=str(Path(__file__).resolve().parent.parent / "data"))
    ap.add_argument("--out", default="reports")
    a = ap.parse_args()
    games, box, pbp = load(Path(a.data))
    out = Path(a.out) / f"season_{a.team.replace(' ', '_')}"; out.mkdir(parents=True, exist_ok=True)

    played = box[box.row_type == "total"].game_id.nunique()
    team_games = box[(box.team == a.team) & (box.row_type == "total")].game_id.nunique()
    label = f"(after round {int(games[games.game_status == 2]['round'].max())}, {team_games} game{'s' if team_games != 1 else ''})"

    s = shots_cm(pbp)
    s_team, s_league = s[s.team == a.team], s[s.team != a.team]
    pt = player_table(box)
    pt_team, pt_league = pt[pt.team == a.team], pt[pt.team != a.team]
    lg = league_line(box[box.team != a.team])

    fig_zone_heatmaps(s_team, s_league, a.team, label, out)
    fig_zone_heatmap_players(s_team, pt_team, a.team, label, out)
    fig_shot_chart(s_team, a.team, label, out)
    fig_zone_shares(s_team, s_league, a.team, label, out)
    fig_player_offense(pt_team, lg, a.team, label, out)
    fig_pir_ts(pt, a.team, label, out)
    fig_turnovers(pt_team, pt_league, a.team, label, out)
    print(f"{played} league games, {team_games} {a.team} games -> {out}")


if __name__ == "__main__":
    main()
