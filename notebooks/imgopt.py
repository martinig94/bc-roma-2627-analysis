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
PALETTE_COLORS = 256   # PNG palette size
BYTES_PER_MB = 1e6


def shrink_png(path: Path) -> int:
    """Re-save a PNG as an optimised 256-colour palette image when that is smaller.

    Args:
        path: PNG file to shrink in place.

    Returns:
        Bytes saved (0 if the file was already palettised or would not get smaller).
    """
    path = Path(path)
    before = path.stat().st_size
    with Image.open(path) as im:
        if im.mode == "P":
            return 0
        im.load()
        method = Image.Quantize.FASTOCTREE if im.mode == "RGBA" else Image.Quantize.MEDIANCUT
        small = im.quantize(PALETTE_COLORS, method=method, dither=Image.Dither.NONE)
    tmp = path.with_name(path.name + ".tmp")
    small.save(tmp, "PNG", optimize=True)
    after = tmp.stat().st_size
    if after < before:
        tmp.replace(path)
        return before - after
    tmp.unlink()
    return 0


def shrink_tree(*folders: Path) -> tuple[int, int]:
    """Shrink every PNG under the given folders; return (files shrunk, total bytes saved)."""
    n = saved = 0
    for folder in folders:
        for f in sorted(Path(folder).rglob("*.png")):
            s = shrink_png(f)
            n += bool(s)
            saved += s
    return n, saved


def main(argv: list[str] | None = None) -> None:
    """Shrink the PNGs of the folders named on the command line (default ``FOLDERS`` under ROOT)."""
    args = sys.argv[1:] if argv is None else argv
    targets = [Path(a) for a in args] or [ROOT / d for d in FOLDERS]
    n, saved = shrink_tree(*targets)
    print(f"{n} PNG files shrunk, {saved / BYTES_PER_MB:.1f} MB saved")


if __name__ == "__main__":
    main()
