"""Player name keys shared by the Manresa scripts and the site build (no third-party imports)."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

# EuroCup spelling -> Legabasket spelling
EC_NAME_FIX = {"BONACINI": "BONACCINI"}
# Generation suffixes dropped from EuroLeague surnames (longest first so " JR." wins over " JR")
GENERATION_SUFFIXES = (" JR.", " JR", " III")
IMAGE_KEY_PATTERN = re.compile(r"image|photo|head", re.I)   # API keys that hold a picture URL


def player_key(name: str) -> str:
    """Normalise 'Timmy Allen' and 'ALLEN, TIMMY' to the same 'allen t' key.

    Args:
        name: Player name, either 'First Last' or 'LAST, FIRST'.

    Returns:
        Lower-case ascii 'surname initial' key.
    """
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    name = re.sub(r"[^a-z, ]", " ", name)
    if "," in name:
        last, first = (part.strip() for part in name.split(",", 1))
    else:
        first, _, last = name.strip().partition(" ")
        last, first = (last or first), (first if last else "")
    last = re.sub(r"\s+", " ", last).strip()
    return f"{last} {first[:1]}".strip()


def photo_name(player: str) -> str:
    """Return the file stem of a player's picture.

    Used as data/manresa/photos/<photo_name>.jpg and photo_<photo_name>.jpg next to the report.
    """
    return re.sub(r"\W+", "_", player_key(player)).strip("_")


def display_name(name: str) -> str:
    """Return 'Timmy Allen' for 'ALLEN, TIMMY'; names already in that form are kept."""
    if "," not in name:
        return name.strip()
    last, first = (part.strip() for part in name.split(",", 1))
    return f"{first.title()} {last.title()}"


def find_image_url(obj: Any, key_hint: bool = False) -> str | None:
    """Return the first http(s) URL under keys that look like image/photo/headshot in a nested API object.

    Args:
        obj: Parsed JSON (dict, list or scalar).
        key_hint: True when an ancestor key already looked like an image key.
    """
    if isinstance(obj, str):
        return obj if key_hint and obj.startswith("http") else None
    items = obj.items() if isinstance(obj, dict) else enumerate(obj) if isinstance(obj, list) else []
    for k, v in items:
        hit = find_image_url(v, key_hint or bool(IMAGE_KEY_PATTERN.search(str(k))))
        if hit:
            return hit
    return None


def ec_surname(raw: str) -> str:
    """Return 'WATSON' for the EuroLeague name 'WATSON JR, PAUL': surname only, suffixes dropped, LBA spelling."""
    sur = raw.split(",")[0]
    for suffix in GENERATION_SUFFIXES:
        sur = sur.replace(suffix, "")
    sur = sur.strip()
    return EC_NAME_FIX.get(sur, sur)
