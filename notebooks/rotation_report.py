"""Team rotation chart: who is on the court minute by minute, one panel per quarter (--competition EC: EuroCup games).

    python notebooks/rotation_report.py --team "BC Roma" --before 2026-10-27 --out reports/rotation_BC_Roma

Each quarter has five horizontal bars (lanes) of ten one-minute cells. For every minute of the game the
five players with the highest share of that minute on the court, averaged over the team's games of the
chosen competition, are shown; a player keeps his lane from one minute to the next when he stays in the
top five, so a change of name inside a lane is a substitution. Cell colour is that share: yellow = low,
dark green = high (a player who is on the court at that minute in every game). Overtimes are ignored.
Below the chart: every player who appears, with the minutes he is shown and his average playing time.
Samples are tiny early in the season: read the shares as tendencies.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import unicodedata

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LinearSegmentedColormap, Normalize

import lba_style
from game_report import PERIOD_LEN, stints
from lba_style import SUP_KW, TEXT, TEXT2, save_fig
from weekly_sections import ec_people
from weekly_config import ROOT

DATA = ROOT / "data"
LBA = "LBA"                            # --competition value and league label for the LBA
EUROCUP_CODE = "EC"                    # --competition value for the EuroCup
EUROCUP_LABEL = "EuroCup"              # league label for the EuroCup
EL_SOURCE_NOTE = "EuroLeague live API"  # chart stamp for EuroCup figures
EUROCUP_RAW = "eurocup_2026_raw.txt"   # EuroCup box scores, inside the data folder
QUARTERS = 4                           # overtimes are left out
MINUTES_PER_QUARTER = PERIOD_LEN // 60
LANES = 5                              # players on the court
SECS_PER_MIN = 60
SHARE_LOW, SHARE_HIGH = 0.2, 1.0       # colour scale: yellow at SHARE_LOW and below, dark green at 100%
CMAP = LinearSegmentedColormap.from_list("yellow_green", ["#f7dc3c", "#9bcf53", "#2e9e5b", "#0b5d2a"])
DARK_TEXT_BELOW = 0.55                 # share under which cells are light enough for dark text
CELL_EDGE = "#ffffff"
LANE_HEIGHT = 0.82
PANEL_INCHES_PER_UNIT = 0.41           # inches per lane-height unit of a quarter panel
OPTION_LONG_LABEL = 22                 # option labels at least this long get a smaller font
OPTIONS = 3                            # default number of next-most-frequent players shown under each minute
OPTION_GAP, OPTION_STEP, OPTION_HEIGHT = 0.3, 0.62, 0.52   # lane-height units: gap under the lanes, row pitch, cell height
FIG_WIDTH = 13
POSITIONS = ["PG", "SG", "SF", "PF", "C"]   # order of the bars at the start of every quarter
# The data only has coarse roles (LBA: Playmaker, Guardia, Ala, Centro and mixes; EuroCup: Guard, Forward, Center),
# so the five positions are an approximation: an "Ala"/Forward is a PF from this height, a EuroCup Guard a PG below the other one.
LBA_ROLE = {"Playmaker": "PG", "Play/Guardia": "PG/SG", "Guardia": "SG", "Guardia/Ala": "SG/SF", "Ala/Centro": "PF/C", "Centro": "C"}
EC_ROLE = {"Center": "C"}
FORWARD_PF_FROM_CM = 203               # "Ala" / "Forward" at least this tall is a PF, shorter a SF
GUARD_PG_BELOW_CM = 190                # EuroCup "Guard" shorter than this is a PG, taller a SG
LIST_COLUMNS = 3                       # columns of the player list under the chart


def minute_presence(box: pd.DataFrame, pbp: pd.DataFrame, team: str) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """Share of each game minute that every player spent on the court, averaged over the team's games.

    Args:
        box: Box scores of the competition.
        pbp: Play-by-play of the competition.
        team: Team name as in the data.

    Returns:
        ``(share, avg_min, n_games)``: `share` has one row per player and one column per game minute
        (0..39) with a value in 0..1 (the denominator is the number of games, so a player absent from a game counts 0);
        `avg_min` has the players' average minutes per game and the games they played.
    """
    games = box[box.team == team].game_id.unique()
    total = {}
    for game_id in games:
        player_stints, _ = stints(pbp[pbp.game_id == game_id].sort_values("seq"), box[box.game_id == game_id], team)
        for s in player_stints.itertuples():
            row = total.setdefault(s.player, {"secs": np.zeros(QUARTERS * MINUTES_PER_QUARTER), "games": set()})
            row["games"].add(game_id)
            for m in range(QUARTERS * MINUTES_PER_QUARTER):
                row["secs"][m] += max(0, min(s.end, (m + 1) * SECS_PER_MIN) - max(s.start, m * SECS_PER_MIN))
    n = len(games)
    share = pd.DataFrame({p: v["secs"] / SECS_PER_MIN / n for p, v in total.items()}).T
    played = pd.Series({p: len(v["games"]) for p, v in total.items()})
    # minutes per game include overtime-free regulation only, consistent with the chart
    avg = pd.DataFrame({"avg_min": share.sum(axis=1) * n / played, "games": played})
    return share, avg, n


def position_rank(label: str | None) -> int:
    """Sort key of a position label ("PG/SG" sorts as PG); players without a position go last."""
    return POSITIONS.index(label.split("/")[0]) if label else len(POSITIONS)


def load_positions(data: Path, team: str, competition: str, players: list[str]) -> dict[str, str]:
    """Position label (PG, SG, SF, PF, C or a mix such as "PG/SG") of each player, from the roster files.

    Args:
        data: Folder holding team_rosters.csv and eurocup/people.csv.
        team: Team name as in the data.
        competition: `LBA` or `EUROCUP_CODE`.
        players: Surnames as the chart shows them (title case).

    Returns:
        Surname -> label; players the roster files do not cover are left out.
    """
    out: dict[str, str] = {}
    if competition == LBA:
        r = pd.read_csv(data / "team_rosters.csv")
        r = r[r.team == team].assign(key=lambda d: d.surname.str.title()).drop_duplicates("key").set_index("key")
        for p in players:
            if p in r.index:
                role, ht = r.loc[p, "role"], r.loc[p, "height_cm"]
                if role == "Ala":
                    out[p] = "PF" if pd.notna(ht) and ht >= FORWARD_PF_FROM_CM else "SF"
                elif role in LBA_ROLE:
                    out[p] = LBA_ROLE[role]
    else:
        ec = ec_people(data, team)
        for p in players:
            norm = unicodedata.normalize("NFKD", p).encode("ascii", "ignore").decode().lower()
            info = ec.get(norm)
            if not info:
                continue
            ht = float(info["height"]) if info["height"] else None
            if info["pos"] == "Guard":
                out[p] = "PG" if ht and ht < GUARD_PG_BELOW_CM else "SG"
            elif info["pos"] == "Forward":
                out[p] = "PF" if ht and ht >= FORWARD_PF_FROM_CM else "SF"
            elif info["pos"] in EC_ROLE:
                out[p] = EC_ROLE[info["pos"]]
    return out


def assign_lanes(share: pd.DataFrame, positions: dict[str, str] | None = None) -> list[list[tuple[str, float]]]:
    """For each minute, five (player, share) pairs in lane order.

    The five players with the highest share are picked; anyone who was in the top five the minute before
    keeps his lane, newcomers take the free lanes (highest share first), so a name change in a lane is a switch.
    At the first minute of every quarter the five are instead ordered by position (PG, SG, SF, PF, C) when `positions` is given.
    """
    tie_break = share.sum(axis=1)   # equal shares: the player with more minutes overall goes first
    prev: list[str | None] = [None] * LANES
    out = []
    for i, m in enumerate(share.columns):
        top = share[m].to_frame("s").assign(t=tie_break).sort_values(["s", "t"], ascending=False).head(LANES).index.tolist()
        if positions is not None and i % MINUTES_PER_QUARTER == 0:
            prev = sorted(top, key=lambda p: (position_rank(positions.get(p)), top.index(p)))
        lanes: list[str | None] = [p if p in top else None for p in prev]
        for p in (p for p in top if p not in lanes):
            lanes[lanes.index(None)] = p
        out.append([(p, float(share.loc[p, m])) for p in lanes])
        prev = lanes
    return out


def next_options(share: pd.DataFrame, lanes: list[list[tuple[str, float]]], n: int) -> list[list[tuple[str, float]]]:
    """For each minute, the `n` most frequent players after the five shown (share above 0), best first."""
    tie_break = share.sum(axis=1)
    out = []
    for m, minute in zip(share.columns, lanes):
        rest = share[m].drop([p for p, _ in minute]).to_frame("s").assign(t=tie_break).sort_values(["s", "t"], ascending=False)
        out.append([(p, float(r.s)) for p, r in rest[rest.s > 0].head(n).iterrows()])
    return out


def text_color(value: float) -> str:
    """Dark text on light (yellow) cells, white on dark green."""
    return TEXT if value < DARK_TEXT_BELOW else "#ffffff"


def fig_rotation(share: pd.DataFrame, avg: pd.DataFrame, n_games: int, team: str, league: str, stamp: str, out: Path, options: int = OPTIONS,
                 positions: dict[str, str] | None = None, filename: str | None = None) -> Path:
    """Save the rotation chart of `team` into `out` and return its path.

    Args:
        share: Output of `minute_presence`.
        avg: Average minutes and games per player (same call).
        n_games: Games behind the shares.
        team: Team name, used in the title and file name.
        league: League label for the title.
        stamp: Period description for the title, e.g. "season to date".
        out: Folder that receives the PNG.
        options: Next-most-frequent players listed under each minute (0 = none).
        filename: PNG name; default `rotation_<team>_<league>.png`.
        positions: Surname -> position label from `load_positions`; shown next to the names and used to order the bars at each quarter start.
    """
    positions = positions or {}
    lanes = assign_lanes(share, positions)
    nxt = next_options(share, lanes, options)
    shown = sorted(share.index)
    minutes_shown = {p: sum(p == q for minute in lanes for q, _ in minute) for p in shown}   # minutes among the top five
    names = avg.loc[shown].sort_values("avg_min", ascending=False)
    rows = int(np.ceil(len(names) / LIST_COLUMNS))
    list_height = 0.32 * rows + 0.5
    norm = Normalize(SHARE_LOW, SHARE_HIGH)
    bottom = LANES + (OPTION_GAP + options * OPTION_STEP if options else 0)
    panel_height = PANEL_INCHES_PER_UNIT * bottom

    fig = plt.figure(figsize=(FIG_WIDTH, QUARTERS * panel_height + list_height + 1.3), layout="none")
    grid = fig.add_gridspec(QUARTERS + 1, 1, height_ratios=[panel_height] * QUARTERS + [list_height], hspace=0.28,
                          top=0.885, bottom=0.03, left=0.07, right=0.985)
    for q in range(QUARTERS):
        ax = fig.add_subplot(grid[q])
        for k in range(MINUTES_PER_QUARTER):
            for lane, (player, value) in enumerate(lanes[q * MINUTES_PER_QUARTER + k]):
                ax.barh(lane, 1, left=k, height=LANE_HEIGHT, color=CMAP(norm(value)), edgecolor=CELL_EDGE, linewidth=1.4)
                ax.text(k + 0.5, lane - 0.12, player, ha="center", va="center", fontsize=8.5, fontweight="bold", color=text_color(value))
                ax.text(k + 0.5, lane + 0.22, f"{value:.0%}" + (f" · {positions[player]}" if player in positions else ""), ha="center", va="center", fontsize=7, color=text_color(value))
            for i, (player, value) in enumerate(nxt[q * MINUTES_PER_QUARTER + k]):
                y = LANES + OPTION_GAP + i * OPTION_STEP - 0.05
                ax.barh(y, 1, left=k, height=OPTION_HEIGHT, color=CMAP(norm(value)), edgecolor=CELL_EDGE, linewidth=1.4)
                label = f"{player} {positions[player] + ' ' if player in positions else ''}{value:.0%}"
                ax.text(k + 0.5, y, label, ha="center", va="center", fontsize=7 if len(label) < OPTION_LONG_LABEL else 6, color=text_color(value))
        if options:
            ax.text(-0.08, LANES + OPTION_GAP + (options - 1) * OPTION_STEP / 2 - 0.05, "next\noptions", ha="right", va="center", fontsize=7.5, color=TEXT2)
        ax.set_xlim(0, MINUTES_PER_QUARTER); ax.set_ylim(bottom - 0.2, -0.55)
        ax.set_xticks(range(MINUTES_PER_QUARTER + 1)); ax.set_xticklabels([str(i) for i in range(MINUTES_PER_QUARTER + 1)], fontsize=8)
        ax.set_yticks([]); ax.set_ylabel(f"Q{q + 1}", rotation=0, fontsize=12, fontweight="bold", labelpad=22, va="center")
        ax.set_facecolor("white")
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        if q < QUARTERS - 1:
            ax.tick_params(axis="x", length=2)
    ax.set_xlabel("minute of the quarter (elapsed)", fontsize=9)

    cax = fig.add_axes([0.76, 0.915, 0.22, 0.008])
    cb = fig.colorbar(ScalarMappable(norm, CMAP), cax=cax, orientation="horizontal")
    cb.set_ticks([SHARE_LOW, 0.4, 0.6, 0.8, SHARE_HIGH]); cb.set_ticklabels([f"≤{SHARE_LOW:.0%}", "40%", "60%", "80%", "100%"])
    cb.ax.tick_params(labelsize=7.5, length=2); cb.outline.set_visible(False)
    fig.text(0.755, 0.919, "share of games on court", fontsize=8, color=TEXT2, ha="right", va="center")

    lax = fig.add_subplot(grid[QUARTERS]); lax.axis("off")
    lax.text(0, 1, "Players (average minutes per game in regulation, games played, minutes of the chart where he is among the five shown)",
             fontsize=9, fontweight="bold", color=TEXT, va="top", transform=lax.transAxes)
    for i, (player, r) in enumerate(names.iterrows()):
        col, row = divmod(i, rows)
        lax.text(col / LIST_COLUMNS, 0.82 - row * (0.82 / max(rows, 1)),
                 f"{player}{' (' + positions[player] + ')' if player in positions else ''}: {r.avg_min:.1f} min, {int(r.games)}/{n_games} g, {minutes_shown.get(player, 0)} of {QUARTERS * MINUTES_PER_QUARTER} min",
                 fontsize=8.5, color=TEXT2, va="top", transform=lax.transAxes)

    fig.suptitle(f"{team}: rotation by minute, {league} {stamp}  |  {n_games} games", x=0.01, ha="left", y=0.985, **SUP_KW)
    fig.text(0.01, 0.945, "Name = player most often on the court at that minute across the games; colour = share of games on court "
             "(yellow low, dark green high); a new name in a bar = substitution;\n"
             "positions (PG, SG, SF, PF, C) come from the roster role, so they are approximate, and order the bars at each quarter start;\n"
             "small rows below a quarter = next most frequent players at that minute.", fontsize=8.5, color=TEXT2, va="center")
    path = out / (filename or f"rotation_{team.replace(' ', '_')}_{league.replace(' ', '')}.png")
    save_fig(fig, path); plt.close(fig)
    return path


def load_competition(data: Path, competition: str, before: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame, str, str]:
    """Box scores and play-by-play of one competition, optionally only the games before a date (it also sets the chart stamp notes).

    Args:
        data: Data folder.
        competition: `LBA` or `EUROCUP_CODE`.
        before: ``YYYY-MM-DD``: keep only games before this date.

    Returns:
        ``(box, pbp, league label, period description for the titles)``.
    """
    league = LBA if competition == LBA else EUROCUP_LABEL
    if competition == EUROCUP_CODE:
        from matchup_report import parse_eurocup
        box = parse_eurocup(data / EUROCUP_RAW)[0]
        pbp = pd.read_csv(data / "eurocup" / "pbp.csv")
        lba_style.SOURCE_NOTE = EL_SOURCE_NOTE
    else:
        box = pd.read_csv(data / "box_scores.csv")
        pbp = pd.read_csv(data / "pbp.csv")
        box["date"] = box.match_datetime.str[:10]
    stamp = "season to date"
    if before:
        box = box[box.date < before]
        pbp = pbp[pbp.game_id.isin(box.game_id.unique())]
        lba_style.STAMP_NOTE = f"games before {pd.Timestamp(before):%d %b %Y} (pre-match snapshot)"
        stamp = f"games before {pd.Timestamp(before):%d %b %Y}"
    return box, pbp, league, stamp


def main() -> None:
    """Command-line entry point: print the minute-by-minute lanes and save the chart for each team."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--team", action="append", required=True)
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--out", default="reports")
    ap.add_argument("--before", default=None, help="YYYY-MM-DD: only games before this date")
    ap.add_argument("--options", type=int, default=OPTIONS, help="next-most-frequent players listed under each minute (0 = none)")
    ap.add_argument("--competition", choices=[LBA, EUROCUP_CODE], default=LBA, help="EC: EuroCup games (data/eurocup_2026_raw.txt and data/eurocup/pbp.csv)")
    a = ap.parse_args()
    box, pbp, league, stamp = load_competition(Path(a.data), a.competition, a.before)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for team in a.team:
        share, avg, n_games = minute_presence(box, pbp, team)
        print(f"\n=== {team}: {n_games} {league} games ===")
        positions = load_positions(Path(a.data), team, a.competition, list(share.index))
        lanes = assign_lanes(share, positions)
        nxt = next_options(share, lanes, a.options)
        for q in range(QUARTERS):
            minute = lanes[q * MINUTES_PER_QUARTER:(q + 1) * MINUTES_PER_QUARTER]
            print(f"Q{q + 1}")
            for lane in range(LANES):
                print("  " + " | ".join(f"{m[lane][0]:>10} {m[lane][1]:>4.0%}" for m in minute))
            for i in range(a.options):
                print("  next " + " | ".join(f"{(o[i][0] + ' ' + format(o[i][1], '.0%')) if len(o) > i else '':>10}" for o in nxt[q * MINUTES_PER_QUARTER:(q + 1) * MINUTES_PER_QUARTER]))
        print(fig_rotation(share, avg, n_games, team, league, stamp, out, a.options, positions))


if __name__ == "__main__":
    main()
