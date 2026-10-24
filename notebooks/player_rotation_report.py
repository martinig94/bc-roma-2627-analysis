"""Player rotation chart: when a player is on the court in each quarter, over the team's last games of a competition.

    python notebooks/player_rotation_report.py --team "Openjobmetis Varese" --player Hale --player Librizzi --out reports/rotation_test
    python notebooks/player_rotation_report.py --team "Openjobmetis Varese" --by-quarter --out reports/rotation_test

One chart per player with one bar per quarter. The x axis is the clock of the quarter, from 10:00 (start) down to 0:00
(end). The colour at each second is the share of the team's last `--games` games (of the competition) in which the
player was on the court at that moment: dark green = in every game, white = in none. Games where the player did not
play count as "not on court". Overtimes are ignored. Samples are tiny: read the shares as tendencies.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LinearSegmentedColormap, Normalize

import lba_style
from game_report import PERIOD_LEN, stints
from lba_style import SUP_KW, TEXT, TEXT2, save_fig
from rotation_report import EUROCUP_CODE, LBA, OPTIONS, fig_rotation, load_competition, load_positions, minute_presence
from weekly_config import ROOT

DATA = ROOT / "data"
QUARTER_ROW_INCHES = 0.42              # inches per player bar in the one-chart-per-quarter version
QUARTERS = 4                           # overtimes are left out
SECS = QUARTERS * PERIOD_LEN
LAST_GAMES = 5
CMAP = LinearSegmentedColormap.from_list("white_green", ["#ffffff", "#b5dcae", "#5cb56a", "#2e9e5b", "#0b5d2a"])
BAR_EDGE = "#c9ccd6"
ROW_INCHES = 0.95
FIG_WIDTH = 12


def last_games(box: pd.DataFrame, team: str, n: int) -> list:
    """Game ids of the team's `n` most recent games in `box`, oldest first."""
    g = box[box.team == team].groupby("game_id").date.first().reset_index().sort_values(["date", "game_id"])
    return g.game_id.tolist()[-n:]


def team_on_court(box: pd.DataFrame, pbp: pd.DataFrame, team: str, games: list) -> dict[str, np.ndarray]:
    """Seconds-resolution presence of every player: surname -> array (games, SECS) of 1 where he is on the court, 0 elsewhere."""
    out: dict[str, np.ndarray] = {}
    for i, game_id in enumerate(games):
        stint, _ = stints(pbp[pbp.game_id == game_id].sort_values("seq"), box[box.game_id == game_id], team)
        for s in stint.itertuples():
            out.setdefault(s.player, np.zeros((len(games), SECS)))[i, int(max(s.start, 0)):int(min(s.end, SECS))] = 1
    return out


def fig_player(share: np.ndarray, n_games: int, player: str, team: str, league: str, dates: list[str], out: Path, filename: str | None = None) -> Path:
    """Save the chart of one player into `out` and return its path.

    Args:
        share: Array (SECS,) with the share of games on court at each second of the game.
        n_games: Games behind the shares.
        player: Surname as the chart shows it.
        team: Team name, used in the title.
        league: League label for the title.
        dates: Dates of the games used, oldest first.
        out: Folder that receives the PNG.
        filename: PNG name; default `player_rotation_<team>_<player>_<league>.png`.
    """
    fig, axes = plt.subplots(QUARTERS, 1, figsize=(FIG_WIDTH, ROW_INCHES * QUARTERS + 1.9), sharex=True,
                             gridspec_kw={"hspace": 0.35}, layout="none")
    fig.subplots_adjust(top=0.8, bottom=0.27, left=0.07, right=0.97)
    for q, ax in enumerate(axes):
        row = share[q * PERIOD_LEN:(q + 1) * PERIOD_LEN]
        ax.imshow(row[None, :], aspect="auto", cmap=CMAP, norm=Normalize(0, 1), interpolation="nearest",
                  extent=[PERIOD_LEN / 60, 0, 0, 1])   # clock runs 10 -> 0
        ax.set_xlim(PERIOD_LEN / 60, 0); ax.set_yticks([])
        ax.set_ylabel(f"Q{q + 1}", rotation=0, fontsize=12, fontweight="bold", labelpad=20, va="center")
        for side in ax.spines.values():
            side.set_color(BAR_EDGE)
        ax.set_xticks(range(PERIOD_LEN // 60, -1, -1)); ax.tick_params(axis="x", labelsize=9)
    axes[-1].set_xlabel("time left in the quarter (minutes)", fontsize=9)
    cax = fig.add_axes([0.35, 0.065, 0.3, 0.018])
    cb = fig.colorbar(ScalarMappable(Normalize(0, 1), CMAP), cax=cax, orientation="horizontal")
    cb.set_ticks([0, 0.25, 0.5, 0.75, 1]); cb.set_ticklabels(["0% (never)", "25%", "50%", "75%", "100% (always)"])
    cb.ax.tick_params(labelsize=8, length=2); cb.outline.set_edgecolor(BAR_EDGE)
    fig.text(0.5, 0.115, f"share of the last {n_games} games on the court", fontsize=8.5, color=TEXT2, ha="center")
    fig.suptitle(f"{player}: on the court by quarter, {team} {league}, last {n_games} games", x=0.01, ha="left", y=0.965, **SUP_KW)
    fig.text(0.01, 0.885, f"Games: {', '.join(dates)}. Overtimes not shown. Dark green = on the court in every game at that moment, white = in none.",
             fontsize=8.5, color=TEXT2, va="center")
    path = out / (filename or f"player_rotation_{team.replace(' ', '_')}_{player.replace(' ', '_')}_{league.replace(' ', '')}.png")
    save_fig(fig, path); plt.close(fig)
    return path


def fig_quarter(shares: dict[str, np.ndarray], q: int, team: str, league: str, dates: list[str], out: Path) -> Path:
    """Save the chart of quarter `q` (0-based) with one bar per player into `out` and return its path.

    Args:
        shares: Surname -> share of games on court at each second of the game (array of SECS).
        q: Quarter index, 0 to 3.
        team: Team name, used in the title.
        league: League label for the title.
        dates: Dates of the games used, oldest first.
        out: Folder that receives the PNG.
    """
    inside = {p: v[q * PERIOD_LEN:(q + 1) * PERIOD_LEN] for p, v in shares.items()}
    order = sorted((p for p in inside if inside[p].sum() > 0), key=lambda p: -inside[p].sum())   # most minutes in this quarter first
    n_games = len(dates)
    height = QUARTER_ROW_INCHES * len(order) + 1.7                       # inches: bars plus header and footer
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, height), layout="none")
    fig.subplots_adjust(top=1 - 0.8 / height, bottom=0.85 / height, left=0.14, right=0.97)
    img = np.vstack([inside[p] for p in order])
    ax.imshow(img, aspect="auto", cmap=CMAP, norm=Normalize(0, 1), interpolation="nearest", extent=[PERIOD_LEN / 60, 0, len(order), 0])
    for k in range(1, len(order)):
        ax.axhline(k, color=BAR_EDGE, lw=0.8)
    ax.set_xlim(PERIOD_LEN / 60, 0); ax.set_ylim(len(order), 0)
    ax.set_yticks(np.arange(len(order)) + 0.5)
    ax.set_yticklabels([f"{p}  ({inside[p].sum() / 60:.1f} min)" for p in order], fontsize=9.5)
    ax.set_xticks(range(PERIOD_LEN // 60, -1, -1)); ax.tick_params(axis="x", labelsize=9)
    ax.set_xlabel("time left in the quarter (minutes)", fontsize=9)
    for side in ax.spines.values():
        side.set_color(BAR_EDGE)
    cax = fig.add_axes([0.35, 0.2 / height, 0.3, 0.1 / height])
    cb = fig.colorbar(ScalarMappable(Normalize(0, 1), CMAP), cax=cax, orientation="horizontal")
    cb.set_ticks([0, 0.25, 0.5, 0.75, 1]); cb.set_ticklabels(["0% (never)", "25%", "50%", "75%", "100% (always)"])
    cb.ax.tick_params(labelsize=8, length=2); cb.outline.set_edgecolor(BAR_EDGE)
    fig.suptitle(f"{team} {league}: Q{q + 1} rotation, last {n_games} games", x=0.01, ha="left", y=1 - 0.1 / height, va="top", **SUP_KW)
    fig.text(0.01, 1 - 0.55 / height, f"Games: {', '.join(dates)}. Colour = share of those games with the player on the court at that moment "
             "(dark green always, white never). In brackets: average minutes in the quarter.", fontsize=8.5, color=TEXT2, va="center")
    path = out / f"quarter_rotation_{team.replace(' ', '_')}_Q{q + 1}_{league.replace(' ', '')}.png"
    save_fig(fig, path); plt.close(fig)
    return path


ROTATION_MINUTES_PNG = "13_rotation_by_minute.png"   # opponent page: who is on the court at each minute, with the next options
PLAYER_ROTATION_PREFIX = "14_player_rotation_"       # opponent individual page: one chart per player
TOP_PLAYERS = 10                                     # players with a chart: the ones with the most minutes in the games used


def opponent_figures(data: Path, team: str, date: str, competition: str, out: Path) -> list[Path]:
    """Save the rotation charts of an opponent into its analysis folder, from the games of `competition` before `date`.

    Writes `13_rotation_by_minute.png` (all those games) and `14_player_rotation_<Surname>.png` for the `TOP_PLAYERS`
    players with the most minutes in the last `LAST_GAMES` games. Nothing is written when the team has no game yet.

    Args:
        data: Data folder.
        team: Opponent name as in the data.
        date: ``YYYY-MM-DD`` of the game being prepared.
        competition: `LBA` or `EUROCUP_CODE`.
        out: Analysis folder.

    Returns:
        The paths written.
    """
    notes = (lba_style.SOURCE_NOTE, lba_style.STAMP_NOTE)
    try:
        box, pbp, league, stamp = load_competition(data, competition, date)
        if box[box.team == team].empty:
            return []
        share, avg, n_games = minute_presence(box, pbp, team)
        positions = load_positions(data, team, competition, list(share.index))
        paths = [fig_rotation(share, avg, n_games, team, league, stamp, out, OPTIONS, positions, ROTATION_MINUTES_PNG)]
        games = last_games(box, team, LAST_GAMES)
        on = team_on_court(box, pbp[pbp.game_id.isin(games)], team, games)
        dates = [str(box[box.game_id == g].date.iloc[0]) for g in games]
        for player in sorted(on, key=lambda p: -on[p].sum())[:TOP_PLAYERS]:
            paths.append(fig_player(on[player].mean(axis=0), len(games), player, team, league, dates, out,
                                    f"{PLAYER_ROTATION_PREFIX}{player.replace(' ', '_')}.png"))
        return paths
    finally:
        lba_style.SOURCE_NOTE, lba_style.STAMP_NOTE = notes


def main() -> None:
    """Command-line entry point: save one chart per requested player."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--team", required=True)
    ap.add_argument("--player", action="append", default=[], help="surname as in the box score (case-insensitive); one chart per player")
    ap.add_argument("--by-quarter", action="store_true", help="instead, one chart per quarter with a bar for every player of the team")
    ap.add_argument("--games", type=int, default=LAST_GAMES, help="how many of the team's latest games to use")
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--out", default="reports")
    ap.add_argument("--before", default=None, help="YYYY-MM-DD: only games before this date")
    ap.add_argument("--competition", choices=[LBA, EUROCUP_CODE], default=LBA, help="EC: EuroCup games (data/eurocup_2026_raw.txt and data/eurocup/pbp.csv)")
    a = ap.parse_args()
    box, pbp, league, _ = load_competition(Path(a.data), a.competition, a.before)
    games = last_games(box, a.team, a.games)
    pbp = pbp[pbp.game_id.isin(games)]
    dates = [str(box[box.game_id == g].date.iloc[0]) for g in games]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if not a.player and not a.by_quarter:
        raise SystemExit("give --player (one or more) and/or --by-quarter")
    on = team_on_court(box, pbp, a.team, games)
    if a.by_quarter:
        shares = {p: v.mean(axis=0) for p, v in on.items()}
        for q in range(QUARTERS):
            print(fig_quarter(shares, q, a.team, league, dates, out))
    names = {p.title(): p for p in box[(box.team == a.team) & (box.row_type == "player")].player_surname.dropna().unique()}
    for wanted in a.player:
        player = wanted.title()
        if player not in names:
            raise SystemExit(f"{wanted}: not in the {a.team} {league} box scores (players: {', '.join(sorted(names))})")
        share = on.get(names[player].title(), np.zeros((1, SECS))).mean(axis=0)
        print(f"{player}: {share.sum() / 60:.1f} min per game on average over {len(games)} games")
        print(fig_player(share, len(games), player, a.team, league, dates, out))


if __name__ == "__main__":
    main()
