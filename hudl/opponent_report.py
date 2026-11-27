"""Opponent numbers and figures from the Hudl Instat feed only (no Synergy).

Usage:
    python -m hudl.opponent_report "Dolomiti Energia Trentino" --out reports/hudl_api/trento_hudl_only

Reads the raw payloads of ``hudl.pull`` and writes ``numbers.txt`` (every table used
by the pages) into the output folder. The figures come from ``hudl.site_figures``.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from hudl.pull import RAW_DIR, TOURNAMENTS

REFERENCE_TEAM = "BC Roma"
SEASON_ID = 38
BASKET_X_M, BASKET_Y_M = 26.425, 7.5
RIM_RADIUS_M = 1.5
PAINT_MIN_X_M, PAINT_HALF_WIDTH_M = 22.2, 2.45
CORNER_MIN_X_M = 25.0
QUARTER_SECONDS = 600
MADE_POINTS = {"2+": 2, "3+": 3, "2+1": 2, "3+1": 3}
MISSED = ("2-", "3-")
SHOOTING_FOULS = ("2F", "3F")
FOUL_PLAYS = ("2+1", "3+1", *SHOOTING_FOULS)
FIELD_GOALS = (*MADE_POINTS, *MISSED)
PLAY_ACTIONS = (*FIELD_GOALS, *SHOOTING_FOULS, "Turnover")
SCORING = {**MADE_POINTS, "1+": 1}
PLAYTYPE_LABELS = {
    "Pick''n''Roll": "P&R ball handler",
    "Catch and shoot": "Catch and shoot",
    "Transition": "Transition",
    "Catch and Drive": "Catch and drive",
    "Hand offs": "Handoff",
    "Cut": "Cut",
    "Pick''n''pop": "Pick and pop",
    "Pick''n''roll roller": "P&R roll man",
    "Isolation": "Isolation",
    "Putbacks": "Put-back",
    "Post": "Post-up",
    "Screen off": "Off screen",
}
POSSESSION_SUFFIX = " - number of possessions in this playtype"
FEED_PLAY_PREFIXES = {
    "PnR Handlers": "P&R ball handler",
    "PnR Rollers": "P&R roll man",
    "Pick'n'Pop": "Pick and pop",
    "Catch and shoot": "Catch and shoot",
    "Catch and drive": "Catch and drive",
    "Screens off": "Off screen",
    "Postsup": "Post-up",
    "Isolation": "Isolation",
    "Hand off": "Handoff",
    "Cuts": "Cut",
    "Put Back": "Put-back",
    "Transition": "Transition",
}
ZONES = ("Rim", "Paint", "Mid-range", "Corner three", "Above-break three")
SHOT_CLOCK_BINS = [-1, 8, 16, 60]
SHOT_CLOCK_LABELS = ["0-8 s", "8-16 s", "16-24 s"]
MIN_DEFENDED_SHOTS = 15
MIN_LINEUP_MINUTES = 8
SHOT_CHART_PLAYERS = 8
MIN_ON_OFF_MINUTES = 100
MIN_MIX_POSSESSIONS = 10


def load_calendar() -> pd.DataFrame:
    """Return the finished games of both competitions, one row per game."""
    frames = []
    for competition in TOURNAMENTS:
        path = RAW_DIR / f"calendar_{competition}_s{SEASON_ID}.json"
        frame = pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))
        frame["competition"] = competition
        frames.append(frame)
    calendar = pd.concat(frames, ignore_index=True)
    calendar["date"] = pd.to_datetime(calendar.match_date).dt.date
    for column in ("team1_score", "team2_score"):
        calendar[column] = calendar[column].astype(int)
    for column in ("team1_name", "team2_name"):
        calendar[column] = calendar[column].str.replace("''", "'")
    return calendar.rename(columns={"id": "match_id"})


def load_events(calendar: pd.DataFrame) -> pd.DataFrame:
    """Return every event row with its competition and numeric clock and coordinates."""
    frames = []
    for match_id in calendar.match_id:
        path = RAW_DIR / "games" / match_id / "events.json"
        frame = pd.DataFrame(json.loads(path.read_text(encoding="utf-8"))["data"]["row"])
        frame["match_id"] = match_id
        frames.append(frame)
    events = pd.concat(frames, ignore_index=True)
    game_columns = ["match_id", "competition", "date", "team1_name", "team2_name"]
    events = events.merge(calendar[game_columns], on="match_id")
    numeric = ["half", "second_clear", "pos_x", "pos_y", "possession_start_clear"]
    events[numeric] = events[numeric].apply(pd.to_numeric)
    names = [c for c in events if c.endswith("_name") and c != "action_name"]
    events[names] = events[names].apply(lambda column: column.str.replace("''", "'"))
    return events


def load_team_games(calendar: pd.DataFrame) -> pd.DataFrame:
    """Return one row per team and game: every team parameter, own and opponent's."""
    records = []
    for match_id in calendar.match_id:
        path = RAW_DIR / "games" / match_id / "teams.json"
        rows = json.loads(path.read_text(encoding="utf-8"))["data"]["row"]
        per_team: dict[str, dict[str, float]] = {}
        for row in rows:
            team = row["team_name"].replace("''", "'")
            per_team.setdefault(team, {})[row["param_name"]] = float(row["value"])
        records.extend({"match_id": match_id, "team": t, **v} for t, v in per_team.items())
    own = pd.DataFrame(records).fillna(0.0)
    other = own.rename(columns={"team": "opponent"}).add_prefix("opp_")
    both = own.merge(other, left_on="match_id", right_on="opp_match_id")
    both = both[both.team != both.opp_opponent].rename(columns={"opp_opponent": "opponent"})
    return both.merge(calendar[["match_id", "competition", "date"]], on="match_id")


def load_player_games(calendar: pd.DataFrame) -> pd.DataFrame:
    """Return one row per player and game with every player parameter."""
    records = []
    for match_id in calendar.match_id:
        path = RAW_DIR / "games" / match_id / "players.json"
        for team in json.loads(path.read_text(encoding="utf-8"))["data"]["team"]:
            for player in team["player"]:
                values = {p["name"]: float(p["value"]) for p in player["param"]}
                records.append(
                    {
                        "match_id": match_id,
                        "team": team["name"].replace("''", "'"),
                        "player": player["name"].replace("''", "'"),
                        **values,
                    }
                )
    frame = pd.DataFrame(records).fillna(0.0)
    return frame.merge(calendar[["match_id", "competition"]], on="match_id")


@dataclass(frozen=True)
class Feed:
    """The tables read from the raw Hudl payloads.

    Attributes:
        calendar: One row per finished game.
        events: Every event row.
        team_games: One row per team and game, own and opponent's parameters.
        player_games: One row per player and game.
        plays: Shots, shooting fouls and turnovers (see ``build_plays``).
    """

    calendar: pd.DataFrame
    events: pd.DataFrame
    team_games: pd.DataFrame
    player_games: pd.DataFrame
    plays: pd.DataFrame


def load_feed() -> Feed:
    """Read every raw payload of the season."""
    calendar = load_calendar()
    events = load_events(calendar)
    return Feed(calendar, events, load_team_games(calendar), load_player_games(calendar), build_plays(events))


def short_names(players: pd.Series) -> dict[str, str]:
    """Map full names to surnames, adding the initial when two surnames collide."""
    full = players.dropna().unique()
    surname = {name: name.split()[-1] for name in full}
    counts = pd.Series(surname).value_counts()
    return {
        name: f"{name[0]}. {last}" if counts[last] > 1 else last
        for name, last in surname.items()
    }


def shot_zone(action: pd.Series, x: pd.Series, y: pd.Series) -> np.ndarray:
    """Classify shots by court zone from Hudl coordinates (metres, one basket)."""
    distance = np.hypot(x - BASKET_X_M, y - BASKET_Y_M)
    in_paint = (x >= PAINT_MIN_X_M) & ((y - BASKET_Y_M).abs() <= PAINT_HALF_WIDTH_M)
    is_three = action.str.startswith("3")
    return np.select(
        [is_three & (x >= CORNER_MIN_X_M), is_three, distance <= RIM_RADIUS_M, in_paint],
        ["Corner three", "Above-break three", "Rim", "Paint"],
        default="Mid-range",
    )


def build_plays(events: pd.DataFrame) -> pd.DataFrame:
    """Return shots, shooting fouls and turnovers with points, zone and court position.

    Free throws made are added to the last fouled play of the same player in the
    same possession, so ``points`` is the full value of the play.
    """
    plays = events[events.action_name.isin(PLAY_ACTIONS)].copy()
    free_throws = (
        events[events.action_name == "1+"]
        .groupby(["match_id", "possession_number", "player_name"])
        .size()
        .rename("free_throw_points")
    )
    fouled = plays[plays.action_name.isin(FOUL_PLAYS)].drop_duplicates(
        ["match_id", "possession_number", "player_name"], keep="last"
    )
    bonus = fouled.join(free_throws, on=["match_id", "possession_number", "player_name"])
    plays["points"] = plays.action_name.map(MADE_POINTS).fillna(0)
    plays.loc[bonus.index, "points"] += bonus.free_throw_points.fillna(0)
    plays["is_fga"] = plays.action_name.isin(FIELD_GOALS)
    plays["made"] = plays.action_name.isin(MADE_POINTS)
    plays["is_three"] = plays.action_name.str.startswith("3") & plays.is_fga
    plays["zone"] = shot_zone(plays.action_name, plays.pos_x, plays.pos_y)
    plays["court_x"] = (plays.pos_y - BASKET_Y_M) * 100
    plays["court_y"] = (BASKET_X_M - plays.pos_x) * 100
    plays["play"] = plays.playtype.map(PLAYTYPE_LABELS)
    plays["defense"] = np.where(
        plays.team_name == plays.team1_name, plays.team2_name, plays.team1_name
    )
    return plays


def rank(values: pd.Series, best_is_high: bool) -> pd.Series:
    """Rank teams, 1 = best."""
    return values.rank(ascending=not best_is_high, method="min").astype(int)


def team_table(team_games: pd.DataFrame, competition: str) -> pd.DataFrame:
    """Return per-team season metrics of a competition with their ranks."""
    games = team_games[team_games.competition == competition]
    total = games.groupby("team").sum(numeric_only=True)
    table = pd.DataFrame({"Games": games.groupby("team").size()})
    fga, opp_fga = total["Field goals attempted"], total["opp_Field goals attempted"]
    metrics = {
        "Possessions per game": (total.Possessions / table.Games, None),
        "Points per 100 possessions": (100 * total.Points / total.Possessions, True),
        "Effective FG%": (
            100 * (total["Field goals made"] + 0.5 * total["3-pt field goals made"]) / fga,
            True,
        ),
        "Turnovers per 100 possessions": (100 * total.Turnovers / total.Possessions, False),
        "Three-point %": (
            100 * total["3-pt field goals made"] / total["3-pt field goals attempted"],
            True,
        ),
        "Threes, share of attempts": (100 * total["3-pt field goals attempted"] / fga, None),
        "Free throws per 100 FGA": (100 * total["Free throws attempted"] / fga, True),
        "Offensive rebound %": (
            100
            * total["Offensive rebounds"]
            / (total["Offensive rebounds"] + total["opp_Defensive rebounds"]),
            True,
        ),
        "Points allowed per 100 possessions": (
            100 * total.opp_Points / total.opp_Possessions,
            False,
        ),
        "Opponents' effective FG%": (
            100
            * (total["opp_Field goals made"] + 0.5 * total["opp_3-pt field goals made"])
            / opp_fga,
            False,
        ),
        "Turnovers forced per 100 possessions": (
            100 * total.opp_Turnovers / total.opp_Possessions,
            True,
        ),
        "Defensive rebound %": (
            100
            * total["Defensive rebounds"]
            / (total["Defensive rebounds"] + total["opp_Offensive rebounds"]),
            True,
        ),
        "Opponents' free throws per 100 FGA": (
            100 * total["opp_Free throws attempted"] / opp_fga,
            False,
        ),
        "Transition points per game": (total["Transition points"] / table.Games, True),
        "Second chance points per game": (total["Second chance points"] / table.Games, True),
        "Points off turnovers per game": (total["Points off turnovers "] / table.Games, True),
        "Paint points per game": (total["Paint points"] / table.Games, True),
        "Bench points per game": (total["Bench points"] / table.Games, True),
        "Uncontested share of FGA": (
            100 * total["Uncontested field goals attempted"] / fga,
            True,
        ),
        "Opponents' uncontested share of FGA": (
            100 * total["opp_Uncontested field goals attempted"] / opp_fga,
            False,
        ),
        "Deflections per game": (total.Deflections / table.Games, True),
    }
    for name, (values, best_is_high) in metrics.items():
        table[name] = values.round(1)
        if best_is_high is not None:
            table[f"{name} rank"] = rank(values, best_is_high)
    return table


def feed_possessions(frame: pd.DataFrame, keys: list[str], prefix: str = "") -> pd.Series:
    """Return the possessions per play type that Hudl counts (turnovers included).

    Args:
        frame: Team or player game rows.
        keys: Columns to group by.
        prefix: ``"opp_"`` to read the opponent's possessions of a team row.

    Returns:
        Possessions indexed by ``keys`` and ``play``.
    """
    columns = {f"{prefix}{feed}{POSSESSION_SUFFIX}": play for feed, play in FEED_PLAY_PREFIXES.items()}
    wide = frame.groupby(keys)[list(columns)].sum().rename(columns=columns)
    return wide.rename_axis(columns="play").stack()


def playtype_table(
    plays: pd.DataFrame, team_games: pd.DataFrame, competition: str, side: str
) -> pd.DataFrame:
    """Return possessions, share, points per possession and rank per team and play type.

    Possessions are Hudl's own count (turnovers included); points come from the
    events, free throws of fouled shots included.

    Args:
        plays: Output of ``build_plays``.
        team_games: Output of ``load_team_games``.
        competition: Competition label.
        side: ``team_name`` for the offense, ``defense`` for what a team allows.
    """
    best_is_high = side == "team_name"
    games = team_games[team_games.competition == competition]
    possessions = feed_possessions(games, ["team"], "" if best_is_high else "opp_")
    tagged = plays[(plays.competition == competition) & plays.play.notna()]
    points = tagged.groupby([side, "play"]).points.sum()
    grouped = pd.DataFrame({"plays": possessions, "points": points.reindex(possessions.index)})
    grouped = grouped.fillna(0)
    grouped["share"] = (100 * grouped.plays / grouped.groupby(level=0).plays.transform("sum")).round(1)
    grouped["ppp"] = (grouped.points / grouped.plays).round(2)
    grouped["rank"] = grouped.groupby(level="play").ppp.rank(
        ascending=not best_is_high, method="min"
    ).astype(int)
    grouped["share_rank"] = grouped.groupby(level="play").share.rank(
        ascending=False, method="min"
    ).astype(int)
    return grouped


def zone_table(plays: pd.DataFrame, competition: str, side: str) -> pd.DataFrame:
    """Return attempts, share, FG% and FG% rank per team and shot zone."""
    shots = plays[(plays.competition == competition) & plays.is_fga]
    grouped = shots.groupby([side, "zone"]).agg(attempts=("made", "size"), made=("made", "sum"))
    grouped["share"] = (
        100 * grouped.attempts / grouped.groupby(level=0).attempts.transform("sum")
    ).round(1)
    grouped["fg_pct"] = (100 * grouped.made / grouped.attempts).round(1)
    best_is_high = side == "team_name"
    grouped["fg_rank"] = grouped.groupby(level="zone").fg_pct.rank(
        ascending=not best_is_high, method="min"
    ).astype(int)
    grouped["share_rank"] = grouped.groupby(level="zone").share.rank(
        ascending=False, method="min"
    ).astype(int)
    return grouped


def player_lines(player_games: pd.DataFrame, plays: pd.DataFrame, team: str) -> pd.DataFrame:
    """Return per-game lines of a team's players with their two main play types."""
    games = player_games[(player_games.team == team) & (player_games["Seconds on the court"] > 0)]
    total = games.groupby(["competition", "player"]).sum(numeric_only=True)
    count = games.groupby(["competition", "player"]).size()
    lines = pd.DataFrame(
        {
            "Games": count,
            "Min": (total["Seconds on the court"] / 60 / count).round(0),
            "Pts": (total.Points / count).round(1),
            "Ast": (total.Assists / count).round(1),
            "Reb": (total.Rebounds / count).round(1),
            "TO": (total.Turnovers / count).round(1),
            "2P": total["2-pt field goals made"].astype(int).astype(str)
            + "/"
            + total["2-pt field goals attempted"].astype(int).astype(str),
            "3P": total["3-pt field goals made"].astype(int).astype(str)
            + "/"
            + total["3-pt field goals attempted"].astype(int).astype(str),
            "Plus/Minus": total["Plus/Minus"].astype(int),
        }
    )
    own = plays[(plays.team_name == team) & plays.play.notna()]
    mix = feed_possessions(games, ["competition", "player"])
    share = 100 * mix / mix.groupby(level=[0, 1]).transform("sum")
    lines["Plays"] = mix.groupby(level=[0, 1]).sum().reindex(lines.index).astype(int)
    lines["Main plays"] = (
        share.groupby(level=[0, 1])
        .apply(lambda s: ", ".join(f"{p} {v:.0f}%" for (_, _, p), v in s.nlargest(2).items()))
        .reindex(lines.index)
    )
    points = own.groupby(["competition", "player_name"]).points.sum().reindex(lines.index)
    lines["Points per play"] = (points / lines.Plays).round(2)
    return lines.sort_values(["competition", "Min"], ascending=[True, False])


def shot_tags(plays: pd.DataFrame, team: str) -> pd.DataFrame:
    """Return per-player shot habits: hand, shot type, drive side, contest, assisted."""
    shots = plays[(plays.team_name == team) & plays.is_fga]
    grouped = shots.groupby("player_name")
    made = shots[shots.made].groupby("player_name")
    table = pd.DataFrame(
        {
            "FGA": grouped.size(),
            "Left hand %": grouped.hand.apply(lambda s: 100 * (s == "Left").mean()),
            "Jumper %": grouped.shot_type.apply(lambda s: 100 * (s == "Jumper").mean()),
            "Lay-up or dunk %": grouped.shot_type.apply(
                lambda s: 100 * s.isin(["Lay up", "Dunk", "Reverse", "Alley oop"]).mean()
            ),
            "Floater %": grouped.shot_type.apply(lambda s: 100 * (s == "Floater").mean()),
            "Drives left": grouped.drive.apply(lambda s: (s == "Drives Left").sum()),
            "Drives right": grouped.drive.apply(lambda s: (s == "Drives Right").sum()),
            "Uncontested %": grouped.contesting.apply(lambda s: 100 * (s == "Uncontested").mean()),
            "Assisted % of makes": made.teammate_name.apply(lambda s: 100 * s.notna().mean()),
            "Step-backs": grouped.dribble_move.apply(lambda s: (s == "Step back").sum()),
        }
    )
    return table.round(0).sort_values("FGA", ascending=False)


def defender_table(plays: pd.DataFrame, team: str) -> pd.DataFrame:
    """Return shots defended by each player of a team (the defender Hudl credits)."""
    shots = plays[(plays.opponent_team_name == team) & plays.is_fga]
    grouped = shots.groupby("opponent_name")
    table = pd.DataFrame(
        {
            "Shots defended": grouped.size(),
            "FG% allowed": (100 * grouped.made.mean()).round(0),
            "Points per shot": grouped.points.mean().round(2),
            "Threes": grouped.is_three.sum(),
            "Most defended plays": shots[shots.play.notna()]
            .groupby("opponent_name")
            .play.apply(lambda s: ", ".join(f"{p} {n}" for p, n in s.value_counts().head(2).items())),
        }
    )
    return table[table["Shots defended"] >= MIN_DEFENDED_SHOTS].sort_values(
        "Shots defended", ascending=False
    )


def coverage_table(team_games: pd.DataFrame, competition: str) -> pd.DataFrame:
    """Return the share of each pick-and-roll coverage per team (row sums to 100)."""
    games = team_games[team_games.competition == competition]
    columns = [c for c in games if c.startswith("Pick'n'roll defense:")]
    total = games.groupby("team")[columns].sum()
    total.columns = [c.split(": ")[1] for c in columns]
    share = (100 * total.div(total.sum(axis=1), axis=0)).round(0)
    share["Screens defended per game"] = (total.sum(axis=1) / games.groupby("team").size()).round(1)
    share.loc["League average"] = (
        100 * total.sum() / total.sum().sum()
    ).round(0).tolist() + [share["Screens defended per game"].mean().round(1)]
    return share


def lineup_stints(events: pd.DataFrame, calendar: pd.DataFrame, team: str) -> pd.DataFrame:
    """Return seconds, possessions and points for and against of every unit of a team."""
    records = []
    team_matches = calendar[(calendar.team1_name == team) | (calendar.team2_name == team)]
    for match in team_matches.itertuples():
        side = "first_team" if match.team1_name == team else "second_team"
        unit_column = "team1_unit_num" if side == "first_team" else "team2_unit_num"
        fives_path = RAW_DIR / "games" / match.match_id / "fives.json"
        units = json.loads(fives_path.read_text(encoding="utf-8"))["data"][side]["units"]
        members = {
            str(unit["unit_num"]): frozenset(
                f"{p['first_name']} {p['lastname']}" for p in unit["players"]
            )
            for unit in units
        }
        game = events[(events.match_id == match.match_id) & events[unit_column].notna()]
        game = game.sort_values(["half", "second_clear"])
        seconds = game.groupby("half").second_clear.diff().shift(-1).clip(lower=0).fillna(0)
        points = game.action_name.map(SCORING).fillna(0)
        own = game.team_name == team
        possession_end = game.possession_name == "End"
        frame = pd.DataFrame(
            {
                "unit": game[unit_column].map(members),
                "seconds": seconds,
                "points_for": points.where(own, 0),
                "points_against": points.where(~own, 0),
                "possessions_for": (possession_end & (game.possession_team_name == team)).astype(int),
                "possessions_against": (
                    possession_end & (game.possession_team_name != team)
                ).astype(int),
                "competition": match.competition,
                "match_id": match.match_id,
            }
        )
        records.append(frame.dropna(subset=["unit"]))
    stints = pd.concat(records)
    return stints.groupby(["competition", "match_id", "unit"], as_index=False).sum(numeric_only=True)


def net_rating(frame: pd.DataFrame) -> pd.Series:
    """Return minutes, offensive, defensive and net rating of summed stints."""
    total = frame[
        ["seconds", "points_for", "points_against", "possessions_for", "possessions_against"]
    ].sum()
    offense = 100 * total.points_for / max(total.possessions_for, 1)
    defense = 100 * total.points_against / max(total.possessions_against, 1)
    return pd.Series(
        {
            "Minutes": round(total.seconds / 60),
            "Offense": round(offense, 1),
            "Defense": round(defense, 1),
            "Net": round(offense - defense, 1),
        }
    )


def lineup_table(stints: pd.DataFrame, names: dict[str, str]) -> pd.DataFrame:
    """Return the most used five-man units with their ratings (both competitions)."""
    table = stints.groupby("unit").apply(net_rating, include_groups=False)
    table = table[table.Minutes >= MIN_LINEUP_MINUTES].sort_values("Minutes", ascending=False)
    table.index = [", ".join(sorted(names.get(p, p.split()[-1]) for p in unit)) for unit in table.index]
    return table


def on_off_table(stints: pd.DataFrame, names: dict[str, str]) -> pd.DataFrame:
    """Return each player's team net rating with him on and off the court."""
    players = sorted(set().union(*stints.unit))
    records = {}
    for player in players:
        is_on = stints.unit.apply(lambda unit, p=player: p in unit)
        on, off = net_rating(stints[is_on]), net_rating(stints[~is_on])
        records[names.get(player, player.split()[-1])] = {
            "Minutes on": on.Minutes,
            "Net on": on.Net,
            "Net off": off.Net,
            "On minus off": round(on.Net - off.Net, 1),
            "Offense on": on.Offense,
            "Defense on": on.Defense,
        }
    return pd.DataFrame(records).T.sort_values("Minutes on", ascending=False)


def shot_clock_table(plays: pd.DataFrame, competition: str, team: str) -> pd.DataFrame:
    """Return when in the possession the plays end, the team against the competition."""
    scoped = plays[(plays.competition == competition) & plays.possession_start_clear.notna()].copy()
    elapsed = scoped.second_clear - scoped.possession_start_clear
    scoped["bin"] = pd.cut(elapsed, SHOT_CLOCK_BINS, labels=SHOT_CLOCK_LABELS)
    rows = {}
    for label, frame in (
        (team, scoped[scoped.team_name == team]),
        (f"{team} defense", scoped[scoped.defense == team]),
        ("Competition", scoped),
    ):
        grouped = frame.groupby("bin", observed=True)
        rows[label] = pd.concat(
            [
                (100 * grouped.size() / len(frame)).round(0).add_suffix(" share"),
                grouped.points.mean().round(2).add_suffix(" points per play"),
            ]
        )
    return pd.DataFrame(rows).T


def quarter_table(events: pd.DataFrame, team: str) -> pd.DataFrame:
    """Return points for and against per quarter and game, by competition."""
    team_matches = events[events.team_name == team].match_id.unique()
    scoring = events[events.match_id.isin(team_matches) & events.action_name.isin(SCORING)].copy()
    scoring["points"] = scoring.action_name.map(SCORING)
    scoring["side"] = np.where(scoring.team_name == team, "For", "Against")
    games = scoring.groupby("competition").match_id.nunique()
    table = scoring.pivot_table(
        index=["competition", "side"], columns="half", values="points", aggfunc="sum"
    )
    return table.div(games, level="competition", axis=0).round(1)


def assist_pairs(plays: pd.DataFrame, team: str, names: dict[str, str]) -> pd.Series:
    """Return the most frequent passer to scorer pairs on made shots."""
    assisted = plays[(plays.team_name == team) & plays.made & plays.teammate_name.notna()]
    pairs = assisted.teammate_name.map(names) + " to " + assisted.player_name.map(names)
    return pairs.value_counts().head(10)


def clip_list(plays: pd.DataFrame, team: str, games: int) -> pd.DataFrame:
    """Return the made shots of the last games, both ends, with quarter and clock."""
    involved = plays[((plays.team_name == team) | (plays.defense == team)) & plays.made]
    last = sorted(involved.date.unique())[-games:]
    clips = involved[involved.date.isin(last) & involved.play.notna()].copy()
    left = (QUARTER_SECONDS - clips.second_clear).clip(lower=0)
    clips["clock"] = (
        "Q" + clips.half.astype(int).astype(str) + " "
        + (left // 60).astype(int).astype(str) + ":"
        + (left % 60).astype(int).astype(str).str.zfill(2)
    )
    clips["end"] = np.where(clips.team_name == team, "scored", "allowed")
    columns = ["date", "end", "play", "clock", "player_name", "opponent_name", "zone"]
    return clips.sort_values(["end", "play", "date", "half", "second_clear"])[columns]


def results_table(calendar: pd.DataFrame, team: str) -> pd.DataFrame:
    """Return the results of a team, oldest first."""
    games = calendar[(calendar.team1_name == team) | (calendar.team2_name == team)].copy()
    home = games.team1_name == team
    games["opponent"] = np.where(home, games.team2_name, games.team1_name)
    games["venue"] = np.where(home, "home", "away")
    games["scored"] = np.where(home, games.team1_score, games.team2_score)
    games["allowed"] = np.where(home, games.team2_score, games.team1_score)
    games["result"] = np.where(games.scored > games.allowed, "W", "L")
    columns = ["competition", "date", "venue", "opponent", "scored", "allowed", "result"]
    return games.sort_values("date")[columns]


def standings_table(calendar: pd.DataFrame, competition: str) -> pd.DataFrame:
    """Return wins, losses and point difference per team of a competition."""
    games = calendar[calendar.competition == competition]
    home = games.rename(columns={"team1_name": "team", "team1_score": "pf", "team2_score": "pa"})
    away = games.rename(columns={"team2_name": "team", "team2_score": "pf", "team1_score": "pa"})
    rows = pd.concat([home[["team", "pf", "pa"]], away[["team", "pf", "pa"]]])
    rows["win"] = rows.pf > rows.pa
    table = rows.groupby("team").agg(W=("win", "sum"), G=("win", "size"), PF=("pf", "sum"), PA=("pa", "sum"))
    table["L"], table["Diff"] = table.G - table.W, table.PF - table.PA
    table = table.sort_values(["W", "Diff"], ascending=False)
    table.insert(0, "Pos", range(1, len(table) + 1))
    return table[["Pos", "W", "L", "Diff"]]


def main() -> None:
    """Write the numbers file and the figures of one opponent."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("team")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    team, out = args.team, args.out
    out.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 250, "display.max_columns", 60, "display.max_rows", 500)

    feed = load_feed()
    calendar, events, team_games = feed.calendar, feed.events, feed.team_games
    player_games, plays = feed.player_games, feed.plays
    names = short_names(events[events.team_name == team].player_name)
    stints = lineup_stints(events, calendar, team)
    competitions = [c for c in TOURNAMENTS if team in set(team_games[team_games.competition == c].team)]
    offense = {c: playtype_table(plays, team_games, c, "team_name") for c in competitions}
    defense = {c: playtype_table(plays, team_games, c, "defense") for c in competitions}
    coverage = {c: coverage_table(team_games, c) for c in competitions}
    on_off = on_off_table(stints, names)

    sections: dict[str, object] = {
        "RESULTS": results_table(calendar, team),
        "ASSIST PAIRS": assist_pairs(plays, team, names),
        "PLAYER LINES": player_lines(player_games, plays, team),
        "SHOT TAGS BY PLAYER": shot_tags(plays, team),
        "DEFENDERS": defender_table(plays, team),
        "LINEUPS": lineup_table(stints, names),
        "ON OFF": on_off,
        "QUARTERS": quarter_table(events, team),
        "MINUTES CHECK (lineup minutes per game)": stints.groupby("match_id").seconds.sum() / 60,
        "CLIPS last 3 games": clip_list(plays, team, 3),
    }
    for competition in competitions:
        teams = team_table(team_games, competition)
        both = [t for t in (team, REFERENCE_TEAM) if t in teams.index]
        sections[f"STANDINGS {competition}"] = standings_table(calendar, competition)
        sections[f"TEAM TABLE {competition} ({len(teams)} teams)"] = teams.loc[both].T
        for label, tables in (("OFFENSE", offense), ("DEFENSE", defense)):
            table = tables[competition]
            sections[f"PLAY TYPES {label} {competition}"] = pd.concat(
                {t: table.loc[t] for t in both if t in table.index.get_level_values(0)}, axis=1
            )
            side = "team_name" if label == "OFFENSE" else "defense"
            zones = zone_table(plays, competition, side)
            sections[f"ZONES {label} {competition}"] = pd.concat(
                {t: zones.loc[t].reindex(ZONES) for t in both}, axis=1
            )
        sections[f"PNR COVERAGE {competition}"] = coverage[competition].loc[[*both, "League average"]]
        sections[f"SHOT CLOCK {competition}"] = shot_clock_table(plays, competition, team)
        out_of_bounds = [c for c in team_games if "Out of Bounds" in c or "combinations" in c]
        scoped = team_games[team_games.competition == competition]
        sections[f"OUT OF BOUNDS {competition}"] = (
            scoped.groupby("team")[out_of_bounds].sum().loc[both].T
        )
        zone_events = events[(events.action_name == "Zone defense") & (events.competition == competition)]
        sections[f"ZONE DEFENSE MARKERS {competition}"] = zone_events.team_name.value_counts()
        own_players = player_games[(player_games.team == team) & (player_games.competition == competition)]
        steals = events[
            (events.action_name == "Turnover") & (events.team_name == team) & (events.competition == competition)
        ]
        sections[f"TURNOVERS BY PLAYER {competition}"] = pd.DataFrame(
            {
                "Turnovers": own_players.groupby("player").Turnovers.sum(),
                "Lost to a steal": steals.groupby("player_name").size(),
                "Minutes": own_players.groupby("player")["Seconds on the court"].sum() / 60,
            }
        ).fillna(0).astype(int).sort_values("Turnovers", ascending=False)
        sections[f"STEALS CHECK {competition}"] = scoped.groupby("team")[["opp_Steals", "Steals", "Turnovers", "Assists"]].sum().loc[both]
    with (out / "numbers.txt").open("w", encoding="utf-8") as handle:
        for title, table in sections.items():
            handle.write(f"\n===== {title} =====\n{table.to_string()}\n")


if __name__ == "__main__":
    main()
