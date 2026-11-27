"""Write Hudl data in the folder formats read by the existing site scripts.

The scouting figures (``notebooks/synergy_scouting_plots.py``), the defense figures
(``notebooks/synergy_defense_plots.py``) and the Key numbers page
(``notebooks/key_numbers.py``) each read a folder of CSV files written from Synergy.
This module writes the same folders from the Hudl feed, so the same code draws the
figures and the page of both workflows.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from hudl.client import ROOT
from hudl.opponent_report import (
    BASKET_X_M,
    BASKET_Y_M,
    PAINT_HALF_WIDTH_M,
    feed_possessions,
    playtype_table,
    short_names,
    team_table,
)

AUTHOR = "Giulia Martini"
SEASON = "2026-27"
ROSTERS = ROOT / "data" / "team_rosters.csv"
SECONDS = "Seconds on the court"

# Hudl play type -> the name Synergy gives to the same play type, where there is one.
SCOUTING_NAMES = {
    "P&R ball handler": "P&R Ball Handler",
    "P&R roll man": "P&R Roll Man",
    "Pick and pop": "Pick and pop",
    "Catch and shoot": "Catch and shoot",
    "Catch and drive": "Catch and drive",
    "Transition": "Transition",
    "Isolation": "Isolation",
    "Cut": "Cut",
    "Off screen": "Off Screen",
    "Put-back": "Offensive Rebounds (Put Backs)",
    "Post-up": "Post-Up",
    "Handoff": "Handoffs",
}
OTHER_PLAYS = ("Handoffs", "Post-Up")  # pooled as "Other" by the play-type figure
SHOT_TYPE_LABELS = {
    "Lay up": "Lay-up",
    "Dunk": "Dunk",
    "Floater": "Floater",
    "Hook": "Hook",
    "Tip in": "Tip-in",
    "Alley oop": "Alley-oop",
    "Reverse": "Reverse lay-up",
}
# Play-type keys of the defense figures: Hudl's own play types, none grouped.
DEFENSE_KEYS = {
    "Catch and shoot": "catchshoot",
    "P&R ball handler": "pnrbh",
    "Transition": "trans",
    "Catch and drive": "catchdrive",
    "P&R roll man": "roll",
    "Pick and pop": "pop",
    "Cut": "cut",
    "Put-back": "putback",
    "Isolation": "iso",
    "Post-up": "post",
    "Handoff": "handoff",
    "Off screen": "offscreen",
}
DEFENSE_PLAY_TYPES = {
    "catchshoot": "Catch and shoot",
    "pnrbh": "P&R ball handler",
    "trans": "Transition",
    "catchdrive": "Catch and drive",
    "roll": "P&R roll man",
    "cut": "Cut",
    "putback": "Put backs",
    "iso": "Isolation",
    "post": "Post-up",
    "handoff": "Handoff",
    "offscreen": "Off screen",
    "pop": "Pick and pop",
}
# Play-type keys of the Key numbers page. Hudl's play types stay apart: the page's
# "spot" key holds the catch and shoot only, and two keys are added for the catch
# and drive and the pick and pop.
KEY_PLAYS = {
    "P&R ball handler": "pnrbh",
    "P&R roll man": "roll",
    "Pick and pop": "pop",
    "Transition": "trans",
    "Isolation": "iso",
    "Post-up": "post",
    "Catch and shoot": "spot",
    "Catch and drive": "catchdrive",
    "Put-back": "putback",
    "Cut": "cut",
    "Handoff": "handoff",
    "Off screen": "offscreen",
}
KEY_ORDER = (
    "pnrbh", "roll", "pop", "trans", "iso", "post", "spot", "catchdrive", "putback", "cut", "handoff", "offscreen",
)
KEY_LABELS = {
    "pnrbh": "P&R ball handler",
    "roll": "Roll man",
    "trans": "Transition",
    "iso": "Isolation",
    "post": "Post-up",
    "spot": "Catch and shoot",
    "catchdrive": "Catch and drive",
    "pop": "Pick and pop",
    "putback": "Put-back",
    "cut": "Cut",
    "handoff": "Handoff",
    "offscreen": "Off screen",
}
SHOT_COUNTS = (
    "shots", "rim_a", "rim_m", "paint_a", "paint_m", "mid_a", "mid_m", "three_a", "three_m",
    "cs3_a", "cs3_m", "jump_tag", "jump_open", "drive_fga", "drive_l", "drive_r",
)
COURT_LENGTH_M = 28.0
PAINT_DEPTH_M = 5.8
CORNER_DEPTH_M = 3.0  # the three-point line runs parallel to the sideline up to here
BASELINE_DEPTH_M = 3.3
TOP_HALF_WIDTH_M = 2.25
TENTHS_OF_FOOT_PER_M = 10 / 0.3048
ZONE_NAMES = {  # (area, side of the offense) -> Synergy zone
    ("corner3", "right"): "Z11-12-3pt",
    ("corner3", "left"): "Z11-16-3pt",
    ("wing3", "right"): "Z11-13-3pt",
    ("wing3", "left"): "Z11-15-3pt",
    ("top3", "right"): "Z11-14-3pt",
    ("top3", "left"): "Z11-14-3pt",
    ("paint", "right"): "Z11-01-2pt",
    ("paint", "left"): "Z11-01-2pt",
    ("base", "right"): "Z11-07-2pt",
    ("base", "left"): "Z11-11-2pt",
    ("wing", "right"): "Z11-08-2pt",
    ("wing", "left"): "Z11-10-2pt",
    ("top", "right"): "Z11-09-2pt",
    ("top", "left"): "Z11-09-2pt",
}
PAINT_ZONE = "Z11-01-2pt"
LAST_GAMES = 3
SYNERGY_RIM_X = 250  # x of the rim in Synergy shot coordinates; a smaller x is the offense's right
SYNERGY_UNITS_PER_M = 10 / 0.3048  # Synergy coordinates are tenths of a foot
FREE_THROW_WEIGHT = 0.44  # share of free throws that end a possession (usual estimate)


@dataclass(frozen=True)
class Matchup:
    """The two teams of a page and how they are written.

    Attributes:
        team: Opponent, as named in the Hudl feed.
        short: Opponent, as written in titles.
        reference: The team the analysis is written for.
        competition: Competition label of the feed.
        date: Date written in footers and captions.
    """

    team: str
    short: str
    reference: str
    competition: str
    date: str

    def label(self, team: str) -> str:
        """Return the name written for ``team``."""
        return self.short if team == self.team else team


def write_json(path: Path, content: dict) -> None:
    """Write ``content`` as indented JSON."""
    path.write_text(json.dumps(content, indent=1, default=str), encoding="utf-8")


def jersey_numbers(team: str, players: pd.Series) -> dict[str, str]:
    """Return the jersey number of each player from the LBA rosters, matched by name."""
    roster = pd.read_csv(ROSTERS, dtype=str)
    roster = roster[roster.team == team]
    numbers = {}
    for player in players.dropna().unique():
        same = roster[[player.casefold().endswith(s.casefold()) for s in roster.surname]]
        if len(same) > 1:
            same = same[same.name.str[0] == player[0]]
        if len(same) == 1:
            numbers[player] = same.number.iloc[0]
    return numbers


def scoped(frame: pd.DataFrame, competition: str) -> pd.DataFrame:
    """Return the rows of one competition."""
    return frame[frame.competition == competition]


# ---------------------------------------------------------------- scouting figures
def write_scouting(feed, matchup: Matchup, folder: Path) -> pd.DataFrame:
    """Write the folder read by ``synergy_scouting_plots`` and return the player table.

    Args:
        feed: Output of ``hudl.opponent_report.load_feed``.
        matchup: Teams, competition and date.
        folder: Folder to write (created).

    Returns:
        One row per player with ``surname``, ``POSS`` and ``FG MADE``, as the
        play-type figures by player expect.
    """
    folder.mkdir(parents=True, exist_ok=True)
    competition = matchup.competition
    team_games = scoped(feed.team_games, competition)
    teams = team_table(feed.team_games, competition)
    for side, points, efg, turnovers in (
        ("offense", "Points per 100 possessions", "Effective FG%", "Turnovers per 100 possessions"),
        ("defense", "Points allowed per 100 possessions", "Opponents' effective FG%",
         "Turnovers forced per 100 possessions"),
    ):
        pd.DataFrame(
            {
                "team": teams.index,
                "name": teams.index,
                "gp": teams.Games,
                "poss_pg": teams["Possessions per game"],
                "ppp": teams[points] / 100,
                "efg": teams[efg],
                "to": teams[turnovers],
            }
        ).to_csv(folder / f"league_team_{side}.csv", index=False)

    tables = {side: playtype_table(feed.plays, feed.team_games, competition, side) for side in ("team_name", "defense")}
    for name, side, team in (
        ("opp_playtypes_offense", "team_name", matchup.team),
        ("opp_playtypes_defense", "defense", matchup.team),
        ("ref_playtypes_offense", "team_name", matchup.reference),
    ):
        rows = tables[side].loc[team].reset_index()
        pd.DataFrame(
            {
                "play_type": rows.play.map(SCOUTING_NAMES),
                "poss": rows.plays.astype(int),
                "pts": rows.points.astype(int),
                "ppp": rows.ppp,
            }
        ).to_csv(folder / f"{name}.csv", index=False)

    own_games = scoped(feed.player_games, competition)
    own_games = own_games[(own_games.team == matchup.team) & (own_games[SECONDS] > 0)]
    names = short_names(own_games.player)
    own_plays = scoped(feed.plays, competition)
    own_plays = own_plays[own_plays.team_name == matchup.team]
    possessions = feed_possessions(own_games, ["player"])
    points = own_plays[own_plays.play.notna()].groupby(["player_name", "play"]).points.sum()
    mix = pd.DataFrame({"poss": possessions, "pts": points.reindex(possessions.index).fillna(0)})
    mix = mix[mix.poss > 0].reset_index()
    mix["full"] = mix.player
    mix["player"] = mix.player.map(names)
    mix["play_type"] = mix.play.map(SCOUTING_NAMES)
    mix["ppp"] = (mix.pts / mix.poss).round(3)
    mix[["player", "play_type", "poss", "pts", "ppp", "full"]].to_csv(
        folder / "opp_players_playtypes_offense.csv", index=False
    )

    shots = own_plays[own_plays.is_fga].copy()
    shots["player"] = shots.player_name.map(names)
    category = shots.play.map(SCOUTING_NAMES)
    shots["category"] = category.where(~category.isin(OTHER_PLAYS)).fillna("Other")
    jumper = shots.shot_type == "Jumper"
    contest = shots.contesting.str.lower().fillna("no contest tag")
    shots["shot_type_label"] = np.where(
        jumper, "Jumper, " + contest, shots.shot_type.map(SHOT_TYPE_LABELS).fillna("Other")
    ) + np.where(shots.is_three, ", 3PT", "")
    by_play = shots.groupby(["player", "category"]).made.agg(fga="size", fgm="sum").reset_index()
    by_play.insert(1, "dimension", "play_type")
    by_play[["player", "dimension", "category", "fgm", "fga"]].to_csv(
        folder / "opp_players_fg_by_zone_and_playtype.csv", index=False
    )
    by_type = shots.groupby(["player", "category", "shot_type_label"]).made.agg(fga="size", fgm="sum")
    by_type.reset_index().rename(columns={"category": "play_type", "shot_type_label": "shot_type"}).to_csv(
        folder / "opp_players_shottype_within_playtype.csv", index=False
    )

    games = {team: int(teams.Games[team]) for team in (matchup.team, matchup.reference)}
    write_json(
        folder / "config.json",
        {
            "opponent": {"name": matchup.short, "abbr": matchup.short[:3].upper(), "games": games[matchup.team]},
            "reference": {
                "name": matchup.reference,
                "abbr": "".join(w[0] for w in matchup.reference.split()).upper(),
                "games": games[matchup.reference],
            },
            "league": competition,
            "competition": competition,
            "league_games_each": int(teams.Games.max()),
            "season": SEASON,
            "date": matchup.date,
            "author": AUTHOR,
        },
    )
    box = pd.DataFrame(
        {"POSS": mix.groupby("player").poss.sum(), "FG MADE": shots.groupby("player").made.sum()}
    ).fillna(0).astype(int)
    return box.rename_axis("surname").reset_index()


# ----------------------------------------------------------------- defense figures
def write_defense(feed, matchup: Matchup, folder: Path) -> None:
    """Write one competition folder read by ``synergy_defense_plots.load``."""
    folder.mkdir(parents=True, exist_ok=True)
    competition = matchup.competition
    games = team_table(feed.team_games, competition).Games
    faced = playtype_table(feed.plays, feed.team_games, competition, "defense").reset_index()
    faced["situation"] = faced.play.map(DEFENSE_KEYS)
    situations = faced.groupby(["team", "situation"], as_index=False)[["plays", "points"]].sum()
    pd.DataFrame(
        {
            "team_id": situations.team,
            "name": situations.team.map(matchup.label),
            "situation": situations.situation,
            "gp": situations.team.map(games),
            "possessions": situations.plays.astype(int),
            "pointMade": situations.points.astype(int),
        }
    ).to_csv(folder / "situations.csv", index=False)

    plays = scoped(feed.plays, competition)
    defended = plays[(plays.defense == matchup.team) & plays.opponent_name.notna() & plays.play.notna()]
    names = {full: short.replace(" ", "") for full, short in short_names(defended.opponent_name).items()}
    defenders = (
        defended.assign(name=defended.opponent_name.map(names), play_type=defended.play.map(DEFENSE_KEYS))
        .groupby(["name", "play_type"])
        .size()
        .rename("possessions")
    )
    defenders.reset_index().to_csv(folder / "defenders.csv", index=False)
    write_json(folder / "meta.json", {"config": {"OPP": matchup.team}})


# -------------------------------------------------------------------- Key numbers
def synergy_shots(plays: pd.DataFrame, numbers: dict[str, str]) -> pd.DataFrame:
    """Return the field-goal attempts as rows of a Synergy shot list.

    The description holds what ``key_numbers.parse_shot`` reads: the shooter, his
    drive, catch-and-shoot jumpers ("No Dribble Jumper") and their contest tag
    ("Open" for uncontested, "Guarded" for contested).
    """
    shots = plays[plays.is_fga].copy()
    lateral = shots.pos_y - BASKET_Y_M
    depth = COURT_LENGTH_M - shots.pos_x
    central = lateral.abs() <= TOP_HALF_WIDTH_M
    in_paint = (lateral.abs() <= PAINT_HALF_WIDTH_M) & (depth <= PAINT_DEPTH_M)
    area = np.where(
        shots.is_three,
        np.select([depth < CORNER_DEPTH_M, central], ["corner3", "top3"], "wing3"),
        np.select([in_paint, central, depth < BASELINE_DEPTH_M], ["paint", "top", "base"], "wing"),
    )
    side = np.where(lateral > 0, "left", "right")
    jumper = shots.shot_type == "Jumper"
    catch_and_shoot = jumper & (shots.playtype == "Catch and shoot")
    contest = shots.contesting.map({"Uncontested": " > Open", "Contested": " > Guarded"}).fillna("")
    description = (
        shots.player_name.map(numbers).fillna("0") + " " + shots.player_name
        + (" > " + shots.drive).fillna("")
        + np.select([catch_and_shoot, jumper], [" > No Dribble Jumper", " > Dribble Jumper"], "")
        + contest.where(catch_and_shoot, "")
    )
    return pd.DataFrame(
        {
            "gameId": shots.match_id,
            "gameDate": shots.date,
            "player": shots.player_name,
            "defender": shots.opponent_name,
            "team": shots.team_name,
            "defense": shots.defense,
            "pointsAttempted": np.where(shots.is_three, 3, 2),
            "made": shots.made.astype(int),
            "zoneName": [ZONE_NAMES[key] for key in zip(area, side)],
            "x": SYNERGY_RIM_X - lateral * SYNERGY_UNITS_PER_M,
            "shotDistance": (
                np.hypot(shots.pos_x - BASKET_X_M, lateral) * TENTHS_OF_FOOT_PER_M
            ).round(0),
            "description": description,
        }
    )


def side_games(feed, competition: str) -> pd.DataFrame:
    """Return one row per team, game and side (``off`` or ``def``) with the team totals.

    A ``def`` row holds what the team allowed. ``defreb`` is the other team's
    defensive rebounds on an ``off`` row and the team's own on a ``def`` row, so
    offreb / (offreb + defreb) is the offensive rebound percentage of the row.
    """
    games = scoped(feed.team_games, competition)
    plays = scoped(feed.plays, competition)
    tagged = plays[plays.play.notna()].assign(key=lambda frame: frame.play.map(KEY_PLAYS))
    frames = []
    for side, prefix, other, team_column in (("off", "", "opp_", "team_name"), ("def", "opp_", "", "defense")):
        frame = pd.DataFrame(
            {
                "team_id": games.team,
                "name": games.team,
                "side": side,
                "game_id": games.match_id,
                "date": games.date.astype(str),
                "vs": games.opponent,
                "gp": 1,
                "possessions": games[f"{prefix}Possessions"],
                "pointMade": games[f"{prefix}Points"],
                "turnover": games[f"{prefix}Turnovers"],
                "shotAttempt": games[f"{prefix}Field goals attempted"],
                "shotMade": games[f"{prefix}Field goals made"],
                "shot3Attempt": games[f"{prefix}3-pt field goals attempted"],
                "shot3Made": games[f"{prefix}3-pt field goals made"],
                "ftAttempt": games[f"{prefix}Free throws attempted"],
                "offreb": games[f"{prefix}Offensive rebounds"],
                "defreb": games[f"{other}Defensive rebounds"],
                "assist": games[f"{prefix}Assists"],
            }
        ).set_index(["team_id", "game_id"], drop=False)
        possessions = feed_possessions(games, ["team", "match_id"], prefix)
        possessions = possessions.groupby([*possessions.index.names[:2], possessions.index.get_level_values(2).map(KEY_PLAYS)]).sum()
        points = tagged.groupby([team_column, "match_id", "key"]).points.sum()
        for label, values in (("poss", possessions), ("pts", points)):
            wide = values.unstack().reindex(index=frame.index, columns=list(KEY_ORDER)).fillna(0)
            frame = frame.join(wide.add_prefix(f"{label}_"))
        tagged_columns = {label: [f"{label}_{key}" for key in KEY_ORDER] for label in ("poss", "pts")}
        frame["poss_misc"] = (frame.possessions - frame[tagged_columns["poss"]].sum(axis=1)).clip(lower=0)
        frame["pts_misc"] = (frame.pointMade - frame[tagged_columns["pts"]].sum(axis=1)).clip(lower=0)
        frames.append(frame.reset_index(drop=True))
    return pd.concat(frames, ignore_index=True)


def player_rows(feed, competition: str, team: str, matches: list[str], numbers: dict[str, str]) -> pd.DataFrame:
    """Return one row per player of ``team`` over ``matches``, as ``players.csv`` of the pull.

    ``possessions`` is the usual estimate (field-goal attempts, 0.44 of the free
    throws and the turnovers): Hudl's play-type counts leave out part of the turnovers.
    """
    games = scoped(feed.player_games, competition)
    games = games[(games.team == team) & games.match_id.isin(matches) & (games[SECONDS] > 0)]
    plays = scoped(feed.plays, competition)
    plays = plays[(plays.team_name == team) & plays.match_id.isin(matches) & plays.play.notna()]
    total = games.groupby("player").sum(numeric_only=True)
    rows = pd.DataFrame(
        {
            "gp": games.groupby("player").size(),
            "pointMade": total.Points,
            "turnover": total.Turnovers,
        }
    )
    possessions = feed_possessions(games, ["player"])
    possessions = possessions.groupby(["player", possessions.index.get_level_values(1).map(KEY_PLAYS)]).sum()
    points = plays.assign(key=plays.play.map(KEY_PLAYS)).groupby(["player_name", "key"]).points.sum()
    for label, values in (("poss", possessions), ("pts", points)):
        wide = values.unstack().reindex(index=rows.index, columns=list(KEY_ORDER)).fillna(0)
        rows = rows.join(wide.add_prefix(f"{label}_"))
    used = total["Field goals attempted"] + FREE_THROW_WEIGHT * total["Free throws attempted"] + total.Turnovers
    rows["possessions"] = used.round(0)
    rows.insert(0, "number", rows.index.map(numbers))
    return rows.rename_axis("name").reset_index()


def defender_rows(feed, competition: str, team: str, matches: list[str]) -> pd.DataFrame:
    """Return the plays that ended on each defender of ``team``, as ``defenders.csv``."""
    plays = scoped(feed.plays, competition)
    plays = plays[
        (plays.defense == team) & plays.match_id.isin(matches) & plays.opponent_name.notna() & plays.play.notna()
    ]
    grouped = plays.assign(key=plays.play.map(KEY_PLAYS)).groupby(["opponent_name", "key"]).points
    rows = pd.DataFrame(index=pd.Index(sorted(plays.opponent_name.unique()), name="name"))
    for label, values in (("poss", grouped.size()), ("pts", grouped.sum())):
        wide = values.unstack().reindex(index=rows.index, columns=list(KEY_ORDER))
        rows = rows.join(wide.add_prefix(f"{label}_"))
    rows["poss_all"] = rows[[f"poss_{key}" for key in KEY_ORDER]].sum(axis=1)
    rows["pts_all"] = rows[[f"pts_{key}" for key in KEY_ORDER]].sum(axis=1)
    return rows.reset_index()


def last_matches(games: pd.DataFrame, team: str) -> list[str]:
    """Return the ids of the last games of ``team``, as the Key numbers page picks them."""
    own = games[(games.team_id == team) & (games.side == "off")].sort_values("date")
    return list(own.game_id.tail(LAST_GAMES))


def write_key_numbers(feed, matchup: Matchup, folder: Path, game: dict[str, str], shot_counts) -> dict[str, list[str]]:
    """Write the folder read by ``notebooks/key_numbers.load``.

    Args:
        feed: Output of ``hudl.opponent_report.load_feed``.
        matchup: Teams, competition and date.
        folder: Folder to write (created).
        game: ``game``, ``game_short`` and ``game_date`` of the page header.
        shot_counts: ``key_numbers.shot_aggregates``, which counts a shot list.

    Returns:
        The ids of the last games of the opponent (``opp``) and of the reference (``ref``).
    """
    folder.mkdir(parents=True, exist_ok=True)
    competition = matchup.competition
    plays = scoped(feed.plays, competition)
    numbers = {
        team: jersey_numbers(team, plays[plays.team_name == team].player_name)
        for team in (matchup.team, matchup.reference)
    }
    shots = synergy_shots(plays, numbers[matchup.team] | numbers[matchup.reference])
    games = side_games(feed, competition)
    last = {who: last_matches(games, team) for who, team in (("opp", matchup.team), ("ref", matchup.reference))}

    counts = pd.concat(
        {
            side: shots.groupby(column).apply(lambda frame: pd.Series(shot_counts(frame)), include_groups=False)
            for side, column in (("off", "team"), ("def", "defense"))
        },
        names=["side", "team_id"],
    )
    teams = games.drop(columns=["game_id", "date", "vs"]).groupby(["team_id", "name", "side"], as_index=False).sum()
    teams.join(counts[list(SHOT_COUNTS)], on=["side", "team_id"]).to_csv(folder / "teams.csv", index=False)

    zones = pd.concat(
        {
            side: shots[shots.zoneName != PAINT_ZONE].groupby([column, "zoneName"]).made.agg(fga="size", fgm="sum")
            for side, column in (("off", "team"), ("def", "defense"))
        },
        names=["side", "team_id", "zone"],
    )
    zones.reset_index()[["team_id", "side", "zone", "fga", "fgm"]].to_csv(folder / "zones.csv", index=False)

    shot_columns = ["gameId", "gameDate", "player", "pointsAttempted", "made", "zoneName", "shotDistance", "description"]
    shots[shots.team == matchup.team][shot_columns].to_csv(folder / "opp_shots.csv", index=False)
    shots[shots.defense == matchup.team][shot_columns].to_csv(folder / "opp_def_shots.csv", index=False)
    allowed = shots[shots.defense == matchup.reference].assign(player=lambda frame: frame.defender)
    allowed[shot_columns].to_csv(folder / "ref_def_shots.csv", index=False)

    who = games.team_id.map({matchup.team: "opp", matchup.reference: "ref"})
    games.assign(who=who).dropna(subset=["who"]).drop(columns=["team_id", "name"]).to_csv(
        folder / "games.csv", index=False
    )

    opponent_games = games[(games.team_id == matchup.team) & (games.side == "off")]
    season = player_rows(feed, competition, matchup.team, list(opponent_games.game_id), numbers[matchup.team])
    season.to_csv(folder / "players.csv", index=False)
    player_rows(feed, competition, matchup.team, last["opp"], numbers[matchup.team]).drop(columns="number").to_csv(
        folder / "players_last.csv", index=False
    )
    play_columns = [f"poss_{key}" for key in KEY_ORDER]
    main_play = season.set_index("name")[play_columns].idxmax(axis=1).str.removeprefix("poss_").map(KEY_LABELS)
    pd.DataFrame(
        {
            "PLAYER": "#" + season.number.fillna("-") + " " + season.name,
            "OFFENSIVE ROLE": "Main play: " + season.name.map(main_play),
        }
    ).to_csv(folder / "box.csv", index=False)
    box = scoped(feed.player_games, competition)
    box = box[box.team == matchup.team]
    pd.DataFrame(
        {
            "game_id": box.match_id,
            "player": box.player,
            "seconds": box[SECONDS],
            "offReb": box["Offensive rebounds"],
        }
    ).to_csv(folder / "box_games.csv", index=False)

    reference_games = games[(games.team_id == matchup.reference) & (games.side == "off")]
    defender_rows(feed, competition, matchup.reference, list(reference_games.game_id)).to_csv(
        folder / "defenders.csv", index=False
    )
    defender_rows(feed, competition, matchup.reference, last["ref"]).to_csv(folder / "defenders_last.csv", index=False)
    pd.Series(numbers[matchup.reference], name="number").rename_axis("name").reset_index().to_csv(
        folder / "ref_numbers.csv", index=False
    )

    write_json(
        folder / "config.json",
        {
            "opponent": {"name": matchup.short, "abbr": matchup.short[:3].upper(), "team_id": matchup.team},
            "reference": {"name": matchup.reference, "abbr": "BCR", "team_id": matchup.reference},
            "competition": competition,
            "season": SEASON,
            "date": matchup.date,
            "author": AUTHOR,
            **game,
        },
    )
    write_json(folder / "meta.json", {"last_game": opponent_games.date.max(), "last3_opp": last["opp"], "last3_ref": last["ref"]})
    return last
