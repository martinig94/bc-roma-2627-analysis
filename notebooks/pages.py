"""The editable pages of a game: weekly/games/<date>/snapshot.md (our team before the game) and analysis.md (the opponent).

A page file is written once, by the generators (weekly.py), and never overwritten: it is yours. It is plain markdown with
  * a few header lines at the top (title:, reviewed:, generated:),
  * your text, section titles and your own images (put the image file in the same folder),
  * automatic blocks written as {{ name }} or {{ figure: image }}: the site build replaces them with the generated tables, figures
    and captions, so they keep refreshing when the data changes. Reorder, delete or add them freely.
Blocks are the macros of weekly/template/blocks.md.j2. A page that does not exist yet is built in memory from the same default.

State of a page (the banner on upcoming games): `reviewed: yes` in the header -> reviewed; the body still equals what was generated
(`generated:` holds its fingerprint) -> automatic draft; otherwise work in progress.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import jinja2

ROOT = Path(__file__).resolve().parent.parent
GAMES = ROOT / "weekly" / "games"
GAMES_REL = "weekly/games"                                     # GAMES relative to ROOT, for the paths shown to the user
TPL = jinja2.Environment(loader=jinja2.FileSystemLoader(ROOT / "weekly" / "template"), autoescape=False, keep_trailing_newline=True,
                         undefined=jinja2.ChainableUndefined)
KINDS = {"snapshot": "snapshot.md", "analysis": "analysis.md"}
SUBPAGES = ("individual_tendencies", "defense_tendencies", "offense_tendencies")   # pages that go deeper, next to analysis.md; linked from it
BLOCKS_TEMPLATE = "blocks.md.j2"                               # macros that render the {{ block }} lines
PAGE_TEMPLATE = "page_{kind}.md.j2"                            # default text of a page, one per kind
REPORTS = ROOT / "reports"
SNAPSHOT_AUTO = "auto.json"                                    # generated data of a snapshot or an analysis folder
ANALYSIS_HAND_WRITTEN = "README.md"                            # an analysis written by hand has no page file
FINGERPRINT_LEN = 10                                           # hex digits of the SHA-1 kept as the body fingerprint
REVIEWED_VALUES = {"yes", "y", "true", "1", "reviewed"}        # accepted values of `reviewed:` in the header
LINEUPS_PREFIX = "lineups_"                                    # figure files that switch the lineups section on
HEADING_LEVELS = (3, 2)                                        # heading levels pruned when empty, deepest first
SKIP = re.compile(r"(<!--.*?-->|`[^`\n]*`)", re.S)            # comments and code spans are never expanded
BLOCK = re.compile(r"\{\{\s*([a-z_]+)\s*(?::\s*([^{}]*?))?\s*\}\}")


# ── file format ─────────────────────────────────────────────────────────────────
def split_front(text: str) -> tuple[dict[str, str], str]:
    """Split a page into its header values and its body.

    The header is the run of `key: value` lines at the top, up to the first blank line.

    Args:
        text: Full text of a page file.

    Returns:
        (header values with lower-case keys, body).
    """
    meta, lines = {}, text.lstrip("﻿").split("\n")
    i = 0
    while i < len(lines) and re.match(r"^[A-Za-z_]+:", lines[i]):
        k, _, v = lines[i].partition(":")
        meta[k.strip().lower()] = v.strip()
        i += 1
    return meta, "\n".join(lines[i:]).lstrip("\n")


def fingerprint(body: str) -> str:
    """Return a short whitespace-insensitive hash of a page body."""
    norm = "\n".join(line.rstrip() for line in body.strip().splitlines())
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:FINGERPRINT_LEN]


def page_path(kind: str, day: str) -> Path:
    """Return the file of the page of `kind` for the game on `day`."""
    return GAMES / day / KINDS[kind]


def edit_path(kind: str, day: str) -> str:
    """Return the repo-relative path of the page, as shown to the person editing it."""
    return f"{GAMES_REL}/{day}/{KINDS[kind]}"


# ── creation ────────────────────────────────────────────────────────────────────
def default_text(kind: str, a: dict[str, Any], files: list[str], notes: dict | None = None, generated: str = "") -> str:
    """Render the default page of `kind` from the generated data `a` and the figure `files`; `notes` and `generated` fill the header."""
    tpl = TPL.get_template(PAGE_TEMPLATE.format(kind=kind))
    text = tpl.render(a=a, files=files, notes=notes, generated=generated, has_lineups=any(f.startswith(LINEUPS_PREFIX) for f in files))
    return re.sub(r"\[\[\s*(.*?)\s*\]\]", r"{{ \1 }}", text)       # [[ block ]] in the templates -> {{ block }} in the page


def new_page(kind: str, a: dict[str, Any], files: list[str], notes: dict | None = None) -> str:
    """The text of a new page; `generated:` fingerprints the automatic body, so that notes carried over from the old files show as work done."""
    fp = fingerprint(split_front(default_text(kind, a, files))[1])
    return default_text(kind, a, files, notes, fp)


def ensure(kind: str, day: str, a: dict[str, Any], files: list[str], notes: dict | None = None) -> tuple[Path, bool]:
    """Create the page file if it does not exist yet. Returns (path, created).
    A page nobody has touched (reviewed: no, body still equal to what was generated) is rewritten when the default page changed, so that
    new blocks of the template reach it; a page with any work of yours is never touched."""
    path = page_path(kind, day)
    if path.exists():
        meta, body = split_front(path.read_text(encoding="utf-8"))
        if state(meta, body) == "draft":
            fresh = new_page(kind, a, files, notes)
            if split_front(fresh)[1] != body:
                path.write_text(fresh, encoding="utf-8")
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_page(kind, a, files, notes), encoding="utf-8")
    return path, True


def ensure_subpages(day: str, a: dict[str, Any], files: list[str]) -> list[tuple[str, Path, bool]]:
    """Create the files of the SUBPAGES of the analysis of `day` that do not exist yet (they are yours: an existing one is never touched).
    Returns [(name, path, created)]."""
    out = []
    for name in SUBPAGES:
        path = GAMES / day / f"{name}.md"
        created = not path.exists()
        if created:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(default_text(name, a, files), encoding="utf-8")
        out.append((name, path, created))
    return out


def load(kind: str, day: str, a: dict[str, Any], files: list[str]) -> tuple[dict[str, str], str]:
    """(header, body) of the page: the file, or the default page built in memory when the file is not there yet."""
    path = page_path(kind, day)
    if path.exists():
        return split_front(path.read_text(encoding="utf-8"))
    return split_front(new_page(kind, a, files))


def state(meta: dict[str, str], body: str) -> str:
    """Return the state of a page: "reviewed", "draft" (body is still the generated one) or "progress"."""
    if meta.get("reviewed", "").strip().lower() in REVIEWED_VALUES:
        return "reviewed"
    return "draft" if meta.get("generated") and fingerprint(body) == meta["generated"] else "progress"


# ── expansion ───────────────────────────────────────────────────────────────────
def figure_md(arg: str, files: list[str]) -> str:
    """Return the markdown image of the figure `arg` (name with or without extension), or a note if the file is missing."""
    name = arg if "." in arg else f"{arg}.png"
    if name not in files:
        return f"*(figure `{arg}` is not available)*"
    caption = re.sub(r"^\d+_", "", Path(name).stem).replace("_", " ")
    return f"![{caption}]({name})"


def expand(body: str, kind: str, a: dict[str, Any], files: list[str], author: str = "") -> str:
    """Replace the {{ block }} lines of a page with the generated markdown (comments and code spans are left as they are)."""
    mod = TPL.get_template(BLOCKS_TEMPLATE).module

    def block(m: re.Match) -> str:
        name, arg = m.group(1), (m.group(2) or "").strip()
        if name == "figure":
            return figure_md(arg, files)
        for cand in (f"{kind}_{name}", name):
            fn = getattr(mod, cand, None)
            if callable(fn):
                return fn(a, files, author, kind).strip()
        return f"*(unknown block `{name}`)*"

    parts = SKIP.split(body)
    out = "".join(p if i % 2 else BLOCK.sub(block, p) for i, p in enumerate(parts))
    return prune_empty(re.sub(r"<!--.*?-->", "", out, flags=re.S)).lstrip()


def prune_empty(md: str) -> str:
    """Drop headings (## and ###) that have nothing under them before the next heading of the same or a higher level: the prompts
    of a page that is still a draft are comments, so its empty sections are simply not shown."""
    for level in HEADING_LEVELS:
        md = re.sub(rf"^#{{{level}}} [^\n]*\n(?:[ \t]*\n)*(?=^#{{1,{level}}} |\Z)", "", md, flags=re.M)
    return md


# ── the pages of one game ───────────────────────────────────────────────────────
def ensure_for(day: str, notes: dict | None = None) -> list[tuple[str, Path | None, bool]]:
    """Create the page files of the game on `day` from the data already generated (reports/): [(kind, path or None, created)].
    The analysis page exists only for generated analyses; one written by hand (README.md / document.md) has no page file."""
    out = []
    snap = REPORTS / "snapshot" / day / SNAPSHOT_AUTO
    if not snap.exists():
        return [("snapshot", None, False), ("analysis", None, False)]
    a = json.loads(snap.read_text(encoding="utf-8"))
    path, created = ensure("snapshot", day, a, sorted(f.name for f in snap.parent.iterdir()), (notes or {}).get("snapshot"))
    out.append(("snapshot", path, created))
    folder = REPORTS / (a.get("opponent_analysis") or "-")
    if (folder / SNAPSHOT_AUTO).exists() and not (folder / ANALYSIS_HAND_WRITTEN).exists():
        auto = json.loads((folder / SNAPSHOT_AUTO).read_text(encoding="utf-8"))
        path, created = ensure("analysis", day, auto, sorted(f.name for f in folder.iterdir()), (notes or {}).get("analysis"))
        out.append(("analysis", path, created))
        ensure_subpages(day, auto, sorted(f.name for f in folder.iterdir()))
    else:
        out.append(("analysis", None, False))
    return out
