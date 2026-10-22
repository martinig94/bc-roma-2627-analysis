"""Extra sections of the weekly report (called by weekly_report.py): roster, playing-time flags, assist matrix,
shot zones, TS% vs PIR (LBA only, EuroCup only).

Every function takes the data as of the round being reported (LBA games up to that round; EuroCup games up to that date).
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

import lba_style
import weekly_config
from lba_style import BLUE, GREEN, LEAGUE, SUP_KW, TEXT, TEXT2, TITLE_KW, save_fig, shots_cm, style_axes, team_color
from matchup_report import apply_starter_overrides, parse_eurocup, plot_zone_heatmap, zone_stats
from player_names import photo_name

ROOT = Path(__file__).resolve().parent.parent
TEAM = weekly_config.load()["team"]
POS_ORDER = {"Guard": 1, "Forward": 2, "Center": 4,          # EuroCup club pages
             "PG": 0, "SG": 1, "G": 1, "SF": 2, "F": 2, "PF": 3, "C": 4,
             "Playmaker": 0, "Guardia": 1, "Guardia/Ala": 1, "Ala": 2, "Ala/Centro": 3, "Centro": 4}   # the last six: legabasket.it roles

# playing-time flag: at least MIN_PLAYED seconds in the game and either +ABS_UP seconds or +REL_UP above the average before
MIN_PLAYED, ABS_UP, REL_UP = 8 * 60, 7 * 60, 0.30

COMP_LBA, COMP_EC = "LBA", "EC"          # values of the `competition` column of load_box()
ALL_ROUNDS, END_OF_TIME = 10**6, "9999-12-31"   # "no limit" for load_box(upto_round, upto_date)
ROSTER_COLS = ["player_id", "surname", "team", "position", "height_cm"]   # data/roster.csv
MIN_PLAUSIBLE_HEIGHT_CM = 150            # EuroCup club pages sometimes carry a placeholder height below this
NAME_SUFFIX_RE = r"\b(jr|sr|ii|iii)\b\.?"   # dropped when matching surnames across sources
NO_VALUE = "–"                           # shown for a figure that does not exist
FTA_POSSESSION_WEIGHT = 0.44             # standard estimate: free-throw attempts that end a possession
EC_GAME_MIN = 40                         # EuroCup totals carry 2400 s for the whole team, not 5 x 2400
TEAM_SEC_PER_MIN = 300                   # LBA totals carry 5 players x 60 s per team minute
BOX_MIN_PER_GAME = 40                    # minutes in a regulation game, for the pace figure
MIN_ASSIST_LINKS = 4                     # assist matrix: drop players involved in fewer assisted baskets than this
EVENT_ASSIST, EVENT_MADE = "Assist", "punti segnato"   # play-by-play event names (Italian feed)
MAX_MPG_FOR_BUBBLE, BUBBLE_SCALE, BUBBLE_MIN = 36, 420, 40   # TS% vs PIR: bubble area = mpg / 36 * 420 + 40
OUT_COLOR, BENCH_COLOR = "#d64545", "#e6e6ee"   # starting-fives grid: out of the game / bench minutes


# ── data ────────────────────────────────────────────────────────────────────────
def load_box(data: Path, upto_round: int, upto_date: str, eurocup_file: str = "") -> pd.DataFrame:
    """Return LBA player/total rows (all teams, rounds <= upto_round) + EuroCup rows (all teams in the file, date <= upto_date).

    Args:
        data: Folder with box_scores.csv (and the starter overrides).
        upto_round: Last LBA round to include.
        upto_date: Last EuroCup date (YYYY-MM-DD) to include.
        eurocup_file: EuroCup box-score file relative to the project root; empty for none.
    """
    lba = apply_starter_overrides(pd.read_csv(data / "box_scores.csv"), data)
    lba = lba[lba["round"] <= upto_round].copy()
    lba["competition"] = COMP_LBA; lba["date"] = lba.match_datetime.str[:10]; lba["game_id"] = lba.game_id.astype(str)
    ec_path = ROOT / eurocup_file if eurocup_file else None
    frames = [lba]
    if ec_path and ec_path.exists():
        ec, _ = parse_eurocup(ec_path)
        frames.append(ec[ec.date <= upto_date])
    box = pd.concat(frames, ignore_index=True)
    box["player_surname"] = box.player_surname.str.upper()
    return box


def load_box_before(data: Path, before: str, eurocup_file: str = "") -> pd.DataFrame:
    """Return everything available before a game: LBA and EuroCup rows dated strictly before `before` (YYYY-MM-DD)."""
    box = load_box(data, ALL_ROUNDS, END_OF_TIME, eurocup_file)
    return box[box.date < before].copy()


def players(box: pd.DataFrame, team: str = TEAM) -> pd.DataFrame:
    """Return the player rows of ``team`` in ``box`` that have court time."""
    return box[(box.row_type == "player") & (box.team == team) & (box.sec > 0)]


def pct(m: float, a: float) -> str:
    """Return ``m`` made of ``a`` attempts as a whole-number percentage string, or a dash when there are none."""
    return NO_VALUE if not a else f"{100 * m / a:.0f}"


# ── roster ──────────────────────────────────────────────────────────────────────
def roster_file(data: Path, raw_players: pd.DataFrame, team: str) -> pd.DataFrame:
    """Return data/roster.csv (player_id, surname, team, position, height_cm): hand-maintained, new players are appended blank."""
    path = data / "roster.csv"
    cols = ROSTER_COLS
    cur = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=cols)
    if "team" not in cur:                       # older file: those players are all the configured team's
        cur.insert(2, "team", TEAM)
    new = raw_players[~raw_players.player_id.isin(cur.player_id)][["player_id", "player_surname"]].drop_duplicates("player_id")
    if len(new):
        add = pd.DataFrame({"player_id": new.player_id.astype(int), "surname": new.player_surname.str.title(), "team": team,
                            "position": "", "height_cm": ""})
        cur = pd.concat([cur, add], ignore_index=True)
        print(f"{path}: added {len(add)} {team} player(s), fill in position (PG/SG/SF/PF/C) and height_cm")
    cur[cols].to_csv(path, index=False)
    return cur


def roster_bios(data: Path, team: str) -> dict[int, dict]:
    """Return player_id -> row of data/team_rosters.csv (the "giocatori" table of the team page on legabasket.it), empty if not collected."""
    path = data / "team_rosters.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    df = df[df.team == team]
    return {int(r["player_id"]): r for r in df.to_dict("records")}


def age_on(birth: str, asof: str) -> int | None:
    """Return the age in whole years on ``asof`` of someone born on ``birth`` (YYYY-MM-DD), or None if unknown."""
    if not isinstance(birth, str) or not birth:
        return None
    b, d = pd.Timestamp(birth), pd.Timestamp(asof)
    return int(d.year - b.year - ((d.month, d.day) < (b.month, b.day)))


def _num(v: object) -> str:
    return "" if v is None or pd.isna(v) else str(int(float(v)))


def ec_people(data: Path, team: str) -> dict[str, dict]:
    """Return the EuroCup club page of a team (data/eurocup/people.csv): last name -> {pos, height, number, photo}, for the players of teams that have no LBA data.
    Last names that two players share are left out (no way to tell them apart in the box score)."""
    people, results = data / "eurocup" / "people.csv", data / "eurocup" / "results.csv"
    if not people.exists() or not results.exists():
        return {}
    res = pd.read_csv(results)
    codes = {**dict(zip(res.home, res.home_code)), **dict(zip(res.away, res.away_code))}
    df = pd.read_csv(people)
    df = df[df.club == codes.get(team)]
    out: dict[str, dict] = {}
    for r in df.itertuples():
        clean = re.sub(NAME_SUFFIX_RE, "", unicodedata.normalize("NFKD", r.player).encode("ascii", "ignore").decode().lower()).split()
        stem = photo_name(r.player)
        info = {"pos": r.position if isinstance(r.position, str) else "", "height": "" if pd.isna(r.height_cm) or r.height_cm < MIN_PLAUSIBLE_HEIGHT_CM else str(int(r.height_cm)),
                "number": _num(getattr(r, "number", None)),
                "photo": stem if (data / "eurocup" / "photos" / f"{stem}.jpg").exists() else None}
        for k in range(1, len(clean)):                       # every tail of the name: "de laat", "laat"
            key = " ".join(clean[k:])
            out[key] = None if key in out else info
    return {k: v for k, v in out.items() if v}


def roster_table(box: pd.DataFrame, data: Path, team: str = TEAM, asof: str | None = None) -> list[dict]:
    """Return one row per player of `team` in `box`; bio columns (number, role, age on `asof`, nationality, weight, birth date) come from
    data/team_rosters.csv and fill position and height when data/roster.csv leaves them blank."""
    asof = asof or pd.Timestamp.today().strftime("%Y-%m-%d")
    bios = roster_bios(data, team)
    p = players(box, team)
    lba_ids = p[p.competition == COMP_LBA].drop_duplicates("player_surname").set_index("player_surname").player_id
    rost = roster_file(data, p[p.competition == COMP_LBA], team).set_index("player_id")
    ecp = ec_people(data, team) if lba_ids.empty else {}          # a team that is only in the EuroCup data: its club page gives position, height, photo
    photos = {int(f.stem) for f in (data / "photos").glob("*.jpg")}
    rows = []
    for sur, g in p.groupby("player_surname"):
        pid = int(lba_ids[sur]) if sur in lba_ids.index else None
        r = rost.loc[pid] if pid in rost.index else None
        bio = bios.get(pid, {})
        pos = "" if r is None or pd.isna(r.position) else str(r.position)
        pos = pos or (bio.get("role") if isinstance(bio.get("role"), str) else "")
        ht = "" if r is None or pd.isna(r.height_cm) or r.height_cm == "" else str(int(float(r.height_cm)))
        ht = ht or _num(bio.get("height_cm"))
        e = ecp.get(re.sub(NAME_SUFFIX_RE, "", sur.lower()).strip())
        if e:
            pos, ht = pos or e["pos"], ht or e["height"]
        num = _num(bio.get("number")) or (e["number"] if e else "")
        n = len(g); fga = g.fg2a.sum() + g.fg3a.sum()
        lba, ec = g[g.competition == COMP_LBA], g[g.competition == COMP_EC]
        rows.append({
            "player_id": pid if pid is not None or not (e and e["photo"]) else f"ec_{e['photo']}",
            "photo": pid in photos or bool(e and e["photo"]), "name": sur.title(), "pos": pos, "height": ht, "gp": n,
            "number": num, "age": age_on(bio.get("birth_date"), asof),
            "country": bio.get("country") if isinstance(bio.get("country"), str) else "", "weight": _num(bio.get("weight_kg")),
            "birth_date": bio.get("birth_date") if isinstance(bio.get("birth_date"), str) else "",
            "min": round(g.sec.sum() / 60 / n, 1), "pts": round(g.pts.sum() / n, 1), "reb": round((g.oreb + g.dreb).sum() / n, 1), "oreb": round(g.oreb.sum() / n, 1),
            "ast": round(g.ast.sum() / n, 1), "pir": round(g.val.sum() / n, 1),
            "fd": round(g.pf_drawn.sum() / n, 1), "pf": round(g.pf.sum() / n, 1),
            "fg2": f"{pct(g.fg2m.sum(), g.fg2a.sum())} ({g.fg2a.sum() / n:.1f})",
            "fg3": f"{pct(g.fg3m.sum(), g.fg3a.sum())} ({g.fg3a.sum() / n:.1f})",
            "ft": f"{pct(g.ftm.sum(), g.fta.sum())} ({g.fta.sum() / n:.1f})",
            "ppg_lba": round(lba.pts.mean(), 1) if len(lba) else None, "ppg_ec": round(ec.pts.mean(), 1) if len(ec) else None,
            "sec_total": int(g.sec.sum()),
        })
    played = {r["player_id"] for r in rows}
    for pid, bio in bios.items():       # on the roster but no game yet: listed with 0 GP
        if pid in played:
            continue
        rr = rost.loc[pid] if pid in rost.index else None
        pos = "" if rr is None or pd.isna(rr.position) else str(rr.position)
        rows.append({
            "player_id": pid, "photo": pid in photos, "name": str(bio["surname"]).title(),
            "pos": pos or (bio["role"] if isinstance(bio.get("role"), str) else ""), "height": _num(bio.get("height_cm")), "gp": 0,
            "number": _num(bio.get("number")), "age": age_on(bio.get("birth_date"), asof),
            "country": bio["country"] if isinstance(bio.get("country"), str) else "", "weight": _num(bio.get("weight_kg")),
            "birth_date": bio["birth_date"] if isinstance(bio.get("birth_date"), str) else "",
            **dict.fromkeys(("min", "pts", "reb", "oreb", "ast", "pir", "fd", "pf", "fg2", "fg3", "ft"), NO_VALUE),
            "ppg_lba": None, "ppg_ec": None, "sec_total": 0})
    rows.sort(key=lambda r: (POS_ORDER.get(r["pos"], 9), -r["sec_total"]))
    return rows


# ── starting fives of the last games ───────────────────────────────────────────
def fig_starting_fives(box: pd.DataFrame, team: str, out: Path, n: int = 5, top: int = 12, idx: int = 1) -> list[dict]:
    """Save 11_starting_fives.png and return the starters of each game. Grid players x last `n` games (LBA and EuroCup, date order): team colour = starter (S, minutes), grey = bench minutes, red = out of the game.
    Rows: the `top` players by minutes over all the games in `box`, plus anyone who started. Written to 11_starting_fives.png."""
    p = box[(box.team == team) & (box.row_type == "player")]
    tot = box[(box.team == team) & (box.row_type == "total")].sort_values(["date", "game_id"]).tail(n)
    if tot.empty:
        return []
    mins_total = p.groupby("player_surname").sec.sum().sort_values(ascending=False)
    rotation = list(mins_total.head(top).index)
    players = rotation + [x for x in p[p.starter == 1].player_surname.unique() if x not in rotation]
    fill, edge = team_color(team, idx)
    fig, ax = plt.subplots(figsize=(1.35 * len(tot) + 2.6, 0.42 * len(players) + 2.2))
    fives = []
    for j, g in enumerate(tot.itertuples()):
        row = p[p.game_id == g.game_id].drop_duplicates("player_surname").set_index("player_surname")
        fives.append({"date": g.date, "opponent": g.opponent, "starters": sorted(x.title() for x in row[row.starter == 1].index)})
        for i, name in enumerate(players):
            r = row.loc[name] if name in row.index else None
            if r is None or r.sec <= 0:
                color, text = OUT_COLOR, "OUT"
            elif r.starter == 1:
                color, text = fill, f"S {r.sec / 60:.0f}'"
            else:
                color, text = BENCH_COLOR, f"{r.sec / 60:.0f}'"
            ax.add_patch(plt.Rectangle((j, -i - 1), 0.94, 0.88, color=color))
            ax.text(j + 0.47, -i - 0.56, text, ha="center", va="center", fontsize=9, color="white" if text == "OUT" else TEXT,
                    fontweight="bold" if text == "OUT" else None)
    ax.set_xlim(-0.05, len(tot)); ax.set_ylim(-len(players) - 0.1, 0)
    ax.set_yticks([-i - 0.56 for i in range(len(players))], [x.title() for x in players], fontsize=9)
    opp_pts = box[(box.row_type == "total") & (box.team != team) & box.game_id.isin(tot.game_id)].groupby("game_id").pts.first()
    labels = [f"{g.date[5:]}\n{str(g.opponent).split()[0][:11]}\n{'LBA' if g.competition == COMP_LBA else 'EC'} {int(g.pts)}-{int(opp_pts.get(g.game_id, 0))}"
              for g in tot.itertuples()]
    ax.set_xticks([j + 0.47 for j in range(len(tot))], labels, fontsize=8)
    ax.xaxis.tick_top(); ax.tick_params(length=0); ax.spines[:].set_visible(False)
    fig.suptitle(f"{team}: starters (S), bench minutes and absences, last {len(tot)} games (LBA and EuroCup)", **SUP_KW)
    save_fig(fig, out / "11_starting_fives.png"); plt.close(fig)
    return fives


# ── turnovers ───────────────────────────────────────────────────────────────────
def turnover_table(box: pd.DataFrame, team: str = TEAM) -> list[dict]:
    """Return turnovers per player over the games in `box` (LBA + EuroCup rows of the team): total, per minute, and the game with the most.
    The two highest single-game totals of the whole roster are flagged (`top`)."""
    p = players(box, team).copy()
    if p.empty:
        return []
    p["label"] = [f"{'at ' if h == 0 else 'vs '}{o} ({d[8:]}/{d[5:7]})" if pd.notna(h) else f"vs {o} ({d[8:]}/{d[5:7]})"
                  for h, o, d in zip(p.get("home", pd.Series(index=p.index, dtype=float)), p.opponent, p.date)]
    p = p.sort_values("date", ascending=False)
    flagged = p.sort_values("tov", ascending=False, kind="stable").head(2)
    top = {(r.player_surname, r.game_id) for r in flagged.itertuples() if r.tov > 0}
    rows = []
    for sur, g in p.groupby("player_surname"):
        worst = g.sort_values("tov", ascending=False, kind="stable").iloc[0]
        mins = g.sec.sum() / 60
        rows.append({"name": sur.title(), "gp": len(g), "min": round(mins, 1), "tov": int(g.tov.sum()),
                     "tov_min": round(g.tov.sum() / mins, 3) if mins else None, "tov_pg": round(g.tov.sum() / len(g), 1),
                     "worst_n": int(worst.tov), "worst_game": worst.label, "top": (sur, worst.game_id) in top})
    rows.sort(key=lambda r: (-r["tov"], -r["min"]))
    return rows


# ── playing time ────────────────────────────────────────────────────────────────
def playing_time_flags(box: pd.DataFrame, game_id: str, game_date: str) -> list[dict]:
    """Return the players whose minutes in this game jumped versus their average in the games they played before it (LBA + EuroCup)."""
    p = players(box)
    cur = p[p.game_id == str(game_id)].set_index("player_surname")
    prev = p[(p.game_id != str(game_id)) & (p.date <= game_date)]
    prev = prev[~((prev.date == game_date) & (prev.competition == COMP_LBA))]
    if prev.empty:   # first game of the season: nothing to compare with
        return []
    avg = prev.groupby("player_surname").sec.agg(["mean", "size"])
    out = []
    for sur, r in cur.iterrows():
        if r.sec < MIN_PLAYED:
            continue
        if sur not in avg.index:
            out.append({"name": sur.title(), "now": r.sec / 60, "avg": None, "gp_before": 0, "diff": None, "pct": None})
            continue
        a, n = avg.loc[sur]
        if r.sec - a >= ABS_UP or r.sec >= (1 + REL_UP) * a:
            out.append({"name": sur.title(), "now": round(r.sec / 60, 1), "avg": round(a / 60, 1), "gp_before": int(n),
                        "diff": round((r.sec - a) / 60, 1), "pct": round(100 * (r.sec / a - 1))})
    return sorted(out, key=lambda x: -(x["diff"] or 99))


# ── assists ─────────────────────────────────────────────────────────────────────
def assist_pairs(pbp: pd.DataFrame, games: list[int], team: str = TEAM) -> pd.DataFrame:
    """Return one row per assisted basket of ``team`` in ``games``: game_id, passer, scorer, pts."""
    p = pbp[pbp.game_id.isin(games)]
    a = p[(p.event == EVENT_ASSIST) & (p.team == team)][["game_id", "player_surname", "linked_seq"]].dropna(subset=["linked_seq"])
    shots = p[p.event.str.contains(EVENT_MADE, na=False)][["game_id", "seq", "player_surname", "event"]]
    m = a.merge(shots, left_on=["game_id", "linked_seq"], right_on=["game_id", "seq"], suffixes=("_passer", "_scorer"))
    m["passer"] = m.player_surname_passer.str.title(); m["scorer"] = m.player_surname_scorer.str.title()
    m["pts"] = m.event.str[0].astype(int)
    return m[["game_id", "passer", "scorer", "pts"]]


def fig_assists(pairs: pd.DataFrame, box_ast: int, out: Path, team: str = TEAM, league: str = "LBA", name: str = "assists") -> list[dict]:
    """Save the assist matrix <name>.png and return the six most frequent passer-scorer pairs.

    Args:
        pairs: Output of ``assist_pairs``.
        box_ast: Box-score assists, to show how many are matched to a basket.
        out: Output folder.
        team: Team name for the title.
        league: Competition name for the title.
        name: File stem of the PNG.
    """
    matrix = pairs.pivot_table(index="passer", columns="scorer", values="pts", aggfunc="size", fill_value=0)
    allp = matrix.index.union(matrix.columns)
    matrix = matrix.reindex(index=allp, columns=allp, fill_value=0)
    involved = matrix.sum(axis=1) + matrix.sum(axis=0)
    keep = involved[involved >= MIN_ASSIST_LINKS].index
    matrix = matrix.loc[keep, keep]
    order = matrix.sum(axis=1).sort_values(ascending=False).index
    matrix = matrix.loc[order, order]
    n = len(matrix)
    fig, ax = plt.subplots(figsize=(max(7, 0.75 * n + 3), max(6, 0.65 * n + 2.5)))
    ax.imshow(matrix.values, cmap="YlOrBr", vmin=0)
    for (i, j), v in np.ndenumerate(matrix.values):
        if v:
            ax.text(j, i, v, ha="center", va="center", fontsize=10, color=TEXT)
    ax.set_xticks(range(n), [f"{c}\n({int(matrix[c].sum())})" for c in matrix.columns], fontsize=8.5, rotation=45, ha="left")
    ax.set_yticks(range(n), [f"{r} ({int(matrix.loc[r].sum())})" for r in matrix.index], fontsize=9)
    ax.xaxis.tick_top(); ax.xaxis.set_label_position("top")
    ax.set_xlabel("scorer (assisted baskets received)", labelpad=8); ax.set_ylabel("passer (assists given)")
    fig.suptitle(f"{team} assist matrix, {league} ({len(pairs)} assisted baskets, {100 * len(pairs) / box_ast:.0f}% of box-score assists)", **SUP_KW)
    save_fig(fig, out / f"{name}.png"); plt.close(fig)
    top = pairs.groupby(["passer", "scorer"]).size().sort_values(ascending=False).head(6)
    return [{"passer": a, "scorer": b, "n": int(n_)} for (a, b), n_ in top.items()]


# ── shot zones ──────────────────────────────────────────────────────────────────
def fig_zones(pbp: pd.DataFrame, games: list, game_id: int | None, out: Path, team: str = TEAM, league: str = "LBA",
              suffix: str = "") -> dict:
    """Save zones<suffix>.png and zone_share<suffix>.png; return the season and league shot share (%) per zone.

    ``game_id`` None skips the single-game panel and bars.
    """
    gold, gold_edge = team_color(team)
    s = shots_cm(pbp[pbp.game_id.isin(games)])
    ref = zone_stats(s[s.team != team])
    mine = s[s.team == team]
    this = mine[mine.game_id == game_id] if game_id is not None else mine.iloc[0:0]
    fig, axes = plt.subplots(1, 2 if game_id is not None else 1, figsize=(15, 8) if game_id is not None else (8.5, 8))
    axes = np.atleast_1d(axes)
    mesh = plot_zone_heatmap(axes[0], mine, f"Season to date: {int(mine.made.sum())}/{len(mine)} FG in {mine.game_id.nunique()} {league} games", ref=ref)
    if game_id is not None:
        plot_zone_heatmap(axes[1], this, f"This game: {int(this.made.sum())}/{len(this)} FG")
    cb = fig.colorbar(mesh, ax=axes, fraction=0.02, pad=0.02); cb.set_ticks([0, 25, 50, 75, 100]); cb.set_label("FG%", fontsize=8)
    fig.suptitle(f"{team} shooting by zone, {league} (small grey text: FG% of all other {league} teams in that zone)", **SUP_KW)
    save_fig(fig, out / f"zones{suffix}.png"); plt.close(fig)

    # where the shots come from vs the league
    labels = lba_style.ZONE_LABELS
    zs = list(labels)
    share = lambda d: d.zone.value_counts(normalize=True).reindex(zs).fillna(0) * 100
    sm, sl, sg = share(mine), share(s[s.team != team]), share(this)
    fig, ax = plt.subplots(figsize=(10, 4.8))
    x = np.arange(len(zs)); w = 0.27
    if game_id is not None:
        ax.bar(x - w, sm, w, color=gold, edgecolor=gold_edge, linewidth=0.6, label=f"{team}, season")
        ax.bar(x, sg, w, color=gold, alpha=0.45, edgecolor=gold_edge, linewidth=0.6, label=f"{team}, this game")
        ax.bar(x + w, sl, w, color=LEAGUE, label=f"other {league} teams")
    else:
        ax.bar(x - w / 2, sm, w, color=gold, edgecolor=gold_edge, linewidth=0.6, label=f"{team}, season")
        ax.bar(x + w / 2, sl, w, color=LEAGUE, label=f"other {league} teams")
    ax.set_xticks(x, [labels[z] for z in zs], rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("% of field-goal attempts"); ax.legend(fontsize=8)
    style_axes(ax, "y")
    ax.set_title("Shot distribution by zone: where the attempts come from", loc="left", **TITLE_KW)
    save_fig(fig, out / f"zone_share{suffix}.png"); plt.close(fig)
    return {"season": {z: round(float(v), 1) for z, v in sm.items()}, "league": {z: round(float(v), 1) for z, v in sl.items()}}


# ── TS% vs PIR ──────────────────────────────────────────────────────────────────
def ts_pir_table(box: pd.DataFrame, min_mpg: float) -> pd.DataFrame:
    """Return per-player GP, MPG, PIR and TS% for the rows in ``box``, keeping players with at least ``min_mpg``."""
    p = box[(box.row_type == "player") & (box.sec > 0)]
    g = p.groupby(["team", "player_surname"]).agg(GP=("game_id", "nunique"), sec=("sec", "sum"), pts=("pts", "sum"), val=("val", "sum"),
                                                  fga=("fg2a", "sum"), fg3a=("fg3a", "sum"), fta=("fta", "sum")).reset_index()
    g["fga"] = g.fga + g.fg3a
    g["MPG"] = g.sec / 60 / g.GP; g["PIR"] = g.val / g.GP
    g["TS"] = 100 * g.pts / (2 * (g.fga + FTA_POSSESSION_WEIGHT * g.fta)).replace(0, np.nan)
    g["Player"] = g.player_surname.str.title()
    return g[g.MPG >= min_mpg].dropna(subset=["TS"])


def fig_ts_pir(box: pd.DataFrame, comp: str, out: Path, min_mpg: float = 10, team: str = TEAM) -> dict:
    """PIR (x) vs TS% (y), bubble = minutes per game; one competition only. Other teams' players in grey."""
    gold, gold_edge = team_color(team)
    d = ts_pir_table(box[box.competition == comp], min_mpg)
    mine, other = d[d.team == team], d[d.team != team]
    name = {COMP_LBA: "LBA", COMP_EC: "EuroCup"}[comp]
    size = lambda mpg: mpg / MAX_MPG_FOR_BUBBLE * BUBBLE_SCALE + BUBBLE_MIN
    fig, ax = plt.subplots(figsize=(12, 7.5))
    ax.scatter(other.PIR, other.TS, s=size(other.MPG), c=LEAGUE, alpha=0.4, edgecolors="none", zorder=2,
               label=f"other {name} players")
    ax.scatter(mine.PIR, mine.TS, s=size(mine.MPG), c=gold, edgecolors=gold_edge, linewidths=0.8, zorder=3, label=team)
    for j, (_, r) in enumerate(mine.sort_values("PIR").iterrows()):
        ax.annotate(f"{r.Player} ({r.MPG:.0f}')", (r.PIR, r.TS), xytext=(6, 6 if j % 2 else -12), textcoords="offset points", fontsize=8.5, color=TEXT)
    best = d.sort_values("PIR", ascending=False).iloc[0]
    ax.scatter([best.PIR], [best.TS], s=size(best.MPG) * 2.2, facecolors="none", edgecolors=GREEN, linewidths=2.5, zorder=4,
               label=f"best PIR: {best.Player} ({best.team}, {best.PIR:.1f})")
    if best.team != team:
        ax.annotate(f"{best.Player} ({best.team})", (best.PIR, best.TS), xytext=(8, 8), textcoords="offset points", fontsize=9, color=GREEN, fontweight="bold")
    ax.axvline(d.PIR.median(), color=TEXT2, lw=0.7, ls="--"); ax.axhline(d.TS.median(), color=TEXT2, lw=0.7, ls="--")
    ax.set_xlabel("PIR per game"); ax.set_ylabel("TS%")
    games = int(mine.GP.max()) if len(mine) else 0
    ax.set_title(f"PIR vs true shooting, {name} games only ({team}: {games} game{'s' if games != 1 else ''}), "
                 f"dot size = minutes per game, min {min_mpg:.0f}'", **TITLE_KW)
    ax.legend(fontsize=9, loc="lower right"); style_axes(ax)
    fname = "ts_pir_lba.png" if comp == COMP_LBA else "ts_pir_eurocup.png"
    save_fig(fig, out / fname); plt.close(fig)
    return {"file": fname, "players": len(mine), "others": len(other), "games": games}


# ── team profile (LBA, to date) ─────────────────────────────────────────────────
def team_profile(box: pd.DataFrame, team: str, comps: tuple[str, ...] = (COMP_LBA,)) -> dict:
    """Return season-to-date team numbers (box = rows of load_box*, all teams): record, pace, ratings, four factors.
    comps: competitions to include, "LBA" and/or "EC" (EuroCup games are only in the data for some teams)."""
    tot = box[box.competition.isin(comps) & (box.row_type == "total")]
    mine = tot[tot.team == team].set_index("game_id")
    if mine.empty:
        return {}
    opp = tot[tot.opponent == team].set_index("game_id").reindex(mine.index)
    n = len(mine)
    poss = lambda t: t.fg2a + t.fg3a - t.oreb + t.tov + FTA_POSSESSION_WEIGHT * t.fta
    pm, po = poss(mine), poss(opp)
    fga, ofga = mine.fg2a + mine.fg3a, opp.fg2a + opp.fg3a
    wins = int((mine.pts > opp.pts).sum())
    minutes = np.where(mine.competition == COMP_EC, EC_GAME_MIN, mine.sec / TEAM_SEC_PER_MIN).sum()   # EuroCup totals carry 2400 s, not 5 x 2400
    r = lambda x, d=1: round(float(x), d)
    return {
        "Games": f"{n} ({(mine.competition == COMP_LBA).sum()} LBA + {(mine.competition == COMP_EC).sum()} EuroCup)" if (mine.competition == COMP_EC).any() and len(comps) > 1 else n,
        "Record": f"{wins}-{n - wins}",
        "Points per game": r(mine.pts.mean()), "Points allowed per game": r(opp.pts.mean()),
        "Offensive rating": r(100 * mine.pts.sum() / pm.sum()), "Defensive rating": r(100 * opp.pts.sum() / po.sum()),
        "Net rating": r(100 * mine.pts.sum() / pm.sum() - 100 * opp.pts.sum() / po.sum()),
        "Pace (possessions per 40')": r(BOX_MIN_PER_GAME * ((pm + po) / 2).sum() / minutes),
        "eFG%": r(100 * (mine.fg2m + 1.5 * mine.fg3m).sum() / fga.sum()),
        "TOV% (per 100 poss.)": r(100 * mine.tov.sum() / pm.sum()),
        "FT rate (FTA/FGA)": r(100 * mine.fta.sum() / fga.sum()),
        "3PA per game": r(mine.fg3a.mean()), "3P%": r(100 * mine.fg3m.sum() / mine.fg3a.sum()),
        "2P%": r(100 * mine.fg2m.sum() / mine.fg2a.sum()), "FT%": r(100 * mine.ftm.sum() / mine.fta.sum()),
        "Assists per game": r(mine.ast.mean()),
        "Offensive rebounds per game": r(mine.oreb.mean()), "Defensive rebounds per game": r(mine.dreb.mean()),
        "OREB%": r(100 * mine.oreb.sum() / (mine.oreb + opp.dreb).sum()),
        "DREB%": r(100 * mine.dreb.sum() / (mine.dreb + opp.oreb).sum()),
        "Opp. eFG%": r(100 * (opp.fg2m + 1.5 * opp.fg3m).sum() / ofga.sum()),
        "Opp. TOV% (forced)": r(100 * opp.tov.sum() / po.sum()),
    }


# ── form across competitions ────────────────────────────────────────────────────
def fig_form(before: pd.DataFrame, out: Path, team: str = TEAM) -> None:
    """Points scored and conceded in every game played so far, in date order; circles = league, squares = EuroCup."""
    gold, gold_edge = team_color(team)
    n = len(before)
    x = np.arange(1, n + 1)
    fig, ax = plt.subplots(figsize=(max(9.0, 1.05 * n + 3), 4.8))
    ax.plot(x, before.pf, color=gold_edge, lw=2.2, zorder=2)
    ax.plot(x, before.pa, color=BLUE, lw=2.2, zorder=2)
    for i, (_, r) in enumerate(before.iterrows(), start=1):
        mk = "o" if r.competition == COMP_LBA else "s"
        ax.scatter(i, r.pf, marker=mk, s=95, color=gold, edgecolor=gold_edge, zorder=3)
        ax.scatter(i, r.pa, marker=mk, s=75, color=BLUE, zorder=3)
        ax.text(i, r.pf + 3, int(r.pf), ha="center", fontsize=9, color=TEXT)
        ax.text(i, r.pa - 7, int(r.pa), ha="center", fontsize=9, color=BLUE)
    ax.set_xticks(x, [f"{o[:15]}\n{d[8:]}/{d[5:7]}" for o, d in zip(before.opponent, before.date)], fontsize=8.5)
    ax.set_ylabel("points")
    ax.legend(handles=[Line2D([], [], color=gold_edge, marker="o", mfc=gold, label=f"{team} scored"),
                       Line2D([], [], color=BLUE, marker="o", label=f"{team} conceded"),
                       Line2D([], [], color=TEXT2, marker="o", ls="", label="league (LBA)"),
                       Line2D([], [], color=TEXT2, marker="s", ls="", label="EuroCup")], loc="upper left", ncol=4, fontsize=8)
    style_axes(ax, "y")
    ax.set_title("Every game so far, both competitions: points scored and conceded", loc="left", **TITLE_KW)
    save_fig(fig, out / "season.png"); plt.close(fig)
