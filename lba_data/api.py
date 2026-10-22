"""Thin client for the (undocumented) legabasket.it JSON API.

Endpoints were discovered by watching the network traffic of the official
site (Next.js app) in September 2026. They are public and need no auth, but
they are not a supported API: expect them to change without notice.

    GET /api/championships/get-championships?s=<year>&cs_id=1&items=1000
        -> competitions for a season (cs_id=1 is Serie A). Regular Season
           2026/27 is championship id 602.
    GET /api/teams/get-teams?year=<year>&items=50
        -> the 16 teams of that season. NOTE: team ids are re-issued every
           season (Milano was 1649 in 2024/25, 1751 in 2026/27).
    GET /api/championships/get-championships-calendar-by-id?id=<champ>&d=<giornata>
        -> matches of one round ("giornata"); `filters.days` lists all rounds.
    GET /api/championships/get-championships-matches-by-id?id=<game>
        -> match header (teams, venue, quarter scores, coaches, referees).
    GET /api/championships/get-championships-matches-scores-by-id?id=<game>&info=true
        -> full box score: scores.ht / scores.vt each with rows (players),
           totals and team (team rebounds etc.).
    GET /api/championships/get-championships-matches-play-by-play?id=<game>&info=true&sort=asc
        -> pbp.actions: every event with period, clock, score, player, team,
           x/y (0-100, % of the court) and shot/foul qualifiers; `legend`
           maps qualifier codes to descriptions.
    GET /api/teams/get-team-roster?id=<team>&year=<year>
        -> the "giocatori" table of the team page (legabasket.it/protagonisti/squadre/<year>/<team>/...):
           `players` with number, role, birth date/place, nationality, height, weight and contract dates.
    GET /api/matches/get-championship-matches-shots-by-id?id=<game>&info=1
        -> zone-aggregated shooting per team (derived; the pbp has the raw shots).
"""
from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://www.legabasket.it/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; bc-roma-2627-analysis/0.1; research use)",
    "Accept": "application/json",
    "Cache-Control": "no-cache",
}

REQUEST_TIMEOUT_S = 30   # seconds before one HTTP call is abandoned
DEFAULT_RETRIES = 3      # attempts per call before giving up
DEFAULT_PAUSE_S = 1.0    # base back-off in seconds; multiplied by the attempt number
SERIE_A_CS_ID = 1        # `cs_id` of Serie A in the championships endpoint
MAX_ITEMS_CHAMPIONSHIPS = 1000   # page size large enough to return every competition of a season
MAX_ITEMS_TEAMS = 50             # page size large enough to return every team of a season

# game_status values seen on the calendar
STATUS_SCHEDULED = "0"
STATUS_LIVE = "1"
STATUS_FINISHED = "2"


def get(path: str, params: dict[str, Any] | None = None, retries: int = DEFAULT_RETRIES,
        pause: float = DEFAULT_PAUSE_S) -> dict:
    """Return the decoded JSON of ``GET {BASE}/{path}``, retrying with a growing pause.

    Args:
        path: Endpoint path relative to ``BASE``.
        params: Query-string parameters.
        retries: Number of attempts before giving up.
        pause: Base sleep in seconds between attempts (times the attempt number).

    Returns:
        The parsed JSON payload.

    Raises:
        RuntimeError: If every attempt failed; the last error is chained.
    """
    url = f"{BASE}/{path}"
    if params:
        url += "?" + urlencode(params)
    last: Exception | None = None
    for attempt in range(retries):
        try:
            with urlopen(Request(url, headers=HEADERS), timeout=REQUEST_TIMEOUT_S) as resp:
                return json.load(resp)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:  # pragma: no cover - network
            last = exc
            time.sleep(pause * (attempt + 1))
    raise RuntimeError(f"failed after {retries} attempts: {url}") from last


def championships(year: int) -> list[dict]:
    """Return the Serie A competitions (regular season, play-offs...) of a season."""
    params = {"s": year, "cs_id": SERIE_A_CS_ID, "items": MAX_ITEMS_CHAMPIONSHIPS}
    return get("championships/get-championships", params)["competitions"]


def teams(year: int) -> list[dict]:
    """Return the teams of a season."""
    return get("teams/get-teams", {"year": year, "items": MAX_ITEMS_TEAMS})["teams"]


def calendar(championship_id: int, day: int | None = None) -> dict:
    """Return the calendar of a championship: all rounds' index, or the matches of round ``day``."""
    params: dict[str, Any] = {"id": championship_id}
    if day is not None:
        params["d"] = day
    return get("championships/get-championships-calendar-by-id", params)


def match(game_id: int) -> dict:
    """Return the match header (teams, venue, quarter scores, coaches, referees)."""
    return get("championships/get-championships-matches-by-id", {"id": game_id})


def box_score(game_id: int) -> dict:
    """Return the full box score (players, team and total rows of both sides)."""
    return get("championships/get-championships-matches-scores-by-id", {"id": game_id, "info": "true"})


def play_by_play(game_id: int) -> dict:
    """Return every play-by-play event of a game in chronological order."""
    return get(
        "championships/get-championships-matches-play-by-play",
        {"id": game_id, "info": "true", "sort": "asc"},
    )


def team_roster(team_id: int, year: int) -> dict:
    """Return the roster table ("giocatori") of a team for a season."""
    return get("teams/get-team-roster", {"id": team_id, "year": year})
