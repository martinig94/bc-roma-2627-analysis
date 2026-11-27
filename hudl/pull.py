"""Download raw Hudl Instat payloads for every finished game of a season.

Usage:
    python -m hudl.pull --season 38

Writes ``data/hudl_raw/games/<match_id>/<template>.json`` (git-ignored) and skips
files that already exist, so a rerun only fetches what is new.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from hudl.client import (
    EUROCUP_TOURNAMENT_ID,
    LBA_TOURNAMENT_ID,
    ROOT,
    InstatClient,
    InstatError,
)

LOGGER = logging.getLogger(__name__)
RAW_DIR = ROOT / "data" / "hudl_raw"
FINISHED_STATUS = "Full breakdown"
MATCH_TEMPLATES = {"events": 89, "players": 129, "teams": 258, "fives": 311}
TOURNAMENTS = {"LBA": LBA_TOURNAMENT_ID, "EuroCup": EUROCUP_TOURNAMENT_ID}


def finished_matches(client: InstatClient, tournament_id: int, season_id: int) -> list[dict]:
    """Return calendar rows of games whose breakdown is complete.

    Args:
        client: Authenticated API client.
        tournament_id: Instat tournament id.
        season_id: Instat season id.

    Returns:
        List of calendar rows with status "Full breakdown".
    """
    calendar = client.get(
        26, tournament_id=tournament_id, season_id=season_id, date_start="", date_end=""
    )
    rows = calendar["data"]["row"]
    return [row for row in rows if row["status_name"] == FINISHED_STATUS]


def pull_match(client: InstatClient, match_id: str) -> None:
    """Download every template of one match that is not already on disk."""
    folder = RAW_DIR / "games" / match_id
    folder.mkdir(parents=True, exist_ok=True)
    for name, tpl in MATCH_TEMPLATES.items():
        target = folder / f"{name}.json"
        if target.exists():
            continue
        try:
            payload = client.get(tpl, match_id=match_id)
        except InstatError as exc:
            LOGGER.warning("match %s %s failed: %s", match_id, name, str(exc)[:120])
            continue
        target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    """Command line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--season", type=int, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    client = InstatClient()
    for label, tournament_id in TOURNAMENTS.items():
        matches = finished_matches(client, tournament_id, args.season)
        LOGGER.info("%s: %d finished matches", label, len(matches))
        (RAW_DIR / f"calendar_{label}_s{args.season}.json").write_text(
            json.dumps(matches, ensure_ascii=False), encoding="utf-8"
        )
        for match in matches:
            pull_match(client, match["id"])


if __name__ == "__main__":
    main()
