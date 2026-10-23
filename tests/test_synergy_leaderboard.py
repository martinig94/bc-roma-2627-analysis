"""Leaderboard page from the Synergy leaderboards pull: latest folder, rank order, Roma highlight, unranked teams. Synthetic data, no network."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "notebooks"))

import synergy_leaderboard as lb  # noqa: E402

COLS = ["play_type", "rank", "team", "name", "gp", "poss", "pct_time", "pts", "ppp", "fga", "fgm", "fg_miss", "fg_pct", "efg_pct", "ssq", "pps", "ssm",
        "to_pct", "ft_pct", "fta_per_fga", "sf_pct", "score_pct", "fg2a", "fg2m", "fg2_miss", "fg2_pct", "fg3a", "fg3m", "fg3_miss", "fg3_pct",
        "fg3a_per_fga", "poss_total"]


def row(play, rank, abbr, name, ppp, poss_total=40) -> dict:
    """One leaderboard row; only the columns the page reads carry meaningful numbers."""
    r = dict.fromkeys(COLS, 1.0)
    r.update(play_type=play, rank=rank, team=abbr, name=name, gp=4, ppp=ppp, poss=poss_total / 4, poss_total=poss_total)
    return r


def write(folder: Path, comp="eurocup", side="defense") -> None:
    rows = [row("All", 3, "MRO", "Maxima Roma (ex Germani Brescia)", 0.97), row("All", 2, "BCR", "Basket Club Roma SPQR (ex Vanoli Cremona)", 0.955), row("All", 1, "ARI", "Aris Thessaloniki", 0.797),
            row("Isolation", 1, "ARI", "Aris Thessaloniki", 0.5), row("Isolation", None, "BCR", "Basket Club Roma SPQR (ex Vanoli Cremona)", 0.4, poss_total=6)]
    folder.mkdir(parents=True)
    pd.DataFrame(rows, columns=COLS).to_csv(folder / f"leaderboard_{comp}_{side}.csv", index=False)


def test_no_data_no_page(tmp_path, monkeypatch):
    monkeypatch.setattr(lb, "SYNERGY", tmp_path)
    assert lb.page_markdown() is None


def test_page_uses_newest_folder_and_its_date(tmp_path, monkeypatch):
    monkeypatch.setattr(lb, "SYNERGY", tmp_path)
    write(tmp_path / "leaderboards_2026-10-23")
    write(tmp_path / "leaderboards_2026-11-02")
    md = lb.page_markdown()
    assert "02 November 2026" in md and "23 October" not in md
    assert "## EuroCup · Defence" in md and "Serie A" not in md        # only the files that exist


def test_ranks_roma_highlight_and_unranked_last(tmp_path, monkeypatch):
    monkeypatch.setattr(lb, "SYNERGY", tmp_path)
    write(tmp_path / "leaderboards_2026-10-23")
    md = lb.page_markdown()
    overall = md.split("### Overall")[1].split("###")[0]
    assert overall.index("Aris Thessaloniki") < overall.index("Basket Club Roma SPQR")      # rank order, not file order
    assert "==Basket Club Roma SPQR==" in overall and "(ex" not in overall                  # highlighted, suffix dropped
    assert "Maxima Roma" in overall and "==Maxima Roma==" not in overall                    # the other Roma team is not
    iso = md.split("### Isolation")[1]
    assert iso.index("Aris") < iso.index("Roma") and "==–==" in iso                       # unranked team last, rank shown as a dash
