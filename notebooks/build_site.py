"""Build the GitHub Pages site (docs/) from the frozen matchup report folders.

    python notebooks/build_site.py

Every reports/matchup_*_before_<date>/ folder with a README.md becomes one entry of the drop-down:
its README and top-level PNGs are copied to docs/analyses/<folder>/ and listed in docs/analyses.json
(newest first). Run it after generating a new report, commit docs/, and the page updates.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"


def main() -> None:
    entries = []
    shutil.rmtree(DOCS / "analyses", ignore_errors=True)
    for folder in sorted((ROOT / "reports").glob("matchup_*_before_*")):
        readme = folder / "README.md"
        if not readme.exists():
            continue
        text = readme.read_text(encoding="utf-8")
        title = re.search(r"^# (.+)$", text, re.M).group(1)
        dest = DOCS / "analyses" / folder.name
        dest.mkdir(parents=True)
        shutil.copy(readme, dest / "README.md")
        for png in folder.glob("*.png"):
            shutil.copy(png, dest / png.name)
        entries.append({"slug": folder.name, "title": title, "date": folder.name.rsplit("_before_", 1)[1]})
    entries.sort(key=lambda e: e["date"], reverse=True)
    (DOCS / "analyses.json").write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(f"{len(entries)} analyses in {DOCS}")


if __name__ == "__main__":
    main()
