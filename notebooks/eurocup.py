"""EuroCup data: results of every game of the season, club rosters with headshots, and standings as of any date.

    python notebooks/eurocup.py                 # fetch results + the rosters (with headshots) of BC Roma and its opponents
    python notebooks/eurocup.py --clubs BCR MAN # other clubs (EuroLeague club codes)

Source: the EuroLeague live API (api-live.euroleague.net), the one wrapped by the `euroleague-api` package
(https://github.com/giasemidis/euroleague_api). Results come through that package (get_gamecodes_season, competition "U");
the club rosters (height, position, headshot) come from the club "people" endpoint, which the package does not wrap.
Needs network access to the host, so it runs in the daily GitHub Action; the files it writes are committed:

  data/eurocup/results.csv    one row per game of the season, played or not: gamecode, round, date, teams, scores, played
  data/eurocup/people.csv     club, player, height_cm, position, number, photo_url
  data/eurocup/photos/<photo_name>.jpg   headshot thumbnails (name key as in player_names.photo_name)

Standings are computed here from results.csv, as of any date, for the group of the team: EuroCup's regular season is played in
groups, and a team's group is the set of teams connected to it through the full schedule (the teams of a group only meet each
other). Ranking: wins, then the games among the tied teams, then point difference (see standings.py); the official tie-breaks
may differ slightly.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import numpy as np
import pandas as pd

import standings as st
import weekly_config
from player_names import display_name, find_image_url, photo_name

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "eurocup"
SEASON = 2026
COMPETITION_CODE = "U"                  # EuroLeague API code of the EuroCup
COMPETITION = "EuroCup"                 # name of the competition in weekly/schedule.csv
CFG = weekly_config.load()
HTTP_TIMEOUT = 60                       # seconds
PHOTO_SIZE = 240                        # px, side of the headshot thumbnail box (height allowed up to twice that)
PHOTO_QUALITY = 88                      # JPEG quality of the thumbnails
# EuroCup spelling -> our spelling (the same map the EuroCup box-score file uses)
NAME_FIX = {"ROMA BASKETBALL": "BC Roma", "MAXIMA ROMA": "Maxima Roma"}
PEOPLE = "https://api-live.euroleague.net/v2/competitions/U/seasons/U{season}/clubs/{club}/people"
RESULT_COLS = ["gamecode", "round", "date", "home_code", "home", "home_score", "away_code", "away", "away_score", "played"]


def team_name(raw: str) -> str:
    """Return a team name in our spelling: a known fix, else title case of the feed's upper-case name."""
    raw = str(raw).strip()
    return NAME_FIX.get(raw.upper(), raw.title())


# ── fetch ───────────────────────────────────────────────────────────────────────
def fetch_results(season: int = SEASON) -> pd.DataFrame:
    """Every game of the EuroCup season (the results feed lists the whole schedule, played or not)."""
    from euroleague_api.game_metadata import GameMetadata
    raw = GameMetadata(COMPETITION_CODE).get_gamecodes_season(season)
    missing = [c for c in ("gameCode", "Round", "date", "homecode", "hometeam", "homescore", "awaycode", "awayteam", "awayscore", "played") if c not in raw]
    if missing:
        raise SystemExit(f"EuroCup results feed has no column(s) {missing}; got {list(raw.columns)}")
    out = pd.DataFrame({
        "gamecode": raw.gameCode, "round": raw.Round,
        "date": pd.to_datetime(raw.date, format="%b %d, %Y", errors="coerce").dt.strftime("%Y-%m-%d"),
        "home_code": raw.homecode.str.strip(), "home": raw.hometeam.map(team_name), "home_score": raw.homescore,
        "away_code": raw.awaycode.str.strip(), "away": raw.awayteam.map(team_name), "away_score": raw.awayscore,
        "played": raw.played.astype(bool),
    })
    return out[RESULT_COLS].sort_values("gamecode")


def fetch_people(club: str, season: int = SEASON) -> pd.DataFrame:
    """Return the players of a club (club, player, height_cm, position, number, photo_url) from the club "people" endpoint."""
    import requests
    r = requests.get(PEOPLE.format(season=season, club=club), headers={"Accept": "application/json"}, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    rows = []
    for person in r.json():
        if person.get("type") != "J" and person.get("typeName") != "Player":
            continue
        info = person["person"]
        rows.append({"club": club, "player": display_name(info["name"]), "height_cm": info.get("height") or None,
                     "position": person.get("positionName"), "number": person.get("dorsal") or None, "photo_url": find_image_url(person)})
    return pd.DataFrame(rows)


def save_photos(people: pd.DataFrame, size: int = PHOTO_SIZE) -> int:
    """Headshot thumbnails into data/eurocup/photos/<photo_name>.jpg; a missing picture never stops the run."""
    import requests
    from PIL import Image
    (DATA / "photos").mkdir(parents=True, exist_ok=True)
    n = 0
    for r in people.itertuples():
        dest = DATA / "photos" / f"{photo_name(r.player)}.jpg"
        if not isinstance(r.photo_url, str) or dest.exists():
            continue
        try:
            img = Image.open(io.BytesIO(requests.get(r.photo_url, timeout=HTTP_TIMEOUT).content)).convert("RGBA")
        except Exception as exc:
            print(f"photo {r.player}: {exc}")
            continue
        bg = Image.new("RGB", img.size, "white"); bg.paste(img, mask=img.split()[3]); bg.thumbnail((size, size * 2))
        bg.save(dest, quality=PHOTO_QUALITY, optimize=True)
        n += 1
    return n


# ── the team's upcoming games into weekly/schedule.csv ────────────────────────────
SCHEDULE = ROOT / "weekly" / "schedule.csv"
SCHEDULE_COLS = ["date", "time", "competition", "opponent", "home", "analysis"]
MATCHUP_PREFIX = "matchup_"           # analysis folders built by opponent.py start with this
GAMES = "https://api-live.euroleague.net/v2/competitions/U/seasons/U{season}/games?teamCode={club}&limit=100"


def upcoming_rows(games: list[dict], club: str, names: dict[str, str]) -> list[dict]:
    """schedule.csv rows for the games of `club` not played yet, from the games endpoint of the EuroLeague API (it lists the whole season).
    `names`: club code -> team name as in the results feed. `analysis` is the folder name opponent.py builds (matchup_<home>_vs_<away>_before_<date>)."""
    rows = []
    for g in games:
        if g.get("played"):
            continue
        home, road = g["local"]["club"], g["road"]["club"]
        at_home = home["code"].strip() == club
        opp = road if at_home else home
        opp_name = names.get(opp["code"].strip()) or team_name(opp["name"])
        team = names[club]
        h, a = (team, opp_name) if at_home else (opp_name, team)
        day = g["date"][:10]
        rows.append({"date": day, "time": g["date"][11:16], "competition": COMPETITION, "opponent": opp_name, "home": "1" if at_home else "0",
                     "analysis": f"{MATCHUP_PREFIX}{h.replace(' ', '_')}_vs_{a.replace(' ', '_')}_before_{day}"})
    return sorted(rows, key=lambda r: r["date"])


def update_schedule(results: pd.DataFrame, team: str, path: Path = SCHEDULE, season: int = SEASON) -> int:
    """Keep the EuroCup games still to play in weekly/schedule.csv up to date (dates change, games are added): rows of the games to come are
    replaced by the API's. Rows you wrote by hand are never touched: a row of a game already played, or whose analysis folder has a hand-written
    README.md / document.md. Returns the number of games to come."""
    import requests
    names = {**dict(zip(results.home_code, results.home)), **dict(zip(results.away_code, results.away))}
    club = next((c for c, n in names.items() if n == team), None)
    if club is None:
        return 0
    r = requests.get(GAMES.format(season=season, club=club), headers={"Accept": "application/json"}, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    new = upcoming_rows(r.json()["data"], club, names)
    old = pd.read_csv(path, dtype=str, keep_default_na=False) if path.exists() else pd.DataFrame(columns=SCHEDULE_COLS)
    played = set(results[results.played].date)

    def by_hand(row) -> bool:
        """Whether the schedule row was written by hand and must be kept."""
        slug = row.analysis
        return (row.competition != COMPETITION or row.date in played or bool(slug) and not slug.startswith(MATCHUP_PREFIX)
                or bool(slug) and ((ROOT / "reports" / slug / "README.md").exists() or (ROOT / "weekly" / "opponent" / slug / "document.md").exists()))

    keep = old[[by_hand(x) for x in old.itertuples()]]
    out = pd.concat([keep, pd.DataFrame(new, columns=SCHEDULE_COLS)], ignore_index=True)
    out = out.drop_duplicates(["competition", "date"], keep="first").sort_values(["date", "time"], kind="stable")
    out[SCHEDULE_COLS].to_csv(path, index=False)
    return len(new)


# ── box scores into the raw file ────────────────────────────────────────────────
RAW = ROOT / "data" / "eurocup_2026_raw.txt"
RAW_NAME = {"BCR": "ROMA BASKETBALL"}      # club codes whose name in the raw file differs from the results feed (see matchup_report.EC_TEAM_MAP)
ZONE_ACTIONS = ("2FGM", "2FGA", "3FGM", "3FGA")
TEAM_ROWS = ("Team", "Total")               # non-player rows of the box-score feed
BOX_STAT_COLS = ["Points", "FieldGoalsMade2", "FieldGoalsAttempted2", "FieldGoalsMade3", "FieldGoalsAttempted3", "FreeThrowsMade",
                 "FreeThrowsAttempted", "OffensiveRebounds", "DefensiveRebounds", "Assistances", "Steals", "Turnovers", "BlocksFavour",
                 "FoulsCommited", "FoulsReceived"]
DNP = "DNP"                                 # minutes value of a player who did not play


def _i(x: object) -> int:
    """Return `x` as an int, 0 for None/NaN."""
    return 0 if x is None or pd.isna(x) else int(x)


def fetch_game_lines(gamecode: int, names: dict[str, str], season: int = SEASON) -> tuple[list[str], list[str]]:
    """Raw-file lines of one played game: (BOX lines, ZONES lines). Format: notebooks/eurocup_fetch.md.
    `names` maps club code -> team name as written in the file. Team totals are the sum of the players and the team row; PIR is the API's team total."""
    from euroleague_api.boxscore_data import BoxScoreData
    from euroleague_api.shot_data import ShotData
    df = BoxScoreData(COMPETITION_CODE).get_players_boxscore_stats(season, gamecode)
    box, order, quarters = [], [], []
    for code in dict.fromkeys(df.Team):
        t = df[df.Team == code]
        name = names.get(code, code)
        order.append(name)
        players = t[~t.Player.isin(TEAM_ROWS)]
        rows = t[t.Player != TEAM_ROWS[1]]          # the "Team" row carries the team rebounds (and the like): part of the totals, not a player
        cols = BOX_STAT_COLS
        for r in players.itertuples():
            m = r.Minutes if isinstance(r.Minutes, str) and ":" in r.Minutes else DNP
            vals = [_i(getattr(r, c)) for c in cols] + [_i(r.Plusminus), _i(r.Valuation)]
            box.append("|".join([str(gamecode), name, r.Player, str(_i(r.IsStarter)), m, *map(str, vals)]))
        tot = [str(int(rows[c].fillna(0).sum())) for c in cols]
        val = int(t[t.Player == TEAM_ROWS[1]].Valuation.iloc[0])
        box.append("|".join([str(gamecode), name, "TOTAL", "", "", *tot, "", str(val)]))
    try:
        q = BoxScoreData(COMPETITION_CODE).get_teams_boxscore_quarter_scores(season, gamecode)
        parts = [f"{r.Team}:{r.Quarter1}-{r.Quarter2}-{r.Quarter3}-{r.Quarter4}" for r in q.itertuples()]
        if parts:
            box.append(f"{gamecode}|QUARTERS|" + ";".join(parts))
    except Exception:
        pass            # the quarters line is informational; nothing reads it
    sh = ShotData(COMPETITION_CODE).get_game_shot_data(season, gamecode)
    sh = sh[sh.ID_ACTION.isin(ZONE_ACTIONS) & sh.ZONE.astype(str).str.strip().ne("")]
    zones = [f"{gamecode}|{code}|{zone}|{act}|{n}" for (code, zone, act), n in sh.groupby(["TEAM", "ZONE", "ID_ACTION"]).size().items()]
    return box, zones


def update_raw(results: pd.DataFrame, path: Path = RAW) -> list[int]:
    """Append the played games that are not in the raw file yet (every team of the EuroCup, so that the league reference is complete).
    Returns the game codes added. A game that cannot be fetched is skipped and tried again on the next run."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else ["BOX", "ZONES"]
    have = {int(l.split("|")[0]) for l in lines if re.match(r"^\d+\|", l)}
    names = {**dict(zip(results.home_code, results.home)), **dict(zip(results.away_code, results.away))}
    names = {c: RAW_NAME.get(c, n.upper()) for c, n in names.items()}
    new_box, new_zones, added = [], [], []
    for gc in results[results.played & ~results.gamecode.isin(have)].gamecode:
        try:
            b, z = fetch_game_lines(int(gc), names)
        except Exception as exc:
            print(f"box score of game {gc}: {exc}")
            continue
        new_box += b; new_zones += z; added.append(int(gc))
    if added:
        i = lines.index("ZONES")
        path.write_text("\n".join(lines[:i] + new_box + lines[i:] + new_zones) + "\n", encoding="utf-8")
    return added


# ── play-by-play (same columns as data/pbp.csv, so the LBA code reads it unchanged) ──────────────────
PBP = DATA / "pbp.csv"
PBP_EVENT = {"2FGM": "2 punti segnato", "2FGA": "2 punti sbagliato", "3FGM": "3 punti segnato", "3FGA": "3 punti sbagliato",
             "FTM": "Tiro libero segnato", "FTA": "Tiro libero sbagliato", "AS": "Assist", "TO": "Palla persa", "ST": "Palla recuperata",
             "D": "Rimbalzo difensivo", "O": "Rimbalzo offensivo", "FV": "Stoppata", "AG": "Stoppata subita", "CM": "Fallo commesso",
             "RV": "Fallo Subito", "IN": "Ingresso", "OUT": "Uscita", "BP": "Inizio Tempo", "EP": "Fine Tempo"}
REGULATION_PERIODS = 4                  # quarters before overtime
PERIOD_SECONDS = 600                    # 10-minute quarter
OVERTIME_SECONDS = 300                  # 5-minute overtime
PERIOD_START = "BP"                     # play type that opens a period
# Shot-list coordinates (cm, basket at origin) -> percent-of-court x/y; inverse of lba_style.shots_cm
SHOT_X_OFFSET_CM, SHOT_X_SCALE = 157.5, 28
SHOT_Y_SCALE = 15
SHOT_Y_CENTRE = 50
ASSIST_MAX_GAP = 6                      # an assist is linked to a basket at most this many events earlier
PBP_COLS = ["game_id", "seq", "period", "clock", "elapsed_sec", "score_home", "score_away", "team", "player_id", "player_name", "player_surname",
            "event", "x", "y", "linked_seq"]
MADE = ("2 punti segnato", "3 punti segnato")


def fetch_game_pbp(gamecode: int, home_code: str, names: dict[str, str], season: int = SEASON) -> pd.DataFrame:
    """One game in the LBA play-by-play layout. The EuroLeague shot list gives the court position of every field goal attempt (centimetres, basket at
    the origin, both ends folded to one half): it is written back as the percent-of-court x/y that lba_style.shots_cm expects. The assist is linked to
    the made basket that precedes it (the feed does not link them)."""
    from euroleague_api.play_by_play_data import PlayByPlay
    from euroleague_api.shot_data import ShotData
    from player_names import ec_surname
    pbp = PlayByPlay(COMPETITION_CODE).get_game_play_by_play_data(season, gamecode)
    pbp = pbp[pbp.PLAYTYPE.isin(PBP_EVENT)].sort_values("NUMBEROFPLAY").copy()
    shots = ShotData(COMPETITION_CODE).get_game_shot_data(season, gamecode)
    shots = shots[shots.ID_ACTION.isin(ZONE_ACTIONS) & ~((shots.COORD_X == -1) & (shots.COORD_Y == -1))].set_index("NUM_ANOT")
    shots = shots[~shots.index.duplicated()]
    left = PERIOD_SECONDS * np.where(pbp.PERIOD <= REGULATION_PERIODS, 1, OVERTIME_SECONDS / PERIOD_SECONDS)
    secs = lambda t: int(t.split(":")[0]) * 60 + int(t.split(":")[1]) if isinstance(t, str) and ":" in t else 0
    rem = np.where(pbp.PLAYTYPE == PERIOD_START, left, pbp.MARKERTIME.map(secs))     # the clock shows the time left in the period
    out = pd.DataFrame({
        "game_id": f"EC{gamecode}", "seq": pbp.NUMBEROFPLAY.values, "period": pbp.PERIOD.values,
        "clock": [f"{int(r // 60):02d}:{int(r % 60):02d}" for r in rem], "elapsed_sec": (left - rem).astype(int),
        "team": [names.get(c, c) if isinstance(c, str) and c.strip() else None for c in pbp.CODETEAM],
        "player_id": pbp.PLAYER_ID.values, "event": pbp.PLAYTYPE.map(PBP_EVENT).values,
    })
    raw = pbp.PLAYER.fillna("").values
    out["player_name"] = [r.split(",")[1].strip().title() if "," in r else None for r in raw]
    out["player_surname"] = [ec_surname(r).title() if r else None for r in raw]
    out["is_home"] = (pbp.CODETEAM.str.strip() == home_code).values
    for col in ("POINTS_A", "POINTS_B"):
        out[col] = pbp[col].values
    out["score_home"] = out.POINTS_A.ffill().fillna(0).astype(int)
    out["score_away"] = out.POINTS_B.ffill().fillna(0).astype(int)
    sx = shots.reindex(pbp.NUMBEROFPLAY.values)
    on_court = out.event.str.contains("punti", na=False).values
    cx, cy = np.where(on_court, sx.COORD_X.values, np.nan), np.where(on_court, sx.COORD_Y.values, np.nan)
    out["x"] = ((cy + SHOT_X_OFFSET_CM) / SHOT_X_SCALE).round(2)             # inverse of lba_style.shots_cm
    out["y"] = (cx / SHOT_Y_SCALE + SHOT_Y_CENTRE).round(2)
    out["linked_seq"] = np.nan
    last = {}                                           # team -> (seq, position in the frame) of its last made basket without an assist
    for i, r in enumerate(out.itertuples()):
        if r.event in MADE:
            last[r.team] = (r.seq, i)
        elif r.event == "Assist" and r.team in last and i - last[r.team][1] <= ASSIST_MAX_GAP:
            out.iat[i, out.columns.get_loc("linked_seq")] = last.pop(r.team)[0]
    return out[PBP_COLS]


def update_pbp(results: pd.DataFrame, path: Path = PBP) -> list[int]:
    """Append the played games that are not in data/eurocup/pbp.csv yet. Returns the game codes added; a game that fails is tried again next run."""
    old = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=PBP_COLS)
    have = {int(str(g)[2:]) for g in old.game_id.unique()}
    names = {**dict(zip(results.home_code, results.home)), **dict(zip(results.away_code, results.away))}
    frames, added = [old], []
    for r in results[results.played & ~results.gamecode.isin(have)].itertuples():
        try:
            frames.append(fetch_game_pbp(int(r.gamecode), r.home_code, names))
        except Exception as exc:
            print(f"play-by-play of game {r.gamecode}: {exc}")
            continue
        added.append(int(r.gamecode))
    if added:
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.concat(frames, ignore_index=True).to_csv(path, index=False)
    return added


# ── which rosters to fetch ──────────────────────────────────────────────────────
def club_codes(results: pd.DataFrame, team: str, schedule: Path | None = None) -> list[str]:
    """Club codes of the team, of every opponent it has played, and of the EuroCup opponents still to come in weekly/schedule.csv
    (matched to the results by name), so the roster and headshots of the next opponent are there before the game."""
    mine = results[(results.home == team) | (results.away == team)]
    codes = {*mine.home_code, *mine.away_code}
    if schedule is not None and schedule.exists():
        names = {**dict(zip(results.home, results.home_code)), **dict(zip(results.away, results.away_code))}
        for r in pd.read_csv(schedule, dtype=str, keep_default_na=False).itertuples():
            if r.competition.lower() != COMPETITION.lower():
                continue
            hit = find_team(names, r.opponent)
            if hit:
                codes.add(names[hit])
    return sorted(codes)


# ── standings ───────────────────────────────────────────────────────────────────
def load_results(data: Path = ROOT / "data") -> pd.DataFrame | None:
    """Return data/eurocup/results.csv as a DataFrame, or None when it has not been fetched yet."""
    path = data / "eurocup" / "results.csv"
    return pd.read_csv(path) if path.exists() else None


def group_teams(results: pd.DataFrame, team: str) -> set[str]:
    """The teams connected to `team` through the full schedule (its group)."""
    links: dict[str, set[str]] = {}
    for h, a in zip(results.home, results.away):
        links.setdefault(h, set()).add(a); links.setdefault(a, set()).add(h)
    seen, todo = set(), [team]
    while todo:
        t = todo.pop()
        if t not in seen:
            seen.add(t); todo += list(links.get(t, ()))
    return seen


def games_frame(results: pd.DataFrame, team: str) -> pd.DataFrame:
    """The team's group's games in the column layout of data/games.csv, so standings.py can rank and draw them."""
    grp = group_teams(results, team)
    r = results[results.home.isin(grp)]
    return pd.DataFrame({
        "game_id": r.gamecode, "round": r["round"], "match_datetime": r.date.astype(str) + "T00:00:00", "game_status": r.played.map({True: 2, False: 0}),
        "home_team": r.home, "away_team": r.away, "home_score": r.home_score, "away_score": r.away_score,
    }).reset_index(drop=True)


def find_team(names, wanted: str) -> str | None:
    """Our name of a club -> its name in the results feed (exact, else the closest spelling)."""
    import difflib
    low = {n.lower(): n for n in names}
    hit = difflib.get_close_matches(wanted.lower(), list(low), n=1, cutoff=0.6)
    return low[hit[0]] if hit else None


def standings_before(results: pd.DataFrame, team: str, before: str) -> pd.DataFrame | None:
    """The team's group table as of `before` (games played strictly before that date); None when the team is not in the data."""
    frame = games_frame(results, team)
    if frame.empty:
        return None
    return st.standings(frame, before)
