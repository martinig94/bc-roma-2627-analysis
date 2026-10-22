"""Shrink the PNG charts so the repository stays light.

Charts have few distinct colours: a 256-colour palette (alpha kept) is visually the same and about 4x smaller.
Already-palettised files are left alone, so running it twice changes nothing.

    python notebooks/imgopt.py            # every PNG under reports/ weekly/ docs/
    python notebooks/imgopt.py some/dir   # only that folder
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
FOLDERS = ("reports", "weekly", "docs")


def shrink_png(path: Path) -> int:
    """Re-save `path` as an optimised 256-colour PNG when that is smaller; returns the bytes saved."""
    path = Path(path)
    before = path.stat().st_size
    with Image.open(path) as im:
        if im.mode == "P":
            return 0
        im.load()
        method = Image.Quantize.FASTOCTREE if im.mode == "RGBA" else Image.Quantize.MEDIANCUT
        small = im.quantize(256, method=method, dither=Image.Dither.NONE)
    tmp = path.with_name(path.name + ".tmp")
    small.save(tmp, "PNG", optimize=True)
    after = tmp.stat().st_size
    if after < before:
        tmp.replace(path)
        return before - after
    tmp.unlink()
    return 0


def shrink_tree(*folders: Path) -> tuple[int, int]:
    n = saved = 0
    for folder in folders:
        for f in sorted(Path(folder).rglob("*.png")):
            s = shrink_png(f)
            n += bool(s); saved += s
    return n, saved


if __name__ == "__main__":
    targets = [Path(a) for a in sys.argv[1:]] or [ROOT / d for d in FOLDERS]
    n, saved = shrink_tree(*targets)
    print(f"{n} PNG files shrunk, {saved / 1e6:.1f} MB saved")
