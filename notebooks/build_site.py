"""Build the GitHub Pages site (docs/).

    python notebooks/build_site.py

Three kinds of page. The dropdown in the header of every page lists the opponents (one entry per game, every competition);
the opponent analysis links to the BC Roma snapshot of the same game, and a game without an analysis opens its snapshot:

  BC Roma snapshots                one per game in every competition, using only data from before it
      reports/snapshot/<date>/{auto.json, PNGs}  +  weekly/snapshot/<date>/notes.md   ->  docs/snapshot/<date>/
  Opponent analyses                one per opponent and game, with the comparison against the team
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

import pandas as pd

import weekly_config
from player_names import photo_name
from team_games import next_games as next_games_df, team_games

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
WEEKLY = ROOT / "weekly"
CFG = weekly_config.load()
AUTHOR = CFG["author"]
TPL = jinja2.Environment(loader=jinja2.FileSystemLoader(WEEKLY / "template"), autoescape=False, keep_trailing_newline=True)
PAGES = ["methodology", "work-plan"]     # weekly/pages/<name>.md, in header order
IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}


# ── helpers ─────────────────────────────────────────────────────────────────────
def parse_notes(path: Path) -> dict:
    """`title:`/`summary:` lines, then `## key` sections of markdown. HTML comments are dropped; empty keys are omitted."""
    if not path.exists():
        return {}
    text = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)
    head, *parts = re.split(r"^## ", text, flags=re.M)
    notes = {k: v.strip() for k, v in re.findall(r"^(title|summary|reviewed):(.*)$", head, re.M)}
    for part in parts:
        key, _, body = part.partition("\n")
        notes[key.strip()] = body.strip()
    return {k: v for k, v in notes.items() if v}


def page_state(notes: dict) -> str:
    """"reviewed" (reviewed: yes in the notes), "progress" (some text written) or "draft" (automatic only)."""
    if notes.get("reviewed", "").strip().lower() in {"yes", "y", "true", "1", "reviewed"}:
        return "reviewed"
    return "progress" if any(k != "reviewed" for k in notes) else "draft"


def day_label(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%-d %b")


def game_text(r) -> str:
    rnd = f" round {int(r['round'])}" if r["competition"] == "LBA" and pd.notna(r["round"]) else ""
    return f"{'at' if r.home is False else 'vs'} {r.opponent} ({r.competition}{rnd}, {day_label(r.date)})"


def flags_for(day: str, tg: pd.DataFrame, today: date, state: str | None, notes_path: str = "") -> list[str]:
    """Banners at the top of a page: games before this one that are not in the data (still to be played, or played and not collected
    yet) and, for a game still to come, whether anyone has worked on the page (state None = hand-written, never a draft)."""
    iso = f"{today:%Y-%m-%d}"
    before = tg[(tg.date < day) & ~tg.finished]
    out = []
    to_play, pending = before[before.date >= iso], before[before.date < iso]
    if len(to_play):
        out.append("⚠ **Games still to be played before this one:** " + "; ".join(game_text(r) for _, r in to_play.iterrows()) +
                   ". This page is a preview and will change after them.")
    if len(pending):
        out.append("⚠ **Played but not collected yet:** " + "; ".join(game_text(r) for _, r in pending.iterrows()) +
                   ". Not included here; the next collection of games updates this page.")
    if day >= iso and state in ("draft", "progress"):
        how = f" Set `reviewed: yes` in `{notes_path}` when done." if notes_path else ""
        out.append("✎ **Automatic draft, not reviewed yet:** generated from the data, no text of yours so far." + how if state == "draft" else
                   "✎ **Work in progress:** some text is written but the page is not marked as reviewed yet." + how)
    return out


def add_flags(md: str, flags: list[str], extra: str = "") -> str:
    """Put the banners (and an optional line) right after the page's first heading."""
    block = "\n\n".join(["> " + f for f in flags] + ([extra] if extra else []))
    if not block:
        return md
    head, _, rest = md.partition("\n")
    return f"{head}\n\n{block}\n{rest}"


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


def add_photos(md: str, files: list[str]) -> str:
    """Put a small picture before the player's name in table rows whose first cell is a name with a photo_<name>.jpg in `files`."""
    have = {f for f in files if f.startswith("photo_")}
    def row(m: re.Match) -> str:
        name = re.sub(r"\s*\(.*?\)", "", m.group(2)).strip()
        stem = f"photo_{photo_name(name)}.jpg" if name else ""
        return f'{m.group(1)}<img class="face" src="{stem}" alt="{name}"> {m.group(2)}{m.group(3)}' if stem in have else m.group(0)
    return re.sub(r"^(\| )([A-Z][^|]*?)( +\|)", row, md, flags=re.M)


def folder_name(home: str, away: str, day: str) -> str:
    return f"matchup_{home.replace(' ', '_')}_vs_{away.replace(' ', '_')}_before_{day}"


def shell(title: str, body: str, root: str, nav: dict, comments: bool = False) -> str:
    c = CFG.get("comments") or {}
    return TPL.get_template("site.html.j2").render(title=title, body=body, root=root, nav=nav, site_title=CFG["site_title"], league=CFG["league"],
                                                   comments=comments, comments_repo=c.get("repo"), comments_label=c.get("label", "comment"))


# ── page builders: each returns the list of entries it created ──────────────────
def snapshot_links() -> dict[str, str]:
    """opponent-analysis folder -> date of the snapshot of the same game (read from the generated snapshots)."""
    out = {}
    for f in (ROOT / "reports" / "snapshot").glob("20*/auto.json"):
        slug = json.loads(f.read_text(encoding="utf-8")).get("opponent_analysis")
        if slug:
            out[slug] = f.parent.name
    return out


def build_opponents(tg: pd.DataFrame, today: date) -> list[dict]:
    shutil.rmtree(DOCS / "opponent", ignore_errors=True)
    snap_of = snapshot_links()
    entries = []
    for folder in sorted((ROOT / "reports").glob("matchup_*_before_*")):
        slug, day = folder.name, folder.name.rsplit("_before_", 1)[1]
        dest = DOCS / "opponent" / slug
        notes_dir = WEEKLY / "opponent" / slug
        files = copy_images(folder, dest=dest)
        readme, auto_path = folder / "README.md", folder / "auto.json"
        document = notes_dir / "document.md"
        state, game_day = "reviewed", day          # a page with your own text (README / document) counts as reviewed
        link = f"../../snapshot/{snap_of[slug]}/" if slug in snap_of else None
        if readme.exists():                          # page with a README (hand-written, or written by a report script)
            text = readme.read_text(encoding="utf-8")
            title = re.search(r"^# (.+)$", text, re.M).group(1)
            page_md, rnd = text, None
            if document.exists():
                # your document (weekly/opponent/<folder>/document.md + its images) comes first, as written; the automatic
                # README follows under its own heading, so nothing of either is lost
                doc = document.read_text(encoding="utf-8")
                title = re.search(r"^# (.+)$", doc, re.M).group(1)
                auto = re.sub(r"^# .+\n", "", text, count=1, flags=re.M)
                auto = re.sub(r"^(#{2,5}) ", lambda m: "#" + m.group(1) + " ", auto, flags=re.M)   # one level down
                doc = add_photos(doc, files)
                page_md = doc.rstrip() + "\n\n## Automatic data report\n\nGenerated from the data by `notebooks/" + \
                    "manresa_report.py`; it repeats some of the sections above with the full figures.\n" + auto
                files += copy_images(notes_dir, dest=dest)
            if (folder / "roster.json").exists():
                roster = json.loads((folder / "roster.json").read_text(encoding="utf-8"))
                block = TPL.from_string("{% from '_macros.j2' import roster_table %}## Roster\n\nPer-game averages before this game, "
                                        "league and EuroCup games. Shooting: percentage (attempts per game).\n\n"
                                        "{{ roster_table(r) }}\n\n").render(r=roster)
                k = page_md.find("\n## Sources")
                page_md = page_md[:k] + "\n" + block + page_md[k:] if k >= 0 else page_md + "\n\n" + block
            if document.exists() and slug in snap_of:
                game_day = snap_of[slug]             # the game itself (the folder name carries the data cut-off date)
        elif auto_path.exists():
            a = json.loads(auto_path.read_text(encoding="utf-8"))
            n = parse_notes(notes_dir / "notes.md")
            state, game_day = page_state(n), a["date"]
            a.update(date_long=long_date(a["date"]), team_suffix=ordinal(a["comparison"]["team"]["position"]),
                     opp_suffix=ordinal(a["comparison"]["opp"]["position"]))
            a["team_link"] = f"../../snapshot/{a['date']}/" if (ROOT / "reports" / "snapshot" / a["date"] / "auto.json").exists() else None
            page_md = TPL.get_template("opponent.md.j2").render(a=a, n=n, author=AUTHOR, files=files)
            title, rnd = n.get("title") or f"{a['home_team']} vs {a['away_team']}", a["round"]
            link = None                              # the template has its own line
        else:
            continue
        extra = f"BC Roma before this game: [pre-game snapshot]({link})." if link else ""
        page_md = add_flags(page_md, flags_for(game_day, tg, today, state, f"weekly/opponent/{slug}/notes.md"), extra)
        entries.append({"slug": slug, "title": title, "date": day, "game_date": game_day, "round": rnd, "state": state, "html": md_html(page_md)})
    entries.sort(key=lambda e: e["date"], reverse=True)
    return entries


def build_snapshots(opponents: list[dict], tg: pd.DataFrame, today: date) -> list[dict]:
    shutil.rmtree(DOCS / "snapshot", ignore_errors=True)
    have_opp = {e["slug"] for e in opponents}
    entries = []
    for src in sorted((ROOT / "reports" / "snapshot").glob("20*")):
        if not (src / "auto.json").exists():
            continue
        a = json.loads((src / "auto.json").read_text(encoding="utf-8"))
        notes_dir = WEEKLY / "snapshot" / src.name
        n = parse_notes(notes_dir / "notes.md")
        if a.get("standings_table", {}).get("position"):
            a["standings_table"]["position_suffix"] = ordinal(a["standings_table"]["position"])
        a.setdefault("standings_table", {"kind": "LBA", "available": True})
        a.update(date_long=long_date(a["date"]), position_suffix=ordinal(a["position"]),
                 opponent_link=f"../../opponent/{a['opponent_analysis']}/" if a.get("opponent_analysis") in have_opp else None)
        state = page_state(n)
        page_md = add_flags(TPL.get_template("snapshot.md.j2").render(a=a, n=n, author=AUTHOR),
                            flags_for(a["date"], tg, today, state, f"weekly/snapshot/{src.name}/notes.md"))
        short = f"{'at' if a['home'] is False else 'vs'} {a['opponent']}"
        title = n.get("title") or f"{a['team']} {short}"
        copy_images(src, notes_dir, dest=DOCS / "snapshot" / src.name)
        entries.append({"slug": src.name, "title": title, "date": a["date"], "html": md_html(page_md), "state": state,
                        "opponent": a["opponent"], "competition": a["competition"], "round": a["round"], "home": a["home"],
                        "opponent_slug": a.get("opponent_analysis") if a.get("opponent_analysis") in have_opp else None})
    entries.sort(key=lambda e: e["date"], reverse=True)
    return entries


def build_info_pages() -> list[dict]:
    """weekly/pages/*.md (Methodology, Work plan, ...) -> docs/<name>/index.html, in the order of PAGES; comments enabled."""
    entries = []
    for name in PAGES:
        src = WEEKLY / "pages" / f"{name}.md"
        shutil.rmtree(DOCS / name, ignore_errors=True)
        if src.exists():
            text = src.read_text(encoding="utf-8")
            title = re.search(r"^# (.+)$", text, re.M).group(1)
            entries.append({"slug": name, "title": title, "html": f'<div class="doc">{md_html(text)}</div>', "url": f"{name}/", "label": title})
    return entries


def build_nav(snaps: list[dict], opps: list[dict]) -> list[dict]:
    """The dropdown: one entry per game, newest first, opening the opponent analysis (which links to the BC Roma snapshot of
    the game) or, when there is no analysis, the snapshot itself."""
    rows, used = [], set()
    for e in snaps:
        where = "at" if e["home"] is False else "vs"
        comp = e["competition"] + (f" round {e['round']}" if e["round"] else "")
        url = f"opponent/{e['opponent_slug']}/" if e["opponent_slug"] else f"snapshot/{e['slug']}/"
        used.add(e["opponent_slug"])
        rows.append({"date": e["date"], "url": url, "label": f"{where} {e['opponent']} · {comp} · {day_label(e['date'])}"})
    for o in opps:                                   # analyses of games without a snapshot
        if o["slug"] not in used:
            rows.append({"date": o["game_date"], "url": f"opponent/{o['slug']}/", "label": f"{o['title']} · {day_label(o['game_date'])}"})
    return sorted(rows, key=lambda r: r["date"], reverse=True)


def build_reviews() -> list[dict]:
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
        page.write_text(shell(f"{e['title']} · {CFG['site_title']}", e["html"], "../../", nav, comments=True), encoding="utf-8")


def next_games(snaps: list[dict], opps: list[dict], today: date) -> list[dict]:
    """The next game still to play in each competition, in date order (team_games.py: LBA, EuroCup, weekly/schedule.csv)."""
    tg = team_games(ROOT / "data", CFG["team"])
    snap = {e["slug"]: e for e in snaps}
    opp = {e["slug"]: e for e in opps}
    out = []
    for _, c in next_games_df(tg, f"{today:%Y-%m-%d}").iterrows():
        home = None if c.home is None or pd.isna(c.home) else bool(c.home)
        out.append({"date": c.date, "time": c.time or "", "competition": c.competition if c.competition != "LBA" else CFG["league"],
                    "opponent": c.opponent, "home": home, "round": None if pd.isna(c["round"]) else int(c["round"]),
                    "analysis": c.analysis if c.analysis in opp else None, "analysis_state": opp[c.analysis]["state"] if c.analysis in opp else None,
                    "snapshot": c.key if c.key in snap else None, "snapshot_state": snap[c.key]["state"] if c.key in snap else None})
    return out


def build_landing(nav: dict, snaps: list[dict], opps: list[dict], reviews: list[dict], today: date) -> None:
    def card(href: str, kicker: str, main: str, sub: str = "", latest: bool = False) -> str:
        return (f'<a class="card{" latest" if latest else ""}" href="{href}"><div class="rd">{kicker}</div>'
                f'<div class="score">{main}</div><div class="rd">{sub}</div></a>')
    badge = lambda state: {"draft": "✎ automatic draft, not reviewed", "progress": "✎ work in progress"}.get(state, "")
    parts = [f"<h1>{CFG['site_title']}</h1>",
             f"<p>The season of {CFG['team']} ({CFG['league']} and EuroCup). The dropdown at the top lists the opponents, game by game: "
             "each page is the analysis of the opponent, with a link to the situation of the team before that game; both use only data from "
             "before the game. Below, the next games and the review of every game played. "
             "<a href=\"methodology/\">Methodology</a> explains how the numbers are made and <a href=\"work-plan/\">Work plan</a> what is done and what comes next; "
             "every page has a comment box at the bottom.</p>"]
    nxt = next_games(snaps, opps, today)
    if nxt:
        parts.append("<h2>Next games</h2><div class=\"cards\">")
        for i, n in enumerate(nxt):
            where = "at" if n["home"] is False else "vs"
            when = f"{long_date(n['date'])}{', ' + n['time'] if n['time'] else ''} · {n['competition']}{' round ' + str(n['round']) if n['round'] else ''}"
            main_href = f"opponent/{n['analysis']}/" if n["analysis"] else (f"snapshot/{n['snapshot']}/" if n["snapshot"] else "#")
            state = n["analysis_state"] or n["snapshot_state"]
            parts.append(card(main_href, when, f"{CFG['team']} {where} {n['opponent']}", badge(state) or "opponent analysis", i == 0))
            if n["analysis"] and n["snapshot"]:
                parts.append(card(f"snapshot/{n['snapshot']}/", f"{CFG['team']} before the game", "Situation, roster, form",
                                  badge(n["snapshot_state"]) or "pre-game snapshot"))
        parts.append("</div>")
    if reviews:
        parts.append("<h2 id=\"reviews\">Game reviews</h2><div class=\"cards\">")
        for i, w in enumerate(reviews):
            cls, where = ("win" if w["win"] else "loss"), ("vs" if w["home"] else "at")
            parts.append(card(f"review/{w['slug']}/", f"Round {w['round']} · {w['date']}",
                              f'<span class="{cls}">{"W" if w["win"] else "L"}</span> {w["score"]} {where} {w["opponent"]}',
                              f"{w['record']} · {w['position']}{ordinal(w['position'])} in the standings" + (f"<div>{w['summary']}</div>" if w["summary"] else ""), i == 0))
        parts.append("</div>")
    if CFG.get("links"):
        links = "".join(f'<a class="card" href="{l["url"]}" target="_blank" rel="noopener"><div class="rd">Official site</div>'
                        f'<div class="score">{l["label"]}</div><div class="rd">{l["url"].split("//")[1].rstrip("/")}</div></a>' for l in CFG["links"])
        parts.append(f'<h2>Official sites</h2><div class="cards">{links}</div>')
    (DOCS / "index.html").write_text(shell(CFG["site_title"], "".join(parts), "", nav), encoding="utf-8")


def main() -> None:
    today = date.today()
    tg = team_games(ROOT / "data", CFG["team"])
    opps = build_opponents(tg, today)
    snaps = build_snapshots(opps, tg, today)
    reviews = build_reviews()
    pages = build_info_pages()
    nav = {"games": build_nav(snaps, opps), "pages": [{"url": p["url"], "label": p["label"]} for p in pages]}
    for p in pages:
        (DOCS / p["slug"]).mkdir(parents=True, exist_ok=True)
        (DOCS / p["slug"] / "index.html").write_text(shell(f"{p['title']} · {CFG['site_title']}", p["html"], "../", nav, comments=True), encoding="utf-8")
    write_pages("opponent", opps, nav); write_pages("snapshot", snaps, nav); write_pages("review", reviews, nav)
    build_landing(nav, snaps, opps, reviews, today)
    for stale in ("prematch.html", "analyses", "analyses.json", "weekly", "weekly.json"):   # replaced by the structure above
        p = DOCS / stale
        shutil.rmtree(p) if p.is_dir() else p.unlink(missing_ok=True)
    print(f"{len(snaps)} snapshots, {len(opps)} opponent analyses, {len(reviews)} reviews in {DOCS}")


if __name__ == "__main__":
    main()
