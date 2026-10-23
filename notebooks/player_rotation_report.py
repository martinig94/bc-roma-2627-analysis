"""Player rotation chart: when a player is on the court in each quarter, over the team's last games of a competition.

    python notebooks/player_rotation_report.py --team "Openjobmetis Varese" --player Hale --player Librizzi --out reports/rotation_test

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
from weekly_config import ROOT

DATA = ROOT / "data"
LBA = "LBA"                            # --competition value and league label for the LBA
EUROCUP_CODE = "EC"                    # --competition value for the EuroCup
EUROCUP_LABEL = "EuroCup"              # league label for the EuroCup
EL_SOURCE_NOTE = "EuroLeague live API"  # chart stamp for EuroCup figures
EUROCUP_RAW = "eurocup_2026_raw.txt"   # EuroCup box scores, inside the data folder
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


def on_court(box: pd.DataFrame, pbp: pd.DataFrame, team: str, player: str, games: list) -> np.ndarray:
    """Seconds-resolution presence of `player`: array (games, SECS) of 1 where he is on the court, 0 elsewhere."""
    out = np.zeros((len(games), SECS))
    for i, game_id in enumerate(games):
        stint, _ = stints(pbp[pbp.game_id == game_id].sort_values("seq"), box[box.game_id == game_id], team)
        for s in stint[stint.player == player].itertuples():
            out[i, int(max(s.start, 0)):int(min(s.end, SECS))] = 1
    return out


def fig_player(share: np.ndarray, n_games: int, player: str, team: str, league: str, dates: list[str], out: Path) -> Path:
    """Save the chart of one player into `out` and return its path.

    Args:
        share: Array (SECS,) with the share of games on court at each second of the game.
        n_games: Games behind the shares.
        player: Surname as the chart shows it.
        team: Team name, used in the title.
        league: League label for the title.
        dates: Dates of the games used, oldest first.
        out: Folder that receives the PNG.
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
    path = out / f"player_rotation_{team.replace(' ', '_')}_{player.replace(' ', '_')}_{league.replace(' ', '')}.png"
    save_fig(fig, path); plt.close(fig)
    return path


def main() -> None:
    """Command-line entry point: save one chart per requested player."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--team", required=True)
    ap.add_argument("--player", action="append", required=True, help="surname as in the box score (case-insensitive)")
    ap.add_argument("--games", type=int, default=LAST_GAMES, help="how many of the team's latest games to use")
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--out", default="reports")
    ap.add_argument("--before", default=None, help="YYYY-MM-DD: only games before this date")
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
    if a.before:
        box = box[box.date < a.before]
        lba_style.STAMP_NOTE = f"games before {pd.Timestamp(a.before):%d %b %Y} (pre-match snapshot)"
    games = last_games(box, a.team, a.games)
    pbp = pbp[pbp.game_id.isin(games)]
    dates = [str(box[box.game_id == g].date.iloc[0]) for g in games]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    names = {p.title(): p for p in box[(box.team == a.team) & (box.row_type == "player")].player_surname.dropna().unique()}
    for wanted in a.player:
        player = wanted.title()
        if player not in names:
            raise SystemExit(f"{wanted}: not in the {a.team} {league} box scores (players: {', '.join(sorted(names))})")
        share = on_court(box, pbp, a.team, player, games).mean(axis=0)
        print(f"{player}: {share.sum() / 60:.1f} min per game on average over {len(games)} games")
        print(fig_player(share, len(games), player, a.team, league, dates, out))


if __name__ == "__main__":
    main()
