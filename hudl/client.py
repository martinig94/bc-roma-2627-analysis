"""Minimal client for the Hudl Instat basketball feed API (read-only).

Credentials come from ``.env`` (HUDL_INSTAT_ID, HUDL_INSTAT_KEY). URLs are never
printed or logged because they contain the key.

Example:
    client = InstatClient()
    teams = client.get(261, tournament_id=115, season_id=36)
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

BASE_URL = "https://service.instatfootball.com/feed.php"
MIN_INTERVAL_S = 0.15  # API limit is 10 requests per second
TIMEOUT_S = 60
ROOT = Path(__file__).resolve().parents[1]

LBA_TOURNAMENT_ID = 115
EUROCUP_TOURNAMENT_ID = 18
SEASON_2025_26 = 36
BC_ROMA_TEAM_ID = 1182311

TEMPLATES = {
    "match_markers": 23,
    "match_info": 24,
    "team_lineups": 25,
    "calendar": 26,
    "fives": 311,
    "player_match_stats": 28,
    "team_match_stats": 29,
    "player_season_stats": 185,
    "team_season_stats": 318,
    "player_info": 263,
    "team_info": 264,
    "tournament_teams": 261,
    "tournaments": 262,
    "seasons": 204,
    "standings": 259,
    "player_career": 265,
}


class InstatError(RuntimeError):
    """Raised when the API returns an error or an unparsable body."""


class InstatClient:
    """Rate-limited GET client for the Instat feed."""

    def __init__(self) -> None:
        load_dotenv(ROOT / ".env")
        self._id = os.environ["HUDL_INSTAT_ID"]
        self._key = os.environ["HUDL_INSTAT_KEY"]
        self._last_call = 0.0

    def get(self, tpl: int, fmt: str = "json", **params: Any) -> Any:
        """Call one template and return parsed JSON (or text for other formats).

        Args:
            tpl: Template id (see TEMPLATES).
            fmt: json, xml, csv or tsv.
            **params: Query parameters such as match_id, team_id, season_id.

        Returns:
            Parsed JSON for ``fmt="json"``, raw text otherwise.

        Raises:
            InstatError: On HTTP error, API error body or invalid JSON.
        """
        wait = MIN_INTERVAL_S - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        query = {
            "id": self._id,
            "key": self._key,
            "tpl": tpl,
            "lang": "en",
            "lang_id": 1,
            "format": fmt,
            **params,
        }
        response = requests.get(BASE_URL, params=query, timeout=TIMEOUT_S)
        self._last_call = time.monotonic()
        if response.status_code != 200:
            raise InstatError(f"tpl={tpl} HTTP {response.status_code}: {response.text[:200]}")
        if fmt != "json":
            return response.text
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise InstatError(f"tpl={tpl} not JSON: {response.text[:200]}") from exc
