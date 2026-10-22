"""Rebuild box_scores.csv and pbp.csv from the raw JSON in data/raw/ (no network).

Use after changing transform.py, e.g. to add a derived column.
"""
from __future__ import annotations

import json
import sys

from .collect import BOX_CSV, PBP_CSV, RAW, _write_csv
from .transform import BOX_FIELDS, PBP_FIELDS, box_rows, pbp_rows


def main() -> int:
    """Rewrite box_scores.csv and pbp.csv from data/raw/; return the exit code."""
    box_all: list[dict] = []
    pbp_all: list[dict] = []
    dirs = sorted((d for d in RAW.iterdir() if d.is_dir()), key=lambda d: int(d.name))
    for d in dirs:
        gid = int(d.name)
        box_all.extend(box_rows(json.loads((d / "box_score.json").read_text(encoding="utf-8"))))
        pbp_all.extend(pbp_rows(gid, json.loads((d / "play_by_play.json").read_text(encoding="utf-8"))))
    _write_csv(BOX_CSV, BOX_FIELDS, box_all)
    _write_csv(PBP_CSV, PBP_FIELDS, pbp_all)
    print(f"rebuilt from {len(dirs)} games: {len(box_all)} box rows, {len(pbp_all)} pbp events", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
