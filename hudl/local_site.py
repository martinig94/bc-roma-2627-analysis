"""Build a Hudl-only analysis as local pages with the look of the published site.

Usage:
    python -m hudl.local_site reports/hudl_api/trento_hudl_only \
        --matchup reports/matchup_BC_Roma_vs_Dolomiti_Energia_Trentino_before_2026-12-06

Reads the markdown pages of the folder (``analysis.md`` and the pages listed in
``SUBPAGES``) and writes ``<folder>/site/``: the same template, styles, automatic
blocks (``{{ standings }}``, ``{{ figure: ... }}``, ...) and section drop-downs as
``notebooks/build_site.py``, with the figures of the matchup report and of the
folder. Nothing is written into ``docs/``: the pages are not published.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

from hudl.client import ROOT

sys.path.insert(0, str(ROOT / "notebooks"))
import build_site  # noqa: E402  (the notebooks folder is not a package)
import pages  # noqa: E402

SUBPAGES = {
    "key_numbers": "Key numbers",
    "player_cards": "Player cards",
    "individual_tendencies": "Individual tendencies",
    "defense_tendencies": "Defense tendencies",
    "offense_tendencies": "Offense tendencies",
    "workflow_comparison": "Hudl vs current workflow",
}
HOME = "index.html"
BANNER = (
    "**Local test page, not published.** Hudl-only version of the analysis: play types, defenders, "
    "coverages and lineups come from the Hudl Instat feed, the automatic blocks from the LBA data. No Synergy."
)


def local_links(markdown: str, site: Path) -> str:
    """Point the site's links (home page, methodology) to files that open from disk."""
    methodology = os.path.relpath(build_site.DOCS / "methodology" / HOME, site).replace(os.sep, "/")
    markdown = markdown.replace("](./#", f"]({HOME}#").replace("](./)", f"]({HOME})")
    return markdown.replace("](../../methodology/#", f"]({methodology}#")


def page_html(markdown: str, title: str, site: Path) -> str:
    """Return a full page: site template around the markdown, with the test banner."""
    body = build_site.md_html(local_links(build_site.add_flags(markdown, [BANNER]), site))
    return build_site.shell(f"{title} · {build_site.CFG['site_title']}", body, "", {"games": [], "pages": []})


def main() -> None:
    """Write the local pages of one analysis folder."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("folder", type=Path, help="folder with the markdown pages and the Hudl figures")
    parser.add_argument("--matchup", type=Path, required=True, help="matchup report folder (auto.json, LBA figures)")
    args = parser.parse_args()
    site = args.folder / "site"
    shutil.rmtree(site, ignore_errors=True)
    shutil.copytree(build_site.WEEKLY / "assets", site / "assets")
    files = build_site.copy_images(args.matchup, args.folder, dest=site)

    auto = json.loads((args.matchup / "auto.json").read_text(encoding="utf-8"))
    comparison = auto["comparison"]
    auto.update(
        date_long=build_site.long_date(auto["date"]),
        team_suffix=build_site.ordinal(comparison["team"]["position"]),
        opp_suffix=build_site.ordinal(comparison["opp"]["position"]),
        team_link=None,
    )
    sources = {name: args.folder / f"{name}.md" for name in SUBPAGES}
    auto["subpages"] = [
        {"name": name, "title": title} for name, title in SUBPAGES.items() if sources[name].exists()
    ]
    game = f"{auto['home_team']} vs {auto['away_team']}"

    _, body = pages.split_front((args.folder / "analysis.md").read_text(encoding="utf-8"))
    markdown = pages.expand(body, "analysis", auto, files, build_site.AUTHOR)
    (site / HOME).write_text(page_html(markdown, game, site), encoding="utf-8")
    for page in auto["subpages"]:
        _, body = pages.split_front(sources[page["name"]].read_text(encoding="utf-8"))
        markdown = pages.expand(body, "analysis", auto, files, build_site.AUTHOR)
        heading = re.search(r"^# (.+)$", markdown, re.M)
        title = heading.group(1) if heading else page["title"]
        head, _, rest = markdown.partition("\n")
        back = f"[← Back to the opponent analysis: {game}]({HOME})"
        html = page_html(f"{head}\n\n{back}\n{rest}", f"{title} · {game}", site)
        (site / f"{page['name']}.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
