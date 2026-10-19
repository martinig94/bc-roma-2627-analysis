"""Settings of the weekly report, read from weekly/config.json (team, season, author, EuroCup file)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = {"team": "BC Roma", "season": "2026/27", "league": "LBA Serie A", "author": "", "eurocup_file": "", "comments": {}}


def load() -> dict:
    path = ROOT / "weekly" / "config.json"
    cfg = dict(DEFAULTS)
    if path.exists():
        cfg.update(json.loads(path.read_text(encoding="utf-8")))
    cfg["site_title"] = f"{cfg['team']} {cfg['season']} · weekly report"
    return cfg
