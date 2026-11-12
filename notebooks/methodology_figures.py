"""Explanatory figures for the Methodology page, drawn with invented (dummy) data and the real plotting functions.

    python notebooks/methodology_figures.py

Writes into weekly/assets/methodology/ (copied to docs/assets by build_site.py):
  triangle_dummy.png     how to read the shot-selection triangles (tendency_triangles.py)
  playtype_dummy.png     how to read the field goals by play type figure (synergy_scouting_plots.py, 05_player_*)
  shottype_dummy.png     how to read the shot types figure (05c_player_*)
  energy_dummy.png       how to read the energy indices (energy_indices.py)
  energy_build_dummy.png how a score is built from its components and shrunk by minutes
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import synergy_scouting_plots as ssp
import energy_indices as ei
import tendency_triangles as tt

plt.rcdefaults()   # lba_style (imported by tendency_triangles) changes the global style: back to the defaults used by the scouting plots
plt.rcParams.update({'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': ssp.SPINE})

OUT = Path(__file__).resolve().parent.parent / "weekly" / "assets" / "methodology"
DUMMY_NOTE = "Invented numbers, only to explain how to read the figure."
NOTE_KW = dict(fontsize=8, color=ssp.INK_4)

# Dummy player: attempts and makes by play type, and by shot type inside the two main play types
PLAYTYPES = [("Spot up", 36, 14, .92), ("Pick and roll ball handler", 22, 10, 1.04), ("Transition", 12, 8, 1.31), ("Cut", 8, 6, 1.5), ("Isolation", 5, 2, .78)]
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
    """Field goals by play type, with invented numbers and callouts."""
    fig = plt.figure(figsize=(10, 5.2))
    ax = fig.add_axes([.24, .17, .5, .6])
    ssp.draw_playtype_bars(ax, PLAYTYPES, zoom=2)
    fig.text(.02, .94, "Player X: field goals by play type", fontsize=14, fontweight="bold")
    fig.text(.02, .89, "Dummy player, 83 field-goal attempts", fontsize=9, color=ssp.INK_3)
    notes = [(.79, .74, "Pale bar = attempts,\nsolid yellow = made"),
             (.79, .60, "Label: made/attempted, FG%\nand share of the player's\nattempts"),
             (.79, .46, "Diamond (top axis): points per\npossession of the play type,\ndotted line = 1.00"),
             (.79, .30,"Green outline and label: the two\nplay types with most attempts,\ndetailed in the shot types figure")]
    for x, y, t in notes:
        fig.text(x, y, t, fontsize=8.5, color=ssp.INK_2, va="center", bbox=dict(boxstyle="round,pad=.4", fc="#F7F7F7", ec="#DDDDDD"))
    fig.text(.02, .04, DUMMY_NOTE + " Rows are sorted by attempts. Free throws are excluded.", **NOTE_KW)
    fig.savefig(out / "playtype_dummy.png", dpi=150); plt.close(fig)


def shottype(out: Path) -> None:
    """Shot types within the two main play types of the dummy player, with invented numbers."""
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.4))
    fig.subplots_adjust(left=.14, right=.97, top=.68, bottom=.22, wspace=1.0)
    for ax, (play, rows) in zip(axs, SHOT_TYPES.items()):
        ssp.draw_shottype_panel(ax, rows, f"{play}\n({sum(r[1] for r in rows)} attempts; made/attempted)")
    fig.text(.02, .94, "Player X: shot types within his main play types", fontsize=14, fontweight="bold", color=ssp.DEEP)
    fig.text(.02, .87, "Deeper look at the field goals by play type: one panel for each of the two play types with the green outline.\n"
             "Pale bar = attempts, dark bar = made; the shot types add up to the attempts of the play type in the field goals by play type figure.",
             fontsize=9, color=ssp.INK_3, va="top")
    fig.text(.02, .04, DUMMY_NOTE + " This figure is drawn only for the players who together use 80% of the roster's possessions.", **NOTE_KW)
    fig.savefig(out / "shottype_dummy.png", dpi=150); plt.close(fig)


def energy(out: Path) -> None:
    """The real energy-index figure with invented players."""
    pl = pd.DataFrame({"player_surname": ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel", "India", "Juliet"],
                       "minutes": [210, 190, 150, 120, 90, 60, 40, 20, 15, 10],
                       "rim_activity_pct": [.15, .92, .55, .30, .80, .62, .45, .70, .52, .38], "high_pace_pct": [.85, .35, .97, .10, .70, .50, .25, .55, .48, .60]})
    ei.energy_figure("Dummy team", pl, "dummy", 7, "invented data", note="Invented numbers, only to explain how to read the figure.",
                     out=out, filename="energy_dummy.png")


def energy_build(out: Path) -> None:
    """How one high-pace score is built (average of z-scores) and how minutes shrink it towards 0."""
    comps = ["Drive\nfinishes", "Fast-break\nshots, assists", "Fouls\ndrawn", "Steals", "Early shots\n(within 8 s)"]
    z = np.array([2.1, 1.4, 0.6, -0.3, 1.9])
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.8), gridspec_kw={"width_ratios": [1.1, 1]})
    fig.subplots_adjust(left=.12, right=.97, top=.82, bottom=.22, wspace=.35)
    a.bar(range(len(z)), z, color=ei.MADE, alpha=.8)
    a.axhline(0, color=ssp.INK_6, lw=.8); a.axhline(z.mean(), color=ei.MISS, lw=1.6, ls="--")
    a.text(len(z) - .5, z.mean() + .08, f"average = raw score {z.mean():.2f}", ha="right", fontsize=8.5, color=ei.MISS, fontweight="bold")
    a.set_xticks(range(len(z))); a.set_xticklabels(comps, fontsize=7.5)
    a.set_ylabel("z-score vs league players (0 = league average)", fontsize=8.5)
    a.set_title("1. Each component is a z-score; the score is their average", fontsize=10, loc="left")
    m = np.linspace(0, 600, 300)
    b.plot(m, m / (m + ei.K_MIN), color=ssp.INK_2, lw=2)
    for (minutes, name), dx, dy in zip(((20, "20'"), (120, "120'"), (400, "400'")), (80, 70, 20), (-.08, -.15, -.25)):
        f = minutes / (minutes + ei.K_MIN)
        b.scatter([minutes], [f], color=ei.MISS, zorder=3)
        b.annotate(f"{name}: x {f:.2f}\nraw 1.00 -> {f:.2f}", (minutes, f), (minutes + dx, f + dy), fontsize=8, arrowprops=dict(arrowstyle="-", color=ssp.INK_6))
    b.set_xlabel("minutes played", fontsize=9); b.set_ylabel("weight kept: minutes / (minutes + 120)", fontsize=8.5)
    b.set_ylim(0, 1.05); b.set_title("2. Few minutes: the score is pulled towards 0", fontsize=10, loc="left")
    b.grid(color="#e5e7eb", lw=.6)
    fig.text(.02, .95, "High pace: from components to the score of a player", fontsize=13, fontweight="bold")
    fig.text(.02, .905, "Rim activity is built the same way (offensive rebounds, blocks, dunks, fouls drawn per 40 minutes).", fontsize=9, color=ssp.INK_3)
    fig.text(.02, .03, DUMMY_NOTE + " The shrunk score is then turned into the percentile among league players with 40+ minutes.", **NOTE_KW)
    fig.savefig(out / "energy_build_dummy.png", dpi=150); plt.close(fig)


def main() -> None:
    """Write the explanatory figures."""
    OUT.mkdir(parents=True, exist_ok=True)
    triangle(OUT); playtype(OUT); shottype(OUT); energy(OUT); energy_build(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
