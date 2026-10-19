"""Build the GitHub Pages site (docs/).

    python notebooks/build_site.py

Weekly reports (the landing page):
  reports/weekly/round-NN/auto.json + PNGs   written by weekly_report.py (automatic part)
  weekly/round-NN/notes.md (+ images)        your text
  weekly/template/page.md.j2                 page layout, merges the two
  -> docs/weekly/round-NN/index.html and the landing page docs/index.html (newest first)

Pre-match analyses (unchanged): every reports/matchup_*_before_<date>/ folder with a README.md is copied to
docs/analyses/<folder>/ and listed in docs/analyses.json; they are browsed from docs/prematch.html.
"""
from __future__ import annotations

import json
import re
import shutil
from datetime import date
from pathlib import Path

import jinja2
import markdown

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
WEEKLY = ROOT / "weekly"
AUTHOR = "Giulia Martini"
TPL = jinja2.Environment(loader=jinja2.FileSystemLoader(WEEKLY / "template"), autoescape=False, keep_trailing_newline=True)


def parse_notes(path: Path) -> dict:
    """`title:`/`summary:` lines, then `## key` sections of markdown. HTML comments are dropped; empty keys are omitted."""
    if not path.exists():
        return {}
    text = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)
    head, *parts = re.split(r"^## ", text, flags=re.M)
    notes = {k: v.strip() for k, v in re.findall(r"^(title|summary):(.*)$", head, re.M)}
    for part in parts:
        key, _, body = part.partition("\n")
        notes[key.strip()] = body.strip()
    return {k: v for k, v in notes.items() if v}


def ordinal(n: int) -> str:
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def md_html(text: str) -> str:
    return markdown.markdown(text, extensions=["tables", "md_in_html", "sane_lists"])


def shell(title: str, body: str, root: str) -> str:
    return TPL.get_template("site.html.j2").render(title=title, body=body, root=root)


def build_weekly() -> list[dict]:
    shutil.rmtree(DOCS / "weekly", ignore_errors=True)
    weeks = []
    for src in sorted((ROOT / "reports" / "weekly").glob("round-*")):
        auto_path = src / "auto.json"
        if not auto_path.exists():
            continue
        a = json.loads(auto_path.read_text(encoding="utf-8"))
        a["date_long"] = date.fromisoformat(a["date"]).strftime("%A %d %B %Y")
        a["position_suffix"] = ordinal(a["position"])
        notes_dir = WEEKLY / src.name
        n = parse_notes(notes_dir / "notes.md")
        page_md = TPL.get_template("page.md.j2").render(a=a, n=n, author=AUTHOR)
        dest = DOCS / "weekly" / src.name
        dest.mkdir(parents=True)
        for f in [*src.glob("*.png"), *src.glob("*.jpg")]:
            shutil.copy(f, dest / f.name)
        for f in notes_dir.glob("*"):
            if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}:
                shutil.copy(f, dest / f.name)
        title = n.get("title") or f"Round {a['round']}: {a['team']} {a['score_for']}-{a['score_against']} {a['opponent']}"
        (dest / "index.html").write_text(shell(f"{title} · BC Roma weekly", md_html(page_md), "../../"), encoding="utf-8")
        weeks.append({"slug": src.name, "round": a["round"], "title": title, "summary": n.get("summary", ""), "date": a["date"],
                      "opponent": a["opponent"], "home": a["home"], "win": a["win"],
                      "score": f"{a['score_for']}-{a['score_against']}", "record": a["record"], "position": a["position"]})
    weeks.sort(key=lambda w: w["round"], reverse=True)
    return weeks


def build_landing(weeks: list[dict]) -> None:
    if not weeks:
        body = "<h1>BC Roma 2026/27 weekly report</h1><p>The first report is coming soon.</p>"
    else:
        cards = []
        for i, w in enumerate(weeks):
            cls = "win" if w["win"] else "loss"
            where = "vs" if w["home"] else "at"
            summary = f"<div>{w['summary']}</div>" if w["summary"] else ""
            cards.append(
                f'<a class="card{" latest" if i == 0 else ""}" href="weekly/{w["slug"]}/">'
                f'<div class="rd">Round {w["round"]} · {w["date"]}{" · latest" if i == 0 else ""}</div>'
                f'<div class="score"><span class="{cls}">{"W" if w["win"] else "L"}</span> {w["score"]} {where} {w["opponent"]}</div>'
                f'<div class="rd">{w["record"]} · {w["position"]}{ordinal(w["position"])} in the standings</div>{summary}</a>')
        body = ("<h1>BC Roma 2026/27 weekly report</h1>"
                "<p>One report per round of the LBA Serie A: the game, the players, the league table. "
                "Pre-match opponent analyses are <a href=\"prematch.html\">here</a>.</p>"
                f'<div class="cards">{"".join(cards)}</div>')
    (DOCS / "index.html").write_text(shell("BC Roma weekly report", body, ""), encoding="utf-8")
    (DOCS / "weekly.json").write_text(json.dumps(weeks, indent=2, ensure_ascii=False), encoding="utf-8")


def build_prematch() -> None:
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
    print(f"{len(entries)} pre-match analyses")


def main() -> None:
    weeks = build_weekly()
    build_landing(weeks)
    build_prematch()
    print(f"{len(weeks)} weekly reports in {DOCS}")


if __name__ == "__main__":
    main()
