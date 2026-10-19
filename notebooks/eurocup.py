"""EuroCup data: results of every game of the season, club rosters with headshots, and standings as of any date.

    python notebooks/eurocup.py                 # fetch results + the rosters (with headshots) of BC Roma and its opponents
    python notebooks/eurocup.py --clubs BCR MAN # other clubs (EuroLeague club codes)

Source: the EuroLeague live API (api-live.euroleague.net), the one wrapped by the `euroleague-api` package
(https://github.com/giasemidis/euroleague_api). Results come through that package (get_gamecodes_season, competition "U");
the club rosters (height, position, headshot) come from the club "people" endpoint, which the package does not wrap.
Needs network access to the host, so it runs in the daily GitHub Action; the files it writes are committed:

  data/eurocup/results.csv    one row per game of the season, played or not: gamecode, round, date, teams, scores, played
  data/eurocup/people.csv     club, player, height_cm, position, photo_url
  data/eurocup/photos/<photo_name>.jpg   headshot thumbnails (name key as in player_names.photo_name)

Standings are computed here from results.csv, as of any date, for the group of the team: EuroCup's regular season is played in
groups, and a team's group is the set of teams connected to it through the full schedule (the teams of a group only meet each
other). Ranking: wins, then the games among the tied teams, then point difference (see standings.py); the official tie-breaks
may differ slightly.
"""
from __future__ import annotations

import argparse
import io
import re
from pathlib import Path

import pandas as pd

import standings as st
import weekly_config
from player_names import display_name, find_image_url, photo_name

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "eurocup"
SEASON = 2026
CFG = weekly_config.load()
# EuroCup spelling -> our spelling (the same map the EuroCup box-score file uses)
NAME_FIX = {"ROMA BASKETBALL": "BC Roma", "MAXIMA ROMA": "Maxima Roma"}
PEOPLE = "https://api-live.euroleague.net/v2/competitions/U/seasons/U{season}/clubs/{club}/people"
RESULT_COLS = ["gamecode", "round", "date", "home_code", "home", "home_score", "away_code", "away", "away_score", "played"]


def team_name(raw: str) -> str:
    raw = str(raw).strip()
    return NAME_FIX.get(raw.upper(), raw.title())


# ── fetch ───────────────────────────────────────────────────────────────────────
def fetch_results(season: int = SEASON) -> pd.DataFrame:
    """Every game of the EuroCup season (the results feed lists the whole schedule, played or not)."""
    from euroleague_api.game_metadata import GameMetadata
    raw = GameMetadata("U").get_gamecodes_season(season)
    missing = [c for c in ("gameCode", "Round", "date", "homecode", "hometeam", "homescore", "awaycode", "awayteam", "awayscore", "played") if c not in raw]
    if missing:
        raise SystemExit(f"EuroCup results feed has no column(s) {missing}; got {list(raw.columns)}")
    out = pd.DataFrame({
        "gamecode": raw.gameCode, "round": raw.Round,
        "date": pd.to_datetime(raw.date, format="%b %d, %Y", errors="coerce").dt.strftime("%Y-%m-%d"),
        "home_code": raw.homecode.str.strip(), "home": raw.hometeam.map(team_name), "home_score": raw.homescore,
        "away_code": raw.awaycode.str.strip(), "away": raw.awayteam.map(team_name), "away_score": raw.awayscore,
        "played": raw.played.astype(bool),
    })
    return out[RESULT_COLS].sort_values("gamecode")


def fetch_people(club: str, season: int = SEASON) -> pd.DataFrame:
    import requests
    r = requests.get(PEOPLE.format(season=season, club=club), headers={"Accept": "application/json"}, timeout=60)
    r.raise_for_status()
    rows = []
    for person in r.json():
        if person.get("type") != "J" and person.get("typeName") != "Player":
            continue
        info = person["person"]
        rows.append({"club": club, "player": display_name(info["name"]), "height_cm": info.get("height") or None,
                     "position": person.get("positionName"), "photo_url": find_image_url(person)})
    return pd.DataFrame(rows)


def save_photos(people: pd.DataFrame, size: int = 240) -> int:
    """Headshot thumbnails into data/eurocup/photos/<photo_name>.jpg; a missing picture never stops the run."""
    import requests
    from PIL import Image
    (DATA / "photos").mkdir(parents=True, exist_ok=True)
    n = 0
    for r in people.itertuples():
        dest = DATA / "photos" / f"{photo_name(r.player)}.jpg"
        if not isinstance(r.photo_url, str) or dest.exists():
            continue
        try:
            img = Image.open(io.BytesIO(requests.get(r.photo_url, timeout=60).content)).convert("RGBA")
        except Exception as exc:
            print(f"photo {r.player}: {exc}")
            continue
        bg = Image.new("RGB", img.size, "white"); bg.paste(img, mask=img.split()[3]); bg.thumbnail((size, size * 2))
        bg.save(dest, quality=88, optimize=True)
        n += 1
    return n


# ── which rosters to fetch ──────────────────────────────────────────────────────
def club_codes(results: pd.DataFrame, team: str, schedule: Path | None = None) -> list[str]:
    """Club codes of the team, of every opponent it has played, and of the EuroCup opponents still to come in weekly/schedule.csv
    (matched to the results by name), so the roster and headshots of the next opponent are there before the game."""
    mine = results[(results.home == team) | (results.away == team)]
    codes = {*mine.home_code, *mine.away_code}
    if schedule is not None and schedule.exists():
        names = {**dict(zip(results.home, results.home_code)), **dict(zip(results.away, results.away_code))}
        for r in pd.read_csv(schedule, dtype=str, keep_default_na=False).itertuples():
            if r.competition.lower() != "eurocup":
                continue
            hit = find_team(names, r.opponent)
            if hit:
                codes.add(names[hit])
    return sorted(codes)


# ── standings ───────────────────────────────────────────────────────────────────
def load_results(data: Path = ROOT / "data") -> pd.DataFrame | None:
    path = data / "eurocup" / "results.csv"
    return pd.read_csv(path) if path.exists() else None


def group_teams(results: pd.DataFrame, team: str) -> set[str]:
    """The teams connected to `team` through the full schedule (its group)."""
    links: dict[str, set[str]] = {}
    for h, a in zip(results.home, results.away):
        links.setdefault(h, set()).add(a); links.setdefault(a, set()).add(h)
    seen, todo = set(), [team]
    while todo:
        t = todo.pop()
        if t not in seen:
            seen.add(t); todo += list(links.get(t, ()))
    return seen


def games_frame(results: pd.DataFrame, team: str) -> pd.DataFrame:
    """The team's group's games in the column layout of data/games.csv, so standings.py can rank and draw them."""
    grp = group_teams(results, team)
    r = results[results.home.isin(grp)]
    return pd.DataFrame({
        "game_id": r.gamecode, "round": r["round"], "match_datetime": r.date.astype(str) + "T00:00:00", "game_status": r.played.map({True: 2, False: 0}),
        "home_team": r.home, "away_team": r.away, "home_score": r.home_score, "away_score": r.away_score,
    }).reset_index(drop=True)


def find_team(names, wanted: str) -> str | None:
    """Our name of a club -> its name in the results feed (exact, else the closest spelling)."""
    import difflib
    low = {n.lower(): n for n in names}
    hit = difflib.get_close_matches(wanted.lower(), list(low), n=1, cutoff=0.6)
    return low[hit[0]] if hit else None


def standings_before(results: pd.DataFrame, team: str, before: str) -> pd.DataFrame | None:
    """The team's group table as of `before` (games played strictly before that date); None when the team is not in the data."""
    frame = games_frame(results, team)
    if frame.empty:
        return None
    return st.standings(frame, before)
