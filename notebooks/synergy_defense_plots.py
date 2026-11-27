"""Defense plots of one opponent from the Synergy defensive pull (synergy/defense_pull.js).

    python notebooks/synergy_defense_plots.py data/synergy/defense_<opponent>_<date>/seriea \
        data/synergy/defense_<opponent>_<date>/euroleague --out weekly/games/<date>

One panel per competition folder given (each holds situations.csv, defenders.csv and meta.json):

  16_defense_playtypes          play types faced: possessions, points allowed per possession, rank in the competition
  17_defenders_playtype_mix     possessions that ended on each defender, by play type

The defensive counterparts of figures 02 and 06 of synergy_scouting_plots.py, same colours. Descriptive only.
"""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes

from imgopt import shrink_png
from synergy_scouting_plots import INK_4, NAVY, PALETTE

ROOT = Path(__file__).resolve().parents[1]
AUTHOR = "Giulia Martini"
SOURCE = "Synergy Sports"                      # data source named in the footer
COMPETITION_NAMES = {"seriea": "Serie A", "euroleague": "Euroleague", "eurocup": "EuroCup"}   # folder name -> label
PLAY_TYPES = {"spot": "Spot up", "pnrbh": "P&R ball handler", "trans": "Transition", "roll": "P&R roll man", "cut": "Cut",
              "putback": "Put backs", "iso": "Isolation", "post": "Post-up", "handoff": "Handoff", "offscreen": "Off screen",
              "misc": "Miscellaneous"}           # situation / play_type key of the pull -> label
MIN_PLAYTYPE_POSS = 10      # play types faced fewer times are left off the play-type figure
MIN_DEFENDER_POSS = 15      # defenders with fewer possessions are left off the defender figure


def load(folder: Path) -> tuple[str, str, pd.DataFrame, pd.DataFrame]:
    """Read one competition folder of the defensive pull.

    Args:
        folder: Folder with situations.csv, defenders.csv and meta.json.

    Returns:
        (competition label, opponent name, play types faced by the opponent with ``ppp``, ``rank`` and ``teams``,
        defender rows by play type).
    """
    opp_id = json.loads((folder / "meta.json").read_text(encoding="utf-8"))["config"]["OPP"]
    sit = pd.read_csv(folder / "situations.csv")
    sit = sit[sit.situation.isin(PLAY_TYPES)].copy()
    sit["ppp"] = sit.pointMade / sit.possessions
    sit["rank"] = sit.groupby("situation").ppp.rank(method="min").astype(int)      # 1 = fewest points allowed
    sit["teams"] = sit.groupby("situation").team_id.transform("size")
    faced = sit[sit.team_id == opp_id]
    defenders = pd.read_csv(folder / "defenders.csv")
    return COMPETITION_NAMES.get(folder.name, folder.name), faced.name.iloc[0], faced, defenders[defenders.play_type.isin(PLAY_TYPES)]


def draw_playtypes_faced(ax: Axes, faced: pd.DataFrame, title: str) -> None:
    """Draw the possessions faced by play type, labelled with the points allowed per possession and its rank."""
    d = faced[faced.possessions >= MIN_PLAYTYPE_POSS].sort_values("possessions")
    ax.barh(d.situation.map(PLAY_TYPES), d.possessions, color=NAVY, height=.6)
    for i, r in enumerate(d.itertuples()):
        ax.text(r.possessions + d.possessions.max() * .015, i, f"{r.possessions}  ·  {r.ppp:.2f} PPP  ·  {r.rank} of {r.teams}",
                va="center", fontsize=8)
    ax.set_xlim(0, d.possessions.max() * 1.55)
    ax.set_title(title, fontsize=11, loc="left")
    ax.set_xlabel("Possessions faced (label: poss · points allowed per possession · rank, 1 = fewest)")


def draw_defender_mix(ax: Axes, defenders: pd.DataFrame, title: str, colors: dict[str, str]) -> None:
    """Draw the possessions that ended on each defender, stacked by play type."""
    pv = defenders.assign(player=defenders.name.str.split().str[-1]).pivot_table(
        index="player", columns="play_type", values="possessions", aggfunc="sum", fill_value=0)
    pv = pv[pv.sum(axis=1) >= MIN_DEFENDER_POSS]
    pv = pv.loc[pv.sum(axis=1).sort_values().index]
    left = np.zeros(len(pv))
    for key in [k for k in colors if k in pv]:
        ax.barh(pv.index, pv[key], left=left, color=colors[key], edgecolor="white", linewidth=1, label=PLAY_TYPES[key], height=.65)
        left += pv[key].to_numpy()
    ax.set_title(title, fontsize=11, loc="left")
    ax.set_xlabel("Possessions that ended on the defender (shot, turnover or free-throw trip)")


def write_figures(pulls: list[tuple[str, str, pd.DataFrame, pd.DataFrame]], out: Path, date: str, source: str = SOURCE,
                  defender_xlabel: str | None = None) -> None:
    """Write the play types faced and the defender mix figures, one panel per competition.

    Args:
        pulls: One ``load`` result per competition.
        out: Folder for the two PNGs.
        date: Date written in the footer.
        source: Data source named in the footer.
        defender_xlabel: X label of the defender figure, when the source counts something else than Synergy does.
    """
    team = pulls[0][1]
    foot = f"{AUTHOR} · {date} · Source: {source} · ranks within each competition"
    colors = dict(zip(PLAY_TYPES, PALETTE))

    fig, axs = plt.subplots(1, len(pulls), figsize=(7.2 * len(pulls), 5.6), squeeze=False)
    for ax, (comp, _, faced, _) in zip(axs[0], pulls):
        draw_playtypes_faced(ax, faced, f"{comp}, {int(faced.gp.max())} games")
    fig.suptitle(f"{team} defense: play types faced and what they yielded", fontsize=13, fontweight="bold", x=.02, ha="left")
    fig.text(.01, .008, f"{foot} · plays ≥{MIN_PLAYTYPE_POSS} poss", fontsize=7, color=INK_4)
    fig.tight_layout(rect=(0, .03, 1, .94))
    save(fig, out / "16_defense_playtypes.png")

    fig, axs = plt.subplots(1, len(pulls), figsize=(7.2 * len(pulls), 5.8), squeeze=False)
    for ax, (comp, _, _, defenders) in zip(axs[0], pulls):
        draw_defender_mix(ax, defenders, comp, colors)
        if defender_xlabel:
            ax.set_xlabel(defender_xlabel)
    axs[0][-1].legend(frameon=False, fontsize=7.5, ncol=2, loc="lower right")
    fig.suptitle(f"{team} defenders: possessions defended by play type (≥{MIN_DEFENDER_POSS} poss)", fontsize=13, fontweight="bold",
                 x=.02, ha="left")
    fig.text(.01, .008, foot, fontsize=7, color=INK_4)
    fig.tight_layout(rect=(0, .03, 1, .94))
    save(fig, out / "17_defenders_playtype_mix.png")


def main() -> None:
    """Write the two defense figures for the competition folders given on the command line."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folders", nargs="+", help="competition folders of one defensive pull")
    ap.add_argument("--out", required=True, help="folder for the two PNGs")
    ap.add_argument("--date", default=f"{datetime.date.today():%d %b %Y}")
    a = ap.parse_args()
    out = Path(a.out) if Path(a.out).is_absolute() else ROOT / a.out
    write_figures([load(Path(f) if Path(f).is_absolute() else ROOT / f) for f in a.folders], out, a.date)
    print("plots written to", out)


def save(fig: plt.Figure, path: Path) -> None:
    """Save ``fig`` to ``path``, shrink the PNG and close the figure."""
    fig.savefig(path, dpi=160)
    shrink_png(path)
    plt.close(fig)


if __name__ == "__main__":
    main()
