"""Build the GitHub Pages site (docs/).

    python notebooks/build_site.py

Three kinds of page. The dropdown in the header of every page lists the opponents (one entry per game, every competition);
the opponent analysis links to the BC Roma snapshot of the same game, and a game without an analysis opens its snapshot:

  BC Roma snapshots                one per game in every competition, using only data from before it
      reports/snapshot/<date>/{auto.json, PNGs}  +  weekly/snapshot/<date>/notes.md   ->  docs/snapshot/<date>/
  Opponent analyses                one per opponent and game, with the comparison against the team
      reports/matchup_*_before_<date>/  README.md (hand-written, used as it is) or auto.json + weekly/opponent/<folder>/notes.md
      ->  docs/opponent/<folder>/
  Game reviews (landing page)      post-game, one per played round; only when "reviews": true in weekly/config.json
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

import pages
import weekly_config
from player_names import photo_name
from team_games import next_games as next_games_df, team_games

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
WEEKLY = ROOT / "weekly"
CFG = weekly_config.load()
AUTHOR = CFG["author"]
TPL = jinja2.Environment(loader=jinja2.FileSystemLoader(WEEKLY / "template"), autoescape=False, keep_trailing_newline=True)
PAGES = ["goal", "methodology", "work-plan"]     # weekly/pages/<name>.md, in header order
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


def flags_for(day: str, tg: pd.DataFrame, today: date, state: str | None, notes_path: str = "", archive: bool = False) -> list[str]:
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
    if archive and day < iso and state == "draft":
        how = f" Set `reviewed: yes` in `{notes_path}` to remove this note." if notes_path else ""
        out.append("🗄 **Archive, automatic only:** this game has been played and no analysis of it is planned; the page is what the data produced "
                   "(tables and figures), with no text of the analyst." + how)
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


def mark_highlights(text: str) -> str:
    """==text== -> a highlighted span (like the marked cells of a Word table); code spans are left alone."""
    parts = re.split(r"(`[^`]*`)", text)
    return "".join(p if p.startswith("`") else re.sub(r"(?<![=\w])==(?=\S)(.+?)(?<=\S)==(?![=\w])", r'<span class="mark">\1</span>', p)
                   for p in parts)


def sections(html_text: str) -> str:
    """Every main heading (h2) and what follows it up to the next one becomes a <details open> section that can be closed.
    What comes before the first h2 (title, banners, intro) stays outside."""
    parts = re.split(r"(<h2(?: [^>]*)?>.*?</h2>)", html_text, flags=re.S)
    if len(parts) < 3:
        return html_text
    out = [parts[0]]
    for head, body in zip(parts[1::2], parts[2::2]):
        out.append(f'<details class="sec" open><summary>{head}</summary><div class="sec-body">{body}</div></details>')
    return "".join(out)


def md_html(text: str) -> str:
    return sections(markdown.markdown(mark_highlights(text), extensions=["tables", "md_in_html", "sane_lists"]))


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


def shell(title: str, body: str, root: str, nav: dict, comments: bool = False, edit: str | None = None) -> str:
    c = CFG.get("comments") or {}
    edit_url = f"https://github.com/{CFG['repo']}/edit/{CFG['branch']}/{edit}" if edit and CFG.get("repo") else None
    return TPL.get_template("site.html.j2").render(title=title, body=body, root=root, nav=nav, site_title=CFG["site_title"], league=CFG["league"], season=CFG["season"],
                                                   comments=comments, author=CFG.get("author"), edit_url=edit_url, has_reviews=bool(CFG.get("reviews")), comments_repo=c.get("repo"), comments_label=c.get("label", "comment"))


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
        edit_file, legacy = None, False
        if readme.exists():
            legacy = True                          # page with a README (hand-written, or written by a report script)
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
                                        "league and EuroCup games. Shooting: 2P%, 3P% and FT%, each followed by the attempts **per game** in brackets (2PA, 3PA, FTA).\n\n"
                                        "{{ roster_table(r) }}\n\n").render(r=roster)
                k = page_md.find("\n## Sources")
                page_md = page_md[:k] + "\n" + block + page_md[k:] if k >= 0 else page_md + "\n\n" + block
            if document.exists() and slug in snap_of:
                game_day = snap_of[slug]             # the game itself (the folder name carries the data cut-off date)
        elif auto_path.exists():
            a = json.loads(auto_path.read_text(encoding="utf-8"))
            a.update(date_long=long_date(a["date"]), team_suffix=ordinal(a["comparison"]["team"]["position"]),
                     opp_suffix=ordinal(a["comparison"]["opp"]["position"]))
            a["team_link"] = f"../../snapshot/{a['date']}/" if (ROOT / "reports" / "snapshot" / a["date"] / "auto.json").exists() else None
            files += copy_images(pages.GAMES / a["date"], dest=dest)       # your own images, next to the page file
            meta, body = pages.load("analysis", a["date"], a, files)       # weekly/games/<date>/analysis.md (or the default)
            state, game_day = pages.state(meta, body), a["date"]
            page_md = pages.expand(body, "analysis", a, files, AUTHOR)
            title, rnd = meta.get("title") or f"{a['home_team']} vs {a['away_team']}", a["round"]
            link, edit_file = a["team_link"], pages.edit_path("analysis", a["date"])
        else:
            continue
        extra = f"➜ **{CFG['team']} before this game:** [situation, roster and form (pre-game snapshot)]({link})" if link else ""
        edit = edit_file or (f"weekly/opponent/{slug}/document.md" if document.exists() else f"reports/{slug}/README.md")  # file with the text
        flags = flags_for(game_day, tg, today, state, edit, archive=not legacy)
        if legacy:
            flags.append(f"🗂 **Old format:** this analysis was written by hand before the game-page workflow, so it is not made of automatic "
                         f"blocks: its tables and figures do not refresh with new data. Its text is in `{edit}`.")
        page_md = add_flags(page_md, flags, extra)
        entries.append({"slug": slug, "title": title, "date": day, "game_date": game_day, "round": rnd, "state": state, "html": md_html(page_md),
                        "edit": edit, "legacy": legacy,
                        "archive": (not legacy) and game_day < f"{today:%Y-%m-%d}" and state == "draft"})
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
        if a.get("standings_table", {}).get("position"):
            a["standings_table"]["position_suffix"] = ordinal(a["standings_table"]["position"])
        a.setdefault("standings_table", {"kind": "LBA", "available": True})
        a.update(date_long=long_date(a["date"]), position_suffix=ordinal(a["position"]),
                 opponent_link=f"../../opponent/{a['opponent_analysis']}/" if a.get("opponent_analysis") in have_opp else None)
        files = copy_images(src, pages.GAMES / a["date"], dest=DOCS / "snapshot" / src.name)     # generated images + your own
        meta, body = pages.load("snapshot", a["date"], a, files)         # weekly/games/<date>/snapshot.md (or the default)
        state = pages.state(meta, body)
        page_md = add_flags(pages.expand(body, "snapshot", a, files, AUTHOR),
                            flags_for(a["date"], tg, today, state, pages.edit_path("snapshot", a["date"]), archive=True))
        short = f"{'at' if a['home'] is False else 'vs'} {a['opponent']}"
        title = meta.get("title") or f"{a['team']} {short}"
        entries.append({"slug": src.name, "title": title, "date": a["date"], "html": md_html(page_md), "state": state, "data": compare_data(a),
                        "archive": a["date"] < f"{today:%Y-%m-%d}" and state == "draft",
                        "edit": pages.edit_path("snapshot", a["date"]),
                        "opponent": a["opponent"], "competition": a["competition"], "round": a["round"], "home": a["home"],
                        "opponent_slug": a.get("opponent_analysis") if a.get("opponent_analysis") in have_opp else None})
    entries.sort(key=lambda e: e["date"], reverse=True)
    return entries


def compare_data(a: dict) -> dict:
    """What the compare page needs from one snapshot (numbers only, small)."""
    where = "at" if a["home"] is False else "vs"
    comp = a["competition"] + (f" round {a['round']}" if a["round"] else "")
    keep = ("player_id", "photo", "name", "pos", "height", "gp", "min", "pts", "reb", "ast", "pir", "fg2", "fg3", "ft")
    return {"key": a["date"], "label": f"{a['date']} · {where} {a['opponent']} · {comp}", "date": a["date"], "game": f"{where} {a['opponent']} ({comp})",
            "record": a["record"], "position": a["position"], "points": a["points"], "record_ec": a.get("record_ec"), "form": a["form"],
            "profile": a.get("profile") or {}, "roster": [{k: r.get(k) for k in keep} for r in a["roster"]]}


COMPARE_JS = r"""
(function () {
  var D = JSON.parse(document.getElementById("snapdata").textContent);
  var by = {}; D.forEach(function (d) { by[d.key] = d; });
  var A = document.getElementById("cmpA"), B = document.getElementById("cmpB"), out = document.getElementById("cmpOut");
  D.forEach(function (d) { [A, B].forEach(function (sel) { sel.add(new Option(d.label, d.key)); }); });
  var q = new URLSearchParams(location.search);
  A.value = by[q.get("a")] ? q.get("a") : (D[D.length - 2] || D[0]).key;
  B.value = by[q.get("b")] ? q.get("b") : D[D.length - 1].key;
  var num = function (x) { return typeof x === "number" && isFinite(x); };
  var delta = function (a, b) { if (!num(a) || !num(b)) return ""; var d = Math.round((b - a) * 10) / 10;
                                return ' <span class="muted">(' + (d > 0 ? "+" : d < 0 ? "−" : "±") + Math.abs(d) + ")</span>"; };
  var ord = function (n) { var m = n % 100, r = n % 10; return n + (m >= 11 && m <= 13 ? "th" : r === 1 ? "st" : r === 2 ? "nd" : r === 3 ? "rd" : "th"); };
  var fmt = function (x) { return x === null || x === undefined || x === "" ? "–" : x; };
  var pair = function (a, b) { return fmt(a) + " → " + fmt(b) + delta(a, b); };
  var esc = function (t) { return String(t).replace(/[&<>]/g, function (c) { return {"&": "&amp;", "<": "&lt;", ">": "&gt;"}[c]; }); };
  function render() {
    var a = by[A.value], b = by[B.value];
    history.replaceState(null, "", "?a=" + a.key + "&b=" + b.key);
    var h = '<h2>The two situations</h2><table><thead><tr><th></th><th>A</th><th>B</th></tr></thead><tbody>' +
      row("Before the game", esc(a.game), esc(b.game)) + row("Date", a.date, b.date) +
      row("LBA record", a.record, b.record) + row("LBA position", ord(a.position), ord(b.position)) +
      row("LBA points", a.points, b.points) + row("EuroCup record", fmt(a.record_ec), fmt(b.record_ec)) +
      row("Last five games", a.form, b.form) + '</tbody></table>' +
      '<p><a href="../snapshot/' + a.key + '/">Open snapshot A</a> · <a href="../snapshot/' + b.key + '/">Open snapshot B</a></p>';
    // team numbers
    var comps = [["LBA", "LBA"], ["EuroCup", "EuroCup"]].filter(function (c) { return (a.profile[c[0]] && Object.keys(a.profile[c[0]]).length) || (b.profile[c[0]] && Object.keys(b.profile[c[0]]).length); });
    var keys = []; comps.forEach(function (c) { [a, b].forEach(function (s) { Object.keys(s.profile[c[0]] || {}).forEach(function (k) { if (keys.indexOf(k) < 0) keys.push(k); }); }); });
    h += '<h2>Team numbers</h2><table><thead><tr><th></th>' + comps.map(function (c) { return "<th>" + c[1] + ": A → B</th>"; }).join("") + "</tr></thead><tbody>";
    keys.forEach(function (k) { h += "<tr><td>" + esc(k) + "</td>" + comps.map(function (c) {
      var x = (a.profile[c[0]] || {})[k], y = (b.profile[c[0]] || {})[k]; return "<td>" + pair(x, y) + "</td>"; }).join("") + "</tr>"; });
    h += '</tbody></table><p class="muted">Ratings are points per 100 possessions. The change in brackets is B minus A.</p>';
    // roster
    var names = [], seen = {};
    b.roster.concat(a.roster).forEach(function (r) { if (!seen[r.name]) { seen[r.name] = 1; names.push(r.name); } });
    var get = function (s, n) { return s.roster.filter(function (r) { return r.name === n; })[0]; };
    var cols = [["gp", "GP"], ["min", "MIN"], ["pts", "PTS"], ["reb", "REB"], ["ast", "AST"], ["pir", "PIR"]];
    h += '<h2>Roster, per-game averages</h2><table><thead><tr><th></th><th>Player</th>' + cols.map(function (c) { return "<th>" + c[1] + "</th>"; }).join("") + "</tr></thead><tbody>";
    names.forEach(function (n) {
      var x = get(a, n), y = get(b, n), p = y && y.photo ? [b.key, y.player_id] : x && x.photo ? [a.key, x.player_id] : null;
      h += "<tr><td>" + (p ? '<img class="face" src="../snapshot/' + p[0] + "/photo_" + p[1] + '.jpg" alt="">' : "") + "</td><td><strong>" + esc(n) + "</strong></td>" +
        cols.map(function (c) { return "<td>" + pair(x ? x[c[0]] : null, y ? y[c[0]] : null) + "</td>"; }).join("") + "</tr>";
    });
    h += "</tbody></table>";
    out.innerHTML = h;
  }
  function row(l, x, y) { return "<tr><td>" + l + "</td><td>" + x + "</td><td>" + y + "</td></tr>"; }
  A.addEventListener("change", render); B.addEventListener("change", render);
  document.getElementById("cmpSwap").addEventListener("click", function () { var t = A.value; A.value = B.value; B.value = t; render(); });
  render();
})();
"""


def build_compare(snaps: list[dict], nav: dict) -> dict | None:
    """compare/index.html: two selects (any two snapshots) and the situations side by side, drawn in the browser from embedded data."""
    shutil.rmtree(DOCS / "compare", ignore_errors=True)
    if len(snaps) < 2:
        return None
    data = sorted((e["data"] for e in snaps), key=lambda d: d["date"])
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    body = ('<div class="doc"><h1>Compare two situations</h1>'
            "<p>Pick two games: the page puts the situation of the team before each of them side by side (record and position, team numbers, "
            "roster averages), with the change from A to B. Every figure comes from the pre-game snapshots, so each side uses only the "
            "data available before its game.</p>"
            '<p class="cmp-pick"><label>A <select id="cmpA"></select></label> <button type="button" id="cmpSwap" title="Swap A and B">&#8646;</button> '
            '<label>B <select id="cmpB"></select></label></p>'
            '<div id="cmpOut"></div></div>'
            f'<script type="application/json" id="snapdata">{blob}</script><script>{COMPARE_JS}</script>')
    dest = DOCS / "compare"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "index.html").write_text(shell(f"Compare two situations · {CFG['site_title']}", body, "../", nav), encoding="utf-8")
    return {"url": "compare/", "label": "Compare"}


def build_info_pages() -> list[dict]:
    """weekly/pages/*.md (Methodology, Work plan, ...) -> docs/<name>/index.html, in the order of PAGES; comments enabled."""
    entries = []
    for name in PAGES:
        src = WEEKLY / "pages" / f"{name}.md"
        shutil.rmtree(DOCS / name, ignore_errors=True)
        if src.exists():
            text = src.read_text(encoding="utf-8")
            title = re.search(r"^# (.+)$", text, re.M).group(1)
            entries.append({"slug": name, "title": title, "html": f'<div class="doc">{md_html(text)}</div>', "url": f"{name}/", "edit": f"weekly/pages/{name}.md", "label": title})
    return entries


def build_nav(snaps: list[dict], opps: list[dict]) -> dict:
    """The Opponents dropdown, newest first: the games that have an opponent analysis (snapshots are reached from the landing page)."""
    by_slug = {e["opponent_slug"]: e for e in snaps if e["opponent_slug"]}
    opponents = []
    for o in opps:
        e = by_slug.get(o["slug"])
        label = (f"{'at' if e['home'] is False else 'vs'} {e['opponent']} · {e['competition']}" + (f" round {e['round']}" if e["round"] else "")
                 + f" · {day_label(e['date'])}") if e else f"{o['title']} · {day_label(o['game_date'])}"
        opponents.append({"date": o["game_date"], "url": f"opponent/{o['slug']}/",
                          "label": label + (" · old format" if o.get("legacy") else " · automatic only" if o.get("archive") else "")})
    key = lambda r: r["date"]
    return {"games": sorted(opponents, key=key, reverse=True)}


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
                        "edit": f"weekly/review/{src.name}/notes.md",
                        "opponent": a["opponent"], "home": a["home"], "win": a["win"], "html": md_html(page_md),
                        "score": f"{a['score_for']}-{a['score_against']}", "record": a["record"], "position": a["position"]})
    entries.sort(key=lambda e: e["round"], reverse=True)
    return entries


def write_pages(kind: str, entries: list[dict], nav: dict) -> None:
    for e in entries:
        page = DOCS / kind / e["slug"] / "index.html"
        page.write_text(shell(f"{e['title']} · {CFG['site_title']}", e["html"], "../../", nav, comments=True, edit=e.get("edit")), encoding="utf-8")


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
                    "analysis_legacy": bool(opp[c.analysis].get("legacy")) if c.analysis in opp else False,
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
             "before the game. Below, the next games and the situation of the team before each game (with a comparison of two games)"
             + (" and the review of every game played. " if reviews else ". ") +
             "<a href=\"methodology/\">Methodology</a> explains how the numbers are made and <a href=\"work-plan/\">Work plan</a> what is done and what comes next; "
             "every page has a comment box at the bottom.</p>"]
    nxt = next_games(snaps, opps, today)
    if nxt:
        parts.append("<h2>Next games</h2><div class=\"cards\">")
        for i, n in enumerate(nxt):
            where = "at" if n["home"] is False else "vs"
            when = f"{long_date(n['date'])}{', ' + n['time'] if n['time'] else ''} · {n['competition']}{' round ' + str(n['round']) if n['round'] else ''}"
            href = f"opponent/{n['analysis']}/" if n["analysis"] else (f"snapshot/{n['snapshot']}/" if n["snapshot"] else "#")
            parts.append(card(href, when, f"{CFG['team']} {where} {n['opponent']}",
                              badge(n["analysis_state"] or n["snapshot_state"]) or ("🗂 old format (hand-written)" if n["analysis_legacy"] else "opponent analysis"), i == 0))
        parts.append("</div>")
    if snaps:
        opts = "".join(f'<option value="snapshot/{e["slug"]}/">{e["data"]["label"]}{" · automatic only" if e.get("archive") else ""}</option>' for e in snaps)
        optk = "".join(f'<option value="{e["slug"]}">{e["data"]["label"]}</option>' for e in snaps)
        upcoming = [e for e in snaps if e["date"] >= f"{today:%Y-%m-%d}"]
        parts.append(f'<h2 id="situation">{CFG["team"]}: situation, roster, form</h2>'
                     "<p>The situation of the team before each game: record and standings, form, team numbers, roster with photos, assists, shot zones "
                     "and efficiency, using only the data available before the game.</p>"
                     f'<p class="pick"><label>Situation before <select id="snapPick"><option value="">choose a game &#9662;</option>{opts}</select></label></p>')
        if upcoming:
            parts.append('<div class="cards">' + "".join(
                card(f"snapshot/{e['slug']}/", f"Before the game · {long_date(e['date'])}",
                     f"{CFG['team']} {'at' if e['home'] is False else 'vs'} {e['opponent']}", badge(e["state"]) or "pre-game snapshot")
                for e in sorted(upcoming, key=lambda e: e["date"])) + "</div>")
        if len(snaps) > 1:
            parts.append('<h3>Compare two situations</h3><p class="pick"><label>A <select id="cmpA">' + optk + '</select></label> '
                         '<label>B <select id="cmpB">' + optk + '</select></label> '
                         '<a class="button" id="cmpGo" href="compare/">Compare</a></p>')
        parts.append("""<script>
(function () {
  var pick = document.getElementById("snapPick");
  if (pick) pick.addEventListener("change", function () { if (pick.value) location.href = pick.value; });
  var A = document.getElementById("cmpA"), B = document.getElementById("cmpB"), go = document.getElementById("cmpGo");
  if (!A) return;
  if (A.options.length > 1) { A.selectedIndex = 1; B.selectedIndex = 0; }   // options are newest first: A = the game before the latest, B = the latest
  var upd = function () { go.href = "compare/?a=" + A.value + "&b=" + B.value; };
  A.addEventListener("change", upd); B.addEventListener("change", upd); upd();
})();
</script>""")
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
    shutil.rmtree(DOCS / "assets", ignore_errors=True)
    shutil.copytree(WEEKLY / "assets", DOCS / "assets")        # logo
    today = date.today()
    tg = team_games(ROOT / "data", CFG["team"])
    opps = build_opponents(tg, today)
    snaps = build_snapshots(opps, tg, today)
    reviews = build_reviews() if CFG.get("reviews") else []
    if not reviews:
        shutil.rmtree(DOCS / "review", ignore_errors=True)       # reviews switched off: nothing of them is published
    pages = build_info_pages()
    nav = {**build_nav(snaps, opps), "pages": [{"url": p["url"], "label": p["label"], "right": i == 0} for i, p in enumerate(pages)]}
    if len(snaps) > 1:
        nav["pages"].insert(0, {"url": "compare/", "label": "Compare"})     # then Goal, Methodology, Work plan, pushed to the right
    build_compare(snaps, nav)
    for p in pages:
        (DOCS / p["slug"]).mkdir(parents=True, exist_ok=True)
        (DOCS / p["slug"] / "index.html").write_text(shell(f"{p['title']} · {CFG['site_title']}", p["html"], "../", nav, comments=True, edit=p.get("edit")), encoding="utf-8")
    write_pages("opponent", opps, nav); write_pages("snapshot", snaps, nav); write_pages("review", reviews, nav)
    build_landing(nav, snaps, opps, reviews, today)
    for stale in ("prematch.html", "analyses", "analyses.json", "weekly", "weekly.json"):   # replaced by the structure above
        p = DOCS / stale
        shutil.rmtree(p) if p.is_dir() else p.unlink(missing_ok=True)
    print(f"{len(snaps)} snapshots, {len(opps)} opponent analyses, {len(reviews)} reviews in {DOCS}")


if __name__ == "__main__":
    main()
