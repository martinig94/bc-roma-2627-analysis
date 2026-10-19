"""Game pages (notebooks/pages.py): header, state, block expansion. No data needed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "notebooks"))

import pages  # noqa: E402

A = {"team": "BC Roma", "opponent": "Varese", "competition": "LBA", "round": 5, "home": False, "date": "2026-10-24",
     "home_team": "Openjobmetis Varese", "away_team": "BC Roma"}


def test_split_front_reads_the_header_lines_only():
    meta, body = pages.split_front("title: A game\nreviewed: no\ngenerated: abc\n\n# Heading\nplain: text\n")
    assert meta == {"title": "A game", "reviewed": "no", "generated": "abc"}
    assert body.startswith("# Heading") and "plain: text" in body


def test_new_page_is_a_draft_until_edited():
    text = pages.new_page("snapshot", A, ["standings.png"])
    meta, body = pages.split_front(text)
    assert pages.state(meta, body) == "draft"
    assert pages.state(meta, body + "\nSome text of mine.\n") == "progress"
    assert pages.state({**meta, "reviewed": "yes"}, body) == "reviewed"


def test_trailing_whitespace_and_final_newline_do_not_count_as_work():
    meta, body = pages.split_front(pages.new_page("snapshot", A, []))
    noisy = "\n".join(line + "  " for line in body.splitlines()) + "\n\n"
    assert pages.state(meta, noisy) == "draft"


def test_notes_carried_over_make_the_page_work_in_progress():
    meta, body = pages.split_front(pages.new_page("analysis", A, ["lineups_BC_Roma.png"], {"lineups": "Prova"}))
    assert "Prova" in body and pages.state(meta, body) == "progress"


def test_expand_fills_blocks_but_not_comments_or_code():
    body = "# T\n\n<!-- {{ roster }} -->\n\n`{{ roster }}`\n\n{{ figure: 07_key_players }}\n\n{{ nonsense }}\n"
    out = pages.expand(body, "analysis", {"team": "BC Roma"}, ["07_key_players.png"])
    assert "![key players](07_key_players.png)" in out
    assert "`{{ roster }}`" in out                       # code span untouched
    assert "unknown block `nonsense`" in out
    assert "<!--" not in out                             # prompts for the editor are not published


def test_missing_figure_is_reported_not_crashing():
    assert "not available" in pages.expand("{{ figure: nope }}", "analysis", {}, [])


def test_empty_sections_are_left_out():
    md = "# T\n\n## Key points\n\n## Real\n\ntext\n\n### Empty sub\n\n### Full sub\n\nmore\n"
    out = pages.prune_empty(md)
    assert "Key points" not in out and "Empty sub" not in out
    assert "## Real" in out and "### Full sub" in out


def test_archive_flag_only_for_a_past_automatic_page():
    from datetime import date

    import pandas as pd

    import build_site as b
    tg = pd.DataFrame({"date": [], "finished": [], "opponent": [], "competition": [], "round": [], "home": []})
    today = date(2026, 10, 19)
    assert any("Archive, automatic only" in f for f in b.flags_for("2026-10-04", tg, today, "draft", "x.md", archive=True))
    assert not b.flags_for("2026-10-04", tg, today, "reviewed", "x.md", archive=True)            # reviewed: yes removes it
    assert not b.flags_for("2026-10-04", tg, today, "progress", "x.md", archive=True)            # the analyst worked on it
    assert not b.flags_for("2026-10-04", tg, today, "draft", "x.md", archive=False)              # snapshots are not flagged
    assert any("Automatic draft" in f for f in b.flags_for("2026-10-24", tg, today, "draft", "x.md", archive=True))   # upcoming: draft flag
