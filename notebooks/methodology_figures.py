"""Explanatory figures for the Methodology page, drawn with invented (dummy) data and the real plotting functions.

    python notebooks/methodology_figures.py

Writes into weekly/assets/methodology/ (copied to docs/assets by build_site.py):
  triangle_dummy.png     how to read the shot-selection triangles (tendency_triangles.py)
  playtype_dummy.png     how to read plot 1, field goals by play type (synergy_scouting_plots.py, 05_player_*)
  shottype_dummy.png     how to read plot 2, shot types within the main play types (05c_player_*)
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import synergy_scouting_plots as ssp
import tendency_triangles as tt

plt.rcdefaults()   # lba_style (imported by tendency_triangles) changes the global style: back to the defaults used by the scouting plots
plt.rcParams.update({'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': ssp.SPINE})

OUT = Path(__file__).resolve().parent.parent / "weekly" / "assets" / "methodology"
DUMMY_NOTE = "Invented numbers, only to explain how to read the figure."
NOTE_KW = dict(fontsize=8, color=ssp.INK_4)

# Dummy player: attempts and makes by play type, and by shot type inside the two main play types
PLAYTYPES = [("Spot up", 36, 14), ("Pick and roll ball handler", 22, 10), ("Transition", 12, 8), ("Cut", 8, 6), ("Isolation", 5, 2)]
SHOT_TYPES = {"Spot up": [("Open, 3PT", 18, 8), ("Guarded, 3PT", 10, 2), ("To basket", 8, 4)],
              "Pick and roll ball handler": [("Dribble jumper, 3PT", 9, 3), ("To basket", 8, 5), ("Pull-up, mid-range", 5, 2)]}


def triangle(out: Path) -> None:
    """Triangle with ten invented games and three of them explained."""
    rng = np.random.default_rng(3)
    shares = rng.dirichlet([6, 5, 2.5], size=10)
    games = pd.DataFrame(shares, columns=list(tt.CORNERS))
    games["win"] = [True, True, False, True, False, True, False, True, True, False]
    avg = shares.mean(axis=0)
    fig = plt.figure(figsize=(11, 5.6))
    ax = fig.add_axes([.02, .1, .5, .8])
    tt.draw_triangle(ax, games, avg, "Ten invented games of one team")
    for i, label in ((0, "A"), (4, "B"), (7, "C")):
        x, y = tt.to_xy(shares[i:i + 1])[0]
        ax.annotate(label, (x, y), (x + .09, y + .07), fontsize=12, fontweight="bold", arrowprops=dict(arrowstyle="-", color=ssp.INK_4))
    lines = ["Each dot is one game of the team.", "",
             "Its position shows how the team's",
             "field-goal attempts of that game split between three kinds of shot:", "",
             "   - top, 3PT: three-point attempts", "   - bottom left, Paint: two-point attempts inside the lane",
             "   - bottom right, Mid-range: all other two-point attempts", "",
             "The closer a dot is to a corner, the larger that share.", "A dot in the middle is a game with an even split.", ""]
    for i, label in ((0, "A"), (4, "B"), (7, "C")):
        s = shares[i]
        lines.append(f"Game {label}: {s[0]:.0%} three-pointers, {s[1]:.0%} paint, {s[2]:.0%} mid-range")
    lines += ["", "Green dot = game won, red = lost. Black square = average of all shots.",
              "Dark area = where the densest 50% of the games sit, light = 80%:", "a small area means a stable shot selection from game to game."]
    fig.text(.55, .88, "\n".join(lines), fontsize=9.5, va="top", ha="left", color=ssp.INK, linespacing=1.5)
    fig.text(.02, .03, DUMMY_NOTE + " Same drawing function as the triangles of the individual tendencies page.", **NOTE_KW)
    fig.savefig(out / "triangle_dummy.png", dpi=150); plt.close(fig)


def playtype(out: Path) -> None:
    """Plot 1 with invented numbers and callouts."""
    fig = plt.figure(figsize=(10, 5.2))
    ax = fig.add_axes([.24, .2, .5, .6])
    ssp.draw_playtype_bars(ax, PLAYTYPES, zoom=2)
    fig.text(.02, .94, "Plot 1 · Player X: field goals by play type", fontsize=14, fontweight="bold")
    fig.text(.02, .89, "Dummy player, 83 field-goal attempts", fontsize=9, color=ssp.INK_3)
    notes = [(.79, .73, "Pale bar = attempts,\nsolid yellow = made"),
             (.79, .56, "Label: made/attempted, FG%\nand share of the player's\nattempts"),
             (.79, .36, "Green outline and label: the two\nplay types with most attempts,\nzoomed in plot 2")]
    for x, y, t in notes:
        fig.text(x, y, t, fontsize=8.5, color=ssp.INK_2, va="center", bbox=dict(boxstyle="round,pad=.4", fc="#F7F7F7", ec="#DDDDDD"))
    fig.text(.02, .04, DUMMY_NOTE + " Rows are sorted by attempts. Free throws are excluded.", **NOTE_KW)
    fig.savefig(out / "playtype_dummy.png", dpi=150); plt.close(fig)


def shottype(out: Path) -> None:
    """Plot 2 with invented numbers: the zoom on the two main play types of the dummy player."""
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.4))
    fig.subplots_adjust(left=.14, right=.97, top=.68, bottom=.22, wspace=1.0)
    for ax, (play, rows) in zip(axs, SHOT_TYPES.items()):
        ssp.draw_shottype_panel(ax, rows, f"{play}\n({sum(r[1] for r in rows)} attempts; made/attempted)")
    fig.text(.02, .94, "Plot 2 · Player X: shot types within his main play types", fontsize=14, fontweight="bold", color=ssp.DEEP)
    fig.text(.02, .87, "Deeper look at plot 1: one panel for each of the two play types with the green outline.\n"
             "Pale bar = attempts, dark bar = made; the shot types add up to the attempts of the play type in plot 1.",
             fontsize=9, color=ssp.INK_3, va="top")
    fig.text(.02, .04, DUMMY_NOTE + " Plot 2 is drawn only for the players who together use 80% of the roster's possessions.", **NOTE_KW)
    fig.savefig(out / "shottype_dummy.png", dpi=150); plt.close(fig)


def main() -> None:
    """Write the three explanatory figures."""
    OUT.mkdir(parents=True, exist_ok=True)
    triangle(OUT); playtype(OUT); shottype(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
