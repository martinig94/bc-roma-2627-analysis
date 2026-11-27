"""Key numbers of one opponent from the Hudl feed, on the layout of the site's page.

Usage:
    python -m hudl.key_numbers "Dolomiti Energia Trentino" --short Trento \
        --game "LBA round 10, home, Sun 6 Dec 2026" --game-short "LBA, Sun 6 Dec" \
        --game-date 2026-12-06 --out reports/hudl_api/trento_hudl_only

Writes ``key_numbers.md`` into the output folder. The page is built by
``notebooks/key_numbers.py`` (same markup, same style, same Season / Last 3 games
switch) from a folder that ``hudl.synergy_format`` writes in the format of the
Synergy pull. Three blocks that only Hudl data allows are added to "The detail":
the pick-and-roll coverage, the shot clock and the net rating on and off the court.
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys
from html import escape
from pathlib import Path

from hudl.client import ROOT
from hudl.opponent_report import (
    MIN_ON_OFF_MINUTES,
    REFERENCE_TEAM,
    SHOT_CLOCK_LABELS,
    Feed,
    coverage_table,
    lineup_stints,
    load_feed,
    on_off_table,
    shot_clock_table,
    short_names,
)
from hudl.pull import RAW_DIR
from hudl.synergy_format import KEY_LABELS, Matchup, write_key_numbers

sys.path.insert(0, str(ROOT / "notebooks"))
import key_numbers as site_page  # noqa: E402  (the notebooks folder is not a package)
from kn_css import CSS, JS  # noqa: E402

COMPETITION = "LBA"
INPUTS = RAW_DIR / "site_inputs"
SCREENS = "Screens defended per game"
LEAGUE = "League average"
INSERT_BEFORE = '<details class="fold"><summary>Drives and 1-on-1'
ON_OFF_GAP = 5.0  # on minus off beyond this is coloured
ADDED_PLAYS = ("catchdrive", "pop")  # Hudl play types the page has no key for
CATCH_AND_SHOOT = "spot"  # key of the page that holds the catch and shoot
# Sentences of the page that describe what Synergy logs, and what holds for Hudl.
REWORDED = (
    (
        "Synergy does not log the coverage (soft, show, switch, over, under), so this is by role. ",
        "By role; the coverages are in the next block. ",
    ),
    (
        "Synergy tags a drive only when the play ends in a shot (his or after his pass); "
        "it does not log whether the driver beats his defender.",
        "Hudl tags the drive on the shot of the player who drives; it does not log whether the "
        "driver beats his defender.",
    ),
    ("Tag = Synergy offensive role (season).", "Tag = his most used play type (season)."),
    ("Synergy game box scores", "Hudl box scores"),
    ("Synergy, ", "Hudl Instat, "),
    ("Synergy", "Hudl"),
)


def use_hudl_play_types() -> None:
    """Make the page show Hudl's play types as they are, none grouped.

    The page's spot-up items become catch and shoot, and the catch and drive and
    the pick and pop get their own play-type rows and style items.
    """
    label = KEY_LABELS[CATCH_AND_SHOOT].lower()
    site_page.PLAY[CATCH_AND_SHOOT] = KEY_LABELS[CATCH_AND_SHOOT]
    site_page.ITEMS[f"ppp_{CATCH_AND_SHOOT}"] = (f"Points per {label}", "{:.2f}", True)
    site_page.DEF_LABEL[f"ppp_{CATCH_AND_SHOOT}"] = f"Points allowed per {label}"
    style = [
        (f"{KEY_LABELS[CATCH_AND_SHOOT]} per 100 possessions", key, fmt) if key == f"per100_{CATCH_AND_SHOOT}" else (name, key, fmt)
        for name, key, fmt in site_page.STYLE
        if not any(key.endswith(added) for added in ADDED_PLAYS)
    ]
    site_page.PT = [key for key in site_page.PT if key not in ADDED_PLAYS] + list(ADDED_PLAYS)
    site_page.MATCHUP_PLAYS = [key for key in site_page.MATCHUP_PLAYS if key not in ADDED_PLAYS] + list(ADDED_PLAYS)
    for key in ADDED_PLAYS:
        site_page.PLAY[key] = KEY_LABELS[key]
        style.append((f"{KEY_LABELS[key]} per 100 possessions", f"per100_{key}", "{:.1f}"))
    site_page.STYLE = style


def meter(value: float, text: str, tone: str = "") -> str:
    """Return a value with the page's small bar (0 to 100)."""
    width = max(0.0, min(float(value), 100.0))
    return (
        f'<span class="mt"><span class="mbar"><i style="width:{width:.0f}%"></i></span>'
        f'<b class="val {tone}">{text}</b></span>'
    )


def fold(title: str, note: str, body: str) -> str:
    """Return one drop-down of "The detail" section."""
    return (
        f'<details class="fold"><summary>{escape(title)}</summary><div class="in">'
        f'<p class="note">{note}</p><div class="panel">{body}</div></div></details>'
    )


def coverage_fold(feed: Feed, matchup: Matchup, matches: list[str] | None) -> str:
    """Return the pick-and-roll coverage block: the team, the reference and the average."""
    season = coverage_table(feed.team_games, COMPETITION)
    own = season
    if matches is not None:
        own = coverage_table(feed.team_games[feed.team_games.match_id.isin(matches)], COMPETITION)
    coverages = season.drop(columns=SCREENS).loc[LEAGUE].sort_values(ascending=False).index
    rows = [
        [
            escape(coverage.capitalize()),
            meter(own.loc[matchup.team, coverage], f"{own.loc[matchup.team, coverage]:.0f}%"),
            f"{season.loc[LEAGUE, coverage]:.0f}%",
            f"{season.loc[matchup.reference, coverage]:.0f}%",
        ]
        for coverage in coverages
    ]
    rows.append(
        [SCREENS, f"<b>{own.loc[matchup.team, SCREENS]:.1f}</b>", f"{season.loc[LEAGUE, SCREENS]:.1f}",
         f"{season.loc[matchup.reference, SCREENS]:.1f}"]
    )
    header = ["Coverage", f"{matchup.short} use it", f"{COMPETITION} average", f"{matchup.reference} use it"]
    note = (
        "Share of the screens defended with each coverage, as Hudl tags it on every pick and roll. "
        f"{COMPETITION} average and {escape(matchup.reference)}: season."
    )
    return fold("Pick and roll: coverage (Hudl only)", note, site_page.table(header, rows))


def shot_clock_fold(feed: Feed, matchup: Matchup, matches: list[str] | None) -> str:
    """Return the shot clock block: when the plays end and what they yield."""
    plays = feed.plays
    table = shot_clock_table(plays, COMPETITION, matchup.team)
    own_rows = [matchup.team, f"{matchup.team} defense"]
    if matches is not None:
        scoped = shot_clock_table(plays[plays.match_id.isin(matches)], COMPETITION, matchup.team)
        table.loc[own_rows] = scoped.loc[own_rows]
    rows = []
    for label in SHOT_CLOCK_LABELS:
        cells = [escape(label)]
        for row in (*own_rows, "Competition"):
            share, points = table.loc[row, f"{label} share"], table.loc[row, f"{label} points per play"]
            cells += [meter(share, f"{share:.0f}%") if row in own_rows else f"{share:.0f}%", f"{points:.2f}"]
        rows.append(cells)
    header = ["Seconds into the possession", "Their offense", "Points per play", "Their defense",
              "Points per play", COMPETITION, "Points per play"]
    note = (
        "When shots, shooting fouls and turnovers come, counted from the start of the possession "
        f"(Hudl gives the clock of both). {COMPETITION}: season, all teams."
    )
    return fold("Shot clock: when the possessions end", note, site_page.table(header, rows))


def on_off_fold(feed: Feed, matchup: Matchup) -> str:
    """Return the block with the team net rating with each player on and off the court."""
    stints = lineup_stints(feed.events, feed.calendar, matchup.team)
    names = short_names(feed.events[feed.events.team_name == matchup.team].player_name)
    table = on_off_table(stints, names)
    table = table[table["Minutes on"] >= MIN_ON_OFF_MINUTES].sort_values("On minus off", ascending=False)
    rows = []
    for player, row in table.iterrows():
        difference = row["On minus off"]
        tone = "bad" if difference >= ON_OFF_GAP else "good" if difference <= -ON_OFF_GAP else "mid"
        rows.append(
            [escape(player), f"{int(row['Minutes on'])}", f"{row['Net on']:+.1f}", f"{row['Net off']:+.1f}",
             f'<b class="val {tone}">{difference:+.1f}</b>']
        )
    competitions = " and ".join(sorted(stints.competition.unique()))
    note = (
        "Team points scored minus allowed per 100 possessions with the player on and off the court. "
        f"Season, {competitions} together ({stints.match_id.nunique()} games), players with "
        f"{MIN_ON_OFF_MINUTES} minutes or more. Red = the team is {ON_OFF_GAP:.0f} points or more better "
        f"with him, green = {ON_OFF_GAP:.0f} or more worse. From the five-man units Hudl gives on every event."
    )
    header = ["Player", "Minutes", "Net rating on", "Net rating off", "On minus off"]
    return fold("On and off the court", note, site_page.table(header, rows))


def care_list(matchup: Matchup, data: dict, teams: int) -> list[str]:
    """Return the "Read with care" lines of the Hudl version of the page."""
    minimum = site_page.MIN
    return [
        f"Source: Hudl Instat feed, {COMPETITION} games of the 2026-27 season up to {data['last_date']}, read "
        f"{matchup.date}. Based solely on the data: no comments on plays. Same page as the Synergy one, built by "
        "the same code from Hudl data.",
        f"Ranks compare the {teams} teams of the {COMPETITION}, each on all of its games in it.",
        "Rank bars: the longer the bar, the higher the team ranks on that item (1st = best value for that team; for "
        "possessions per game and style items, 1st = most). On this page a long red bar is an item where the "
        "opponent ranks high.",
        "Last 3 games: only the three most recent games of BC Roma and of the opponent in this competition, ranked "
        "against the season values of every other team. Minimum samples are cut to 30% of the season ones.",
        "Play types are Hudl's own, none grouped: catch and shoot, catch and drive and pick and pop are separate "
        "play types, where Synergy has the spot-up and counts the pop with the roll man. Points per pick and roll = "
        "ball handler plus roll man, without the pick and pop. Possessions per play type are Hudl's own counts "
        "(turnovers included); points are the baskets and the free throws of the fouled shots.",
        "Who defends it for us: points per play on the shots, shooting fouls and turnovers where Hudl names him as "
        f"the defender (season: at least {minimum['season']['def']}). It does not adjust for who he guarded.",
        "At the rim = 2-point attempts within 6 ft of the basket, from the shot coordinates. Points in the paint = "
        "field goals only. Open = catch-and-shoot jump shots Hudl tags as uncontested. Drives = shots Hudl tags "
        "with a drive to the left or to the right.",
        f"Shot zones need {minimum['season']['zone']} shots to be colored ({minimum['last']['zone']} on the last 3 "
        "games). The zones are cut from the Hudl shot coordinates on the same 11 zones, with the paint split into "
        "the rim (6 ft) and the rest.",
        "Player minutes and offensive rebounds come from the Hudl box scores; jersey numbers from the LBA rosters. "
        "A player's turnover share is over the possessions he used: field-goal attempts, 0.44 of his free throws "
        "and turnovers.",
        "Not in Hudl either: box-outs, blow-bys, closeouts, crashing the glass, passes per chance.",
    ]


def render(feed: Feed, matchup: Matchup, game: dict[str, str]) -> str:
    """Return the markdown of the page (a heading and the page's HTML)."""
    use_hudl_play_types()
    folder = INPUTS / matchup.short.lower() / "key_numbers"
    last = write_key_numbers(feed, matchup, folder, game, site_page.shot_aggregates)
    data = site_page.load(folder)
    config, teams = data["cfg"], data["boards"]["season"].n
    scopes = []
    for scope, matches in (("season", None), ("last", last["opp"])):
        added = (
            coverage_fold(feed, matchup, matches)
            + shot_clock_fold(feed, matchup, matches)
            + on_off_fold(feed, matchup)
        )
        scopes.append(site_page.build_scope(scope, data).replace(INSERT_BEFORE, added + INSERT_BEFORE, 1))
    care = "".join(f"<li>{escape(line)}</li>" for line in care_list(matchup, data, teams))
    body = (
        f'<div class="kn2"><style>{CSS}</style>'
        f'<div class="topbar"><div class="note">{escape(matchup.short)} · {escape(config["game"])} · Hudl Instat · '
        f'{escape(config["author"])}, {escape(config["date"])}</div>'
        '<div class="scopes" role="group" aria-label="Games used">'
        '<button type="button" data-scope="season" aria-pressed="true">Season</button>'
        '<button type="button" data-scope="last" aria-pressed="false">Last 3 games</button></div></div>'
        + "".join(scopes)
        + f'<div class="readcare"><div class="h2">Read with care</div><ul>{care}</ul></div>'
        + f"<script>{JS}</script></div>"
    )
    for old, new in REWORDED:
        body = body.replace(old, new)
    body = re.sub(r"\n\s*\n", "\n", body)
    return f"# Key numbers\n\n{body}\n"


def main() -> None:
    """Write ``key_numbers.md`` for one opponent."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("team")
    parser.add_argument("--short", required=True, help="team name written on the page")
    parser.add_argument("--game", required=True, help='e.g. "LBA round 10, home, Sun 6 Dec 2026"')
    parser.add_argument("--game-short", required=True, help='e.g. "LBA, Sun 6 Dec"')
    parser.add_argument("--game-date", required=True, help="ISO date of the game")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--date", default=f"{datetime.date.today():%d %b %Y}")
    args = parser.parse_args()
    matchup = Matchup(args.team, args.short, REFERENCE_TEAM, COMPETITION, args.date)
    game = {"game": args.game, "game_short": args.game_short, "game_date": args.game_date}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "key_numbers.md").write_text(render(load_feed(), matchup, game), encoding="utf-8")


if __name__ == "__main__":
    main()
