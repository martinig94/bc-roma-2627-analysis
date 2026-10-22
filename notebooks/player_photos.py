"""Download and cache player photos (thumbnails) from the legabasket.it media CDN.

    python notebooks/player_photos.py                 # every player of the configured team found in data/raw
    python notebooks/player_photos.py --team "Maxima Roma"

The box-score JSON carries `player_p_key` (only on some payloads); the original picture is
https://lba-media.s3.eu-south-1.amazonaws.com/<key>. Thumbnails (max 240 px, JPEG) are stored in
data/photos/<player_id>.jpg and committed, so building the site never needs the network.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image

import weekly_config

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PHOTOS = DATA / "photos"
RAW = DATA / "raw"
ROSTERS_CSV = DATA / "team_rosters.csv"
CDN = "https://lba-media.s3.eu-south-1.amazonaws.com"
USER_AGENT = "Mozilla/5.0 (lba-2627-data; research use)"
SIZE = 240              # thumbnail width limit in pixels (height limit is twice this)
HEIGHT_FACTOR = 2
DOWNLOAD_TIMEOUT_S = 60
JPEG_QUALITY = 88
BACKGROUND = "white"    # transparent pictures are flattened onto this
ALPHA_BAND = 3          # index of the alpha channel in an RGBA image


def photo_keys(team: str) -> dict[int, str]:
    """Return player_id -> picture key from all raw box scores of the team."""
    keys: dict[int, str] = {}
    for f in sorted(RAW.glob("*/box_score.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        m = d["match"]
        side = "ht" if m["h_team_name"] == team else "vt" if m["v_team_name"] == team else None
        for r in (d["scores"][side]["rows"] if side else []):
            if r.get("player_p_key"):
                keys[int(r["player_id"])] = r["player_p_key"]
    return keys


def roster_keys(team: str) -> dict[int, str]:
    """Return player_id -> picture key from data/team_rosters.csv: the whole roster, also players who have not played yet."""
    path = ROSTERS_CSV
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as fh:
        return {int(r["player_id"]): r["picture_key"] for r in csv.DictReader(fh)
                if r["team"] == team and r.get("picture_key")}


def fetch(player_id: int, key: str) -> Path | None:
    """Download one player's picture as a JPEG thumbnail into data/photos/ unless it is cached.

    Args:
        player_id: Legabasket player id (the file stem).
        key: Picture key on the media CDN.

    Returns:
        Path of the cached file, or None if the download or decoding failed.
    """
    dest = PHOTOS / f"{player_id}.jpg"
    if dest.exists():
        return dest
    try:
        request = Request(f"{CDN}/{key}", headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=DOWNLOAD_TIMEOUT_S) as r:
            img = Image.open(io.BytesIO(r.read()))
    except Exception as exc:  # network or format problem: the report just goes without that photo
        print(f"photo {player_id}: {exc}")
        return None
    img = img.convert("RGBA")
    bg = Image.new("RGB", img.size, BACKGROUND)
    bg.paste(img, mask=img.split()[ALPHA_BAND])
    bg.thumbnail((SIZE, SIZE * HEIGHT_FACTOR))
    PHOTOS.mkdir(parents=True, exist_ok=True)
    bg.save(dest, quality=JPEG_QUALITY, optimize=True)
    return dest


def main_quiet(team: str) -> None:
    """Fetch the photos of a team that are not cached yet (no-op offline); used by the report scripts."""
    for pid, key in {**photo_keys(team), **roster_keys(team)}.items():
        fetch(pid, key)


def main() -> None:
    """Fetch the photos of the team given by ``--team`` (default: the configured team) and list them."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", default=weekly_config.load()["team"], help="team name as in the box scores")
    a = ap.parse_args()
    keys = {**photo_keys(a.team), **roster_keys(a.team)}
    for pid, key in keys.items():
        print(pid, fetch(pid, key))


if __name__ == "__main__":
    main()
