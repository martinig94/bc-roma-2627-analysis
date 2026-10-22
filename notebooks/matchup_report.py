"""Pre-game matchup report between two LBA teams, season to date, with the league as reference.

    python notebooks/matchup_report.py --home "Maxima Roma" --away "BC Roma" --out reports/
    python notebooks/matchup_report.py --home "BC Roma" --away "Umana Reyer Venezia" --no-eurocup

Figures (all season-to-date, both LBA and EuroCup games when the EuroCup file is present):
  01_results_timeline     game-by-game points for/against, both teams
  02_starters_bench       points from the starting five vs the bench, per game + league average
  03_minutes              minutes distribution per player (per game), both rosters
  04_scoring_sources      points ≤4.5 m from the rim, mid-range, threes, free throws; 3PA per game
  05_shooting             2P% / 3P% / FT% / eFG% / TS% vs league, per team
  06_hot_spots            nine-zone FG% heatmaps side by side (LBA shots only — they carry coordinates)
  06b_shot_charts_<team>_<n>  zone shot chart (FG% per zone, as in the hot spots) of each player, three players per image, both teams, most FGA first
  07_key_players          PIR vs TS% scatter with minutes, league in grey; top-5 table per team
  08_shot_distribution    share of team FGA per player, twos vs threes
  09_basic_stats          assists, rebounds, steals, blocks, turnovers, fouls per game and per 100 possessions (LBA only)
  10_major_factors        who carries each category: leader's share of the team total (2nd/3rd when close), LBA only
  00_standings + standings.md   LBA results so far and current standings (notebooks/standings.py); every page
                          README includes the standings.md section under its intro, with both teams' positions

EuroCup box scores come from data/eurocup_box.csv (see notebooks/eurocup_fetch.md for how to refresh it);
they carry per-zone shot counts, not coordinates, so they feed every chart except the hot spots.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import lba_style
from player_names import ec_surname
import standings as lba_standings
from lba_style import (save_fig, draw_zone_fill, BLUE, DPI, GREEN, LEAGUE, RED, SUP_KW, TEXT, TEXT2, TITLE_KW, ZONE_LABEL_POS, ZONE_LABELS,
                       assign_zone_arr, draw_half_court, mins, shots_cm, style_axes, team_color)

PAINT_CM = 450
COMP, COMP_NAME = "LBA", "LBA"       # the competition the reference figures (league averages, key players, basic stats) are drawn from; "EC" for a EuroCup-only report
SHARED_NAME = "LBA"     # the competition(s) the two teams have in common ("LBA", "EuroCup" or "LBA + EuroCup"), set in main()
SOCIAL = False          # --social: portrait 4:5 versions (1080x1350) of selected figures for Instagram
SOCIAL_SIZE = (6.0, 7.5)   # inches; the saved PNG is padded to exactly 1080x1350 px


def grid(ncols_wide: int = 2, figsize=(14, 5), **kw):
    """1 x N panels for the report, N x 1 (stacked) for the social version."""
    if SOCIAL:
        kw.pop("sharey", None); kw.pop("sharex", None)
        if "gridspec_kw" in kw and "width_ratios" in kw["gridspec_kw"]:
            kw["gridspec_kw"] = {"height_ratios": kw["gridspec_kw"]["width_ratios"]}
        return plt.subplots(ncols_wide, 1, figsize=SOCIAL_SIZE, **kw)
    return plt.subplots(1, ncols_wide, figsize=figsize, **kw)


def sup(fig, text: str, social_text: str | None = None):
    import textwrap
    fig.suptitle(textwrap.fill(social_text or text, 46) if SOCIAL else text, **SUP_KW)


def save(fig, path):
    save_fig(fig, path)
    if SOCIAL:   # pad to a 4:5 white canvas, 1080x1350
        from PIL import Image
        im = Image.open(path).convert("RGB"); W, H = 1080, 1350
        r = min((W - 60) / im.width, (H - 60) / im.height)
        im = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
        canvas = Image.new("RGB", (W, H), "white"); canvas.paste(im, ((W - im.width) // 2, (H - im.height) // 2)); canvas.save(path)


def short(name: str) -> str:
    toks = [t for t in str(name).split() if t.lower() not in ("basket", "basketball", "pallacanestro")]
    return toks[-1] if toks else str(name)  # "points in the paint" = made field goals within 4.5 m of the rim (zones A/B/C)

# ── EuroCup file ────────────────────────────────────────────────────────────────
EC_TEAM_MAP = {"ROMA BASKETBALL": "BC Roma", "MAXIMA ROMA": "Maxima Roma"}
EC_CODE_MAP = {"BCR": "BC Roma", "MRO": "Maxima Roma"}
EC_DATES = {6: "2026-09-30", 16: "2026-09-30", 24: "2026-10-06", 29: "2026-10-07"}   # gamecode -> date


def parse_eurocup(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (player/total rows, zone rows) in the same shape as the LBA tables."""
    txt = path.read_text(encoding="utf-8").splitlines()
    box_lines, zone_lines, section = [], [], None
    for ln in txt:
        if ln in ("BOX", "ZONES", "PLAYERZONES"):
            section = ln; continue
        if not ln.strip():
            continue
        (box_lines if section == "BOX" else zone_lines if section == "ZONES" else []).append(ln.split("|"))
    rows, games = [], {}
    for f in box_lines:
        gc = int(f[0])
        if f[1] == "QUARTERS":
            continue
        team = EC_TEAM_MAP.get(f[1], f[1].title())
        if f[2] == "TOTAL":
            games.setdefault(gc, []).append((team, int(f[5])))
            rows.append(dict(game_id=f"EC{gc}", competition="EC", team=team, row_type="total", player_surname=None,
                             starter=None, sec=2400, pts=int(f[5]), fg2m=int(f[6]), fg2a=int(f[7]), fg3m=int(f[8]),
                             fg3a=int(f[9]), ftm=int(f[10]), fta=int(f[11]), oreb=int(f[12]), dreb=int(f[13]),
                             ast=int(f[14]), stl=int(f[15]), tov=int(f[16]), blk=int(f[17]), pf=int(f[18]),
                             pf_drawn=int(f[19]), plus_minus=0, val=int(f[21])))
        else:
            m = f[4]
            sec = 0 if m in ("DNP", "") else int(m.split(":")[0]) * 60 + int(m.split(":")[1])
            surname = ec_surname(f[2])
            rows.append(dict(game_id=f"EC{gc}", competition="EC", team=team, row_type="player", player_surname=surname,
                             starter=int(f[3]), sec=sec, pts=int(f[5]), fg2m=int(f[6]), fg2a=int(f[7]), fg3m=int(f[8]),
                             fg3a=int(f[9]), ftm=int(f[10]), fta=int(f[11]), oreb=int(f[12]), dreb=int(f[13]),
                             ast=int(f[14]), stl=int(f[15]), tov=int(f[16]), blk=int(f[17]), pf=int(f[18]),
                             pf_drawn=int(f[19]), plus_minus=int(f[20]), val=int(f[21])))
    box = pd.DataFrame(rows)
    # opponent / home / score columns from the totals
    for gc, teams in games.items():
        for team, pts in teams:
            other = [t for t in teams if t[0] != team][0]
            sel = (box.game_id == f"EC{gc}") & (box.team == team)
            box.loc[sel, "opponent"] = other[0]; box.loc[sel, "opp_pts"] = other[1]
    box["reb"] = box.oreb + box.dreb
    box["home"] = [int(games[int(g[2:])][0][0] == t) for g, t in zip(box.game_id, box.team)]    # the first team listed in a game is the home team
    dates, codes = dict(EC_DATES), dict(EC_CODE_MAP)
    feed = path.parent / "eurocup" / "results.csv"            # every game of the season: gamecode -> date, club code -> team name
    if feed.exists():
        res = pd.read_csv(feed)
        dates.update(dict(zip(res.gamecode, res.date)))
        codes.update({**dict(zip(res.home_code, res.home)), **dict(zip(res.away_code, res.away))})
    box["date"] = box.game_id.str[2:].astype(int).map(dates)
    zones = pd.DataFrame([dict(game_id=f"EC{f[0]}", team=codes.get(f[1], f[1]), zone=f[2], action=f[3], n=int(f[4]))
                          for f in zone_lines], columns=["game_id", "team", "zone", "action", "n"])
    return box, zones


# ── LBA tables ──────────────────────────────────────────────────────────────────
def apply_starter_overrides(box: pd.DataFrame, data: Path) -> pd.DataFrame:
    """Starter flags of data/starter_overrides.csv (game_id, player_surname, starter): box scores checked against the play-by-play."""
    fix = data / "starter_overrides.csv"
    if fix.exists():
        for r in pd.read_csv(fix).itertuples():
            box.loc[(box.game_id == r.game_id) & (box.player_surname == r.player_surname) & (box.row_type == "player"), "starter"] = r.starter
    return box


def load_lba(data: Path):
    games = pd.read_csv(data / "games.csv")
    box = pd.read_csv(data / "box_scores.csv"); box["competition"] = "LBA"
    box = apply_starter_overrides(box, data)
    pbp = pd.read_csv(data / "pbp.csv")
    tot = box[box.row_type == "total"][["game_id", "team", "pts"]]
    opp = tot.rename(columns={"team": "opponent", "pts": "opp_pts"})
    box = box.merge(opp, on=["game_id", "opponent"], how="left")
    box["date"] = box.match_datetime.str[:10]
    return games, box, pbp


def game_list(box: pd.DataFrame, team: str) -> pd.DataFrame:
    t = box[(box.team == team) & (box.row_type == "total")].copy()
    t["date_key"] = t.game_id.astype(str)
    t["label"] = np.where(t.competition == "LBA", "LBA", "EC")
    return t


# ── per-game derived metrics ────────────────────────────────────────────────────
def scoring_sources(box, pbp, ec_zones, team) -> pd.DataFrame:
    """Per game: points ≤4.5 m, mid-range 2s, threes, free throws, 3PA, FGA."""
    out = []
    tots = box[(box.team == team) & (box.row_type == "total")].sort_values("date")
    s_all = shots_cm(pbp)
    for _, t in tots.iterrows():
        if t.competition == "LBA":
            s = s_all[(s_all.game_id == t.game_id) & (s_all.team == team)]
            paint = int(2 * s[(s.pts == 2) & s.made & (s.dist <= PAINT_CM)].shape[0])
        else:
            z = ec_zones[(ec_zones.game_id == t.game_id) & (ec_zones.team == team)]
            paint = int(2 * z[(z.action == "2FGM") & z.zone.isin(["A", "B", "C"])].n.sum())
        out.append(dict(date=t.date, game_id=t.game_id, competition=t.competition, team=team, opponent=t.opponent, pts=t.pts,
                        opp_pts=t.opp_pts, paint=paint, mid=int(2 * t.fg2m - paint), three=int(3 * t.fg3m),
                        ft=int(t.ftm), fg3a=int(t.fg3a), fga=int(t.fg2a + t.fg3a), ftm=int(t.ftm), fta=int(t.fta)))
    return pd.DataFrame(out)


def starters_bench(box, team) -> pd.DataFrame:
    p = box[(box.team == team) & (box.row_type == "player")]
    g = p.groupby(["date", "game_id", "competition", "starter"]).pts.sum().unstack("starter").fillna(0)
    g.columns = ["bench" if c == 0 else "starters" for c in g.columns]
    return g.reset_index().sort_values("date")


def shooting_line(box, team=None) -> dict:
    t = box[box.row_type == "total"] if team is None else box[(box.team == team) & (box.row_type == "total")]
    fga = (t.fg2a + t.fg3a).sum(); fgm = (t.fg2m + t.fg3m).sum()
    return {"2P%": 100 * t.fg2m.sum() / t.fg2a.sum(), "3P%": 100 * t.fg3m.sum() / t.fg3a.sum(),
            "FT%": 100 * t.ftm.sum() / t.fta.sum(), "eFG%": 100 * (fgm + 0.5 * t.fg3m.sum()) / fga,
            "TS%": 100 * t.pts.sum() / (2 * (fga + 0.44 * t.fta.sum())), "3PA/g": t.fg3a.sum() / len(t),
            "FTA/g": t.fta.sum() / len(t), "TOV/g": t.tov.sum() / len(t), "OREB/g": t.oreb.sum() / len(t)}


def player_table(box, team) -> pd.DataFrame:
    p = box[(box.team == team) & (box.row_type == "player")]
    g = p.groupby("player_surname").agg(GP=("game_id", "nunique"), GS=("starter", "sum"), sec=("sec", "sum"), pts=("pts", "sum"),
                                        reb=("reb", "sum"), ast=("ast", "sum"), tov=("tov", "sum"), val=("val", "sum"),
                                        fg2m=("fg2m", "sum"), fg2a=("fg2a", "sum"), fg3m=("fg3m", "sum"), fg3a=("fg3a", "sum"),
                                        ftm=("ftm", "sum"), fta=("fta", "sum"), pm=("plus_minus", "sum")).reset_index()
    g = g[g.sec > 0].copy()
    g["Player"] = g.player_surname.str.title(); g["MIN"] = g.sec / 60; g["MPG"] = g.MIN / g.GP
    g["PPG"], g["RPG"], g["APG"], g["PIR"] = g.pts / g.GP, g.reb / g.GP, g.ast / g.GP, g.val / g.GP
    fga = g.fg2a + g.fg3a
    g["TS%"] = 100 * g.pts / (2 * (fga + 0.44 * g.fta)).replace(0, np.nan)
    g["3P"] = g.fg3m.astype(int).astype(str) + "/" + g.fg3a.astype(int).astype(str)
    return g.sort_values("MIN", ascending=False)


# ── figures ─────────────────────────────────────────────────────────────────────
def fig_timeline(box, A, B, out):
    fig, axes = grid(2, figsize=(14, 4.6), sharey=True)
    for ax, team, i in ((axes[0], A, 0), (axes[1], B, 1)):
        g = game_list(box, team).sort_values("date")
        fill, edge = team_color(team, i)
        x = np.arange(len(g))
        ax.bar(x - 0.2, g.pts, 0.4, color=fill, edgecolor=edge, linewidth=0.6, label=f"{team} points")
        ax.bar(x + 0.2, g.opp_pts, 0.4, color=LEAGUE, label="opponent points")
        for xi, (p, o) in enumerate(zip(g.pts, g.opp_pts)):
            ax.text(xi, max(p, o) + 2, "W" if p > o else "L", ha="center", fontweight="bold", color=GREEN if p > o else RED)
        ax.set_xticks(x); ax.set_xticklabels([f"{c}\n{short(o)}" for c, o in zip(g.competition, g.opponent)], fontsize=8)
        ax.set_title(f"{team}: {int((g.pts > g.opp_pts).sum())}–{int((g.pts < g.opp_pts).sum())}, "
                     f"{g.pts.mean():.0f} for / {g.opp_pts.mean():.0f} against per game", **TITLE_KW)
        ax.legend(fontsize=8, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.0) if SOCIAL else (0.5, 1.0)); style_axes(ax, "y")
        ax.set_ylim(0, max(115, g[["pts", "opp_pts"]].max().max() + 12) + (14 if SOCIAL else 0))
    comps = {c for t in (A, B) for c in game_list(box, t).competition}
    sup(fig, "Results so far — " + " and ".join(n for c, n in (("LBA", "LBA"), ("EC", "EuroCup")) if c in comps))
    save(fig, out / "01_results_timeline.png"); plt.close(fig)


def fig_starters_bench(box, A, B, out):
    p = box[(box.row_type == "player") & (box.competition == COMP)]
    lg_tot = p.groupby(["game_id", "team", "starter"]).pts.sum().unstack("starter").fillna(0)
    lg_st, lg_bn = lg_tot[1].mean(), lg_tot[0].mean()
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for ax, team, i in ((axes[0], A, 0), (axes[1], B, 1)):
        sb = starters_bench(box, team)
        fill, edge = team_color(team, i)
        x = np.arange(len(sb))
        ax.bar(x, sb.starters, 0.6, color=fill, edgecolor=edge, linewidth=0.6, label="starting five")
        ax.bar(x, sb.bench, 0.6, bottom=sb.starters, color=LEAGUE, label="bench")
        for xi, (s, b) in enumerate(zip(sb.starters, sb.bench)):
            ax.text(xi, s / 2, f"{int(s)}", ha="center", va="center", color="white" if fill != "#F2C300" else TEXT, fontsize=9, fontweight="bold")
            ax.text(xi, s + b / 2, f"{int(b)}", ha="center", va="center", color="white", fontsize=9, fontweight="bold")
        ax.axhline(lg_st, color=TEXT2, lw=1, ls="--"); ax.text(len(sb) - 0.5, lg_st + 1, f"league starters {lg_st:.0f}", ha="right", fontsize=8, color=TEXT2)
        ax.axhline(lg_st + lg_bn, color=TEXT2, lw=1, ls=":"); ax.text(len(sb) - 0.5, lg_st + lg_bn + 1, f"league total {lg_st + lg_bn:.0f} (bench {lg_bn:.0f})", ha="right", fontsize=8, color=TEXT2)
        opp = box[(box.team == team) & (box.row_type == "total")].set_index("game_id").opponent
        ax.set_xticks(x); ax.set_xticklabels([f"{c}\n{short(opp.get(g, ''))}" for c, g in zip(sb.competition, sb.game_id)], fontsize=8)
        ax.set_ylabel("points")
        ax.set_title(f"{team}\nstarters {sb.starters.mean():.0f} + bench {sb.bench.mean():.0f} per game "
                     f"({100 * sb.bench.sum() / (sb.starters.sum() + sb.bench.sum()):.0f}% from the bench)", **TITLE_KW)
        ax.legend(fontsize=8, loc="upper left"); style_axes(ax, "y")
    fig.suptitle(f"Points from the starting five vs the bench (dashed: {COMP_NAME} league averages)", **SUP_KW)
    save_fig(fig, out / "02_starters_bench.png"); plt.close(fig)


def fig_minutes(box, A, B, out):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2))
    for ax, team, i in ((axes[0], A, 0), (axes[1], B, 1)):
        pt = player_table(box, team)
        fill, edge = team_color(team, i)
        y = np.arange(len(pt))
        ax.barh(y, pt.MPG, color=fill, edgecolor=edge, linewidth=0.6, height=0.65)
        for yi, (m, gp, gs, ppg) in enumerate(zip(pt.MPG, pt.GP, pt.GS, pt.PPG)):
            ax.text(m + 0.4, yi, f"{m:.1f}'  ({int(gs)}/{int(gp)} starts, {ppg:.1f} ppg)", va="center", fontsize=8, color=TEXT2)
        ax.set_yticks(y); ax.set_yticklabels(pt.Player, fontsize=9); ax.invert_yaxis(); ax.set_xlim(0, 44)
        ax.axvline(20, color=TEXT2, lw=0.7, ls="--")
        top7 = pt.MIN.head(7).sum() / pt.MIN.sum() * 100
        ax.set_title(f"{team}\nminutes per game — {len(pt)} players used, top 7 play {top7:.0f}% of minutes", **TITLE_KW)
        style_axes(ax, "x")
    fig.suptitle(f"Minutes distribution, {SHARED_NAME} games", **SUP_KW)
    save_fig(fig, out / "03_minutes.png"); plt.close(fig)


def fig_scoring_sources(box, pbp, ec_zones, A, B, out):
    lg_src = []
    for tm in box[box.competition == COMP].team.unique():
        if tm in (A, B):
            continue
        lg_src.append(scoring_sources(box[box.competition == COMP], pbp, ec_zones, tm))
    lg = pd.concat(lg_src)
    lg_mean = lg[["paint", "mid", "three", "ft", "fg3a", "fga"]].mean()
    srcA, srcB = scoring_sources(box, pbp, ec_zones, A), scoring_sources(box, pbp, ec_zones, B)
    fig, axes = grid(2, figsize=(14, 5), gridspec_kw={"width_ratios": [2.2, 1]})
    cats = ["paint", "mid", "three", "ft"]; labels = ["≤4.5 m from rim", "mid-range 2s", "threes", "free throws"]
    x = np.arange(4); w = 0.27
    for i, (team, src) in enumerate(((A, srcA), (B, srcB))):
        fill, edge = team_color(team, i)
        m = src[cats].mean()
        axes[0].bar(x + (i - 1) * w, m, w, color=fill, edgecolor=edge, linewidth=0.6, label=f"{team} ({len(src)} g)")
        for xi, v in zip(x, m):
            axes[0].text(xi + (i - 1) * w, v + 0.6, f"{v:.0f}", ha="center", fontsize=8, color=TEXT2)
    axes[0].bar(x + w, lg_mean[cats], w, color=LEAGUE, label=f"{COMP_NAME} league avg")
    for xi, v in zip(x, lg_mean[cats]):
        axes[0].text(xi + w, v + 0.6, f"{v:.0f}", ha="center", fontsize=8, color=TEXT2)
    axes[0].set_xticks(x); axes[0].set_xticklabels(labels); axes[0].set_ylabel("points per game")
    axes[0].set_title("Where the points come from (per game)", **TITLE_KW); axes[0].legend(fontsize=8); style_axes(axes[0], "y")
    vals = [srcA.fg3a.mean(), srcB.fg3a.mean(), lg_mean.fg3a]; shares = [srcA.fg3a.sum() / srcA.fga.sum(), srcB.fg3a.sum() / srcB.fga.sum(), lg_mean.fg3a / lg_mean.fga]
    cols = [team_color(A, 0)[0], team_color(B, 1)[0], LEAGUE]
    axes[1].bar([0, 1, 2], vals, 0.6, color=cols, edgecolor=[team_color(A, 0)[1], team_color(B, 1)[1], LEAGUE], linewidth=0.6)
    for xi, (v, s) in enumerate(zip(vals, shares)):
        axes[1].text(xi, v + 0.5, f"{v:.1f}\n({100 * s:.0f}% of FGA)", ha="center", fontsize=8.5, color=TEXT2)
    axes[1].set_xticks([0, 1, 2]); axes[1].set_xticklabels([A, B, "league"], fontsize=9); axes[1].set_ylim(0, max(vals) * 1.3)
    axes[1].set_title("Three-point attempts per game", **TITLE_KW); style_axes(axes[1], "y")
    sup(fig, f"Scoring sources and three-point volume, {SHARED_NAME} games (league = other {COMP_NAME} teams)",
        f"Where the points come from — {SHARED_NAME} games (league = other {COMP_NAME} teams)")
    save(fig, out / "04_scoring_sources.png"); plt.close(fig)
    return srcA, srcB, lg_mean


def fig_shooting(box, A, B, out):
    keys = ["2P%", "3P%", "FT%", "eFG%", "TS%"]
    lines = {A: shooting_line(box, A), B: shooting_line(box, B),
             "league": shooting_line(box[(box.competition == COMP) & ~box.team.isin([A, B])])}
    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(keys)); w = 0.27
    for i, (name, ln) in enumerate(lines.items()):
        fill, edge = team_color(name, i) if name != "league" else (LEAGUE, LEAGUE)
        vals = [ln[k] for k in keys]
        ax.bar(x + (i - 1) * w, vals, w, color=fill, edgecolor=edge, linewidth=0.6, label=name)
        for xi, v in zip(x, vals):
            ax.text(xi + (i - 1) * w, v + 0.8, f"{v:.0f}", ha="center", fontsize=8.5, color=TEXT2)
    ax.set_xticks(x); ax.set_xticklabels(keys); ax.set_ylim(0, 100); ax.set_ylabel("%")
    ax.set_title(f"Shooting percentages, season to date ({SHARED_NAME} games; league = other {COMP_NAME} teams)", **TITLE_KW)
    ax.legend(fontsize=9); style_axes(ax, "y")
    save_fig(fig, out / "05_shooting.png"); plt.close(fig)
    return lines


def zone_stats(s):
    agg = s.groupby("zone").agg(att=("made", "size"), mk=("made", "sum"))
    return {z: (int(r.mk), int(r.att), 100 * r.mk / r.att) for z, r in agg.iterrows()}


def plot_zone_heatmap(ax, s, title, ref=None):
    st = zone_stats(s)
    cmap = plt.cm.RdYlGn.copy()
    draw_zone_fill(ax, {z: p for z, (_, _, p) in st.items()}, cmap)
    mesh = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 100)); mesh.set_array([])
    draw_half_court(ax, color="#3a3d52", lw=1.6)
    for z, (cx, cy) in ZONE_LABEL_POS.items():
        mk, att, p = st.get(z, (0, 0, 0.0))
        if att == 0:
            lab, col = "0/0\n—", "#8a8d9c"
        else:
            lab, col = f"{mk}/{att}\n{p:.0f}%", "black" if 25 < p < 75 else "white"
            if ref and z in ref and ref[z][1] > 0 and not SOCIAL:
                lab += f"\nleague {ref[z][2]:.0f}%"
        ax.text(cx, cy, lab, ha="center", va="center", color=col, fontsize=7.5 if SOCIAL else 8.5, fontweight="bold", zorder=5)
    ax.set_title(title, **TITLE_KW)
    return mesh


def fig_player_shot_charts(pbp, A, B, out, per_image=3, max_players=9, min_fga=5):
    """One zone heatmap per player (same style as the hot spots: made/attempts, FG% and the league FG% in each zone) for the players with
    at least `min_fga` shots (play-by-play coordinates), `per_image` players per image."""
    s = shots_cm(pbp)
    ref = zone_stats(s[~s.team.isin([A, B])])
    for team in (A, B):
        st = s[s.team == team]
        top = st.groupby("player_surname").size().loc[lambda n: n >= min_fga].sort_values(ascending=False).head(max_players).index
        slug = team.replace(" ", "_")
        for k in range(0, len(top), per_image):
            group = top[k:k + per_image]
            fig, axes = plt.subplots(1, len(group), figsize=(6.2 * len(group), 6.6), squeeze=False)
            for ax, sn in zip(axes[0], group):
                ps = st[st.player_surname == sn]
                mesh = plot_zone_heatmap(ax, ps, f"{sn.title()} — {int(ps.made.sum())}/{len(ps)} FG in {ps.game_id.nunique()} games", ref=ref)
            cb = fig.colorbar(mesh, ax=axes.ravel().tolist(), fraction=0.02, pad=0.02); cb.set_ticks([0, 25, 50, 75, 100]); cb.set_label("FG%", fontsize=8)
            fig.suptitle(f"{team} — shot charts by zone, {COMP_NAME} games (third line = FG% of all other {COMP_NAME} teams in that zone)", **SUP_KW)
            save_fig(fig, out / f"06b_shot_charts_{slug}_{k // per_image + 1}.png"); plt.close(fig)


def fig_hot_spots(pbp, A, B, out):
    s = shots_cm(pbp)
    ref = zone_stats(s[~s.team.isin([A, B])])
    fig, axes = grid(2, figsize=(15, 8))
    for ax, team in zip(axes, (A, B)):
        st = s[s.team == team]
        mesh = plot_zone_heatmap(ax, st, f"{team} — {int(st.made.sum())}/{len(st)} FG in {st.game_id.nunique()} {COMP_NAME} games", ref=ref)
    if not SOCIAL:
        cb = fig.colorbar(mesh, ax=axes, fraction=0.02, pad=0.02); cb.set_ticks([0, 25, 50, 75, 100]); cb.set_label("FG%", fontsize=8)
    sup(fig, f"Hot spots — FG% by zone, {COMP_NAME} games (third line = FG% of all other {COMP_NAME} teams in that zone)",
        f"Hot spots — FG% by zone, {COMP_NAME} games (red = cold, green = hot)")
    save(fig, out / "06_hot_spots.png"); plt.close(fig)
    # per-zone attempt share for the text
    share = {tm: s[s.team == tm].zone.value_counts(normalize=True).round(3).to_dict() for tm in (A, B)}
    share["league"] = s[~s.team.isin([A, B])].zone.value_counts(normalize=True).round(3).to_dict()
    return share


def fig_key_players(box, A, B, out, min_mpg=10):
    pts = {tm: player_table(box[box.competition == COMP], tm) for tm in (A, B)}   # LBA only, same basis as the league dots
    lgp = box[(box.competition == COMP) & (box.row_type == "player") & ~box.team.isin([A, B])]
    lg = lgp.groupby(["team", "player_surname"]).agg(GP=("game_id", "nunique"), sec=("sec", "sum"), pts=("pts", "sum"), val=("val", "sum"),
                                                     fg2a=("fg2a", "sum"), fg3a=("fg3a", "sum"), fta=("fta", "sum")).reset_index()
    lg["MPG"] = lg.sec / 60 / lg.GP; lg["PIR"] = lg.val / lg.GP
    lg["TS%"] = 100 * lg.pts / (2 * (lg.fg2a + lg.fg3a + 0.44 * lg.fta)).replace(0, np.nan)
    lg = lg[lg.MPG >= min_mpg]
    fig, ax = plt.subplots(figsize=(13, 8.5))
    size = lambda mpg: mpg / 36 * 420 + 40
    ax.scatter(lg.PIR, lg["TS%"], s=size(lg.MPG), c=LEAGUE, alpha=0.4, edgecolors="none", label=f"other {COMP_NAME} players", zorder=2)
    both = pd.concat([pts[tm][pts[tm].MPG >= min_mpg].assign(team=tm) for tm in (A, B)])
    cands = pd.concat([both[["Player", "team", "PIR", "TS%", "MPG"]],
                       lg.assign(Player=lg.player_surname.str.title())[["Player", "team", "PIR", "TS%", "MPG"]]])
    best = cands.sort_values("PIR", ascending=False).iloc[0]
    for i, tm in enumerate((A, B)):
        d = pts[tm][pts[tm].MPG >= min_mpg]
        fill, edge = team_color(tm, i)
        ax.scatter(d.PIR, d["TS%"], s=size(d.MPG), c=fill, edgecolors=edge, linewidths=0.8, zorder=3, label=tm)
        for j, (_, r) in enumerate(d.sort_values("PIR").iterrows()):
            is_best = r.Player == best.Player and tm == best.team
            ax.annotate(f"{r.Player} ({r.MPG:.0f}')", (r.PIR, r["TS%"]), xytext=(6, 6 if j % 2 else -12), textcoords="offset points",
                        fontsize=9 if is_best else 8, color=GREEN if is_best else TEXT, fontweight="bold" if is_best else "normal")
    ax.scatter([best.PIR], [best["TS%"]], s=size(best.MPG) * 2.2, facecolors="none", edgecolors=GREEN, linewidths=2.5, zorder=4,
               label=f"best PIR in the league: {best.Player} ({best.team}, PIR {best.PIR:.1f})")
    if best.team not in (A, B):
        ax.annotate(f"{best.Player} ({best.team}, {best.MPG:.0f}')", (best.PIR, best["TS%"]), xytext=(8, 8), textcoords="offset points",
                    fontsize=9, color=GREEN, fontweight="bold")
    ax.axvline(lg.PIR.median(), color=TEXT2, lw=0.7, ls="--"); ax.axhline(lg["TS%"].median(), color=TEXT2, lw=0.7, ls="--")
    ax.text(lg.PIR.median() + 0.2, ax.get_ylim()[0] + 1.5, "league median PIR", color=TEXT2, fontsize=8)
    ax.text(ax.get_xlim()[0] + 0.3, lg["TS%"].median() + 0.8, "league median TS%", color=TEXT2, fontsize=8)
    ax.set_xlabel("PIR per game (LBA valutazione)" if COMP == "LBA" else "PIR per game"); ax.set_ylabel("TS%")
    ax.set_title(f"Key players — PIR vs true shooting, dot size = minutes per game (min {min_mpg}')\n"
                 f"{COMP_NAME} games only, all players on the same basis", **TITLE_KW)
    ax.legend(fontsize=9, loc="lower right"); style_axes(ax)
    save_fig(fig, out / "07_key_players.png"); plt.close(fig)
    return pts


def fig_shot_distribution(box, A, B, out):
    """Share of the team's field-goal attempts per player, split into twos and threes (all the games in `box`: LBA+EC, or EC only)."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.5))
    for ax, team, i in ((axes[0], A, 0), (axes[1], B, 1)):
        p = box[(box.team == team) & (box.row_type == "player")]
        g = p.groupby("player_surname").agg(fg2a=("fg2a", "sum"), fg3a=("fg3a", "sum"), fga=("fg2a", "sum"), fta=("fta", "sum"),
                                            pts=("pts", "sum"), GP=("game_id", "nunique"), sec=("sec", "sum")).reset_index()
        g["fga"] = g.fg2a + g.fg3a
        g = g[g.fga > 0].sort_values("fga", ascending=False)
        tot = g.fga.sum()
        g["share"] = 100 * g.fga / tot
        fill, edge = team_color(team, i)
        y = np.arange(len(g))
        ax.barh(y, 100 * g.fg2a / tot, color=fill, edgecolor=edge, linewidth=0.6, height=0.65, label="two-point attempts")
        ax.barh(y, 100 * g.fg3a / tot, left=100 * g.fg2a / tot, color=LEAGUE, edgecolor=edge, linewidth=0.6, height=0.65, label="three-point attempts")
        for yi, r in zip(y, g.itertuples()):
            ax.text(r.share + 0.4, yi, f"{r.share:.0f}%  ({int(r.fga)} FGA, {r.fga / r.GP:.1f}/g, {40 * r.fga / (r.sec / 60):.1f} per 40')",
                    va="center", fontsize=8.5, color=TEXT2)
        ax.set_yticks(y); ax.set_yticklabels(g.player_surname.str.title(), fontsize=9); ax.invert_yaxis()
        ax.set_xlim(0, g.share.max() * 1.9); ax.set_xlabel("% of the team's field-goal attempts")
        top3 = g.share.head(3).sum()
        ax.set_title(f"{team} — {int(tot)} FGA in {p.game_id.nunique()} games\ntop 3 take {top3:.0f}%, top 5 take {g.share.head(5).sum():.0f}%", **TITLE_KW)
        ax.legend(fontsize=8, loc="lower right"); style_axes(ax, "x")
    fig.suptitle(f"Who takes the shots — share of team FGA per player ({SHARED_NAME})", **SUP_KW)
    save_fig(fig, out / "08_shot_distribution.png"); plt.close(fig)


BASIC_STATS = [("ast", "assists"), ("dreb", "def. rebounds"), ("oreb", "off. rebounds"), ("stl", "steals"), ("blk", "blocks"),
               ("tov", "turnovers"), ("pf", "fouls"), ("pf_drawn", "fouls drawn")]


def basic_line(box_tot: pd.DataFrame) -> pd.Series:
    """Per-game and per-100-possession totals from a set of team 'total' rows (one row per team-game)."""
    t = box_tot.copy()
    t["poss"] = t.fg2a + t.fg3a - t.oreb + t.tov + 0.44 * t.fta
    out = {"games": len(t), "poss": t.poss.mean(), "pts": t.pts.mean()}
    for k, _ in BASIC_STATS:
        out[f"{k}_pg"] = t[k].mean()
        out[f"{k}_p100"] = 100 * t[k].sum() / t.poss.sum()
    out["pts_p100"] = 100 * t.pts.sum() / t.poss.sum()
    return pd.Series(out)


def fig_basic_stats(box, A, B, out):
    """Assists, rebounds, steals, blocks, turnovers, fouls: per game and per 100 possessions (LBA only)."""
    tot = box[(box.competition == COMP) & (box.row_type == "total")]
    lines = {A: basic_line(tot[tot.team == A]), B: basic_line(tot[tot.team == B]), "league": basic_line(tot[~tot.team.isin([A, B])])}
    fig, axes = grid(2, figsize=(16, 5.6))
    x = np.arange(len(BASIC_STATS)); w = 0.27
    for ax, suffix, title in ((axes[0], "_pg", "per game"), (axes[1], "_p100", "per 100 possessions")):
        for i, (name, ln) in enumerate(lines.items()):
            fill, edge = team_color(name, i) if name != "league" else (LEAGUE, LEAGUE)
            vals = [ln[f"{k}{suffix}"] for k, _ in BASIC_STATS]
            ax.bar(x + (i - 1) * w, vals, w, color=fill, edgecolor=edge, linewidth=0.6, label=name)
            for xi, v in zip(x, vals):
                ax.text(xi + (i - 1) * w, v + 0.3, f"{v:.0f}" if SOCIAL else f"{v:.1f}", ha="center", fontsize=6.5 if SOCIAL else 7.5, color=TEXT2)
        ax.set_xticks(x); ax.set_xticklabels([lab for _, lab in BASIC_STATS], fontsize=8 if SOCIAL else 9,
                                              rotation=25 if SOCIAL else 0, ha="right" if SOCIAL else "center")
        ax.set_title(f"Basic stats {title}", **TITLE_KW); ax.legend(fontsize=9); style_axes(ax, "y")
    pace = " · ".join(f"{n}: {ln.poss:.1f} poss/g, {ln.pts_p100:.0f} pts per 100" for n, ln in lines.items())
    if SOCIAL:
        fig.suptitle(f"Team comparison — {COMP_NAME} games only\n({int(lines[A].games)} per team; league = the other teams)", **SUP_KW)
        axes[1].set_xlabel("per 100 possessions (FGA − OREB + TOV + 0.44·FTA)\n" + pace.replace(" · ", "\n"), fontsize=7.5, color=TEXT2)
    else:
        fig.suptitle(f"Team comparison — {COMP_NAME} games only ({int(lines[A].games)} per team; league = the other teams)\n{pace}", **SUP_KW)
        axes[1].set_xlabel("possessions estimated as FGA − OREB + TOV + 0.44·FTA", fontsize=8, color=TEXT2)
    save(fig, out / "09_basic_stats.png"); plt.close(fig)
    return pd.DataFrame(lines)


FACTOR_STATS = [("pts", "points"), ("ast", "assists"), ("dreb", "def. rebounds"), ("oreb", "off. rebounds"), ("stl", "steals"),
                ("blk", "blocks"), ("fg3m", "threes made"), ("pf_drawn", "fouls drawn"), ("tov", "turnovers")]


def fig_major_factors(box, A, B, out, close=0.8, max_players=3):
    """For each category, which player carries the team: share of the team total for the leader, plus the 2nd and
    3rd when they are within `close` (80%) of the leader's share. LBA only. Grey = rest of the roster."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 7.2), sharey=True)
    for ax, team, ti in ((axes[0], A, 0), (axes[1], B, 1)):
        p = box[(box.competition == COMP) & (box.row_type == "player") & (box.team == team)]
        totals = p.groupby("player_surname")[[k for k, _ in FACTOR_STATS]].sum()
        fill, edge = team_color(team, ti)
        shades = [fill, "#e8d77a" if fill == "#F2C300" else "#6b6b7a", "#f3e7b3" if fill == "#F2C300" else "#a8a8b4"]
        y = np.arange(len(FACTOR_STATS))
        for yi, (k, lab) in enumerate(FACTOR_STATS):
            col = totals[k]; tot = col.sum()
            if tot <= 0:
                ax.text(1, yi, "none", va="center", fontsize=8, color=TEXT2); continue
            share = (col / tot).sort_values(ascending=False)
            lead = share.iloc[0]
            chosen = share[share >= close * lead].head(max_players)
            left = 0
            for j, (name, sh) in enumerate(chosen.items()):
                ax.barh(yi, 100 * sh, left=left, color=shades[j], edgecolor=edge, linewidth=0.6, height=0.7)
                ax.text(left + 50 * sh, yi, f"{name.title()}\n{100 * sh:.0f}%", ha="center", va="center", fontsize=7.5 if len(chosen) > 1 else 8,
                        color=TEXT if (fill == "#F2C300" or j > 0) else "white", fontweight="bold" if j == 0 else "normal")
                left += 100 * sh
            ax.barh(yi, 100 - left, left=left, color="#dcdde3", height=0.7)
            ax.text(101, yi, f"rest {100 - left:.0f}%  (team {int(tot)})", va="center", fontsize=8, color=TEXT2)
        ax.set_yticks(y); ax.set_yticklabels([lab for _, lab in FACTOR_STATS], fontsize=9.5)
        ax.set_xlim(0, 135); ax.set_xticks([0, 25, 50, 75, 100]); ax.set_xlabel("% of the team total")
        ax.set_title(f"{team}", **TITLE_KW); style_axes(ax, "x")
    axes[0].invert_yaxis()   # shared y: invert once
    fig.suptitle(f"Who carries each category — share of the team total, {COMP_NAME} games only\n"
                 f"leader shown; 2nd and 3rd added when within {int(close * 100)}% of the leader's share", **SUP_KW)
    save_fig(fig, out / "10_major_factors.png"); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", required=True); ap.add_argument("--away", required=True)
    ap.add_argument("--data", default=str(Path(__file__).resolve().parent.parent / "data"))
    ap.add_argument("--eurocup", default=None, help="path to the EuroCup raw file (default data/eurocup_2026_raw.txt)")
    ap.add_argument("--no-eurocup", action="store_true")
    ap.add_argument("--competition", choices=["LBA", "EC"], default="LBA",
                    help="EC: a EuroCup game: EuroCup box scores and play-by-play only, the EuroCup group table, the other EuroCup teams as the league")
    ap.add_argument("--out", default="reports")
    ap.add_argument("--social", action="store_true", help="also write portrait 4:5 (1080x1350) versions of figures 01, 04, 06, 09 into <out>/social/")
    ap.add_argument("--before", default=None, help="YYYY-MM-DD: use only games played before this date (frozen pre-match "
                                                     "snapshot; output folder gets a _before_<date> suffix and charts say so)")
    a = ap.parse_args()
    data = Path(a.data)
    suffix = f"_before_{a.before}" if a.before else ""
    out = Path(a.out) / f"matchup_{a.home.replace(' ', '_')}_vs_{a.away.replace(' ', '_')}{suffix}"; out.mkdir(parents=True, exist_ok=True)
    games, box, pbp = load_lba(data)
    if a.competition == "EC":
        global COMP, COMP_NAME, SHARED_NAME
        COMP, COMP_NAME, SHARED_NAME = "EC", "EuroCup", "EuroCup"
        box, pbp = box.iloc[0:0], pbp.iloc[0:0]          # replaced below by the EuroCup box scores and play-by-play
    import lba_style
    if a.before:
        from datetime import date as _d
        lba_style.STAMP_NOTE = f"games before {_d.fromisoformat(a.before):%d %b %Y} (pre-match snapshot)"
        box = box[box.date < a.before]; pbp = pbp[pbp.game_id.isin(box.game_id.unique())]
        games = games[games.match_datetime.str[:10] < a.before]
    ec_path = Path(a.eurocup) if a.eurocup else data / "eurocup_2026_raw.txt"
    ec_zones = pd.DataFrame(columns=["game_id", "team", "zone", "action", "n"])
    if not a.no_eurocup and ec_path.exists():
        ec_box, ec_zones = parse_eurocup(ec_path)
        if a.competition != "EC":
            ec_box = ec_box[ec_box.team.isin([a.home, a.away])]
        if a.before:
            ec_box = ec_box[ec_box.date < a.before]; ec_zones = ec_zones[ec_zones.game_id.isin(ec_box.game_id.unique())]
        box = pd.concat([box, ec_box], ignore_index=True)
        if a.competition != "EC":                         # compare only in the competitions both teams play (Varese has no EuroCup games)
            shared = set.intersection(*({*box[box.team == t].competition} for t in (a.home, a.away)))
            if "LBA" not in shared:
                raise SystemExit(f"{a.home} and {a.away} share no LBA games: use --competition EC for a EuroCup-only comparison")
            box = box[box.competition.isin(shared)]
            ec_zones = ec_zones[ec_zones.game_id.isin(box.game_id.unique())]
            SHARED_NAME = " + ".join(n for c, n in (("LBA", "LBA"), ("EC", "EuroCup")) if c in shared)
        if a.competition == "EC":
            pbp = pd.read_csv(data / "eurocup" / "pbp.csv")
            pbp = pbp[pbp.game_id.isin(ec_box.game_id.unique())]
    A, B = a.home, a.away
    if a.competition == "EC":
        import eurocup
        frame = eurocup.games_frame(eurocup.load_results(data), A)       # the group of the first team
        lba_style.SOURCE_NOTE = "EuroLeague live API"
        lba_standings.fig_standings(frame, a.before, [A, B], out, title_label="EuroCup 2026/27")
        (out / "standings.md").write_text(lba_standings.standings_md(frame, a.before, [A, B], "EuroCup"), encoding="utf-8")
    else:
        all_games = pd.read_csv(data / "games.csv")   # standings use every finished LBA game before the cut-off
        lba_standings.fig_standings(all_games, a.before, [A, B], out)
        (out / "standings.md").write_text(lba_standings.standings_md(all_games, a.before, [A, B]), encoding="utf-8")
    fig_timeline(box, A, B, out)
    fig_starters_bench(box, A, B, out)
    fig_minutes(box, A, B, out)
    srcA, srcB, lg_src = fig_scoring_sources(box, pbp, ec_zones, A, B, out)
    lines = fig_shooting(box, A, B, out)
    share = fig_hot_spots(pbp, A, B, out)
    fig_player_shot_charts(pbp, A, B, out)
    pts = fig_key_players(box, A, B, out)
    fig_shot_distribution(box, A, B, out)
    basic = fig_basic_stats(box, A, B, out)
    fig_major_factors(box, A, B, out)
    if a.social:
        global SOCIAL
        SOCIAL = True
        soc = out / "social"; soc.mkdir(exist_ok=True)
        fig_timeline(box, A, B, soc); fig_scoring_sources(box, pbp, ec_zones, A, B, soc)
        fig_hot_spots(pbp, A, B, soc); fig_basic_stats(box, A, B, soc)
        SOCIAL = False
        print(f"social versions in {soc}")
    print(basic.round(1).to_string())

    pd.set_option("display.width", 200)
    print(f"\n=== {A} vs {B} — season to date ===")
    for tm, src in ((A, srcA), (B, srcB)):
        print(f"\n{tm} games:\n", src.to_string(index=False))
        print(f"{tm} starters/bench:\n", starters_bench(box, tm).to_string(index=False))
        print(f"{tm} players:\n", pts[tm][["Player", "GP", "GS", "MPG", "PPG", "RPG", "APG", "PIR", "TS%", "3P", "pm"]].round(1).to_string(index=False))
    print("\nleague per-game scoring sources:", lg_src.round(1).to_dict())
    print("shooting lines:", {k: {kk: round(vv, 1) for kk, vv in v.items()} for k, v in lines.items()})
    print("zone shares:", share)
    print(f"\nfigures in {out}")


if __name__ == "__main__":
    main()
