"""Player cards of one opponent from the Hudl feed: the players with the most shots.

Usage:
    python -m hudl.player_cards "Dolomiti Energia Trentino" --short Trento \
        --out reports/hudl_api/trento_hudl_only

Writes ``player_cards.md`` and three figures per player into the output folder.
Each card joins two existing looks:

  the Key numbers page (``notebooks/key_numbers.py``): the numbers of the player,
  the lines with what he does, the split bars and the court with his zones;

  the shot history of one player (``notebooks/synergy_player_history.py``, written
  for Bello): what he shoots out of the pick-and-roll and from which side
  (10e_player_<name>_pnr_shots), left or right of the floor
  (10g_player_<name>_left_right), drawn by that code from Hudl shots, with the
  competitions in the place of the seasons.

One figure is new, from tags that only Hudl has: the shooting hand, the shot
types, the drive direction and the dribble move (10h_player_<name>_hand_shot_types).
"""
from __future__ import annotations

import argparse
import datetime
import sys
from html import escape
from pathlib import Path
from urllib.parse import quote

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.patches import Patch

from hudl.client import ROOT
from hudl.opponent_report import Feed, feed_possessions, load_feed
from hudl.pull import TOURNAMENTS
from hudl.synergy_format import AUTHOR, SEASON, SECONDS, SYNERGY_RIM_X, jersey_numbers, synergy_shots

sys.path.insert(0, str(ROOT / "notebooks"))
import key_numbers as site_page  # noqa: E402  (the notebooks folder is not a package)
import synergy_player_history as history  # noqa: E402
from kn_css import CSS  # noqa: E402

PLAYERS = 8
MAIN_COMPETITION = "LBA"
PNR_PLAY = "P&R ball handler"
TO_BASKET = ("Lay up", "Dunk", "Reverse", "Alley oop")
SHOT_TYPES = {
    "Jumper": "Jumper",
    "Lay up": "Lay-up",
    "Floater": "Floater",
    "Dunk": "Dunk",
    "Hook": "Hook",
    "Tip in": "Tip-in",
    "Alley oop": "Alley-oop",
    "Reverse": "Reverse lay-up",
}
KINDS = [("All shots", None), ("Threes", "3PT"), ("Mid-range", "Mid-range"), ("Paint", "Paint")]
HAND_COLORS = {"Left": history.SIDE_COLORS["left"], "Right": history.SIDE_COLORS["right"], "Both": "#CCCCCC"}
COMPETITION_COLORS = {"EuroCup": "#4F7FBF", "LBA": "#1F3A5F"}
MIN_PNR_SHOTS = 10  # pick-and-roll shots for the pick-and-roll figure and line
MIN_ZONE_SHOTS = 5  # shots of a zone for it to be coloured on the court
MIN_DRIVES = 8
MIN_THREES = 20
MIN_RIM = 15
HIGH_THREE, LOW_THREE = 38, 30  # 3PT% shown as a strength / as a low number
HIGH_RIM, LOW_RIM = 65, 50
ONE_SIDED = 60  # share of threes from one side of the floor that gets a line
LEFT_HAND_SHARE = 15  # share of left-hand shots that gets a line
MIN_MOVES = 5
FIGURES = (
    ("10e", "pnr_shots", "Pick and roll: three, drive or mid-range, and from which side"),
    ("10g", "left_right", "Left or right of the floor"),
    ("10h", "hand_shot_types", "Shooting hand, shot types, drives and dribble moves (Hudl only)"),
)
PNR_INTRO = (
    "Every field-goal attempt where he is the P&R ball handler. Drive = lay-up, dunk, reverse or alley-oop "
    "(Hudl shot type); three = any three;\n"
    'mid-range = other two-point shots outside the paint; "Other" = jumpers, floaters and hooks in the paint. '
    "Side = left or right of the rim (offense's point of view) from the shot coordinates."
)
PNR_NOTE = (
    "Possessions ending in a pass, a turnover or a foul are not counted. One bar per competition in the place "
    "of the seasons; small samples per competition, side and type: tendencies, not rules."
)
LR_NOTE = (
    "Shots only. Side from the Hudl shot coordinates; a shot right under the basket counts on the side of its "
    "coordinate."
)


def use_hudl_history() -> None:
    """Make the shot-history figures read competitions as seasons, with Hudl's notes."""
    history.SEASON_COLORS = COMPETITION_COLORS
    history.LR_ROWS = [(" + ".join(TOURNAMENTS), None), (f"{MAIN_COMPETITION} only", (MAIN_COMPETITION,))]
    history.PNR_INTRO, history.PNR_NOTE, history.LR_NOTE = PNR_INTRO, PNR_NOTE, LR_NOTE


def team_shots(feed: Feed, team: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return the shots of the feed and of ``team`` in the columns both looks read.

    Returns:
        (every shot with its court zone of the Key numbers page, the shots of the
        team with the Hudl tags and the columns of the shot-history figures).
    """
    plays = feed.plays
    numbers = jersey_numbers(team, plays[plays.team_name == team].player_name)
    shots = synergy_shots(plays, numbers)
    shots["zone12"] = shots.apply(site_page.zone12, axis=1)
    tags = ["competition", "play", "hand", "shot_type", "drive", "dribble_move", "contesting", "teammate_name"]
    own = shots[shots.team == team].join(plays[tags])
    own["season"] = own.competition
    own["comp"] = own.competition
    own["game_id"] = own.gameId
    own["pts_att"] = own.pointsAttempted
    own["pt"] = np.where(own.play == PNR_PLAY, "P&R Ball Handler", own.play)
    own["zone"] = own.zoneName.map(history.zone)
    own["kind"] = np.where(own.pts_att == 3, "3PT", np.where(own.zone == "Paint", "Paint", "Mid-range"))
    own["description"] = np.where(own.shot_type.isin(TO_BASKET), "To Basket", "")
    own["side"] = np.where(own.x < SYNERGY_RIM_X, "right", "left")
    own["number"] = own.player.map(numbers)
    return shots, own


def share_label(frame: pd.DataFrame, total: int) -> tuple[float, str]:
    """Return the share of ``frame`` in ``total`` shots and its bar label."""
    share = 100 * len(frame) / total if total else 0.0
    made = int(frame.made.sum())
    field_goal = f"{100 * made / len(frame):.0f}% FG ({made}/{len(frame)})" if len(frame) else ""
    return share, f"{share:.0f}%\n{field_goal}"


def stacked_rows(ax: Axes, rows: list[tuple[str, pd.DataFrame]], column: str, colors: dict[str, str]) -> None:
    """Draw one stacked bar per row: the share of each value of ``column``, with FG%."""
    for index, (_, frame) in enumerate(rows):
        tagged = frame[frame[column].isin(colors)]
        left = 0.0
        for value, color in colors.items():
            share, label = share_label(tagged[tagged[column] == value], len(tagged))
            ax.barh(index, share, left=left, color=color, height=0.62)
            if share >= 14:
                dark = color == history.SIDE_COLORS["right"]
                ax.text(left + share / 2, index, label, ha="center", va="center", fontsize=8.5,
                        color="white" if dark else history.TEXT)
            left += share
    ax.set_yticks(range(len(rows)), [f"{name} ({len(frame)})" for name, frame in rows], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 50, 100], ["0%", "50%", "100%"], fontsize=8)
    ax.tick_params(axis="y", length=0)


def made_attempted(ax: Axes, counts: pd.DataFrame) -> None:
    """Draw made over attempted shots, one bar per row of ``counts`` (``fga``, ``fgm``)."""
    counts = counts.sort_values("fga")
    ax.barh(counts.index, counts.fga, color=history.SIDE_COLORS["right"], alpha=0.25, height=0.62)
    ax.barh(counts.index, counts.fgm, color=history.SIDE_COLORS["right"], height=0.62)
    top = counts.fga.max() if len(counts) else 1
    for position, row in enumerate(counts.itertuples()):
        ax.text(row.fga + top * 0.02, position, f"{int(row.fgm)}/{int(row.fga)}  {100 * row.fgm / row.fga:.0f}%",
                va="center", fontsize=8.5, color=history.TEXT2)
    ax.set_xlim(0, top * 1.3)
    ax.tick_params(axis="y", length=0, labelsize=9)
    ax.tick_params(axis="x", labelsize=8)


def fig_hand_shot_types(context: history.Ctx, player: str, shots: pd.DataFrame, games: pd.DataFrame) -> None:
    """Draw the shooting hand, the shot types, the drive direction and the dribble moves of a player."""
    own = shots[shots.player == player]
    fig, axes = plt.subplots(2, 2, figsize=(14, 6.8))
    fig.subplots_adjust(left=0.11, right=0.97, top=0.75, bottom=0.1, hspace=0.6, wspace=0.28)

    hand, types, drives, moves = axes.flat
    stacked_rows(hand, [(name, own if kind is None else own[own.kind == kind]) for name, kind in KINDS], "hand", HAND_COLORS)
    hand.set_title("Shooting hand", fontsize=10.5, loc="left", color=history.TEXT, pad=6)
    hand.legend(handles=[Patch(fc=color, label=f"{name} hand" if name != "Both" else "Both hands")
                         for name, color in HAND_COLORS.items()],
                ncol=3, fontsize=8, loc="lower right", bbox_to_anchor=(1, 1.0), frameon=False)

    by_type = own.assign(label=own.shot_type.map(SHOT_TYPES)).groupby("label").made.agg(fga="size", fgm="sum")
    made_attempted(types, by_type)
    types.set_title("Shot types (made / attempted, FG%)", fontsize=10.5, loc="left", color=history.TEXT, pad=6)

    driven = own[own.drive.notna()].assign(direction=lambda frame: frame.drive.str.split().str[-1])
    rows = [(name, driven if seasons is None else driven[driven.season.isin(seasons)]) for name, seasons in history.LR_ROWS]
    stacked_rows(drives, rows, "direction", {"Left": HAND_COLORS["Left"], "Right": HAND_COLORS["Right"]})
    drives.set_title("Drive direction", fontsize=10.5, loc="left",
                     color=history.TEXT, pad=6)
    drives.legend(handles=[Patch(fc=HAND_COLORS[name], label=f"Drives {name.lower()}") for name in ("Left", "Right")],
                  ncol=2, fontsize=8, loc="lower right", bbox_to_anchor=(1, 1.0), frameon=False)

    by_move = own[own.dribble_move.notna()].groupby("dribble_move").made.agg(fga="size", fgm="sum")
    made_attempted(moves, by_move)
    moves.set_title("Dribble move before the shot (made / attempted, FG%)", fontsize=10.5, loc="left",
                    color=history.TEXT, pad=6)

    fig.text(0.02, 0.955, f"{player}: shooting hand, shot types, drives and moves", fontsize=14, fontweight="bold")
    fig.text(0.02, 0.915, history.season_line(player, shots, games), fontsize=8.5, color=history.TEXT2, va="top")
    fig.text(0.02, 0.835, "Every field-goal attempt, all play types. Hand, shot type, drive direction and dribble move "
             "are the tags Hudl puts on each shot; the number in brackets is the number of shots of the row.",
             fontsize=8.5, color=history.TEXT2, va="top")
    fig.text(0.02, 0.04, "Shots only. A drive or a dribble move is tagged on part of the shots; small samples: "
             "tendencies, not rules.", fontsize=7, color=history.TEXT3)
    context.save(fig, figure_name("10h", player, "hand_shot_types"), "free throws excluded")


def figure_name(prefix: str, player: str, kind: str) -> str:
    """Return the file name of a figure of a player, as the shot-history code names it."""
    return f"{prefix}_player_{player.lower()}_{kind}.png"


def percent(made: float, attempts: float) -> float:
    """Return a percentage, 0 when there is no attempt."""
    return 100 * made / attempts if attempts else 0.0


def split(labels: list[tuple[str, float, str]], name: str) -> str:
    """Return a labelled split bar of the Key numbers page (label, share, colour class)."""
    captions = "".join(f"<span>{escape(label)} {share:.0f}%</span>" for label, share, _ in labels)
    parts = "".join(f'<i class="{color}" style="width:{share:.0f}%"></i>' for _, share, color in labels)
    return (f'<div class="split"><div class="lab">{captions}</div>'
            f'<div class="seg" role="img" aria-label="{escape(name)}">{parts}</div></div>')


def line(kind: str, text: str) -> str:
    """Return one line of a card: ``g`` what he does, ``r`` a low number, ``n`` a tendency."""
    icon = {"g": ("+", "Does"), "r": ("&minus;", "Below the others"), "n": ("&bull;", "Tendency")}[kind]
    return f'<div class="ln {kind}"><i aria-label="{icon[1]}">{icon[0]}</i><span>{text}</span></div>'


def card_lines(own: pd.DataFrame) -> str:
    """Return the lines of a card, one number per line, from the shots of the player."""
    threes, paint = own[own.kind == "3PT"], own[own.kind == "Paint"]
    rim = own[own.zone12 == "rim"]
    pnr = own[own.pt == "P&R Ball Handler"]
    driven = own[own.drive.notna()]
    lines = []
    three_pct, rim_pct = percent(threes.made.sum(), len(threes)), percent(rim.made.sum(), len(rim))
    if len(threes) >= MIN_THREES and three_pct >= HIGH_THREE:
        lines.append(line("g", f"Makes <b>{three_pct:.0f}%</b> of his threes ({int(threes.made.sum())}/{len(threes)})"))
    if len(rim) >= MIN_RIM and rim_pct >= HIGH_RIM:
        lines.append(line("g", f"Makes <b>{rim_pct:.0f}%</b> of his shots at the rim ({int(rim.made.sum())}/{len(rim)})"))
    if len(threes) >= MIN_THREES and three_pct < LOW_THREE:
        lines.append(line("r", f"Shoots <b>{three_pct:.0f}%</b> from three ({int(threes.made.sum())}/{len(threes)})"))
    if len(rim) >= MIN_RIM and rim_pct < LOW_RIM:
        lines.append(line("r", f"Makes <b>{rim_pct:.0f}%</b> of his shots at the rim ({int(rim.made.sum())}/{len(rim)})"))
    if len(driven) >= MIN_DRIVES:
        left = int((driven.drive == "Drives Left").sum())
        side, count = ("left", left) if left >= len(driven) - left else ("right", len(driven) - left)
        lines.append(line("n", f"Drives to his {side} on <b>{percent(count, len(driven)):.0f}%</b> of his drives "
                               f"({count} of {len(driven)})"))
    left_hand = percent((own.hand == "Left").sum(), len(own))
    paint_left = percent((paint.hand == "Left").sum(), len(paint))
    if left_hand >= LEFT_HAND_SHARE:
        lines.append(line("n", f"Shoots with his left hand on <b>{left_hand:.0f}%</b> of his shots"))
    elif len(paint) >= MIN_RIM:
        lines.append(line("n", f"Finishes with his left hand on <b>{paint_left:.0f}%</b> of his paint shots"))
    if len(threes) >= MIN_THREES:
        right = percent((threes.side == "right").sum(), len(threes))
        if max(right, 100 - right) >= ONE_SIDED:
            side = "right" if right >= 50 else "left"
            lines.append(line("n", f"Takes <b>{max(right, 100 - right):.0f}%</b> of his threes from the {side} of the floor"))
    if len(pnr) >= MIN_PNR_SHOTS:
        kinds = history.pnr_shot_type(pnr.description, pnr.pts_att, pnr.zone).value_counts()
        top = kinds.index[0]
        lines.append(line("n", f"Out of the pick and roll his first shot is the {top.lower()}: "
                               f"<b>{percent(kinds.iloc[0], len(pnr)):.0f}%</b> of {len(pnr)} shots"))
    moves = own.dribble_move.value_counts()
    if len(moves) and moves.iloc[0] >= MIN_MOVES:
        lines.append(line("n", f"Most used move before the shot: {moves.index[0].lower()}, <b>{moves.iloc[0]}</b> times"))
    made = own[own.made == 1]
    lines.append(line("n", f"<b>{percent(made.teammate_name.notna().sum(), len(made)):.0f}%</b> of his made shots "
                           "come after a pass (assisted)"))
    return "".join(lines)


def card(player: str, own: pd.DataFrame, box: pd.Series, league: dict[str, float], main_play: str, files: set[str],
         caption: str) -> str:
    """Return the card of one player: numbers, lines, split bars, court and figures."""
    games = max(int(box.games), 1)
    threes, rim = own[own.kind == "3PT"], own[own.zone12 == "rim"]
    driven = own[own.drive.notna()]
    three_pct = percent(threes.made.sum(), len(threes))
    tone = "bad" if len(threes) >= MIN_THREES and three_pct >= HIGH_THREE else (
        "good" if len(threes) >= MIN_THREES and three_pct < LOW_THREE else "")
    big = (
        f'<div class="big4"><div><b>{box.points / games:.1f}</b><span>Points</span></div>'
        f'<div><b>{len(own) / games:.1f}</b><span>Shots</span></div>'
        f'<div><b class="val {tone}">{three_pct:.0f}%</b><span>3PT% ({len(threes) / games:.1f})</span></div>'
        f'<div><b>{len(driven) / games:.1f}</b><span>Drives</span></div></div>'
    )
    rim_share, three_share = percent(len(rim), len(own)), percent(len(threes), len(own))
    hands = own[own.hand.isin(["Left", "Right"])]
    left_hand = percent((hands.hand == "Left").sum(), len(hands))
    left_side = percent((own.side == "left").sum(), len(own))
    splits = [
        split([("Rim", rim_share, "c-rim"), ("Mid", 100 - rim_share - three_share, "c-mid"),
               ("Three", three_share, "c-three")], "Shot mix"),
        split([("Left hand", left_hand, "c-left"), ("Right hand", 100 - left_hand, "c-right")], "Shooting hand"),
        split([("Left of the floor", left_side, "c-left"), ("Right of the floor", 100 - left_side, "c-right")],
              "Side of the floor"),
    ]
    if len(driven) >= MIN_DRIVES:
        drives_left = percent((driven.drive == "Drives Left").sum(), len(driven))
        splits.append(split([("Drives left", drives_left, "c-left"), ("Drives right", 100 - drives_left, "c-right")],
                            "Drive direction"))
    counts = own.groupby("zone12").made.agg(["size", "sum"])
    zones = {zone: [int(row["size"]), int(row["sum"])] for zone, row in counts.iterrows()}
    slug = player.lower().replace(" ", "-")
    court = site_page.zones_svg(zones, league, MIN_ZONE_SHOTS, slug, f"Shot zones of {player}", caption)
    folds = "".join(
        f'<details class="fold"><summary>{escape(title)}</summary><div class="in">'
        f'<img src="{quote(figure_name(prefix, player, kind))}" alt="{escape(player)}: {escape(title.lower())}" '
        'style="max-width:100%"></div></details>'
        for prefix, kind, title in FIGURES
        if figure_name(prefix, player, kind) in files
    )
    number = f"#{box.number} · " if isinstance(box.number, str) else ""
    return (
        f'<div class="sec" id="{slug}"><header><div class="eyebrow">{number}Main play: {escape(main_play)} · '
        f'{games} games · {box.seconds / 60 / games:.0f} minutes per game</div><div class="h2">{escape(player)}</div></header>'
        f'<div class="cols2"><div class="pc">{big}<div class="lines">{card_lines(own)}</div>{"".join(splits)}</div>'
        f'<div class="panel"><h3>Where he shoots</h3>{court}</div></div>'
        f'<div class="folds">{folds}</div></div>'
    )


def render(feed: Feed, team: str, short: str, out: Path, date: str) -> str:
    """Draw the figures of the players and return the markdown of the cards page."""
    use_hudl_history()
    shots, own = team_shots(feed, team)
    players = list(own.player.value_counts().head(PLAYERS).index)
    box_games = feed.player_games[(feed.player_games.team == team) & (feed.player_games[SECONDS] > 0)]
    games = box_games.rename(columns={"match_id": "game_id"}).assign(season=lambda f: f.competition, comp=lambda f: f.competition)
    box = pd.DataFrame(
        {
            "games": box_games.groupby("player").size(),
            "points": box_games.groupby("player").Points.sum(),
            "seconds": box_games.groupby("player")[SECONDS].sum(),
        }
    )
    box["number"] = own.groupby("player").number.first()
    main_play = feed_possessions(box_games, ["player"]).unstack().idxmax(axis=1)
    league = (100 * shots.groupby("zone12").made.mean()).to_dict()

    context = history.Ctx(out, AUTHOR, date)
    context.foot_prefix = f"{AUTHOR} · {date} · Source: Hudl Instat, {SEASON} (shot events, {' and '.join(TOURNAMENTS)}) · "
    files = set()
    for player in players:
        if (own[own.player == player].pt == "P&R Ball Handler").sum() >= MIN_PNR_SHOTS:
            history.fig_pnr(context, player, own, games)
            files.add(figure_name("10e", player, "pnr_shots"))
        history.fig_left_right(context, player, own, games)
        fig_hand_shot_types(context, player, own, games)
        files |= {figure_name("10g", player, "left_right"), figure_name("10h", player, "hand_shot_types")}

    competitions = " and ".join(TOURNAMENTS)
    caption = f"Hudl Instat, {competitions}, season, up to {feed.calendar.date.max()} · {AUTHOR} · {date}"
    index = " · ".join(f'<a href="#{p.lower().replace(" ", "-")}">{escape(p)}</a>' for p in players)
    cards = "".join(card(p, own[own.player == p], box.loc[p], league, main_play[p], files, caption) for p in players)
    care = [
        f"Source: Hudl Instat feed, every {competitions} game of {short} in the {SEASON} season up to "
        f"{feed.calendar.date.max()}, read {date}. Field-goal attempts only: possessions ending in a pass, a "
        "turnover or a foul are not counted. Based solely on the data: no comments on plays.",
        f"The {PLAYERS} players with the most field-goal attempts. Points, shots, threes and drives are per game.",
        "+ what he does, - where his numbers are low, a dot for a tendency. One number per line; small samples are "
        "left out (20 threes, 15 shots at the rim, 8 drives, 10 pick-and-roll shots).",
        "Hand, shot type, drive direction and dribble move are Hudl's tags on each shot. A drive is tagged on about "
        "1 shot in 6, so drives per game counts the shots taken after a drive, not every drive.",
        "Left and right are the offense's, seen from behind the offense facing the basket. Side of the floor comes "
        "from the shot coordinates.",
        f"Court: big number = FG% in the zone, small = share of his shots. Red = 3 points or more above the average "
        f"of the zone in {competitions}, green = 3 or more below, zones with fewer than {MIN_ZONE_SHOTS} shots are "
        "not colored. At the rim = within 6 ft of the basket.",
        "The figures in the drop-downs are drawn by the code of the Bello shot history, with one bar per competition "
        "in the place of the seasons: only this season is in the Hudl feed for these players.",
    ]
    body = (
        f'<div class="kn2"><style>{CSS}</style>'
        f'<div class="topbar"><div class="note">{escape(short)} · {competitions}, {SEASON} · Hudl Instat · '
        f"{escape(AUTHOR)}, {escape(date)}</div></div>"
        f'<p class="note">Jump to: {index}</p><div style="display:grid;gap:40px;margin:16px 0">{cards}</div>'
        '<div class="readcare"><div class="h2">Read with care</div><ul>'
        + "".join(f"<li>{escape(text)}</li>" for text in care)
        + "</ul></div></div>"
    )
    return f"# Player cards: {short}\n\n{body}\n"


def main() -> None:
    """Write ``player_cards.md`` and the figures of the players of one opponent."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("team")
    parser.add_argument("--short", required=True, help="team name written on the page")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--date", default=f"{datetime.date.today():%d %b %Y}")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    markdown = render(load_feed(), args.team, args.short, args.out, args.date)
    (args.out / "player_cards.md").write_text(markdown, encoding="utf-8")


if __name__ == "__main__":
    main()
