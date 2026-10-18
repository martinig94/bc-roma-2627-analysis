"""Download Kids&Us Manresa 2026/27 games (Liga Endesa + EuroCup) into data/manresa/.

    python notebooks/manresa_fetch.py

Sources (no API key needed):
  * Liga Endesa: live.acb.com game pages (box score and play list are embedded as JSON in the page).
  * EuroCup: EuroLeague live API (results, Boxscore, PlayByPlay) and the club roster for heights.

Output CSVs (one row per ...):
  games.csv   game
  box.csv     Manresa player per game
  events.csv  Manresa substitution / period boundary with the running score, used for lineups
  assists.csv assisted made field goal (passer, scorer, points) between Manresa players
  shots.csv   EuroCup field-goal attempts with court coordinates (cm, basket at origin);
              ACB publishes no shot locations
"""
from __future__ import annotations

import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

OUT = Path(__file__).resolve().parent.parent / "data" / "manresa"
HEADERS = {"User-Agent": "Mozilla/5.0 (BC Roma scouting; contact giulia.martini@un.org)"}
ACB_CALENDAR = "https://www.acb.com/calendario"
ACB_GAME = "https://live.acb.com/partidos/{slug}/{page}"
EL_RESULTS = "https://api-live.euroleague.net/v1/results?seasonCode=U2026"
EL_BOX = "https://live.euroleague.net/api/Boxscore?gamecode={n}&seasoncode=U2026"
EL_PBP = "https://live.euroleague.net/api/PlayByPlay?gamecode={n}&seasoncode=U2026"
EL_PEOPLE = "https://api-live.euroleague.net/v2/competitions/U/seasons/U2026/clubs/MAN/people"
PERIOD_QUARTERS = ("FirstQuarter", "SecondQuarter", "ThirdQuarter", "ForthQuarter", "ExtraTime")
# ACB numeric play types for substitutions (checked against starters + on-court counts).
ACB_SUB_IN, ACB_SUB_OUT, ACB_STARTERS = 112, 115, 599
# Made field goals (2P, 3P, dunk) and assist types (checked against the per-player assist counters).
ACB_MADE_FG, ACB_ASSIST = {93, 94, 100}, {107, 108, 119}
EL_MADE_FG = {"2FGM", "3FGM", "DUNK"}
EL_POINTS = "https://live.euroleague.net/api/Points?gamecode={n}&seasoncode=U2026"
BOX_COLS = ["pts", "fg2m", "fg2a", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb", "ast", "stl", "tov",
            "blk", "pf", "plus_minus"]


def get(url: str) -> requests.Response:
    """GET with a polite user agent; raises on HTTP errors."""
    resp = requests.get(url, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp


def player_key(name: str) -> str:
    """Normalise 'Timmy Allen' and 'ALLEN, TIMMY' to the same 'allen t' key."""
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    name = re.sub(r"[^a-z, ]", " ", name)
    if "," in name:
        last, first = (part.strip() for part in name.split(",", 1))
    else:
        first, _, last = name.strip().partition(" ")
        last, first = (last or first), (first if last else "")
    last = re.sub(r"\s+", " ", last).strip()
    return f"{last} {first[:1]}".strip()


def display_name(name: str) -> str:
    """'ALLEN, TIMMY' -> 'Timmy Allen'; already formatted names are kept."""
    if "," not in name:
        return name.strip()
    last, first = (part.strip() for part in name.split(",", 1))
    return f"{first.title()} {last.title()}"


def minutes_to_seconds(clock: str) -> int:
    """'27:31' -> 1651."""
    minutes, seconds = clock.split(":")
    return int(minutes) * 60 + int(seconds)


def period_start(period: int) -> int:
    """Elapsed seconds at the start of a period (4 x 10 min, 5 min overtimes)."""
    return 600 * (period - 1) if period <= 4 else 2400 + 300 * (period - 5)


def period_length(period: int) -> int:
    """Length in seconds of a period."""
    return 600 if period <= 4 else 300


def flight_json(html: str, key: str) -> list | dict:
    """Pull `"key": [json list]` out of the Next.js flight payload embedded in an ACB page."""
    parts = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', html, re.S)
    text = "".join(json.loads(f'"{part}"') for part in parts)
    start = text.index(f'"{key}":[') + len(key) + 3
    return json.JSONDecoder().raw_decode(text[start:])[0]


# ------------------------------------------------------------------------------ Liga Endesa
def acb_game_slugs() -> list[str]:
    """Slugs ('kidsandus-manresa-vs-x-105386') of played Manresa games, in game-id order."""
    html = get(ACB_CALENDAR).text
    slugs = set(re.findall(r'live\.acb\.com/partidos/([^"/]*manresa[^"/]*)/estadisticas', html))
    return sorted(slugs, key=lambda s: int(s.rsplit("-", 1)[1]))


def parse_acb_game(slug: str) -> tuple[dict, list[dict], list[dict], list[dict]]:
    """Return (game row, Manresa box rows, Manresa events, assists) for one ACB game."""
    game_id = slug.rsplit("-", 1)[1]
    stats = flight_json(get(ACB_GAME.format(slug=slug, page="estadisticas")).text, "teamBoxscores")
    plays = flight_json(get(ACB_GAME.format(slug=slug, page="jugadas")).text, "plays")
    plays = sorted(plays, key=lambda p: p["order"])
    man_home = slug.startswith("kidsandus-manresa-vs")

    teams = {}
    for team in stats:
        name = team["team"]["fullName"]
        players = team["statsByPeriods"][0]["stats"]["players"]
        teams["man" if "Manresa" in name else "opp"] = (name, players)
    id_name = {p["player"]["id"]: p["player"]["nickname"] for p in teams["man"][1]}

    box = []
    for p in teams["man"][1]:
        if minutes_to_seconds(p["playTime"]) == 0:
            continue
        box.append({
            "comp": "Liga Endesa", "game_id": game_id, "player": p["player"]["nickname"],
            "role_es": p["player"]["gameRole"], "starter": int(p["isStarted"]),
            "sec": minutes_to_seconds(p["playTime"]), "pts": p["points"],
            "fg2m": p["twoPointersMade"], "fg2a": p["twoPointersAttempted"],
            "fg3m": p["threePointersMade"], "fg3a": p["threePointersAttempted"],
            "ftm": p["freeThrowsMade"], "fta": p["freeThrowsAttempted"],
            "oreb": p["offRebounds"], "dreb": p["defRebounds"], "ast": p["assists"],
            "stl": p["steals"], "tov": p["turnovers"], "blk": p["blocks"],
            "pf": p["personalFouls"], "plus_minus": p["plusMinus"],
        })

    def score(play: dict) -> tuple[int, int]:
        home, away = play["scoreHome"], play["scoreAway"]
        return (home, away) if man_home else (away, home)

    assists, made = [], None
    for play in plays:
        if play["playType"] in ACB_MADE_FG:
            made = play
        elif play["playType"] in ACB_ASSIST and made is not None:
            same_moment = all(made[k] == play[k] for k in ("quarter", "minute", "second", "local"))
            passer, scorer = id_name.get(play["playerLicenseId"]), id_name.get(made["playerLicenseId"])
            if same_moment and passer and scorer:
                assists.append({"comp": "Liga Endesa", "game_id": game_id, "passer": passer,
                                "scorer": scorer, "pts": 3 if made["playType"] == 94 else 2})

    events, last = [], {}
    for play in plays:
        if play["playType"] in (ACB_SUB_IN, ACB_SUB_OUT) and play["playerLicenseId"] in id_name:
            kind = "IN" if play["playType"] == ACB_SUB_IN else "OUT"
            player = id_name[play["playerLicenseId"]]
        elif play["playType"] == ACB_STARTERS and play["playerLicenseId"] in id_name:
            kind, player = "START", id_name[play["playerLicenseId"]]
        else:
            if play["quarter"]:
                last[play["quarter"]] = play
            continue
        left = play["minute"] * 60 + play["second"]
        quarter = max(play["quarter"], 1)
        man_pts, opp_pts = score(play)
        elapsed = 0 if kind == "START" else period_start(quarter) + period_length(quarter) - left
        events.append({"comp": "Liga Endesa", "game_id": game_id, "period": quarter,
                       "elapsed": elapsed,
                       "kind": kind, "player": player, "man": man_pts, "opp": opp_pts})
    for quarter, play in last.items():
        man_pts, opp_pts = score(play)
        events.append({"comp": "Liga Endesa", "game_id": game_id, "period": quarter,
                       "elapsed": period_start(quarter) + period_length(quarter), "kind": "END",
                       "player": "", "man": man_pts, "opp": opp_pts})

    final = score(plays[-1])
    opponent = teams["opp"][0]
    game = {"comp": "Liga Endesa", "game_id": game_id, "opponent": opponent,
            "home": int(man_home), "man_pts": final[0], "opp_pts": final[1]}
    return game, box, events, assists


# --------------------------------------------------------------------------------- EuroCup
def eurocup_games() -> list[dict]:
    """Played EuroCup games of Manresa from the EuroLeague results feed."""
    root = ET.fromstring(get(EL_RESULTS).content)
    games = []
    for node in root.iter("game"):
        if node.findtext("played") != "true" or "MAN" not in (node.findtext("homecode"),
                                                              node.findtext("awaycode")):
            continue
        games.append({"number": int(node.findtext("gamenumber")), "date": node.findtext("date"),
                      "home": node.findtext("homecode") == "MAN"})
    return sorted(games, key=lambda g: g["number"])


def parse_eurocup_game(info: dict) -> tuple[dict, list[dict], list[dict], list[dict]]:
    """Return (game row, Manresa box rows, Manresa events, assists) for one EuroCup game."""
    number, game_id = info["number"], f"EC{info['number']}"
    box_json = get(EL_BOX.format(n=number)).json()
    pbp = get(EL_PBP.format(n=number)).json()

    box, opponent = [], ""
    for team in box_json["Stats"]:
        code = team["PlayersStats"][0]["Team"].strip() if team["PlayersStats"] else ""
        is_man = code == "MAN"
        if not is_man:
            opponent = team["Team"].title()
            continue
        for p in team["PlayersStats"]:
            if p["Minutes"] in ("DNP", "", None):
                continue
            box.append({
                "comp": "EuroCup", "game_id": game_id, "player": display_name(p["Player"]),
                "role_es": "", "starter": p["IsStarter"], "sec": minutes_to_seconds(p["Minutes"]),
                "pts": p["Points"], "fg2m": p["FieldGoalsMade2"], "fg2a": p["FieldGoalsAttempted2"],
                "fg3m": p["FieldGoalsMade3"], "fg3a": p["FieldGoalsAttempted3"],
                "ftm": p["FreeThrowsMade"], "fta": p["FreeThrowsAttempted"],
                "oreb": p["OffensiveRebounds"], "dreb": p["DefensiveRebounds"],
                "ast": p["Assistances"], "stl": p["Steals"], "tov": p["Turnovers"],
                "blk": p["BlocksFavour"], "pf": p["FoulsCommited"], "plus_minus": p["Plusminus"],
            })
    team_a_is_man = pbp["CodeTeamA"].strip() == "MAN"

    events = [{"comp": "EuroCup", "game_id": game_id, "period": 1, "elapsed": 0, "kind": "START",
               "player": row["player"], "man": 0, "opp": 0} for row in box if row["starter"]]
    home = away = 0
    assists, made = [], None
    man_score = opp_score = 0
    for period, key in enumerate(PERIOD_QUARTERS, start=1):
        rows = pbp.get(key) or []
        if not rows:
            continue
        for row in sorted(rows, key=lambda r: r["NUMBEROFPLAY"]):
            if row["PLAYTYPE"] in EL_MADE_FG:
                made = row
            elif (row["PLAYTYPE"] == "AS" and made is not None and row["CODETEAM"].strip() == "MAN"
                  and made["CODETEAM"].strip() == "MAN"
                  and row["NUMBEROFPLAY"] - made["NUMBEROFPLAY"] <= 10):
                assists.append({"comp": "EuroCup", "game_id": game_id, "passer": display_name(row["PLAYER"]),
                                "scorer": display_name(made["PLAYER"]),
                                "pts": 3 if made["PLAYTYPE"] == "3FGM" else 2})
            if row["POINTS_A"] is not None:
                home = row["POINTS_A"]
            if row["POINTS_B"] is not None:
                away = row["POINTS_B"]
            man_score, opp_score = (home, away) if team_a_is_man else (away, home)
            if row["PLAYTYPE"] in ("IN", "OUT") and row["CODETEAM"].strip() == "MAN":
                left = minutes_to_seconds(row["MARKERTIME"]) if row["MARKERTIME"] else 0
                events.append({"comp": "EuroCup", "game_id": game_id, "period": period,
                               "elapsed": period_start(period) + period_length(period) - left,
                               "kind": row["PLAYTYPE"], "player": display_name(row["PLAYER"]),
                               "man": man_score, "opp": opp_score})
        events.append({"comp": "EuroCup", "game_id": game_id, "period": period,
                       "elapsed": period_start(period) + period_length(period), "kind": "END",
                       "player": "", "man": man_score, "opp": opp_score})
    game = {"comp": "EuroCup", "game_id": game_id, "opponent": opponent,
            "home": int(info["home"]), "man_pts": man_score, "opp_pts": opp_score}
    return game, box, events, assists


def fetch_shots(info: dict) -> list[dict]:
    """Manresa field-goal attempts with coordinates for one EuroCup game."""
    rows = get(EL_POINTS.format(n=info["number"])).json()["Rows"]
    return [{"game_id": f"EC{info['number']}", "player": display_name(r["PLAYER"]),
             "made": int(r["ID_ACTION"].strip().endswith("M")), "three": int(r["ID_ACTION"].startswith("3")),
             "x": r["COORD_X"], "y": r["COORD_Y"], "zone": r["ZONE"].strip()}
            for r in rows if r["TEAM"].strip() == "MAN" and r["ID_ACTION"].strip()[:1] in "23"
            and r["ID_ACTION"].strip()[1:3] == "FG"]


def fetch_heights() -> pd.DataFrame:
    """Roster heights (cm) and positions from the EuroLeague club endpoint."""
    rows = []
    for person in get(EL_PEOPLE).json():
        if person["type"] != "J" and person["typeName"] != "Player":
            continue
        info = person["person"]
        rows.append({"player": display_name(info["name"]), "height_cm": info["height"] or None,
                     "position_en": person["positionName"]})
    return pd.DataFrame(rows)


def main() -> None:
    """Fetch everything and write the CSVs."""
    OUT.mkdir(parents=True, exist_ok=True)
    games, boxes, events, assists = [], [], [], []
    ec_games = eurocup_games()
    parsed = [parse_acb_game(slug) for slug in acb_game_slugs()]
    parsed += [parse_eurocup_game(info) for info in ec_games]
    for game, box, evs, ast in parsed:
        games.append(game)
        boxes += box
        events += evs
        assists += ast
    pd.DataFrame(assists).to_csv(OUT / "assists.csv", index=False)
    pd.DataFrame([row for info in ec_games for row in fetch_shots(info)]).to_csv(
        OUT / "shots.csv", index=False)
    pd.DataFrame(games).to_csv(OUT / "games.csv", index=False)
    pd.DataFrame(boxes).to_csv(OUT / "box.csv", index=False)
    pd.DataFrame(events).to_csv(OUT / "events.csv", index=False)
    fetch_heights().to_csv(OUT / "heights.csv", index=False)
    print(f"{len(games)} games, {len(boxes)} box rows, {len(events)} events -> {OUT}")


if __name__ == "__main__":
    main()
