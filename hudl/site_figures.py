"""Draw the figures of a Hudl-only opponent analysis with the site's own plot code.

Usage:
    python -m hudl.site_figures "Dolomiti Energia Trentino" --short Trento \
        --out reports/hudl_api/trento_hudl_only

Writes into the output folder the figures of the published analyses, drawn by the
same functions from Hudl data (``hudl.synergy_format`` writes their inputs):

  02_opponent_playtypes, 06_players_playtype_mix, 05_player_<name>_shot_profile,
  05c_player_<name>_shot_types    notebooks/synergy_scouting_plots.py
  16_defense_playtypes, 17_defenders_playtype_mix    notebooks/synergy_defense_plots.py
  15_energy_indices    notebooks/energy_indices.py (LBA play-by-play, not Hudl)

and two figures that only Hudl data allows, in the same colours:

  18_pnr_coverage    how the team defends the pick-and-roll, against the competition
  19_on_off          team net rating with each player on and off the court
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from hudl.client import ROOT
from hudl.opponent_report import (
    MIN_ON_OFF_MINUTES,
    REFERENCE_TEAM,
    Feed,
    coverage_table,
    lineup_stints,
    load_feed,
    on_off_table,
    short_names,
)
from hudl.pull import RAW_DIR, TOURNAMENTS
from hudl.synergy_format import (
    AUTHOR,
    DEFENSE_PLAY_TYPES,
    SEASON,
    Matchup,
    write_defense,
    write_scouting,
)

sys.path.insert(0, str(ROOT / "notebooks"))
import energy_indices  # noqa: E402  (the notebooks folder is not a package)
import synergy_defense_plots as defense_plots  # noqa: E402
import synergy_scouting_plots as scouting_plots  # noqa: E402
from imgopt import shrink_png  # noqa: E402

SOURCE = "Hudl Instat"
INPUTS = RAW_DIR / "site_inputs"
MAIN_COMPETITION = "LBA"
SCREENS = "Screens defended per game"
DEFENDER_XLABEL = "Plays that ended on the defender Hudl names (shot, shooting foul or turnover)"
ENERGY_SOURCE = "legabasket.it play-by-play"
UNUSED_FIGURES = ("03_playtype_ppp_ref_vs_opp.png",)  # drawn with the play types, not shown on the pages
EXTRA_PLAY_COLOR = "#C9A227"  # Hudl has one play type more than the palette has colours
TITLE_KW = {"fontsize": 13, "fontweight": "bold", "x": 0.02, "ha": "left"}


def footer(date: str, text: str) -> str:
    """Return the footer of a figure: author, date, source and ``text``."""
    return f"{AUTHOR} · {date} · Source: {SOURCE}, {SEASON} · {text}"


def save(fig: plt.Figure, path: Path) -> None:
    """Save ``fig`` like the site figures: 160 dpi, shrunk PNG, figure closed."""
    fig.savefig(path, dpi=160)
    shrink_png(path)
    plt.close(fig)


def scouting_figures(feed: Feed, matchup: Matchup, out: Path) -> None:
    """Draw the play types, the play-type mix by player and the field goals by player."""
    folder = INPUTS / matchup.short.lower() / "scouting"
    box = write_scouting(feed, matchup, folder)
    config = json.loads((folder / "config.json").read_text(encoding="utf-8"))
    context = scouting_plots.Ctx(folder, folder, config)
    context.plots = out
    context.foot_prefix = footer(matchup.date, "")
    scouting_plots.plot02_03(context)
    scouting_plots.plot06(context)
    scouting_plots.plot05(context, box)
    for name in UNUSED_FIGURES:
        (out / name).unlink(missing_ok=True)


def defense_figures(feed: Feed, matchups: list[Matchup], out: Path) -> None:
    """Draw the play types faced and the defender mix, one panel per competition."""
    defense_plots.PLAY_TYPES = DEFENSE_PLAY_TYPES
    defense_plots.PALETTE = [*scouting_plots.PALETTE, EXTRA_PLAY_COLOR]
    pulls = []
    for matchup in matchups:
        folder = INPUTS / matchup.short.lower() / "defense" / matchup.competition
        write_defense(feed, matchup, folder)
        pulls.append(defense_plots.load(folder))
    defense_plots.write_figures(pulls, out, matchups[0].date, source=SOURCE, defender_xlabel=DEFENDER_XLABEL)


def coverage_figure(feed: Feed, matchups: list[Matchup], out: Path) -> None:
    """Draw the pick-and-roll coverage mix of the team against each competition's average."""
    fig, axes = plt.subplots(1, len(matchups), figsize=(7.2 * len(matchups), 5.2), squeeze=False)
    for ax, matchup in zip(axes[0], matchups):
        table = coverage_table(feed.team_games, matchup.competition)
        shares = table.drop(columns=SCREENS)
        shares = shares[shares.loc["League average"].sort_values().index]
        rows = [(matchup.team, matchup.short, scouting_plots.NAVY)]
        if matchup.reference in shares.index:
            rows.append((matchup.reference, matchup.reference, scouting_plots.YELLOW))
        rows.append(("League average", f"{matchup.competition} average", scouting_plots.GREY))
        height = 0.8 / len(rows)
        positions = np.arange(shares.shape[1])
        for index, (team, label, color) in enumerate(rows):
            offset = (len(rows) - 1) / 2 - index
            bars = ax.barh(positions + offset * height, shares.loc[team], height=height, color=color, label=label)
            ax.bar_label(bars, labels=[f"{value:.0f}%" for value in shares.loc[team]], padding=3, fontsize=8)
        ax.set_yticks(positions, [name.capitalize() for name in shares.columns])
        ax.set_xlim(0, shares.to_numpy().max() * 1.15)
        ax.set_xlabel("Share of the pick-and-rolls defended (%)")
        ax.set_title(
            f"{matchup.competition}: {table.loc[matchup.team, SCREENS]:.1f} screens defended per game",
            fontsize=11, loc="left",
        )
        ax.legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle(f"{matchups[0].short} defense: how it covers the pick-and-roll", **TITLE_KW)
    fig.text(0.01, 0.008, footer(matchups[0].date, "coverage as tagged by Hudl on each screen"),
             fontsize=7, color=scouting_plots.INK_4)
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    save(fig, out / "18_pnr_coverage.png")


def on_off_figure(feed: Feed, matchup: Matchup, out: Path) -> None:
    """Draw the team's net rating with each player on the court minus off."""
    stints = lineup_stints(feed.events, feed.calendar, matchup.team)
    names = short_names(feed.events[feed.events.team_name == matchup.team].player_name)
    table = on_off_table(stints, names)
    rows = table[table["Minutes on"] >= MIN_ON_OFF_MINUTES].sort_values("On minus off")
    fig, ax = plt.subplots(figsize=(10, 0.46 * len(rows) + 2.2))
    bars = ax.barh(rows.index, rows["On minus off"], color=scouting_plots.NAVY, height=0.62)
    labels = [
        f"{difference:+.1f}  (on {on:+.1f}, off {off:+.1f}, {int(minutes)}')"
        for difference, on, off, minutes in zip(rows["On minus off"], rows["Net on"], rows["Net off"], rows["Minutes on"])
    ]
    ax.bar_label(bars, labels=labels, padding=4, fontsize=8)
    ax.axvline(0, color=scouting_plots.GREY, lw=1)
    ax.margins(x=0.45)
    ax.set_xlabel("Team net rating with the player on the court minus off (points per 100 possessions)")
    ax.set_title(
        f"{matchup.short}: net rating on and off the court (players with {MIN_ON_OFF_MINUTES}+ minutes)",
        fontsize=13, fontweight="bold", loc="left",
    )
    games = stints.match_id.nunique()
    fig.text(0.01, 0.008, footer(matchup.date, f"{games} games, {' and '.join(sorted(stints.competition.unique()))}"),
             fontsize=7, color=scouting_plots.INK_4)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    save(fig, out / "19_on_off.png")


def energy_figure(team: str, out: Path) -> None:
    """Draw the energy indices of ``team`` from the LBA play-by-play (not Hudl data)."""
    table = energy_indices.lba_table(None)
    table = table[table.minutes > 0]
    reference = table[table.minutes >= energy_indices.MIN_REF]
    table = energy_indices.percentiles(
        energy_indices.add_indices(table, reference), energy_indices.add_indices(table, reference)
    )
    players = table[table.team == team]
    energy_indices.energy_figure(
        team, players, "opponent", players.games.max(), ENERGY_SOURCE, out=out, filename="15_energy_indices.png"
    )


def main() -> None:
    """Write every figure of one opponent."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("team")
    parser.add_argument("--short", required=True, help="team name written in the titles")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--date", default=f"{datetime.date.today():%d %b %Y}")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    feed = load_feed()
    played = {c: set(feed.team_games[feed.team_games.competition == c].team) for c in TOURNAMENTS}
    matchups = [
        Matchup(args.team, args.short, REFERENCE_TEAM, competition, args.date)
        for competition in TOURNAMENTS
        if args.team in played[competition]
    ]
    main_matchup = next(m for m in matchups if m.competition == MAIN_COMPETITION)
    scouting_figures(feed, main_matchup, args.out)
    defense_figures(feed, matchups, args.out)
    coverage_figure(feed, matchups, args.out)
    on_off_figure(feed, main_matchup, args.out)
    energy_figure(args.team, args.out)


if __name__ == "__main__":
    main()
