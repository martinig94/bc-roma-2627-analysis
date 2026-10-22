"""Five-man lineup report for one or more teams, LBA games only (--competition EC: EuroCup games): most used, best and worst units.

    python notebooks/lineups_report.py --team "BC Roma" --team "Umana Reyer Venezia" \
        --before 2026-10-17 --out reports/matchup_BC_Roma_vs_Umana_Reyer_Venezia_before_2026-10-17

Lineups are rebuilt from the play-by-play (see game_report.stints). A unit is a set of five
players on court together; "best" and "worst" rank units with at least --min-minutes together
by net points per 40 minutes. Samples are tiny early in the season: read them as tendencies.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import lba_style
from game_report import stints
from lba_style import GREEN, RED, SUP_KW, TEXT, TEXT2, save_fig, style_axes, team_bar_kw
from weekly_config import ROOT

DATA = ROOT / "data"
LBA = "LBA"                            # --competition value and league label for the LBA
EUROCUP_CODE = "EC"                    # --competition value for the EuroCup
EUROCUP_LABEL = "EuroCup"              # league label for the EuroCup
EL_SOURCE_NOTE = "EuroLeague live API"  # chart stamp for EuroCup figures
EUROCUP_RAW = "eurocup_2026_raw.txt"   # EuroCup box scores, inside the data folder
SECONDS_PER_40_MIN = 2400              # net rating is expressed per 40 minutes
BAR_HEIGHT = 0.62
ROW_HEIGHT = 0.34                      # inches per chart row
FIG_WIDTH, FIG_PAD_HEIGHT = 13, 1.8    # inches
NET_LIMIT_FLOOR = 10                   # minimum half-width of the net-rating axis (points per 40)
NET_LIMIT_MARGIN = 1.5                 # headroom factor on the net-rating axis
MIN_LIMIT_MARGIN = 1.3                 # headroom factor on the minutes axis


def team_lineups(box: pd.DataFrame, pbp: pd.DataFrame, team: str) -> pd.DataFrame:
    """Aggregate five-man units over all of the team's games.

    Args:
        box: LBA box scores.
        pbp: LBA play-by-play.
        team: Team name as in the data.

    Returns:
        One row per unit: lineup (tuple of surnames), secs, pm, stints, games, net40.
    """
    frames = []
    for game_id in box[box.team == team].game_id.unique():
        _, stint = stints(pbp[pbp.game_id == game_id].sort_values("seq"), box[box.game_id == game_id], team)
        stint["game_id"] = game_id
        frames.append(stint)
    stint = pd.concat(frames)
    agg = stint.groupby("lineup").agg(secs=("secs", "sum"), pm=("plus_minus", "sum"),
                                      stints=("secs", "size"), games=("game_id", "nunique")).reset_index()
    agg = agg[agg.secs > 0].copy()
    agg["net40"] = agg.pm / agg.secs * SECONDS_PER_40_MIN
    return agg


def pick(agg: pd.DataFrame, min_secs: int, top: int) -> list[tuple[str, pd.DataFrame]]:
    """Return the chart sections (title, units): most used, best and worst (net per 40) among units above `min_secs`."""
    used = agg.sort_values("secs", ascending=False).head(top)
    eligible = agg[agg.secs >= min_secs]
    best = eligible.sort_values(["net40", "secs"], ascending=[False, False]).head(top)
    worst = eligible[~eligible.lineup.isin(best.lineup)].sort_values(["net40", "secs"]).head(top)
    return [("Most used", used), (f"Best net rating (min {min_secs // 60} min together)", best),
            (f"Worst net rating (min {min_secs // 60} min together)", worst.sort_values("net40", ascending=False))]


def fig_lineups(agg: pd.DataFrame, team: str, min_secs: int, top: int, out: Path, stamp: str, league: str = LBA) -> Path:
    """Save the lineup chart of `team` into `out` and return its path.

    Args:
        agg: Output of `team_lineups`.
        team: Team name, used in the title and file name.
        min_secs: Minimum time together for the best/worst sections.
        top: Units per section.
        out: Folder that receives the PNG.
        stamp: Period description for the title, e.g. "season to date".
        league: League label for the title.
    """
    sections = pick(agg, min_secs, top)
    rows = []   # (kind, payload)
    for title, df in sections:
        rows.append(("head", title))
        rows += [("row", r) for r in df.itertuples()]
    y = np.arange(len(rows))[::-1]
    fig, (ax_min, ax_net) = plt.subplots(1, 2, figsize=(FIG_WIDTH, ROW_HEIGHT * len(rows) + FIG_PAD_HEIGHT), sharey=True,
                                         gridspec_kw={"wspace": 0.04, "width_ratios": [1, 1]})
    labels = []
    for yi, (kind, r) in zip(y, rows):
        if kind == "head":
            labels.append(""); ax_min.text(0, yi, r, fontsize=10.5, fontweight="bold", color=TEXT, va="center",
                                           transform=ax_min.get_yaxis_transform(), ha="left")
            continue
        labels.append(" · ".join(r.lineup))
        ax_min.barh(yi, r.secs / 60, height=BAR_HEIGHT, **team_bar_kw())
        ax_min.text(r.secs / 60 + 0.1, yi, f"{int(r.secs // 60)}:{int(r.secs % 60):02d}  ({r.games} g)",
                    va="center", fontsize=8, color=TEXT2)
        ax_net.barh(yi, r.net40, height=BAR_HEIGHT, color=GREEN if r.net40 >= 0 else RED)
        ax_net.text(r.net40 + (1 if r.net40 >= 0 else -1), yi, f"{r.net40:+.0f}  ({r.pm:+.0f} in {r.secs / 60:.1f}')",
                    va="center", ha="left" if r.net40 >= 0 else "right", fontsize=8, color=TEXT2)
    ax_min.set_yticks(y); ax_min.set_yticklabels(labels, fontsize=8.5)
    ax_min.set_xlabel("minutes together, all games"); ax_net.set_xlabel("net points per 40 minutes (total plus/minus, minutes)")
    lim = max(abs(agg[agg.secs >= min_secs].net40).max(), NET_LIMIT_FLOOR) * NET_LIMIT_MARGIN
    ax_net.set_xlim(-lim, lim); ax_net.axvline(0, color=TEXT2, lw=0.8)
    ax_min.set_xlim(0, agg.secs.max() / 60 * MIN_LIMIT_MARGIN)
    for ax in (ax_min, ax_net):
        style_axes(ax, "x")
    total = agg.secs.sum() / 60
    fig.suptitle(f"{team}: five-man lineups, {league} {stamp}  |  {len(agg)} units in {total:.0f} minutes, "
                 f"{int((agg.secs >= min_secs).sum())} with {min_secs // 60}+ min together", **SUP_KW)
    path = out / f"lineups_{team.replace(' ', '_')}.png"
    save_fig(fig, path); plt.close(fig)
    return path


def main() -> None:
    """Command-line entry point: print the lineup tables and save one chart per team."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--team", action="append", required=True)
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--out", default="reports")
    ap.add_argument("--before", default=None, help="YYYY-MM-DD: only games before this date")
    ap.add_argument("--min-minutes", type=int, default=3)
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--competition", choices=[LBA, EUROCUP_CODE], default=LBA, help="EC: EuroCup games (data/eurocup_2026_raw.txt and data/eurocup/pbp.csv)")
    a = ap.parse_args()
    league = LBA if a.competition == LBA else EUROCUP_LABEL
    if a.competition == EUROCUP_CODE:
        from matchup_report import parse_eurocup
        box = parse_eurocup(Path(a.data) / EUROCUP_RAW)[0]
        pbp = pd.read_csv(Path(a.data) / "eurocup" / "pbp.csv")
        lba_style.SOURCE_NOTE = EL_SOURCE_NOTE
    else:
        box = pd.read_csv(Path(a.data) / "box_scores.csv")
        pbp = pd.read_csv(Path(a.data) / "pbp.csv")
        box["date"] = box.match_datetime.str[:10]
    stamp = "season to date"
    if a.before:
        box = box[box.date < a.before]
        pbp = pbp[pbp.game_id.isin(box.game_id.unique())]
        lba_style.STAMP_NOTE = f"games before {pd.Timestamp(a.before):%d %b %Y} (pre-match snapshot)"
        stamp = f"games before {pd.Timestamp(a.before):%d %b %Y}"
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 220); pd.set_option("display.max_colwidth", 80)
    for team in a.team:
        agg = team_lineups(box, pbp, team)
        print(f"\n=== {team}: {len(agg)} units, {agg.secs.sum() / 60:.0f} min ===")
        for title, df in pick(agg, a.min_minutes * 60, a.top):
            print(f"\n{title}")
            print(df.assign(lineup=df.lineup.map(" · ".join), min=(df.secs / 60).round(1), net40=df.net40.round(1))
                  [["lineup", "min", "pm", "net40", "stints", "games"]].to_string(index=False))
        print(fig_lineups(agg, team, a.min_minutes * 60, a.top, out, stamp, league))


if __name__ == "__main__":
    main()
