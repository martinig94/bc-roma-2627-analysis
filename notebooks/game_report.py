"""Single-game report: rotation chart with score margin, five-man lineups, shot charts, shot profile.

    python notebooks/game_report.py --game 25602 --team "BC Roma" --out reports/

``--team`` defaults to the team in weekly/config.json. Writes rotation.png, lineups.png, shotmap.png
and shot_profile.png into ``<out>/<game>_<team>/``.

Lineups are reconstructed from the play-by-play (starters from the box score, then every
"Ingresso"/"Uscita"). Shot profile includes the league (all other collected games) as reference.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import weekly_config
from lba_style import (save_fig, BLUE, GOLD, GOLD_EDGE, GREEN, LEAGUE, RED, SUP_KW, TEXT, TEXT2, TITLE_KW,
                       draw_half_court, mins, shots_cm, style_axes, team_bar_kw)

ROOT = weekly_config.ROOT
PERIOD_LEN = 600   # seconds in a regulation quarter
OT_LEN = 300       # seconds in an overtime period
REGULATION_PERIODS = 4
TICK_STEP = 300    # x-axis tick spacing of the rotation chart (seconds)
LABEL_PAD = 40     # gap between the end of the game and the plus/minus labels (seconds)
OPP_EDGE = "#6f7590"      # edge of the opponent's markers on the shot chart
PERIOD_LINE = "#cfd1db"   # quarter separators on the rotation chart
NEG_EDGE = "#a83a3a"      # edge of red (negative plus/minus) rotation bars
# Shot-profile zones: distance bin edges (cm from the basket) and their labels.
ZONE_EDGES = [0, 200, 450, 674, 9999]
ZONE_NAMES = ["rim\n<2 m", "paint\n2–4.5 m", "mid-range\n4.5–6.75 m", "three"]
BAR_WIDTH = 0.27   # width of one bar in the three-series shot-profile groups
TOP_LINEUPS = 8


def load(data: Path, game_id: int) -> tuple[pd.Series, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the league files and slice one game.

    Args:
        data: Folder holding games.csv, box_scores.csv and pbp.csv.
        game_id: Game to slice out.

    Returns:
        ``(game_row, box_all, pbp_all, box_game, pbp_game)``; the game's play-by-play is sorted by ``seq``.
    """
    games = pd.read_csv(data / "games.csv")
    box = pd.read_csv(data / "box_scores.csv")
    pbp = pd.read_csv(data / "pbp.csv")
    g = games[games.game_id == game_id].iloc[0]
    return g, box, pbp, box[box.game_id == game_id].copy(), pbp[pbp.game_id == game_id].sort_values("seq").copy()


def game_clock(pbp: pd.DataFrame) -> pd.Series:
    """Return seconds since tip-off for every play-by-play row (overtimes last ``OT_LEN``)."""
    prior = np.where(pbp.period <= REGULATION_PERIODS, (pbp.period - 1) * PERIOD_LEN,
                     REGULATION_PERIODS * PERIOD_LEN + (pbp.period - REGULATION_PERIODS - 1) * OT_LEN)
    return pd.Series(prior + pbp.elapsed_sec.values, index=pbp.index)


def fmt_clock(sec: float) -> str:
    """Format game seconds as ``Q2`` at a period start, else ``Q2 4:30`` (elapsed in the period)."""
    q = int(sec // PERIOD_LEN) + 1
    return f"Q{q}" if sec % PERIOD_LEN == 0 else f"Q{q} {int(sec % PERIOD_LEN) // 60:d}:{int(sec % 60):02d}"


# ── lineups ─────────────────────────────────────────────────────────────────────
def stints(pbp: pd.DataFrame, box: pd.DataFrame, team: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(player_stints, lineup_stints) for `team`; lineup stints carry the margin change while on court."""
    pbp = pbp.copy()
    pbp["t"] = game_clock(pbp)
    home = bool(box[box.team == team].home.iloc[0])
    starters = set(box[(box.team == team) & (box.row_type == "player") & (box.starter == 1)].player_surname.str.title())
    total_len = int(pbp.t.max())
    pbp["margin"] = ((pbp.score_home - pbp.score_away) * (1 if home else -1)).ffill().fillna(0)

    on, cur_start, cur_margin = set(starters), 0, 0.0
    player_open = {p: 0 for p in on}
    p_rows, l_rows = [], []
    subs = pbp[(pbp.team == team) & pbp.event.isin(["Ingresso", "Uscita"])]
    for t, grp in subs.groupby("t", sort=True):
        m = float(pbp.loc[pbp.t <= t, "margin"].iloc[-1])
        if t > cur_start:
            l_rows.append({"start": cur_start, "end": t, "lineup": tuple(sorted(on)), "plus_minus": m - cur_margin})
        for _, r in grp.iterrows():
            name = str(r.player_surname).title()
            if r.event == "Uscita" and name in on:
                on.discard(name); p_rows.append({"player": name, "start": player_open.pop(name, t), "end": t})
            elif r.event == "Ingresso":
                on.add(name); player_open[name] = t
        cur_start, cur_margin = t, m
    l_rows.append({"start": cur_start, "end": total_len, "lineup": tuple(sorted(on)),
                   "plus_minus": float(pbp.margin.iloc[-1]) - cur_margin})
    p_rows += [{"player": n, "start": s, "end": total_len} for n, s in player_open.items()]
    lineups = pd.DataFrame(l_rows); lineups["secs"] = lineups.end - lineups.start
    return pd.DataFrame(p_rows), lineups


# ── figures ─────────────────────────────────────────────────────────────────────
def fig_rotation(pbp: pd.DataFrame, box: pd.DataFrame, team: str, g: pd.Series, out: Path) -> None:
    """Save rotation.png: score margin on top, one row of on-court stints per player below."""
    p_st, _ = stints(pbp, box, team)
    pbp = pbp.copy(); pbp["t"] = game_clock(pbp)
    home = bool(box[box.team == team].home.iloc[0])
    m = ((pbp.score_home - pbp.score_away) * (1 if home else -1)).ffill().fillna(0)
    order = (box[(box.team == team) & (box.row_type == "player") & (box.sec > 0)]
             .sort_values(["starter", "sec"], ascending=[False, False]))
    names = order.player_surname.str.title().tolist()
    pm = dict(zip(names, order.plus_minus)); secs = dict(zip(names, order.sec))
    end = pbp.t.max()

    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(12, 7.6), sharex=True,
                                   gridspec_kw={"height_ratios": [1.1, 2.6], "hspace": 0.08})
    ax0.fill_between(pbp.t, m, 0, where=m >= 0, color=GREEN, alpha=0.25, step="post")
    ax0.fill_between(pbp.t, m, 0, where=m < 0, color=RED, alpha=0.25, step="post")
    ax0.step(pbp.t, m, where="post", color=TEXT, lw=1.6)
    ax0.axhline(0, color=TEXT2, lw=0.8)
    ax0.set_ylabel(f"{team} margin"); style_axes(ax0, "y")
    ax0.set_title("Score margin and rotation", **TITLE_KW)
    for i, n in enumerate(names):
        v = pm.get(n, 0)
        kw = team_bar_kw() if v >= 0 else dict(color=RED, edgecolor=NEG_EDGE, linewidth=0.6)
        for _, s in p_st[p_st.player == n].iterrows():
            ax1.barh(i, s.end - s.start, left=s.start, height=0.62, **kw)
        ax1.text(end + LABEL_PAD, i, f"{v:+.0f}", va="center", ha="left", color=GREEN if v > 0 else RED if v < 0 else TEXT2,
                 fontsize=9, fontweight="bold")
    ax1.set_yticks(range(len(names))); ax1.set_yticklabels([f"{n}  ({mins(secs[n] / 60)})" for n in names]); ax1.invert_yaxis()
    ax1.text(end + LABEL_PAD, -0.9, "+/-", color=TEXT2, fontsize=9, ha="left")
    for q in range(1, int(end // PERIOD_LEN) + 1):
        for ax in (ax0, ax1):
            ax.axvline(q * PERIOD_LEN, color=PERIOD_LINE, lw=1)
    ticks = np.arange(0, end + 1, TICK_STEP)
    ax1.set_xticks(ticks); ax1.set_xticklabels([("End" if t == end else fmt_clock(t)) if t % PERIOD_LEN == 0 else "" for t in ticks])
    ax1.set_xlim(0, end + 260); style_axes(ax1, "x")
    fig.suptitle(f"{team} — {g.home_team} {g.home_score}–{g.away_score} {g.away_team}, round {g['round']}, {str(g.match_datetime)[:10]}", **SUP_KW)
    fig.text(0.01, 0.01, "Bars: time on court (minutes in brackets), gold = finished with plus/minus >= 0, red = negative. "
             "Top: score margin from the team's perspective. Source: legabasket.it play-by-play.", color=TEXT2, fontsize=8)
    save_fig(fig, out / "rotation.png"); plt.close(fig)


def fig_lineups(pbp: pd.DataFrame, box: pd.DataFrame, team: str, g: pd.Series, out: Path,
                top: int = TOP_LINEUPS) -> pd.DataFrame:
    """Save lineups.png (minutes and plus/minus of the ``top`` five-man units) and return the table."""
    _, lu = stints(pbp, box, team)
    agg = lu.groupby("lineup").agg(secs=("secs", "sum"), pm=("plus_minus", "sum")).reset_index()
    agg = agg[agg.secs > 0].sort_values("secs", ascending=False).head(top)
    agg["label"] = agg.lineup.apply(lambda l: " · ".join(l))
    fig, axes = plt.subplots(1, 2, figsize=(12, 0.55 * len(agg) + 1.8), sharey=True, gridspec_kw={"wspace": 0.05})
    y = np.arange(len(agg))
    axes[0].barh(y, agg.secs / 60, height=0.6, **team_bar_kw())
    axes[0].invert_yaxis()
    axes[0].set_yticks(y); axes[0].set_yticklabels(agg.label, fontsize=8.5)
    for yi, sec in zip(y, agg.secs):
        axes[0].text(sec / 60 + 0.1, yi, f"{int(sec // 60)}:{int(sec % 60):02d}", va="center", fontsize=8.5, color=TEXT2)
    top_secs, all_secs = agg.secs.sum(), lu.secs.sum()
    axes[0].set_xlabel(f"minutes together  (these {len(agg)} lineups: {int(top_secs // 60)}:{int(top_secs % 60):02d} "
                       f"of {int(all_secs // 60)}:{int(all_secs % 60):02d}, {100 * top_secs / all_secs:.0f}% of the game; "
                       f"{lu.lineup.nunique()} lineups used in total)")
    axes[1].barh(y, agg.pm, color=[GREEN if v >= 0 else RED for v in agg.pm], height=0.6)
    axes[1].axvline(0, color=TEXT2, lw=0.8); axes[1].set_xlabel("plus / minus while on court")
    for yi, v in zip(y, agg.pm):
        axes[1].text(v + (0.3 if v >= 0 else -0.3), yi, f"{v:+.0f}", va="center", ha="left" if v >= 0 else "right", fontsize=8.5, color=TEXT2)
    lim = max(abs(agg.pm).max(), 1) * 1.35; axes[1].set_xlim(-lim, lim)
    for ax in axes:
        style_axes(ax, "x")
    fig.suptitle(f"{team} — five-man lineups, top {len(agg)} by minutes  |  round {g['round']} vs {g.away_team if g.home_team == team else g.home_team}", **SUP_KW)
    save_fig(fig, out / "lineups.png"); plt.close(fig)
    return agg


def fig_shotmap(shots_game: pd.DataFrame, team: str, opp: str, g: pd.Series, out: Path) -> None:
    """Save shotmap.png: every field-goal attempt of the game, one half court per team."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 7.2))
    for ax, tm, col, edge in ((axes[0], team, GOLD, GOLD_EDGE), (axes[1], opp, LEAGUE, OPP_EDGE)):
        s = shots_game[shots_game.team == tm]
        draw_half_court(ax)
        miss, made = s[~s.made], s[s.made]
        ax.scatter(miss.cx, miss.cy, s=60, facecolors="none", edgecolors=RED, linewidths=1.4, label=f"missed ({len(miss)})", zorder=3)
        ax.scatter(made.cx, made.cy, s=60, color=col, edgecolors=edge, linewidths=0.7, label=f"made ({len(made)})", zorder=4)
        two, three = s[s.pts == 2], s[s.pts == 3]
        ax.set_title(f"{tm}\n{int(s.made.sum())}/{len(s)} FG  ·  2pt {int(two.made.sum())}/{len(two)}  ·  3pt {int(three.made.sum())}/{len(three)}", **TITLE_KW)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=2, fontsize=9)
    fig.suptitle(f"Shot charts — {g.home_team} {g.home_score}–{g.away_score} {g.away_team}, round {g['round']}", **SUP_KW)
    fig.text(0.01, 0.01, "Every field-goal attempt from the play-by-play, both halves folded onto one basket.", color=TEXT2, fontsize=8)
    save_fig(fig, out / "shotmap.png"); plt.close(fig)


def fig_shot_profile(shots_game: pd.DataFrame, shots_league: pd.DataFrame, team: str, opp: str,
                     g: pd.Series, out: Path) -> None:
    """Save shot_profile.png: share of attempts and points per attempt by distance zone vs the league."""
    zones = ZONE_NAMES

    def tab(s: pd.DataFrame) -> pd.DataFrame:
        z = pd.cut(s.dist, ZONE_EDGES, labels=zones)
        d = s.assign(z=z, p=s.made * s.pts).groupby("z", observed=False).agg(att=("made", "size"), pts=("p", "sum"))
        d["share"] = 100 * d.att / d.att.sum(); d["ppa"] = d.pts / d.att.replace(0, np.nan)
        return d.reindex(zones)

    series = [(team, tab(shots_game[shots_game.team == team]), GOLD, GOLD_EDGE),
              (opp, tab(shots_game[shots_game.team == opp]), BLUE, BLUE),
              ("league (other games)", tab(shots_league), LEAGUE, LEAGUE)]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw={"wspace": 0.25})
    x = np.arange(len(zones)); w = BAR_WIDTH
    for i, (name, d, col, edge) in enumerate(series):
        off = (i - 1) * w
        axes[0].bar(x + off, d.share, w, color=col, edgecolor=edge, linewidth=0.6, label=name)
        axes[1].bar(x + off, d.ppa, w, color=col, edgecolor=edge, linewidth=0.6, label=name)
        if i < 2:
            for xi, (sh, a) in enumerate(zip(d.share, d.att)):
                axes[0].text(xi + off, sh + 0.8, f"{int(a)}", ha="center", fontsize=8, color=TEXT2)
    axes[0].set_title("Where the shots came from (share of FGA, n on bars)", **TITLE_KW); axes[0].set_ylabel("% of attempts")
    axes[1].set_title("Points per attempt by zone", **TITLE_KW); axes[1].set_ylabel("points / FGA")
    axes[1].axhline(1.0, color=TEXT2, lw=0.8, ls="--")
    for ax in axes:
        ax.set_xticks(x); ax.set_xticklabels(zones); style_axes(ax, "y"); ax.legend(fontsize=9)
    fig.suptitle(f"Shot profile — {g.home_team} {g.home_score}–{g.away_score} {g.away_team}, round {g['round']}", **SUP_KW)
    save_fig(fig, out / "shot_profile.png"); plt.close(fig)


def main() -> None:
    """Parse the command line and write the four single-game figures."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", type=int, required=True)
    ap.add_argument("--team", default=weekly_config.load()["team"])
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--out", default="reports")
    a = ap.parse_args()
    out = Path(a.out) / f"{a.game}_{a.team.replace(' ', '_')}"; out.mkdir(parents=True, exist_ok=True)
    g, box_all, pbp_all, box, pbp = load(Path(a.data), a.game)
    opp = g.away_team if g.home_team == a.team else g.home_team
    shots_all = shots_cm(pbp_all)
    shots_game, shots_league = shots_all[shots_all.game_id == a.game], shots_all[shots_all.game_id != a.game]
    fig_rotation(pbp, box, a.team, g, out)
    lu = fig_lineups(pbp, box, a.team, g, out)
    fig_shotmap(shots_game, a.team, opp, g, out)
    fig_shot_profile(shots_game, shots_league, a.team, opp, g, out)
    print(lu[["label", "secs", "pm"]].to_string(index=False)); print(f"written to {out}")


if __name__ == "__main__":
    main()
