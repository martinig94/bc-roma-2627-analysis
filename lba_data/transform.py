"""Flatten legabasket.it JSON payloads into tidy row dicts (pure functions, no I/O)."""
from __future__ import annotations

from collections.abc import Iterable

STARTER_FLAG = "1"   # value of the API's `sf` field for a starter
SCORE_SEPARATOR = "-"         # separator in the pbp running score, e.g. "12-10"
SECONDS_PER_MINUTE = 60

GAME_FIELDS = [
    "game_id", "championship_id", "competition", "year", "round", "round_name", "phase_id",
    "match_datetime", "game_status", "home_team_id", "home_team", "away_team_id", "away_team",
    "home_score", "away_score",
    "q1_home", "q1_away", "q2_home", "q2_away", "q3_home", "q3_away", "q4_home", "q4_away",
    "ot_home", "ot_away", "venue", "town", "spectators", "home_coach", "away_coach", "updated_at",
]

BOX_STAT_FIELDS = [
    "min", "sec", "pun", "t2_r", "t2_t", "t3_r", "t3_t", "tl_r", "tl_t",
    "rimbalzi_o", "rimbalzi_d", "rimbalzi_t", "ass", "palle_r", "palle_p",
    "stoppate_dat", "stoppate_sub", "falli_c", "falli_sf", "falli_tc1", "falli_fla",
    "sc", "val_lega", "val_oer", "plus_minus",
]
# English aliases for the Italian stat keys, applied in the CSV header.
STAT_RENAME = {
    "pun": "pts", "t2_r": "fg2m", "t2_t": "fg2a", "t3_r": "fg3m", "t3_t": "fg3a",
    "tl_r": "ftm", "tl_t": "fta", "rimbalzi_o": "oreb", "rimbalzi_d": "dreb", "rimbalzi_t": "reb",
    "ass": "ast", "palle_r": "stl", "palle_p": "tov", "stoppate_dat": "blk", "stoppate_sub": "blk_against",
    "falli_c": "pf", "falli_sf": "pf_drawn", "falli_tc1": "tech_fouls", "falli_fla": "flagrant_fouls",
    "sc": "dunks", "val_lega": "val", "val_oer": "oer", "plus_minus": "plus_minus",
    "min": "min", "sec": "sec",
}

BOX_FIELDS = [
    "game_id", "match_datetime", "round", "team_id", "team", "opponent_id", "opponent", "home",
    "row_type", "player_id", "player_code", "player_num", "player_name", "player_surname", "starter",
] + [STAT_RENAME[f] for f in BOX_STAT_FIELDS]

PBP_FIELDS = [
    "game_id", "seq", "period", "clock", "elapsed_sec", "score_home", "score_away",
    "team_id", "team", "home_club", "player_id", "player_num", "player_name", "player_surname",
    "event", "qualifier_1_code", "qualifier_1", "qualifier_2_code", "qualifier_2",
    "x", "y", "side", "zone", "area", "in_area", "dunk", "linked_seq",
]


def game_row(m: dict) -> dict:
    """Return one flat games.csv row from a match header.

    Args:
        m: Calendar entry or the ``match`` object of matches-by-id.

    Returns:
        Dict keyed by ``GAME_FIELDS``; fields missing from ``m`` are None.
    """
    return {
        "game_id": m.get("id"),
        "championship_id": m.get("championship_id"),
        "competition": m.get("competition_name"),
        "year": m.get("year"),
        "round": m.get("day_serial"),
        "round_name": m.get("day_name"),
        "phase_id": m.get("day_phase_id"),
        "match_datetime": m.get("match_datetime"),
        "game_status": m.get("game_status"),
        "home_team_id": m.get("h_team_id"),
        "home_team": m.get("h_team_name"),
        "away_team_id": m.get("v_team_id"),
        "away_team": m.get("v_team_name"),
        "home_score": m.get("home_final_score"),
        "away_score": m.get("visitor_final_score"),
        "q1_home": m.get("q1_hs"), "q1_away": m.get("q1_vs"),
        "q2_home": m.get("q2_hs"), "q2_away": m.get("q2_vs"),
        "q3_home": m.get("q3_hs"), "q3_away": m.get("q3_vs"),
        "q4_home": m.get("q4_hs"), "q4_away": m.get("q4_vs"),
        "ot_home": m.get("ot_hs"), "ot_away": m.get("ot_vs"),
        "venue": m.get("plant_name"),
        "town": m.get("town_name"),
        "spectators": m.get("spectators"),
        "home_coach": m.get("home_coach_fullname"),
        "away_coach": m.get("visitor_coach_fullname"),
        "updated_at": m.get("updated_at"),
    }


def _stats(src: dict) -> dict:
    """Return the box-score stat columns of a player/team/total object under their English names."""
    return {STAT_RENAME[f]: src.get(f) for f in BOX_STAT_FIELDS}


def box_rows(payload: dict) -> Iterable[dict]:
    """Yield one box-score row per player, plus a ``team`` row (team rebounds etc.) and a ``total`` row per side.

    Args:
        payload: Response of the box-score endpoint.

    Yields:
        Dicts keyed by ``BOX_FIELDS``.
    """
    m = payload["match"]
    sides = [
        ("ht", m.get("h_team_id"), m.get("h_team_name"), m.get("v_team_id"), m.get("v_team_name"), 1),
        ("vt", m.get("v_team_id"), m.get("v_team_name"), m.get("h_team_id"), m.get("h_team_name"), 0),
    ]
    for key, tid, tname, oid, oname, home in sides:
        side = payload["scores"].get(key) or {}
        base = {
            "game_id": m.get("id"), "match_datetime": m.get("match_datetime"), "round": m.get("day_serial"),
            "team_id": tid, "team": tname, "opponent_id": oid, "opponent": oname, "home": home,
        }
        for p in side.get("rows", []):
            yield {
                **base, "row_type": "player",
                "player_id": p.get("player_id"), "player_code": p.get("player_code"),
                "player_num": p.get("player_num"), "player_name": p.get("player_name"),
                "player_surname": p.get("player_surname"),
                "starter": 1 if str(p.get("sf")) == STARTER_FLAG else 0,
                **_stats(p),
            }
        for row_type, src in (("team", side.get("team")), ("total", side.get("totals"))):
            if src:
                yield {
                    **base, "row_type": row_type, "player_id": None, "player_code": None,
                    "player_num": None, "player_name": None, "player_surname": None, "starter": None,
                    **_stats(src),
                }


def _split_score(s: str | None) -> tuple[int | None, int | None]:
    """Split a running score such as ``"12-10"`` into (home, away); (None, None) if unparsable."""
    if not s or SCORE_SEPARATOR not in s:
        return None, None
    a, b = s.split(SCORE_SEPARATOR, 1)
    try:
        return int(a), int(b)
    except ValueError:
        return None, None


def pbp_rows(game_id: int, payload: dict) -> Iterable[dict]:
    """Yield one row per play-by-play event of a game.

    Args:
        game_id: Id stored in every row.
        payload: Response of the play-by-play endpoint.

    Yields:
        Dicts keyed by ``PBP_FIELDS``; ``x``/``y`` are 0-100 percent of the court.
    """
    actions = (payload.get("pbp") or {}).get("actions") or []
    for a in actions:
        sh, sa = _split_score(a.get("score"))
        yield {
            "game_id": game_id,
            "seq": a.get("action_id"),
            "period": a.get("period"),
            "clock": a.get("print_time"),
            "elapsed_sec": (a.get("minute") or 0) * SECONDS_PER_MINUTE + (a.get("seconds") or 0),
            "score_home": sh, "score_away": sa,
            "team_id": a.get("team_id"), "team": a.get("team_name"), "home_club": a.get("home_club"),
            "player_id": a.get("player_id"), "player_num": a.get("player_number"),
            "player_name": a.get("player_name"), "player_surname": a.get("player_surname"),
            "event": a.get("description"),
            "qualifier_1_code": a.get("action_1_qualifier_code"),
            "qualifier_1": a.get("action_1_qualifier_description"),
            "qualifier_2_code": a.get("action_2_qualifier_code"),
            "qualifier_2": a.get("action_2_qualifier_description"),
            "x": a.get("x"), "y": a.get("y"), "side": a.get("side"),
            "zone": a.get("side_area_zone"), "area": a.get("side_area_code"),
            "in_area": a.get("in_area"), "dunk": a.get("dunk"),
            "linked_seq": a.get("linked_action_id"),
        }
