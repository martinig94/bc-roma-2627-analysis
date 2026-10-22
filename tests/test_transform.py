"""Unit tests against a real (trimmed) Round 1 payload: Treviso 109-94 BC Roma, 26 Sep 2026."""
from __future__ import annotations

import json
from pathlib import Path

from lba_data.transform import BOX_FIELDS, GAME_FIELDS, PBP_FIELDS, box_rows, game_row, pbp_rows

FIX = json.loads((Path(__file__).parent / "fixtures" / "game_25602.json").read_text(encoding="utf-8"))


def test_game_row_from_calendar_and_header() -> None:
    """Check game row from calendar and header."""
    cal = game_row(FIX["cal"]["matches"][0])
    hdr = game_row(FIX["scores"]["match"])
    assert set(cal) == set(GAME_FIELDS) == set(hdr)
    assert cal["game_id"] == hdr["game_id"] == 25602
    assert cal["round"] == 1 and cal["home_team"] == "Nutribullet Treviso Basket" and cal["away_team"] == "BC Roma"
    assert (cal["home_score"], cal["away_score"]) == (109, 94)
    assert hdr["spectators"] == 4122 and hdr["away_coach"] == "Magro Alessandro"
    assert hdr["q1_home"] == 29 and hdr["q4_away"] == 27


def test_box_rows() -> None:
    """Check box rows."""
    rows = list(box_rows(FIX["scores"]))
    assert all(set(r) == set(BOX_FIELDS) for r in rows)
    players = [r for r in rows if r["row_type"] == "player"]
    totals = {r["team"]: r for r in rows if r["row_type"] == "total"}
    assert len(players) == 4 and len(totals) == 2
    capp = next(r for r in players if r["player_surname"] == "CAPPELLETTI")
    assert capp["pts"] == 15 and capp["ast"] == 9 and capp["fg2m"] == 4 and capp["plus_minus"] == 8
    assert capp["starter"] == 0 and capp["home"] == 1 and capp["opponent"] == "BC Roma"
    mannion = next(r for r in players if r["player_surname"] == "MANNION")
    assert mannion["starter"] == 1 and mannion["home"] == 0 and mannion["plus_minus"] == -24
    assert totals["BC Roma"]["pts"] == 94 and totals["BC Roma"]["fg3a"] == 36
    team_rows = [r for r in rows if r["row_type"] == "team"]
    assert team_rows[0]["reb"] == 7  # team rebounds, Treviso


def test_pbp_rows() -> None:
    """Check pbp rows."""
    rows = list(pbp_rows(25602, FIX["pbp"]))
    assert all(set(r) == set(PBP_FIELDS) for r in rows)
    assert len(rows) == 6
    shot = next(r for r in rows if r["event"] == "3 punti sbagliato")
    assert shot["player_surname"] == "Macura" and (shot["x"], shot["y"]) == (31, 63)
    assert shot["qualifier_1"] == "Tiro in sospensione" and shot["clock"] == "09:44" and shot["elapsed_sec"] == 16
    made = next(r for r in rows if r["event"] == "2 punti segnato")
    assert (made["score_home"], made["score_away"]) == (0, 2) and made["in_area"] is True
    reb = next(r for r in rows if r["event"].startswith("Rimbalzi offensivi"))
    assert reb["linked_seq"] == shot["seq"]
