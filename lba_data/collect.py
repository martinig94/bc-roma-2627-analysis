"""Incremental collector: pulls new finished games and appends them to the CSVs.

    python -m lba_data.collect                 # 2026/27 regular season (championship 602)
    python -m lba_data.collect --champ 602 --year 2026
    python -m lba_data.collect --refresh-games # re-pull the calendar only (schedule changes)

State = the set of game_ids already present in data/box_scores.csv, so re-running is idempotent.
Raw JSON for every collected game is kept under data/raw/<game_id>/ so any derived table can be
rebuilt without hitting the site again (python -m lba_data.rebuild).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

from . import api
from .transform import BOX_FIELDS, GAME_FIELDS, PBP_FIELDS, box_rows, game_row, pbp_rows

DATA = Path(__file__).resolve().parent.parent / "data"
RAW = DATA / "raw"
GAMES_CSV = DATA / "games.csv"
BOX_CSV = DATA / "box_scores.csv"
PBP_CSV = DATA / "pbp.csv"
TEAMS_CSV = DATA / "teams.csv"
ROSTERS_CSV = DATA / "team_rosters.csv"
ROSTER_FIELDS = ["year", "team_id", "team", "player_id", "name", "surname", "number", "role", "birth_date",
                 "place_of_birth", "country", "height_cm", "weight_kg", "start_date", "end_date", "picture_key"]

DEFAULT_CHAMP = 602   # Regular Season 2026/27
DEFAULT_YEAR = 2026
CALENDAR_PAUSE_S = 0.3   # seconds between calendar / roster calls (be polite to the site)
DEFAULT_GAME_PAUSE_S = 1.0   # seconds between games
# Game fields that the calendar leaves empty and the match header fills in.
HEADER_ONLY_FIELDS = ("spectators", "home_coach", "away_coach", "phase_id")


def _write_csv(path: Path, fields: list[str], rows: list[dict], append: bool = False) -> None:
    """Write ``rows`` to a CSV with header ``fields`` (header only when the file is new or rewritten)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists() or not append
    with path.open("a" if append else "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerows(rows)


def _existing_game_ids(path: Path) -> set[int]:
    """Return the game ids already present in a CSV (empty set if the file does not exist)."""
    if not path.exists():
        return set()
    with path.open(newline="", encoding="utf-8") as fh:
        return {int(r["game_id"]) for r in csv.DictReader(fh) if r.get("game_id")}


def roster_rows(team_id: int, team: str, payload: dict, year: int) -> list[dict]:
    """Flatten the roster endpoint payload of one team into rows keyed by ``ROSTER_FIELDS``."""
    return [{"year": year, "team_id": team_id, "team": team, "player_id": p["id"], "name": p.get("name"),
             "surname": p.get("surname"), "number": p.get("player_number"), "role": p.get("player_role"),
             "birth_date": p.get("birth_date"), "place_of_birth": p.get("place_of_birth"), "country": p.get("country"),
             "height_cm": p.get("height"), "weight_kg": p.get("weight"), "start_date": p.get("start_date"),
             "end_date": p.get("end_date"), "picture_key": p.get("player_picture_key")} for p in payload.get("players", [])]


def collect_rosters(teams: list[dict], year: int) -> None:
    """Write the "giocatori" table of every team page to data/team_rosters.csv.

    The file is rewritten each run because rosters change in-season. A team whose call fails
    keeps its rows from the previous file.

    Args:
        teams: Team objects from ``api.teams``.
        year: Season start year.
    """
    prev: list[dict] = []
    if ROSTERS_CSV.exists():
        with ROSTERS_CSV.open(newline="", encoding="utf-8") as fh:
            prev = [r for r in csv.DictReader(fh) if r["year"] == str(year)]
    rows: list[dict] = []
    for t in teams:
        name = t.get("name") or t.get("full_name")
        try:
            got = roster_rows(t["id"], name, api.team_roster(t["id"], year), year)
        except Exception as exc:  # noqa: BLE001 - the rest of the collection does not depend on it
            print(f"roster {name}: FAILED {exc}", file=sys.stderr)
            got = [r for r in prev if r["team_id"] == str(t["id"])]
        rows += got
        time.sleep(CALENDAR_PAUSE_S)
    if rows:
        _write_csv(ROSTERS_CSV, ROSTER_FIELDS, rows)
        print(f"rosters: {len(rows)} players, {len(teams)} teams", file=sys.stderr)


def fetch_calendar(champ: int) -> list[dict]:
    """Return every match of a championship, de-duplicated and sorted by game id."""
    first = api.calendar(champ)
    days = [d["event_serial"] for d in first["filters"]["days"]]
    matches: dict[int, dict] = {}
    for d in days:
        for m in api.calendar(champ, d)["matches"]:
            matches[m["id"]] = m
        time.sleep(CALENDAR_PAUSE_S)
    return [matches[k] for k in sorted(matches)]


def collect_game(game_id: int) -> tuple[dict, list[dict], list[dict]]:
    """Download one game, keep its raw JSON under data/raw/ and return (header, box rows, pbp rows)."""
    header = api.match(game_id)
    box = api.box_score(game_id)
    pbp = api.play_by_play(game_id)
    raw_dir = RAW / str(game_id)
    raw_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in (("match", header), ("box_score", box), ("play_by_play", pbp)):
        (raw_dir / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return game_row(header["match"]), list(box_rows(box)), list(pbp_rows(game_id, pbp))


def main(argv: list[str] | None = None) -> int:
    """Run the incremental collection (see the module docstring); return the process exit code."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--champ", type=int, default=DEFAULT_CHAMP, help="championship id (602 = RS 2026/27)")
    ap.add_argument("--year", type=int, default=DEFAULT_YEAR)
    ap.add_argument("--limit", type=int, default=None, help="collect at most N new games (for testing)")
    ap.add_argument("--refresh-games", action="store_true", help="only rewrite games.csv from the calendar")
    ap.add_argument("--sleep", type=float, default=DEFAULT_GAME_PAUSE_S, help="seconds between games (be polite)")
    args = ap.parse_args(argv)

    teams = api.teams(args.year)
    _write_csv(TEAMS_CSV, ["team_id", "team", "year"],
               [{"team_id": t["id"], "team": t.get("name") or t.get("full_name"), "year": args.year} for t in teams])

    collect_rosters(teams, args.year)

    calendar = fetch_calendar(args.champ)
    games = [game_row(m) for m in calendar]
    print(f"calendar: {len(games)} games, {sum(g['game_status'] == api.STATUS_FINISHED for g in games)} finished",
          file=sys.stderr)
    if args.refresh_games:
        _write_csv(GAMES_CSV, GAME_FIELDS, games)
        return 0

    done = _existing_game_ids(BOX_CSV)
    todo = [g["game_id"] for g in games if g["game_status"] == api.STATUS_FINISHED and g["game_id"] not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"already collected: {len(done)}; new finished games to collect: {len(todo)}", file=sys.stderr)

    game_details: dict[int, dict] = {}
    failed: list[int] = []
    for i, gid in enumerate(todo, 1):
        try:
            hdr, box, pbp = collect_game(gid)
        except Exception as exc:  # noqa: BLE001 - keep going, report at the end
            print(f"[{i}/{len(todo)}] game {gid}: FAILED {exc}", file=sys.stderr)
            failed.append(gid)
            continue
        if not box:
            print(f"[{i}/{len(todo)}] game {gid}: box score empty, skipping for now", file=sys.stderr)
            continue
        _write_csv(BOX_CSV, BOX_FIELDS, box, append=True)
        _write_csv(PBP_CSV, PBP_FIELDS, pbp, append=True)
        game_details[gid] = hdr
        print(f"[{i}/{len(todo)}] game {gid}: {hdr['home_team']} {hdr['home_score']}-{hdr['away_score']} "
              f"{hdr['away_team']} ({len(box)} box rows, {len(pbp)} pbp events)", file=sys.stderr)
        time.sleep(args.sleep)

    # games.csv: calendar rows, enriched with header details (spectators, coaches) where we have them
    prev: dict[int, dict] = {}
    if GAMES_CSV.exists():
        with GAMES_CSV.open(newline="", encoding="utf-8") as fh:
            prev = {int(r["game_id"]): r for r in csv.DictReader(fh)}
    merged = []
    for g in games:
        gid = g["game_id"]
        detail = game_details.get(gid) or prev.get(gid) or {}
        for k in HEADER_ONLY_FIELDS:
            if not g.get(k) and detail.get(k):
                g[k] = detail[k]
        merged.append(g)
    _write_csv(GAMES_CSV, GAME_FIELDS, merged)

    if failed:
        print(f"failed games (will retry next run): {failed}", file=sys.stderr)
    return 1 if failed and not game_details else 0


if __name__ == "__main__":
    sys.exit(main())
