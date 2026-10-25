"""Game pages (notebooks/pages.py): header, state, block expansion. No data needed."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "notebooks"))

import pages  # noqa: E402

A = {"team": "BC Roma", "opponent": "Varese", "competition": "LBA", "round": 5, "home": False, "date": "2026-10-24",
     "home_team": "Openjobmetis Varese", "away_team": "BC Roma"}


def test_split_front_reads_the_header_lines_only() -> None:
    """Check split front reads the header lines only."""
    meta, body = pages.split_front("title: A game\nreviewed: no\ngenerated: abc\n\n# Heading\nplain: text\n")
    assert meta == {"title": "A game", "reviewed": "no", "generated": "abc"}
    assert body.startswith("# Heading") and "plain: text" in body


def test_new_page_is_a_draft_until_edited() -> None:
    """Check new page is a draft until edited."""
    text = pages.new_page("snapshot", A, ["standings.png"])
    meta, body = pages.split_front(text)
    assert pages.state(meta, body) == "draft"
    assert pages.state(meta, body + "\nSome text of mine.\n") == "progress"
    assert pages.state({**meta, "reviewed": "yes"}, body) == "reviewed"


def test_trailing_whitespace_and_final_newline_do_not_count_as_work() -> None:
    """Check trailing whitespace and final newline do not count as work."""
    meta, body = pages.split_front(pages.new_page("snapshot", A, []))
    noisy = "\n".join(line + "  " for line in body.splitlines()) + "\n\n"
    assert pages.state(meta, noisy) == "draft"


def test_notes_carried_over_make_the_page_work_in_progress() -> None:
    """Check notes carried over make the page work in progress."""
    meta, body = pages.split_front(pages.new_page("analysis", A, ["lineups_BC_Roma.png"], {"lineups": "Prova"}))
    assert "Prova" in body and pages.state(meta, body) == "progress"


def test_expand_fills_blocks_but_not_comments_or_code() -> None:
    """Check expand fills blocks but not comments or code."""
    body = "# T\n\n<!-- {{ roster }} -->\n\n`{{ roster }}`\n\n{{ figure: 07_key_players }}\n\n{{ nonsense }}\n"
    out = pages.expand(body, "analysis", {"team": "BC Roma"}, ["07_key_players.png"])
    assert "![key players](07_key_players.png)" in out
    assert "`{{ roster }}`" in out                       # code span untouched
    assert "unknown block `nonsense`" in out
    assert "<!--" not in out                             # prompts for the editor are not published


def test_missing_figure_is_reported_not_crashing() -> None:
    """Check missing figure is reported not crashing."""
    assert "not available" in pages.expand("{{ figure: nope }}", "analysis", {}, [])


def test_empty_sections_are_left_out() -> None:
    """Check empty sections are left out."""
    md = "# T\n\n## Key points\n\n## Real\n\ntext\n\n### Empty sub\n\n### Full sub\n\nmore\n"
    out = pages.prune_empty(md)
    assert "Key points" not in out and "Empty sub" not in out
    assert "## Real" in out and "### Full sub" in out


def test_archive_flag_only_for_a_past_automatic_page() -> None:
    """Check archive flag only for a past automatic page."""
    from datetime import date

    import pandas as pd

    import build_site as b
    tg = pd.DataFrame({"date": pd.Series([], dtype=str), "finished": pd.Series([], dtype=bool), "opponent": pd.Series([], dtype=str),
                       "competition": pd.Series([], dtype=str), "round": pd.Series([], dtype=float), "home": pd.Series([], dtype=object)})
    today = date(2026, 10, 19)
    assert any("Archive, automatic only" in f for f in b.flags_for("2026-10-04", tg, today, "draft", "x.md", archive=True))
    assert not b.flags_for("2026-10-04", tg, today, "reviewed", "x.md", archive=True)            # reviewed: yes removes it
    assert not b.flags_for("2026-10-04", tg, today, "progress", "x.md", archive=True)            # the analyst worked on it
    assert not b.flags_for("2026-10-04", tg, today, "draft", "x.md", archive=False)              # hand-written pages are not flagged
    assert any("Automatic draft" in f for f in b.flags_for("2026-10-24", tg, today, "draft", "x.md", archive=True))   # upcoming: draft flag


def test_new_analysis_has_the_standard_sections_in_order() -> None:
    """Every analysis page has the same sections in the same order; an empty one gets the grey box."""
    text = pages.new_page("analysis", {**A, "home_team": "BC Roma", "away_team": "Bosna", "opponent": "Bosna"}, [])
    heads = [line for line in text.splitlines() if line.startswith("## ")]
    assert heads == ["## Key points", "## LBA so far: results and standings", "## BC Roma and Bosna compared", "## Bosna roster",
                     "## Starting five and bench", "## Scoring sources, tendencies and shooting maps", "## Key players", "## Assists",
                     "## Turnovers", "## Lineups", "## Defensive attitude", "## What to expect", "## Clips suggested",
                     "## Other suggested checks"]
    assert "### Shooting" in text


def test_pending_box_is_grey_and_keeps_the_section() -> None:
    """Check pending box is grey and keeps the section."""
    out = pages.expand("## Key points\n\n{{ pending }}\n\n## Empty\n\n## Next\n\ntext\n", "analysis", {}, [])
    assert 'class="pending"' in out and "This section will be filled when the game is reviewed" in out
    assert "## Key points" in out and "## Empty" not in out        # a section with no text and no box is left out


def test_eurocup_analysis_names_the_competition_in_its_heading() -> None:
    """Check eurocup analysis names the competition in its heading."""
    text = pages.new_page("analysis", {**A, "competition": "EuroCup"}, [])
    assert "## EuroCup so far: results and standings" in text
