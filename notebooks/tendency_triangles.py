"""Triangle plots of where a team (and each of its players) makes its shots, game by game.

    python notebooks/tendency_triangles.py --team "Openjobmetis Varese" --before 2026-10-24 --competition LBA --out reports/<folder>
    python notebooks/tendency_triangles.py --team "BC Roma" --before 2026-10-27 --competition EC --out reports/<folder>

Writes into --out (<prefix> is 12_triangles_ unless --prefix says otherwise):
  <prefix>team_made.png            the team: share of the made field goals that are 3PT / paint / mid-range, one dot per game
  <prefix>players_high_made.png    the players who take HIGH_VOLUME_FGA or more attempts per game they play, one triangle each
  <prefix>players_low_made.png     the other players (with enough games); the volume groups are by attempts

The corners are the made 3-pointers (top), the made paint shots (bottom left) and the made mid-range shots (bottom right); paint + mid-range
are the 2-point field goals. Paint = inside the lane (the key: 4.9 m wide, baseline to free-throw line); mid-range = every other 2-point
shot. A dot close to a corner is a game made mostly of that kind of shot; green = a win of the team, red = a loss. The smoothed areas
(kernel density) hold the densest 50% (dark) and 80% (light) of the games; the black square is the average over all the shots.
Only games before --before count; --competition LBA uses the league play-by-play, EC the EuroCup one, ALL both.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Polygon

import lba_style
from lba_style import GOLD, GOLD_EDGE, GREEN, GRID, RED, SUP_KW, TEXT, TEXT2, save_fig, shots_cm

ROOT = Path(__file__).resolve().parent.parent
LANE_HALF_WIDTH, LANE_LENGTH = 245, lba_style.FREE_THROW_Y     # cm: the key is 4.9 m wide, from the baseline to the free-throw line
MIN_GAMES = 3                                                  # a player needs this many games with enough shots to get a triangle
MIN_MADE = 2                                                   # made shots of a game for it to count as a dot of a player (fewer = too noisy)
HIGH_VOLUME_FGA = 6.0                                          # attempts per game played: from here a player is "high volume"
COLS = 4
SHADE_INNER, SHADE_OUTER = 0.5, 0.8                            # share of the games inside the dark and the light shade
CORNERS = {"3PT": (0.5, math.sqrt(3) / 2), "Paint": (0.0, 0.0), "Mid-range": (1.0, 0.0)}   # top, bottom left, bottom right
BLACK = "#111118"
WIN_COLOR, LOSS_COLOR = GREEN, RED
COMPETITIONS = {"LBA": "LBA", "EC": "EuroCup", "ALL": "LBA + EuroCup"}


def classify(s: pd.DataFrame) -> pd.DataFrame:
    """Return the shots with a ``kind`` column: "3PT", "Paint" or "Mid-range"."""
    paint = (s.cx.abs() <= LANE_HALF_WIDTH) & (s.cy <= LANE_LENGTH)
    return s.assign(kind=np.where(s.pts == 3, "3PT", np.where(paint, "Paint", "Mid-range")))


def results(data: Path, team: str, competition: str) -> dict[str, bool]:
    """game_id (as text) -> True if `team` won that game, for the played games of `competition` ("LBA" or "EC")."""
    if competition == "EC":
        r = pd.read_csv(data / "eurocup" / "results.csv")
        r = r[r.played & ((r.home == team) | (r.away == team))]
        return {f"EC{int(x.gamecode)}": bool((x.home_score > x.away_score) == (x.home == team)) for x in r.itertuples()}
    g = pd.read_csv(data / "games.csv")
    g = g[((g.home_team == team) | (g.away_team == team)) & (g.home_score + g.away_score > 0)]
    return {str(x.game_id): bool((x.home_score > x.away_score) == (x.home_team == team)) for x in g.itertuples()}


def load_shots(data: Path, team: str, before: str, competition: str) -> pd.DataFrame:
    """The classified field-goal attempts of `team` in the games of `competition` ("LBA", "EC" or "ALL") played before `before`
    (with coordinates); ``game_id`` is text and ``win`` says whether the team won that game."""
    if competition == "ALL":
        both = [b for b in (load_shots(data, team, before, c) for c in ("LBA", "EC")) if not b.empty]
        return pd.concat(both, ignore_index=True) if both else pd.DataFrame()
    if competition == "EC":
        res = pd.read_csv(data / "eurocup" / "results.csv")
        ids = {f"EC{int(g)}" for g in res[(res.date < before) & res.played & ((res.home == team) | (res.away == team))].gamecode}
        pbp = pd.read_csv(data / "eurocup" / "pbp.csv")
    else:
        games = pd.read_csv(data / "games.csv")
        done = games[(games.match_datetime.str[:10] < before) & ((games.home_team == team) | (games.away_team == team))]
        ids = {str(g) for g in done.game_id}
        pbp = pd.read_csv(data / "pbp.csv")
    pbp = pbp.assign(game_id=pbp.game_id.astype(str))
    pbp = pbp[pbp.game_id.isin(ids)]
    if pbp.empty:
        return pd.DataFrame()
    s = shots_cm(pbp)
    s = classify(s[s.team == team])
    return s.assign(win=s.game_id.map(results(data, team, competition)))


def game_shares(s: pd.DataFrame, min_made: int = 1) -> pd.DataFrame:
    """One row per game with the share (0-1) of 3PT, Paint and Mid-range among the made shots, their number and ``win``."""
    wins = s.groupby("game_id").win.first()
    s = s[s.made]
    n = s.groupby(["game_id", "kind"]).size().unstack(fill_value=0).reindex(columns=list(CORNERS), fill_value=0)
    n = n[n.sum(axis=1) >= min_made]
    return n.div(n.sum(axis=1), axis=0).assign(n=n.sum(axis=1), win=wins.reindex(n.index).astype(bool))


def to_xy(shares: np.ndarray) -> np.ndarray:
    """Triangle coordinates of rows of (3PT, Paint, Mid-range) shares."""
    top, left, right = (np.array(CORNERS[k]) for k in CORNERS)
    return shares[:, [0]] * top + shares[:, [1]] * left + shares[:, [2]] * right


GRID_N = 220                                                   # resolution of the density grid
MIN_BANDWIDTH = 0.06                                           # smoothing never narrower than this (triangle side = 1)
TRIANGLE = np.array(list(CORNERS.values()))


def density_levels(xy: np.ndarray, fracs: tuple[float, ...]) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[float]]:
    """Gaussian kernel density of the games inside the triangle and, for each share in `fracs`, the density level whose area holds that
    share of the games (highest-density regions). Returns (grid x, grid y, density with NaN outside the triangle, levels)."""
    gx, gy = np.meshgrid(np.linspace(-0.02, 1.02, GRID_N), np.linspace(-0.02, 0.89, GRID_N))
    top, left, right = TRIANGLE
    inside = (gy >= -1e-9) & (gy <= top[1] * (1 - np.abs(gx - 0.5) * 2) + 1e-9)
    h = max(MIN_BANDWIDTH, float(np.sqrt(xy.var(axis=0).mean())) * len(xy) ** (-1 / 6))        # Scott's rule, with a floor
    dens = np.zeros_like(gx)
    for x, y in xy:
        dens += np.exp(-((gx - x) ** 2 + (gy - y) ** 2) / (2 * h * h))
    dens = np.where(inside, dens, np.nan)
    vals = np.sort(dens[inside])[::-1]
    mass = np.cumsum(vals) / vals.sum()
    return gx, gy, dens, [float(vals[min(np.searchsorted(mass, f), len(vals) - 1)]) for f in fracs]


def draw_triangle(ax, sh: pd.DataFrame, avg: np.ndarray, title: str, small: bool = False) -> None:
    """One triangle: grid, corner labels, the smoothed 50% / 80% areas, a dot per game (green win, red loss) and the black square of the average."""
    top, left, right = (CORNERS[k] for k in CORNERS)
    ax.add_patch(Polygon([top, left, right], closed=True, facecolor="white", edgecolor=TEXT2, lw=1.1, zorder=1))
    for t in (0.2, 0.4, 0.6, 0.8):                      # grid lines of the three shares
        for a, b, c in ((top, left, right), (left, right, top), (right, top, left)):
            p = np.array(a) * t + np.array(b) * (1 - t); q = np.array(a) * t + np.array(c) * (1 - t)
            ax.plot([p[0], q[0]], [p[1], q[1]], color=GRID, lw=0.7, zorder=2)
    fs = 8 if small else 10
    ax.text(top[0], top[1] + 0.03, "3PT", ha="center", va="bottom", fontsize=fs, fontweight="bold", color=TEXT)
    ax.text(left[0] - 0.02, left[1] - 0.03, "Paint", ha="center", va="top", fontsize=fs, fontweight="bold", color=TEXT)
    ax.text(right[0] + 0.02, right[1] - 0.03, "Mid-range", ha="center", va="top", fontsize=fs, fontweight="bold", color=TEXT)
    xy = to_xy(sh[list(CORNERS)].to_numpy())
    if len(xy) >= 3:
        gx, gy, dens, (lo, hi) = density_levels(xy, (SHADE_OUTER, SHADE_INNER))
        for level, upper, alpha in ((lo, hi, 0.28), (hi, np.nanmax(dens) * 1.01, 0.5)):    # light: inside the 80% area, dark: inside the 50% area
            ax.contourf(gx, gy, dens, levels=[level, upper], colors=[GOLD], alpha=alpha, zorder=3)
            ax.contour(gx, gy, dens, levels=[level], colors=[GOLD_EDGE], linewidths=0.9, alpha=0.8, zorder=3)
    colors = np.where(sh.win.to_numpy(), WIN_COLOR, LOSS_COLOR)
    ax.scatter(xy[:, 0], xy[:, 1], s=40 if small else 58, c=colors, edgecolor="white", linewidth=0.8, zorder=5)
    ax.scatter(*to_xy(avg[None, :])[0], marker="s", s=44 if small else 62, color=BLACK, edgecolor="white", linewidth=0.8, zorder=6)
    ax.set_title(title, fontsize=9 if small else 11, fontweight="bold", color=TEXT, pad=14 if small else 18)
    ax.set_xlim(-0.12, 1.12); ax.set_ylim(-0.12, 1.0); ax.set_aspect("equal"); ax.axis("off")


def panel_title(name: str, sh: pd.DataFrame, avg: np.ndarray, extra: str = "") -> str:
    """Name, record in the games shown and the average split (3PT / paint / mid-range, in %)."""
    w = int(sh.win.sum())
    return f"{name}{extra}\n{len(sh)} games ({w}W-{len(sh) - w}L) · avg {avg[0] * 100:.0f}% 3PT · {avg[1] * 100:.0f}% paint · {avg[2] * 100:.0f}% mid"


def kind_split(shots: pd.DataFrame) -> np.ndarray:
    """Share of 3PT / Paint / Mid-range over all the given shots."""
    n = shots.kind.value_counts().reindex(list(CORNERS), fill_value=0).to_numpy()
    return n / n.sum()


def footer(fig, players: bool) -> None:
    """Legend (win / loss / average / areas) and the explanation under the figure."""
    from matplotlib.lines import Line2D
    items = [Line2D([], [], marker="o", ls="", color=WIN_COLOR, label="game won"), Line2D([], [], marker="o", ls="", color=LOSS_COLOR, label="game lost"),
             Line2D([], [], marker="s", ls="", color=BLACK, label="average of all shots"),
             Line2D([], [], marker="s", ls="", color=GOLD, alpha=0.5, markersize=10, label=f"densest {SHADE_INNER:.0%} of the games"),
             Line2D([], [], marker="s", ls="", color=GOLD, alpha=0.28, markersize=10, label=f"densest {SHADE_OUTER:.0%}")]
    fig.legend(handles=items, loc="lower center", ncol=5, fontsize=8.5, bbox_to_anchor=(0.5, -0.01))
    note = (f"Corners: 3-point, paint (inside the lane) and mid-range (other 2-point shots) made field goals; paint + mid-range = 2-point. Areas: kernel density, drawn with 3+ games."
            + (f" Players: at least {MIN_GAMES} games with {MIN_MADE}+ made shots; high volume = {HIGH_VOLUME_FGA:g}+ attempts per game played." if players else ""))
    fig.text(0.01, -0.045, note, fontsize=7.5, color=TEXT2, ha="left", va="top")


def fig_team(s: pd.DataFrame, team: str, comp_name: str, out: Path, prefix: str) -> Path | None:
    """Save <prefix>team_made.png: the triangle of the team."""
    shots = s[s.made]
    if shots.empty:
        return None
    sh = game_shares(s)
    fig, ax = plt.subplots(figsize=(7.2, 7.6))
    draw_triangle(ax, sh, kind_split(shots), panel_title(team, sh, kind_split(shots)))
    fig.suptitle(f"{team} — made field goals by type, one dot per game ({comp_name} games)", **SUP_KW)
    footer(fig, players=False)
    path = out / f"{prefix}team_made.png"
    save_fig(fig, path); plt.close(fig)
    return path


def fig_players(s: pd.DataFrame, team: str, comp_name: str, out: Path, prefix: str) -> list[Path]:
    """Save <prefix>players_high_made.png and <prefix>players_low_made.png: one triangle per player, split by attempts per game."""
    shots = s[s.made]
    groups: dict[str, list] = {"high": [], "low": []}
    for player, allp in s.groupby("player_surname"):
        sh = game_shares(allp, MIN_MADE)
        if len(sh) < MIN_GAMES:
            continue
        vol = len(allp) / allp.game_id.nunique()
        mine = shots[shots.player_surname == player]
        groups["high" if vol >= HIGH_VOLUME_FGA else "low"].append((vol, player.title(), sh, kind_split(mine), f" · {vol:.1f} FGA/g"))
    paths = []
    for grp, label in (("high", f"high volume ({HIGH_VOLUME_FGA:g}+ attempts per game)"), ("low", f"lower volume (under {HIGH_VOLUME_FGA:g} attempts per game)")):
        panels = sorted(groups[grp], key=lambda p: -p[0])
        if not panels:
            continue
        rows = math.ceil(len(panels) / COLS)
        fig, axes = plt.subplots(rows, COLS, figsize=(4.6 * COLS, 4.9 * rows), squeeze=False)
        for ax in axes.ravel():
            ax.axis("off")
        for ax, (_, name, sh, avg, extra) in zip(axes.ravel(), panels):
            draw_triangle(ax, sh, avg, panel_title(name, sh, avg, extra), small=True)
        fig.suptitle(f"{team} — players, {label}: made field goals by type ({comp_name} games)", **SUP_KW)
        footer(fig, players=True)
        path = out / f"{prefix}players_{grp}_made.png"
        save_fig(fig, path); plt.close(fig)
        paths.append(path)
    return paths


def main() -> None:
    """Command line entry point."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--team", required=True)
    ap.add_argument("--before", required=True, help="YYYY-MM-DD: only games before this date count")
    ap.add_argument("--competition", choices=sorted(COMPETITIONS), default="LBA")
    ap.add_argument("--out", required=True)
    ap.add_argument("--prefix", default="12_triangles_", help="file name start of the figures, see the top of this file")
    ap.add_argument("--data", default=str(ROOT / "data"))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    s = load_shots(Path(a.data), a.team, a.before, a.competition)
    if s.empty:
        raise SystemExit(f"no shots of {a.team} before {a.before} in {COMPETITIONS[a.competition]}")
    lba_style.SOURCE_NOTE = {"EC": "EuroCup play-by-play (EuroLeague API)", "ALL": "legabasket.it and EuroLeague API play-by-play"}.get(a.competition, lba_style.SOURCE_NOTE)
    lba_style.STAMP_NOTE = f"games before {pd.Timestamp(a.before):%d %b %Y} (pre-match snapshot)"
    for p in [fig_team(s, a.team, COMPETITIONS[a.competition], out, a.prefix), *fig_players(s, a.team, COMPETITIONS[a.competition], out, a.prefix)]:
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
