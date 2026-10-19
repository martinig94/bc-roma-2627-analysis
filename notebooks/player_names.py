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
