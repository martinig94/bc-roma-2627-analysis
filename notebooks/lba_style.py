"""Shared style + court helpers for the LBA report scripts (white background, BC Roma in gold).

Layout and chart types follow martinig94/basketball_analytics (utils_plot.py); the palette is a
light-mode version of it so the figures work in docs and slides on white.
"""
from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.patches import Arc, Circle, Rectangle

matplotlib.use("Agg")

# ── palette ──────────────────────────────────────────────────────────────────────
BG, PANEL_BG = "#ffffff", "#f6f6f9"
GOLD = "#F2C300"          # team colour (BC Roma) – every team mark uses this
GOLD_EDGE = "#B08D00"     # thin edge so gold reads on white
RED, GREEN, BLUE, ORANGE = "#d94b4b", "#2e9e5b", "#4a7fc1", "#e08c52"
LEAGUE = "#9aa0b4"        # muted steel for league / opponent reference
TEXT, TEXT2, GRID, COURT = "#1a1a2e", "#5a5e73", "#e3e4ea", "#5b5f78"
TITLE_KW = dict(color=TEXT, fontsize=13, fontweight="bold", pad=12)
SUP_KW = dict(color=TEXT, fontsize=15, fontweight="bold")
DPI = 160

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": PANEL_BG, "savefig.facecolor": BG,
    "text.color": TEXT, "axes.labelcolor": TEXT2, "xtick.color": TEXT2, "ytick.color": TEXT2,
    "axes.edgecolor": GRID, "grid.color": GRID, "grid.linewidth": 0.8,
    "font.family": "DejaVu Sans", "legend.frameon": False,
    "figure.constrained_layout.use": True, "figure.constrained_layout.h_pad": 0.12, "figure.constrained_layout.w_pad": 0.12,   # keeps suptitles, axes titles and colorbars from overlapping
})


AUTHOR = "Giulia Martini"
STAMP_NOTE = ""   # set by the report scripts, e.g. "data as of 10 Oct 2026 (pre-match snapshot)"


def save_fig(fig, path, **kw) -> None:
    """Save with an author/date stamp in the bottom-right corner (every published chart carries it)."""
    from datetime import date
    note = f" · {STAMP_NOTE}" if STAMP_NOTE else ""
    fig.text(0.995, -0.035, f"{AUTHOR} · {date.today():%d %b %Y} · data: legabasket.it play-by-play{note}",
             ha="right", va="bottom", fontsize=7.5, color=TEXT2, alpha=0.9)
    fig.savefig(path, dpi=kw.pop("dpi", DPI), bbox_inches="tight", **kw)


def team_bar_kw() -> dict:
    return dict(color=GOLD, edgecolor=GOLD_EDGE, linewidth=0.6)


def mins(m: float) -> str:
    return f"{m:.0f}'"


def style_axes(ax: Axes, grid: str | None = None) -> None:
    ax.spines[:].set_visible(False)
    ax.tick_params(length=0)
    if grid:
        ax.grid(axis=grid, color=GRID, lw=0.8); ax.set_axisbelow(True)


# ── court geometry (cm, basket at origin, court extends +y) ──────────────────────
THREE_PT_RADIUS, CORNER_X, CORNER_Y, RESTRICTED_R, SHORT_RANGE_MAX = 675, 660, 90, 125, 449
ZONE_LABELS = {"A": "Under basket", "B": "Left short", "C": "Right short", "D": "Left mid", "E": "Centre mid",
               "F": "Right mid", "G": "Left 3PT", "H": "Centre 3PT", "I": "Right 3PT"}
ZONE_LABEL_POS = {"A": (0, 55), "B": (-215, 270), "C": (215, 270), "D": (-450, 360), "E": (0, 560),
                  "F": (450, 360), "G": (-620, 480), "H": (0, 950), "I": (620, 480)}


def assign_zone_arr(x: np.ndarray, y: np.ndarray) -> np.ndarray:
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
    """FIBA half court, basket at the origin, units cm (same frame as basketball_analytics).

    Baseline at y = -157.5 (the rim is 1.575 m in from it), half-way line at y = 1242.5.
    """
    ft_y, base = 422, -157.5
    for el in [Circle((0, 0), 22.5, lw=lw, color=color, fill=False),
               Rectangle((-91.5, -20), 183, -4, lw=lw, color=color),
               Rectangle((-245, base), 490, ft_y - base, lw=lw, edgecolor=color, facecolor="none"),
               Arc((0, ft_y), 360, 360, theta1=0, theta2=180, lw=lw, color=color),
               Arc((0, ft_y), 360, 360, theta1=180, theta2=0, lw=lw, color=color, linestyle="dashed"),
               Arc((0, 0), 250, 250, theta1=0, theta2=180, lw=lw, color=color),
               Rectangle((-660, base), 0, 299, lw=lw, color=color), Rectangle((660, base), 0, 299, lw=lw, color=color),
               Arc((0, 0), 1350, 1350, theta1=12, theta2=168, lw=lw, color=color),
               Rectangle((-750, base), 1500, 1400, lw=lw, edgecolor=color, facecolor="none"),
               Arc((0, base + 1400), 360, 360, theta1=180, theta2=0, lw=lw, color=color)]:
        ax.add_patch(el)
    ax.set_xlim(-790, 790); ax.set_ylim(-200, 1290); ax.set_aspect("equal"); ax.axis("off")


COURT_X, COURT_Y = (-742, 742), (-150, 1235)   # inside the lines; shots are clipped to this box


def shots_cm(pbp: pd.DataFrame) -> pd.DataFrame:
    """All FGA in the play-by-play, converted to cm with the basket at the origin, both ends folded.

    Legabasket coordinates are percent of the full court (x along the 28 m length, y across the
    15 m width). Teams swap ends at half time, so attempts at x>50 are rotated 180 degrees.
    """
    s = pbp[pbp.event.str.match(r"^\d punti", na=False)].dropna(subset=["x", "y"]).copy()
    s["made"] = s.event.str.contains("segnato")
    s["pts"] = s.event.str[0].astype(int)
    flip = s.x > 50
    xf = np.where(flip, 100 - s.x, s.x); yf = np.where(flip, 100 - s.y, s.y)
    s["cx"] = np.clip((yf - 50) * 15.0, *COURT_X)      # scorer clicks occasionally land outside the lines
    s["cy"] = np.clip(xf * 28.0 - 157.5, *COURT_Y)
    s["dist"] = np.hypot(s.cx, s.cy)
    s["zone"] = assign_zone_arr(s.cx.values, s.cy.values)
    s["player"] = s.player_surname.fillna("").str.title()
    return s


# ── team colours (BC Roma always gold; add others as needed) ──────────────────────
TEAM_COLORS = {"BC Roma": (GOLD, GOLD_EDGE), "Maxima Roma": ("#2b2b36", "#111118")}
_FALLBACK = [(BLUE, "#2f5f99"), (ORANGE, "#b46a3a"), (GREEN, "#1f6e3f")]


def team_color(team: str, idx: int = 0) -> tuple[str, str]:
    """(fill, edge) for a team; unknown teams cycle through blue/orange/green by idx."""
    return TEAM_COLORS.get(team, _FALLBACK[idx % len(_FALLBACK)])


# ── zone polygons (vector, smooth edges) ────────────────────────────────────────
def zone_polygons() -> dict:
    """The nine A–I zones as shapely polygons in the court frame (cm), mirroring assign_zone_arr exactly.

    Used to draw zone heatmaps as filled vector patches instead of a pixel grid.
    """
    from shapely.geometry import Point, Polygon, box
    from shapely.ops import unary_union

    court = box(-750, -157.5, 750, 1242.5)
    circ = lambda r: Point(0, 0).buffer(r, resolution=256)
    strips = unary_union([box(-750, -157.5, -CORNER_X, CORNER_Y), box(CORNER_X, -157.5, 750, CORNER_Y)])
    inside3 = circ(THREE_PT_RADIUS).difference(strips).intersection(court)
    three = court.difference(inside3)
    a = circ(RESTRICTED_R).intersection(court)
    short = circ(SHORT_RANGE_MAX).difference(circ(RESTRICTED_R)).intersection(court)
    mid = inside3.difference(circ(SHORT_RANGE_MAX))
    big = 5000
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


def draw_zone_fill(ax, pct_by_zone: dict, cmap, vmin=0, vmax=100, alpha=0.85, empty="#e6e6ee", zorder=1):
    """Fill the nine zones with cmap(pct) as smooth vector patches; zones missing from pct_by_zone get `empty`."""
    from matplotlib.colors import Normalize
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath
    norm = Normalize(vmin, vmax)
    for z, geom in zone_polygons().items():
        geoms = geom.geoms if hasattr(geom, "geoms") else [geom]
        color = cmap(norm(pct_by_zone[z])) if z in pct_by_zone else empty
        for g in geoms:
            verts, codes = [], []
            for ring in [g.exterior, *g.interiors]:
                pts = list(ring.coords)
                verts += pts; codes += [MPath.MOVETO] + [MPath.LINETO] * (len(pts) - 2) + [MPath.CLOSEPOLY]
            ax.add_patch(PathPatch(MPath(verts, codes), facecolor=color, edgecolor=color, linewidth=0.3, alpha=alpha, zorder=zorder))
