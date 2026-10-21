"""Player name keys shared by the Manresa scripts and the site build (no third-party imports)."""
from __future__ import annotations

import re
import unicodedata


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


def photo_name(player: str) -> str:
    """File stem of a player's picture: data/manresa/photos/<photo_name>.jpg, photo_<photo_name>.jpg next to the report."""
    return re.sub(r"\W+", "_", player_key(player)).strip("_")


def display_name(name: str) -> str:
    """'ALLEN, TIMMY' -> 'Timmy Allen'; names already in that form are kept."""
    if "," not in name:
        return name.strip()
    last, first = (part.strip() for part in name.split(",", 1))
    return f"{first.title()} {last.title()}"


def find_image_url(obj, key_hint: bool = False) -> str | None:
    """First http(s) URL under keys that look like image/photo/headshot in a (nested) API object."""
    if isinstance(obj, str):
        return obj if key_hint and obj.startswith("http") else None
    items = obj.items() if isinstance(obj, dict) else enumerate(obj) if isinstance(obj, list) else []
    for k, v in items:
        hit = find_image_url(v, key_hint or bool(re.search(r"image|photo|head", str(k), re.I)))
        if hit:
            return hit
    return None


EC_NAME_FIX = {"BONACINI": "BONACCINI"}   # EuroCup spelling -> Legabasket spelling


def ec_surname(raw: str) -> str:
    """'WATSON JR, PAUL' (EuroLeague box score / play-by-play) -> 'WATSON': surname only, generation suffixes dropped, LBA spelling."""
    sur = raw.split(",")[0].replace(" JR.", "").replace(" JR", "").replace(" III", "").strip()
    return EC_NAME_FIX.get(sur, sur)
