"""Settings of the weekly report, read from weekly/config.json (team, season, author, EuroCup file)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "weekly" / "config.json"
# Fallbacks for keys missing from weekly/config.json (this is the one place with the team/season literals).
DEFAULTS: dict[str, Any] = {
    "team": "BC Roma", "season": "2026/27", "league": "LBA Serie A", "author": "", "eurocup_file": "",
    "comments": {}, "links": [], "repo": "", "branch": "master", "reviews": False,
}


def load() -> dict[str, Any]:
    """Return the weekly-report settings: ``DEFAULTS`` overridden by weekly/config.json.

    Returns:
        Dict with team, season, league, author, eurocup_file, comments, links, repo, branch,
        reviews, plus the derived ``site_title``.
    """
    path = CONFIG_PATH
    cfg = dict(DEFAULTS)
    if path.exists():
        cfg.update(json.loads(path.read_text(encoding="utf-8")))
    cfg["site_title"] = f"{cfg['team']} {cfg['season']} · weekly report"
    return cfg
