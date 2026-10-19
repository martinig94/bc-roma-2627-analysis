"""Download and cache player photos (thumbnails) from the legabasket.it media CDN.

    python notebooks/player_photos.py                 # every player of the configured team found in data/raw
    python notebooks/player_photos.py --team "Maxima Roma"

The box-score JSON carries `player_p_key` (only on some payloads); the original picture is
https://lba-media.s3.eu-south-1.amazonaws.com/<key>. Thumbnails (max 240 px, JPEG) are stored in
data/photos/<player_id>.jpg and committed, so building the site never needs the network.
"""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image

import weekly_config

ROOT = Path(__file__).resolve().parent.parent
PHOTOS = ROOT / "data" / "photos"
CDN = "https://lba-media.s3.eu-south-1.amazonaws.com"
SIZE = 240


def photo_keys(team: str) -> dict[int, str]:
    """player_id -> picture key, from all raw box scores of the team."""
    keys: dict[int, str] = {}
    for f in sorted((ROOT / "data" / "raw").glob("*/box_score.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        m = d["match"]
        side = "ht" if m["h_team_name"] == team else "vt" if m["v_team_name"] == team else None
        for r in (d["scores"][side]["rows"] if side else []):
            if r.get("player_p_key"):
                keys[int(r["player_id"])] = r["player_p_key"]
    return keys


def fetch(player_id: int, key: str) -> Path | None:
    dest = PHOTOS / f"{player_id}.jpg"
    if dest.exists():
        return dest
    try:
        with urlopen(Request(f"{CDN}/{key}", headers={"User-Agent": "Mozilla/5.0 (lba-2627-data; research use)"}), timeout=60) as r:
            img = Image.open(io.BytesIO(r.read()))
    except Exception as exc:  # network or format problem: the report just goes without that photo
        print(f"photo {player_id}: {exc}")
        return None
    img = img.convert("RGBA")
    bg = Image.new("RGB", img.size, "white"); bg.paste(img, mask=img.split()[3])
    bg.thumbnail((SIZE, SIZE * 2))
    PHOTOS.mkdir(parents=True, exist_ok=True)
    bg.save(dest, quality=88, optimize=True)
    return dest


def main_quiet(team: str) -> None:
    """Fetch the photos that are not cached yet (no-op offline); used by weekly_report.py."""
    for pid, key in photo_keys(team).items():
        fetch(pid, key)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", default=weekly_config.load()["team"])
    a = ap.parse_args()
    keys = photo_keys(a.team)
    for pid, key in keys.items():
        print(pid, fetch(pid, key))


if __name__ == "__main__":
    main()
