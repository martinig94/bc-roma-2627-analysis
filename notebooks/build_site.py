"""Build the GitHub Pages site (docs/).

    python notebooks/build_site.py

Three kinds of page, all reachable from the two dropdowns in the header of every page:

  BC Roma snapshots (dropdown 1)   one per game, using only data from before it
      reports/snapshot/round-NN/{auto.json, PNGs}  +  weekly/snapshot/round-NN/notes.md   ->  docs/snapshot/round-NN/
  Opponent analyses (dropdown 2)   one per opponent and game, with the comparison against the team
      reports/matchup_*_before_<date>/  README.md (hand-written, used as it is) or auto.json + weekly/opponent/<folder>/notes.md
      ->  docs/opponent/<folder>/
  Game reviews (landing page)      post-game, one per played round
      reports/review/round-NN/{auto.json, PNGs}  +  weekly/review/round-NN/notes.md      ->  docs/review/round-NN/

Notes files: `title:`/`summary:` lines, then `## key` sections of markdown merged into the templates in weekly/template/.
"""
from __future__ import annotations

import json
import re
import shutil
from datetime import date
from pathlib import Path

import jinja2
import markdown

import weekly_config

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
WEEKLY = ROOT / "weekly"
CFG = weekly_config.load()
AUTHOR = CFG["author"]
TPL = jinja2.Environment(loader=jinja2.FileSystemLoader(WEEKLY / "template"), autoescape=False, keep_trailing_newline=True)
IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}


# ── helpers ─────────────────────────────────────────────────────────────────────
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


def long_date(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%A %d %B %Y")


def md_html(text: str) -> str:
    return markdown.markdown(text, extensions=["tables", "md_in_html", "sane_lists"])


def copy_images(src: Path, *more: Path, dest: Path) -> list[str]:
    dest.mkdir(parents=True, exist_ok=True)
    names = []
    for folder in (src, *more):
        for f in sorted(folder.glob("*")):
            if f.suffix.lower() in IMAGES:
                shutil.copy(f, dest / f.name); names.append(f.name)
    return names


def folder_name(home: str, away: str, day: str) -> str:
    return f"matchup_{home.replace(' ', '_')}_vs_{away.replace(' ', '_')}_before_{day}"


def shell(title: str, body: str, root: str, nav: dict) -> str:
    return TPL.get_template("site.html.j2").render(title=title, body=body, root=root, nav=nav, site_title=CFG["site_title"], league=CFG["league"])


# ── page builders: each returns the list of entries it created ──────────────────
def build_opponents(nav_holder: dict) -> list[dict]:
    shutil.rmtree(DOCS / "opponent", ignore_errors=True)
    entries = []
    for folder in sorted((ROOT / "reports").glob("matchup_*_before_*")):
        slug, day = folder.name, folder.name.rsplit("_before_", 1)[1]
        dest = DOCS / "opponent" / slug
        notes_dir = WEEKLY / "opponent" / slug
        files = copy_images(folder, dest=dest)
        readme, auto_path = folder / "README.md", folder / "auto.json"
        if readme.exists():                          # hand-written page, used as it is
            text = readme.read_text(encoding="utf-8")
            title = re.search(r"^# (.+)$", text, re.M).group(1)
            page_md, rnd = text, None
            if (folder / "roster.json").exists():
                roster = json.loads((folder / "roster.json").read_text(encoding="utf-8"))
                block = TPL.from_string("{% from '_macros.j2' import roster_table %}## Roster\n\nPer-game averages before this game, "
                                        "league and EuroCup games. Shooting: percentage (attempts per game).\n\n"
                                        "{{ roster_table(r) }}\n\n").render(r=roster)
                k = page_md.find("\n## Sources")
                page_md = page_md[:k] + "\n" + block + page_md[k:] if k >= 0 else page_md + "\n\n" + block
        elif auto_path.exists():
            a = json.loads(auto_path.read_text(encoding="utf-8"))
            n = parse_notes(notes_dir / "notes.md")
            a.update(date_long=long_date(a["date"]), team_suffix=ordinal(a["comparison"]["team"]["position"]),
                     opp_suffix=ordinal(a["comparison"]["opp"]["position"]))
            a["team_link"] = f"../../snapshot/round-{a['round']:02d}/" if (ROOT / "reports" / "snapshot" / f"round-{a['round']:02d}" / "auto.json").exists() else None
            page_md = TPL.get_template("opponent.md.j2").render(a=a, n=n, author=AUTHOR, files=files)
            title, rnd = n.get("title") or f"{a['home_team']} vs {a['away_team']}", a["round"]
        else:
            continue
        entries.append({"slug": slug, "title": title, "date": day, "round": rnd, "html": md_html(page_md)})
    entries.sort(key=lambda e: e["date"], reverse=True)
    nav_holder["opponent"] = [{"url": f"opponent/{e['slug']}/", "label": f"{e['title']} · {e['date']}"} for e in entries]
    return entries


def build_snapshots(nav_holder: dict, opponents: list[dict]) -> list[dict]:
    shutil.rmtree(DOCS / "snapshot", ignore_errors=True)
    have_opp = {e["slug"] for e in opponents}
    entries = []
    for src in sorted((ROOT / "reports" / "snapshot").glob("round-*")):
        if not (src / "auto.json").exists():
            continue
        a = json.loads((src / "auto.json").read_text(encoding="utf-8"))
        notes_dir = WEEKLY / "snapshot" / src.name
        n = parse_notes(notes_dir / "notes.md")
        home_t, away_t = (a["team"], a["opponent_full"]) if a["home"] else (a["opponent_full"], a["team"])
        slug = folder_name(home_t, away_t, a["date"])
        a.update(date_long=long_date(a["date"]), position_suffix=ordinal(a["position"]),
                 opponent_link=f"../../opponent/{slug}/" if slug in have_opp else None)
        page_md = TPL.get_template("snapshot.md.j2").render(a=a, n=n, author=AUTHOR)
        title = n.get("title") or f"{a['team']} {'vs' if a['home'] else 'at'} {a['opponent']}"
        copy_images(src, notes_dir, dest=DOCS / "snapshot" / src.name)
        entries.append({"slug": src.name, "round": a["round"], "title": title, "date": a["date"], "html": md_html(page_md),
                        "opponent": a["opponent"], "home": a["home"], "record": a["record"], "position": a["position"],
                        "opponent_slug": slug if slug in have_opp else None})
    entries.sort(key=lambda e: e["round"], reverse=True)
    nav_holder["snapshot"] = [{"url": f"snapshot/{e['slug']}/",
                               "label": f"Round {e['round']}: {e['title']} · {e['date']}"} for e in entries]
    return entries


def build_reviews(nav_holder: dict) -> list[dict]:
    shutil.rmtree(DOCS / "review", ignore_errors=True)
    entries = []
    for src in sorted((ROOT / "reports" / "review").glob("round-*")):
        if not (src / "auto.json").exists():
            continue
        a = json.loads((src / "auto.json").read_text(encoding="utf-8"))
        a.update(date_long=long_date(a["date"]), position_suffix=ordinal(a["position"]))
        notes_dir = WEEKLY / "review" / src.name
        n = parse_notes(notes_dir / "notes.md")
        page_md = TPL.get_template("review.md.j2").render(a=a, n=n, author=AUTHOR)
        title = n.get("title") or f"Round {a['round']}: {a['team']} {a['score_for']}-{a['score_against']} {a['opponent']}"
        copy_images(src, notes_dir, dest=DOCS / "review" / src.name)
        entries.append({"slug": src.name, "round": a["round"], "title": title, "summary": n.get("summary", ""), "date": a["date"],
                        "opponent": a["opponent"], "home": a["home"], "win": a["win"], "html": md_html(page_md),
                        "score": f"{a['score_for']}-{a['score_against']}", "record": a["record"], "position": a["position"]})
    entries.sort(key=lambda e: e["round"], reverse=True)
    return entries


def write_pages(kind: str, entries: list[dict], nav: dict) -> None:
    for e in entries:
        page = DOCS / kind / e["slug"] / "index.html"
        page.write_text(shell(f"{e['title']} · {CFG['site_title']}", e["html"], "../../", nav), encoding="utf-8")


def build_landing(nav: dict, snaps: list[dict], opps: list[dict], reviews: list[dict]) -> None:
    def card(href: str, kicker: str, main: str, sub: str = "", latest: bool = False) -> str:
        return (f'<a class="card{" latest" if latest else ""}" href="{href}"><div class="rd">{kicker}</div>'
                f'<div class="score">{main}</div><div class="rd">{sub}</div></a>')
    parts = [f"<h1>{CFG['site_title']}</h1>",
             f"<p>The {CFG['league']} season of {CFG['team']}, in three parts: the team's situation before every game, "
             "the analysis of every opponent, and the review of every game played. "
             "The first two are always available from the dropdowns at the top; each uses only data from before its game.</p>"]
    if snaps or opps:
        parts.append("<h2>Next game</h2><div class=\"cards\">")
        if snaps:
            s = snaps[0]
            parts.append(card(f"snapshot/{s['slug']}/", f"{CFG['team']} before round {s['round']} · {s['date']}",
                              f"{'vs' if s['home'] else 'at'} {s['opponent']}", f"{s['record']} · {s['position']}{ordinal(s['position'])} in the standings", True))
        o = next((x for x in opps if snaps and x["slug"] == snaps[0]["opponent_slug"]), None)
        if o:
            parts.append(card(f"opponent/{o['slug']}/", f"Opponent analysis · {o['date']}", o["title"], "with the comparison against " + CFG["team"]))
        parts.append("</div>")
    if reviews:
        parts.append("<h2 id=\"reviews\">Game reviews</h2><div class=\"cards\">")
        for i, w in enumerate(reviews):
            cls, where = ("win" if w["win"] else "loss"), ("vs" if w["home"] else "at")
            parts.append(card(f"review/{w['slug']}/", f"Round {w['round']} · {w['date']}",
                              f'<span class="{cls}">{"W" if w["win"] else "L"}</span> {w["score"]} {where} {w["opponent"]}',
                              f"{w['record']} · {w['position']}{ordinal(w['position'])} in the standings" + (f"<div>{w['summary']}</div>" if w["summary"] else ""), i == 0))
        parts.append("</div>")
    (DOCS / "index.html").write_text(shell(CFG["site_title"], "".join(parts), "", nav), encoding="utf-8")


def main() -> None:
    nav: dict = {}
    opps = build_opponents(nav)
    snaps = build_snapshots(nav, opps)
    reviews = build_reviews(nav)
    nav.setdefault("snapshot", []); nav.setdefault("opponent", [])
    write_pages("opponent", opps, nav); write_pages("snapshot", snaps, nav); write_pages("review", reviews, nav)
    build_landing(nav, snaps, opps, reviews)
    for stale in ("prematch.html", "analyses", "analyses.json", "weekly", "weekly.json"):   # replaced by the structure above
        p = DOCS / stale
        shutil.rmtree(p) if p.is_dir() else p.unlink(missing_ok=True)
    print(f"{len(snaps)} snapshots, {len(opps)} opponent analyses, {len(reviews)} reviews in {DOCS}")


if __name__ == "__main__":
    main()
