"""Shared style + court helpers for the LBA report scripts (white background, BC Roma in gold).

Layout and chart types follow martinig94/basketball_analytics (utils_plot.py); the palette is a
light-mode version of it so the figures work in docs and slides on white.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.colors import Normalize
from matplotlib.figure import Figure
from matplotlib.patches import Arc, Circle, PathPatch, Rectangle
from matplotlib.path import Path as MPath

import weekly_config

matplotlib.use("Agg")

# ── palette ──────────────────────────────────────────────────────────────────────
BG, PANEL_BG = "#ffffff", "#f6f6f9"
GOLD = "#F2C300"          # team colour (BC Roma) – every team mark uses this
GOLD_EDGE = "#B08D00"     # thin edge so gold reads on white
RED, GREEN, BLUE, ORANGE = "#d94b4b", "#2e9e5b", "#4a7fc1", "#e08c52"
LEAGUE = "#9aa0b4"        # muted steel for league / opponent reference
TEXT, TEXT2, GRID, COURT = "#1a1a2e", "#5a5e73", "#e3e4ea", "#5b5f78"
EMPTY_ZONE = "#e6e6ee"    # zone fill when a zone has no value
ROMA_RIVAL_FILL, ROMA_RIVAL_EDGE = "#2b2b36", "#111118"   # near-black for the other Rome club
BLUE_EDGE, ORANGE_EDGE, GREEN_EDGE = "#2f5f99", "#b46a3a", "#1f6e3f"
TITLE_KW: dict[str, Any] = dict(color=TEXT, fontsize=13, fontweight="bold", pad=12)
SUP_KW: dict[str, Any] = dict(color=TEXT, fontsize=15, fontweight="bold")
DPI = 160

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": PANEL_BG, "savefig.facecolor": BG,
    "text.color": TEXT, "axes.labelcolor": TEXT2, "xtick.color": TEXT2, "ytick.color": TEXT2,
    "axes.edgecolor": GRID, "grid.color": GRID, "grid.linewidth": 0.8,
    "font.family": "DejaVu Sans", "legend.frameon": False,
    "figure.constrained_layout.use": True, "figure.constrained_layout.h_pad": 0.12, "figure.constrained_layout.w_pad": 0.12,   # keeps suptitles, axes titles and colorbars from overlapping
})


AUTHOR: str = weekly_config.load()["author"]   # chart stamp; report scripts may override it
STAMP_FONT_SIZE = 7.5
STAMP_ALPHA = 0.9
STAMP_X, STAMP_Y = 0.995, -0.035   # figure fractions: bottom-right, just below the axes
SOURCE_NOTE = "legabasket.it play-by-play"   # data source shown in the chart stamp
STAMP_NOTE = ""   # set by the report scripts, e.g. "data as of 10 Oct 2026 (pre-match snapshot)"


def save_fig(fig: Figure, path: str | Path, **kw: Any) -> None:
    """Save a figure with an author/date stamp in the bottom-right corner (every published chart carries it).

    Args:
        fig: Figure to save.
        path: Output file; a ``.png`` is also palette-shrunk afterwards.
        **kw: Passed to ``Figure.savefig``; ``dpi`` defaults to ``DPI``.
    """
    note = f" · {STAMP_NOTE}" if STAMP_NOTE else ""
    fig.text(STAMP_X, STAMP_Y, f"{AUTHOR} · {date.today():%d %b %Y} · data: {SOURCE_NOTE}{note}",
             ha="right", va="bottom", fontsize=STAMP_FONT_SIZE, color=TEXT2, alpha=STAMP_ALPHA)
    fig.savefig(path, dpi=kw.pop("dpi", DPI), bbox_inches="tight", **kw)
    if str(path).lower().endswith(".png"):
        from imgopt import shrink_png      # 256-colour PNG: ~4x smaller, same look
        shrink_png(path)


def team_bar_kw() -> dict[str, Any]:
    """Return the bar-chart keyword arguments of a team mark (gold fill, thin edge)."""
    return dict(color=GOLD, edgecolor=GOLD_EDGE, linewidth=0.6)


def mins(m: float) -> str:
    """Format minutes as a whole number with a prime, e.g. ``32'``."""
    return f"{m:.0f}'"


def style_axes(ax: Axes, grid: str | None = None) -> None:
    """Hide the spines and tick marks of ``ax``; draw light grid lines along ``grid`` (``"x"``/``"y"``) if given."""
    ax.spines[:].set_visible(False)
    ax.tick_params(length=0)
    if grid:
        ax.grid(axis=grid, color=GRID, lw=0.8)
        ax.set_axisbelow(True)


# ── court geometry (cm, basket at origin, court extends +y) ──────────────────────
THREE_PT_RADIUS, CORNER_X, CORNER_Y, RESTRICTED_R, SHORT_RANGE_MAX = 675, 660, 90, 125, 449
BASELINE_Y = -157.5        # the rim is 1.575 m in from the baseline
HALF_COURT_LENGTH = 1400   # baseline to half-way line (rounded, as drawn)
HALF_WAY_Y = 1242.5        # y of the half-way line used to clip the zone polygons
HALF_WIDTH = 750           # half of the 15 m court width
FREE_THROW_Y = 422         # free-throw line
ZONE_BIG = 5000            # "infinity" for the sector polygons, far outside the court
FULL_PCT = 100             # coordinates in the play-by-play are 0-100 percent
CM_PER_PCT_X, CM_PER_PCT_Y = 28.0, 15.0   # 1 percent of the 28 m length / 15 m width, in cm
MID_LINE_PCT = 50          # x percent at which teams' attacking ends are folded together
ZONE_LABELS = {"A": "Under basket", "B": "Left short", "C": "Right short", "D": "Left mid", "E": "Centre mid",
               "F": "Right mid", "G": "Left 3PT", "H": "Centre 3PT", "I": "Right 3PT"}
ZONE_LABEL_POS = {"A": (0, 55), "B": (-215, 270), "C": (215, 270), "D": (-450, 360), "E": (0, 560),
                  "F": (450, 360), "G": (-620, 480), "H": (0, 950), "I": (620, 480)}


def assign_zone_arr(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Return the zone letter (A-I, see ``ZONE_LABELS``) of each shot given court coordinates in cm."""
    d2 = x * x + y * y
    z = np.full(x.shape, "E", dtype="<U1")
    left, right = x < -y, x > y
    z[left] = "D"; z[right] = "F"
    three = (d2 >= THREE_PT_RADIUS**2) | ((np.abs(x) >= CORNER_X) & (y <= CORNER_Y))
    z[three & left] = "G"; z[three & right] = "I"; z[three & ~left & ~right] = "H"
    short = (d2 <= SHORT_RANGE_MAX**2) & ~three
    z[short & (x < 0)] = "B"; z[short & (x >= 0)] = "C"
    z[d2 <= RESTRICTED_R**2] = "A"
    return z


def draw_half_court(ax: Axes, color: str = COURT, lw: float = 1.4) -> None:
    """Draw a FIBA half court on ``ax``, basket at the origin, units cm (same frame as basketball_analytics).

    Baseline at y = -157.5 (the rim is 1.575 m in from it), half-way line at y = 1242.5.

    Args:
        ax: Axes to draw on; its limits and aspect are set and the axis is hidden.
        color: Line colour.
        lw: Line width.
    """
    ft_y, base = FREE_THROW_Y, BASELINE_Y
    for el in [Circle((0, 0), 22.5, lw=lw, color=color, fill=False),
               Rectangle((-91.5, -20), 183, -4, lw=lw, color=color),
               Rectangle((-245, base), 490, ft_y - base, lw=lw, edgecolor=color, facecolor="none"),
               Arc((0, ft_y), 360, 360, theta1=0, theta2=180, lw=lw, color=color),
               Arc((0, ft_y), 360, 360, theta1=180, theta2=0, lw=lw, color=color, linestyle="dashed"),
               Arc((0, 0), 250, 250, theta1=0, theta2=180, lw=lw, color=color),
               Rectangle((-660, base), 0, 299, lw=lw, color=color), Rectangle((660, base), 0, 299, lw=lw, color=color),
               Arc((0, 0), 1350, 1350, theta1=12, theta2=168, lw=lw, color=color),
               Rectangle((-HALF_WIDTH, base), 2 * HALF_WIDTH, HALF_COURT_LENGTH, lw=lw, edgecolor=color, facecolor="none"),
               Arc((0, base + HALF_COURT_LENGTH), 360, 360, theta1=180, theta2=0, lw=lw, color=color)]:
        ax.add_patch(el)
    ax.set_xlim(-790, 790); ax.set_ylim(-200, 1290); ax.set_aspect("equal"); ax.axis("off")


COURT_X, COURT_Y = (-742, 742), (-150, 1235)   # inside the lines; shots are clipped to this box


def shots_cm(pbp: pd.DataFrame) -> pd.DataFrame:
    """Return all field-goal attempts of a play-by-play in cm, basket at the origin, both ends folded.

    Legabasket coordinates are percent of the full court (x along the 28 m length, y across the
    15 m width). Teams swap ends at half time, so attempts at x>50 are rotated 180 degrees.

    Args:
        pbp: Play-by-play rows with ``event``, ``x``, ``y`` and ``player_surname``.

    Returns:
        The shot rows plus ``made``, ``pts``, ``cx``, ``cy``, ``dist``, ``zone`` and ``player``.
    """
    s = pbp[pbp.event.str.match(r"^\d punti", na=False)].dropna(subset=["x", "y"]).copy()
    s["made"] = s.event.str.contains("segnato")
    s["pts"] = s.event.str[0].astype(int)
    flip = s.x > MID_LINE_PCT
    xf = np.where(flip, FULL_PCT - s.x, s.x)
    yf = np.where(flip, FULL_PCT - s.y, s.y)
    s["cx"] = np.clip((yf - MID_LINE_PCT) * CM_PER_PCT_Y, *COURT_X)      # scorer clicks occasionally land outside the lines
    s["cy"] = np.clip(xf * CM_PER_PCT_X + BASELINE_Y, *COURT_Y)
    s["dist"] = np.hypot(s.cx, s.cy)
    s["zone"] = assign_zone_arr(s.cx.values, s.cy.values)
    s["player"] = s.player_surname.fillna("").str.title()
    return s


# ── team colours (BC Roma always gold; add others as needed) ──────────────────────
RIVAL_ROME_TEAM = "Maxima Roma"
TEAM_COLORS = {weekly_config.load()["team"]: (GOLD, GOLD_EDGE), RIVAL_ROME_TEAM: (ROMA_RIVAL_FILL, ROMA_RIVAL_EDGE)}
_FALLBACK = [(BLUE, BLUE_EDGE), (ORANGE, ORANGE_EDGE), (GREEN, GREEN_EDGE)]


def team_color(team: str, idx: int = 0) -> tuple[str, str]:
    """Return the (fill, edge) colours of a team; unknown teams cycle through blue/orange/green by ``idx``."""
    return TEAM_COLORS.get(team, _FALLBACK[idx % len(_FALLBACK)])


# ── zone polygons (vector, smooth edges) ────────────────────────────────────────
def zone_polygons() -> dict:
    """Return the nine A–I zones as shapely polygons in the court frame (cm), mirroring assign_zone_arr exactly.

    Used to draw zone heatmaps as filled vector patches instead of a pixel grid.
    """
    from shapely.geometry import Point, Polygon, box
    from shapely.ops import unary_union

    court = box(-HALF_WIDTH, BASELINE_Y, HALF_WIDTH, HALF_WAY_Y)
    circ = lambda r: Point(0, 0).buffer(r, resolution=256)
    strips = unary_union([box(-HALF_WIDTH, BASELINE_Y, -CORNER_X, CORNER_Y), box(CORNER_X, BASELINE_Y, HALF_WIDTH, CORNER_Y)])
    inside3 = circ(THREE_PT_RADIUS).difference(strips).intersection(court)
    three = court.difference(inside3)
    a = circ(RESTRICTED_R).intersection(court)
    short = circ(SHORT_RANGE_MAX).difference(circ(RESTRICTED_R)).intersection(court)
    mid = inside3.difference(circ(SHORT_RANGE_MAX))
    big = ZONE_BIG
    left_sector = Polygon([(0, 0), (-big, big), (-big, -big), (big, -big)])    # x < -y
    right_sector = Polygon([(0, 0), (big, big), (big, -big), (-big, -big)])    # x > y
    left_half, right_half = box(-big, -big, 0, big), box(0, -big, big, big)
    zones = {
        "A": a,
        "B": short.intersection(left_half), "C": short.intersection(right_half),
        "D": mid.intersection(left_sector), "F": mid.intersection(right_sector),
        "G": three.intersection(left_sector), "I": three.intersection(right_sector),
    }
    zones["E"] = mid.difference(zones["D"]).difference(zones["F"])
    zones["H"] = three.difference(zones["G"]).difference(zones["I"])
    return zones


def draw_zone_fill(ax: Axes, pct_by_zone: dict[str, float], cmap: Callable[[float], Any], vmin: float = 0,
                   vmax: float = 100, alpha: float = 0.85, empty: str = EMPTY_ZONE, zorder: float = 1) -> None:
    """Fill the nine zones with ``cmap(pct)`` as smooth vector patches.

    Args:
        ax: Axes of a half court (see ``draw_half_court``).
        pct_by_zone: Value per zone letter; zones missing from it get ``empty``.
        cmap: Colormap mapping a normalised value to a colour.
        vmin: Value that maps to the bottom of the colormap.
        vmax: Value that maps to the top of the colormap.
        alpha: Patch opacity.
        empty: Fill colour of zones without a value.
        zorder: Drawing order.
    """
    norm = Normalize(vmin, vmax)
    for z, geom in zone_polygons().items():
        geoms = geom.geoms if hasattr(geom, "geoms") else [geom]
        color = cmap(norm(pct_by_zone[z])) if z in pct_by_zone else empty
        for g in geoms:
            verts, codes = [], []
            for ring in [g.exterior, *g.interiors]:
                pts = list(ring.coords)
                verts += pts
                codes += [MPath.MOVETO] + [MPath.LINETO] * (len(pts) - 2) + [MPath.CLOSEPOLY]
            ax.add_patch(PathPatch(MPath(verts, codes), facecolor=color, edgecolor=color, linewidth=0.3, alpha=alpha, zorder=zorder))
