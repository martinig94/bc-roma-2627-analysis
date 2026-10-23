"""Triangle plots of where a team (and each of its players) takes and makes its shots, game by game.

    python notebooks/tendency_triangles.py --team "Openjobmetis Varese" --before 2026-10-24 --competition LBA --out reports/<folder>
    python notebooks/tendency_triangles.py --team "BC Roma" --before 2026-10-27 --competition EC --out reports/<folder>

Writes into --out:
  12_triangles_attempts.png   share of the field-goal attempts that are 3PA / paint / mid-range, one dot per game
  12_triangles_made.png       the same for the made shots

The corners are the 3-point attempts (top), the paint attempts (bottom left) and the mid-range attempts (bottom right); paint + mid-range
are the 2-point attempts. Paint = inside the lane (the key: 4.9 m wide, baseline to free-throw line); mid-range = every other 2-point
attempt. A dot close to a corner is a game made mostly of that kind of shot. The dark shade holds the 50% of the games closest to the
typical game (the median of the games), the light shade the 80%; the diamond is the average over all the shots of the team.
Only games before --before count; --competition LBA uses the league play-by-play, EC the EuroCup one, ALL both. The team is the first panel,
then the players with enough games (see MIN_GAMES).
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
from lba_style import BLUE, GOLD, GOLD_EDGE, GRID, RED, SUP_KW, TEXT, TEXT2, save_fig, shots_cm

ROOT = Path(__file__).resolve().parent.parent
LANE_HALF_WIDTH, LANE_LENGTH = 245, lba_style.FREE_THROW_Y     # cm: the key is 4.9 m wide, from the baseline to the free-throw line
MIN_GAMES = 3                                                  # a player needs this many games with enough shots to get a triangle
MIN_SHOTS = {"attempts": 3, "made": 2}                         # shots of a game for it to count as a dot of a player (fewer = too noisy)
MAX_PLAYERS = 11
COLS = 4
SHADE_INNER, SHADE_OUTER = 0.5, 0.8                            # share of the games inside the dark and the light shade
CORNERS = {"3PT": (0.5, math.sqrt(3) / 2), "Paint": (0.0, 0.0), "Mid-range": (1.0, 0.0)}   # top, bottom left, bottom right
KINDS = {"attempts": "Attempts", "made": "Made shots"}
COMPETITIONS = {"LBA": "LBA", "EC": "EuroCup", "ALL": "LBA + EuroCup"}


def classify(s: pd.DataFrame) -> pd.DataFrame:
    """Return the shots with a ``kind`` column: "3PT", "Paint" or "Mid-range"."""
    paint = (s.cx.abs() <= LANE_HALF_WIDTH) & (s.cy <= LANE_LENGTH)
    return s.assign(kind=np.where(s.pts == 3, "3PT", np.where(paint, "Paint", "Mid-range")))


def load_shots(data: Path, team: str, before: str, competition: str) -> pd.DataFrame:
    """The classified field-goal attempts of `team` in the games of `competition` played before `before` (with coordinates)."""
    if competition == "ALL":
        both = [load_shots(data, team, before, c) for c in ("LBA", "EC")]
        both = [b.assign(game_id=b.game_id.astype(str)) for b in both if not b.empty]
        return pd.concat(both, ignore_index=True) if both else pd.DataFrame()
    if competition == "EC":
        res = pd.read_csv(data / "eurocup" / "results.csv")
        ids = {f"EC{int(g)}" for g in res[(res.date < before) & res.played & ((res.home == team) | (res.away == team))].gamecode}
        pbp = pd.read_csv(data / "eurocup" / "pbp.csv")
    else:
        games = pd.read_csv(data / "games.csv")
        done = games[(games.match_datetime.str[:10] < before) & ((games.home_team == team) | (games.away_team == team))]
        ids = set(done.game_id)
        pbp = pd.read_csv(data / "pbp.csv")
    pbp = pbp[pbp.game_id.isin(ids)]
    if pbp.empty:
        return pd.DataFrame()
    s = shots_cm(pbp)
    return classify(s[s.team == team])


def game_shares(s: pd.DataFrame, what: str, min_shots: int = 1) -> pd.DataFrame:
    """One row per game with the share (0-1) of 3PT, Paint and Mid-range among the attempts (or the made shots) and their number."""
    if what == "made":
        s = s[s.made]
    n = s.groupby(["game_id", "kind"]).size().unstack(fill_value=0).reindex(columns=list(CORNERS), fill_value=0)
    n = n[n.sum(axis=1) >= min_shots]
    return n.div(n.sum(axis=1), axis=0).assign(n=n.sum(axis=1))


def to_xy(shares: np.ndarray) -> np.ndarray:
    """Triangle coordinates of rows of (3PT, Paint, Mid-range) shares."""
    top, left, right = (np.array(CORNERS[k]) for k in CORNERS)
    return shares[:, [0]] * top + shares[:, [1]] * left + shares[:, [2]] * right


def convex_hull(points: np.ndarray) -> np.ndarray:
    """Corners of the convex hull of 2-D points (Andrew's monotone chain), counter-clockwise; fewer than 3 corners = no area."""
    pts = sorted({(round(float(x), 9), round(float(y), 9)) for x, y in points})
    if len(pts) < 3:
        return np.array(pts)

    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0]) <= 0:
                h.pop()
            h.append(p)
        return h[:-1]
    return np.array(half(pts) + half(pts[::-1]))


def central_hull(xy: np.ndarray, frac: float) -> np.ndarray | None:
    """Corners of the convex hull of the ceil(frac * n) games closest to the median game, or None if they do not span an area."""
    centre = np.median(xy, axis=0)
    k = math.ceil(frac * len(xy))
    near = xy[np.argsort(np.hypot(*(xy - centre).T), kind="stable")[:k]]
    hull = convex_hull(near)
    return hull if len(hull) >= 3 else None


def draw_triangle(ax, sh: pd.DataFrame, avg: np.ndarray, title: str, small: bool = False) -> None:
    """One triangle: grid, corner labels, the two shades (50% / 80% of the games), a dot per game and the diamond of the average."""
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
    for frac, alpha in ((SHADE_OUTER, 0.22), (SHADE_INNER, 0.42)):
        hull = central_hull(xy, frac)
        if hull is not None:
            ax.add_patch(Polygon(hull, closed=True, facecolor=GOLD, edgecolor=GOLD_EDGE, alpha=alpha, lw=0.8, zorder=3))
    ax.scatter(xy[:, 0], xy[:, 1], s=34 if small else 50, color=BLUE, edgecolor="white", linewidth=0.8, zorder=5)
    ax.scatter(*to_xy(avg[None, :])[0], marker="D", s=46 if small else 64, color=RED, edgecolor="white", linewidth=0.8, zorder=6)
    ax.set_title(title, fontsize=9 if small else 11, fontweight="bold", color=TEXT, pad=14 if small else 18)
    ax.set_xlim(-0.12, 1.12); ax.set_ylim(-0.12, 1.0); ax.set_aspect("equal"); ax.axis("off")


def panel_title(name: str, sh: pd.DataFrame, avg: np.ndarray) -> str:
    """Name, number of games and the average split (3PT / paint / mid-range, in %)."""
    return f"{name}\n{len(sh)} games · avg {avg[0] * 100:.0f}% 3PT · {avg[1] * 100:.0f}% paint · {avg[2] * 100:.0f}% mid"


def fig_triangles(s: pd.DataFrame, team: str, what: str, comp_name: str, out: Path, prefix: str = "12_triangles_") -> Path | None:
    """Save 12_triangles_<what>.png: the team and each player with enough games. Returns the file, or None without shots."""
    shots = s[s.made] if what == "made" else s
    if shots.empty:
        return None
    panels = []
    team_sh = game_shares(s, what)
    panels.append((team, team_sh, shots.kind.value_counts().reindex(list(CORNERS), fill_value=0).to_numpy() / len(shots)))
    for player, ps in shots.groupby("player_surname"):
        sh = game_shares(s[s.player_surname == player], what, MIN_SHOTS[what])
        if len(sh) >= MIN_GAMES:
            ps_kind = ps.kind.value_counts().reindex(list(CORNERS), fill_value=0).to_numpy()
            panels.append((player.title(), sh, ps_kind / ps_kind.sum(), len(ps)))
    team_panel, players = panels[0], sorted(panels[1:], key=lambda p: -p[3])[:MAX_PLAYERS]
    rows = 1 + math.ceil(len(players) / COLS)
    fig = plt.figure(figsize=(4.6 * COLS, 4.9 * rows))
    gs = fig.add_gridspec(rows, COLS)
    ax = fig.add_subplot(gs[0, 1:3])
    draw_triangle(ax, team_panel[1], team_panel[2], panel_title(team_panel[0], team_panel[1], team_panel[2]))
    for i, (name, sh, avg, _) in enumerate(players):
        ax = fig.add_subplot(gs[1 + i // COLS, i % COLS])
        draw_triangle(ax, sh, avg, panel_title(name, sh, avg), small=True)
    what_txt = "made field goals" if what == "made" else "field-goal attempts"
    fig.suptitle(f"{team} — {what_txt} by type, one dot per game ({comp_name} games)", **SUP_KW)
    note = (f"Corners: 3-point, paint (inside the lane) and mid-range (other 2-point shots) {what_txt}; paint + mid-range = 2-point. "
            f"Dark shade: the {SHADE_INNER:.0%} of the games closest to the typical game; light shade: {SHADE_OUTER:.0%}; diamond: all shots together. "
            f"Players: at least {MIN_GAMES} games with {MIN_SHOTS[what]}+ {'made shots' if what == 'made' else 'attempts'}; shades need 3+ games.")
    fig.text(0.01, 0.0, note, fontsize=7.5, color=TEXT2, ha="left", va="top", wrap=True)
    path = out / f"{prefix}{what}.png"
    save_fig(fig, path); plt.close(fig)
    return path


def main() -> None:
    """Command line entry point."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--team", required=True)
    ap.add_argument("--before", required=True, help="YYYY-MM-DD: only games before this date count")
    ap.add_argument("--competition", choices=sorted(COMPETITIONS), default="LBA")
    ap.add_argument("--out", required=True)
    ap.add_argument("--prefix", default="12_triangles_", help="file name start; the file is <prefix>attempts.png / <prefix>made.png")
    ap.add_argument("--data", default=str(ROOT / "data"))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    s = load_shots(Path(a.data), a.team, a.before, a.competition)
    if s.empty:
        raise SystemExit(f"no shots of {a.team} before {a.before} in {COMPETITIONS[a.competition]}")
    if a.competition == "EC":
        lba_style.SOURCE_NOTE = "EuroCup play-by-play (EuroLeague API)"
    elif a.competition == "ALL":
        lba_style.SOURCE_NOTE = "legabasket.it and EuroLeague API play-by-play"
    lba_style.STAMP_NOTE = f"games before {pd.Timestamp(a.before):%d %b %Y} (pre-match snapshot)"
    for what in KINDS:
        p = fig_triangles(s, a.team, what, COMPETITIONS[a.competition], out, a.prefix)
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
