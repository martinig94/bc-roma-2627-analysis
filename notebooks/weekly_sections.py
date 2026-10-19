"""Extra sections of the weekly report (called by weekly_report.py): roster, playing-time flags, assist matrix,
shot zones, TS% vs PIR (LBA only, EuroCup only).

Every function takes the data as of the round being reported (LBA games up to that round; EuroCup games up to that date).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import lba_style
import weekly_config
from lba_style import GREEN, LEAGUE, SUP_KW, TEXT, TEXT2, TITLE_KW, save_fig, shots_cm, style_axes, team_color
from matchup_report import parse_eurocup, plot_zone_heatmap, zone_stats

ROOT = Path(__file__).resolve().parent.parent
TEAM = weekly_config.load()["team"]
POS_ORDER = {"PG": 0, "SG": 1, "G": 1, "SF": 2, "F": 2, "PF": 3, "C": 4}

# playing-time flag: at least MIN_PLAYED seconds in the game and either +ABS_UP seconds or +REL_UP above the average before
MIN_PLAYED, ABS_UP, REL_UP = 8 * 60, 7 * 60, 0.30


# ── data ────────────────────────────────────────────────────────────────────────
def load_box(data: Path, upto_round: int, upto_date: str, eurocup_file: str = "") -> pd.DataFrame:
    """LBA player/total rows (all teams, rounds <= upto_round) + EuroCup rows (all teams in the file, date <= upto_date)."""
    lba = pd.read_csv(data / "box_scores.csv")
    lba = lba[lba["round"] <= upto_round].copy()
    lba["competition"] = "LBA"; lba["date"] = lba.match_datetime.str[:10]; lba["game_id"] = lba.game_id.astype(str)
    ec_path = ROOT / eurocup_file if eurocup_file else None
    frames = [lba]
    if ec_path and ec_path.exists():
        ec, _ = parse_eurocup(ec_path)
        frames.append(ec[ec.date <= upto_date])
    box = pd.concat(frames, ignore_index=True)
    box["player_surname"] = box.player_surname.str.upper()
    return box


def players(box: pd.DataFrame, team: str = TEAM) -> pd.DataFrame:
    return box[(box.row_type == "player") & (box.team == team) & (box.sec > 0)]


def pct(m, a) -> str:
    return "–" if not a else f"{100 * m / a:.0f}"


# ── roster ──────────────────────────────────────────────────────────────────────
def roster_file(data: Path, raw_players: pd.DataFrame) -> pd.DataFrame:
    """data/roster.csv (player_id, surname, position, height_cm): hand-maintained, new players are appended blank."""
    path = data / "roster.csv"
    cur = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=["player_id", "surname", "position", "height_cm"])
    new = raw_players[~raw_players.player_id.isin(cur.player_id)][["player_id", "player_surname"]].drop_duplicates("player_id")
    if len(new):
        add = pd.DataFrame({"player_id": new.player_id.astype(int), "surname": new.player_surname.str.title(), "position": "", "height_cm": ""})
        cur = pd.concat([cur, add], ignore_index=True)
        cur.to_csv(path, index=False)
        print(f"{path}: added {len(add)} player(s), fill in position (PG/SG/SF/PF/C) and height_cm")
    return cur


def roster_table(box: pd.DataFrame, data: Path) -> list[dict]:
    p = players(box)
    lba_ids = p[p.competition == "LBA"].drop_duplicates("player_surname").set_index("player_surname").player_id
    rost = roster_file(data, p[p.competition == "LBA"]).set_index("player_id")
    photos = {int(f.stem) for f in (data / "photos").glob("*.jpg")}
    rows = []
    for sur, g in p.groupby("player_surname"):
        pid = int(lba_ids[sur]) if sur in lba_ids.index else None
        r = rost.loc[pid] if pid in rost.index else None
        pos = "" if r is None or pd.isna(r.position) else str(r.position)
        ht = "" if r is None or pd.isna(r.height_cm) or r.height_cm == "" else str(int(float(r.height_cm)))
        n = len(g); fga = g.fg2a.sum() + g.fg3a.sum()
        lba, ec = g[g.competition == "LBA"], g[g.competition == "EC"]
        rows.append({
            "player_id": pid, "photo": pid in photos, "name": sur.title(), "pos": pos, "height": ht, "gp": n,
            "min": round(g.sec.sum() / 60 / n, 1), "pts": round(g.pts.sum() / n, 1), "reb": round((g.oreb + g.dreb).sum() / n, 1),
            "ast": round(g.ast.sum() / n, 1), "pir": round(g.val.sum() / n, 1),
            "fg": f"{pct(g.fg2m.sum() + g.fg3m.sum(), fga)} ({fga / n:.1f})",
            "fg3": f"{pct(g.fg3m.sum(), g.fg3a.sum())} ({g.fg3a.sum() / n:.1f})",
            "ft": f"{pct(g.ftm.sum(), g.fta.sum())} ({g.fta.sum() / n:.1f})",
            "ppg_lba": round(lba.pts.mean(), 1) if len(lba) else None, "ppg_ec": round(ec.pts.mean(), 1) if len(ec) else None,
            "sec_total": int(g.sec.sum()),
        })
    rows.sort(key=lambda r: (POS_ORDER.get(r["pos"], 9), -r["sec_total"]))
    return rows


# ── playing time ────────────────────────────────────────────────────────────────
def playing_time_flags(box: pd.DataFrame, game_id: str, game_date: str) -> list[dict]:
    """Players whose minutes in this game jumped versus their average in the games they played before it (LBA + EuroCup)."""
    p = players(box)
    cur = p[p.game_id == str(game_id)].set_index("player_surname")
    prev = p[(p.game_id != str(game_id)) & (p.date <= game_date)]
    prev = prev[~((prev.date == game_date) & (prev.competition == "LBA"))]
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
    p = pbp[pbp.game_id.isin(games)]
    a = p[(p.event == "Assist") & (p.team == team)][["game_id", "player_surname", "linked_seq"]].dropna(subset=["linked_seq"])
    shots = p[p.event.str.contains("punti segnato", na=False)][["game_id", "seq", "player_surname", "event"]]
    m = a.merge(shots, left_on=["game_id", "linked_seq"], right_on=["game_id", "seq"], suffixes=("_passer", "_scorer"))
    m["passer"] = m.player_surname_passer.str.title(); m["scorer"] = m.player_surname_scorer.str.title()
    m["pts"] = m.event.str[0].astype(int)
    return m[["game_id", "passer", "scorer", "pts"]]


def fig_assists(pairs: pd.DataFrame, box_ast: int, out: Path, team: str = TEAM) -> list[dict]:
    matrix = pairs.pivot_table(index="passer", columns="scorer", values="pts", aggfunc="size", fill_value=0)
    allp = matrix.index.union(matrix.columns)
    matrix = matrix.reindex(index=allp, columns=allp, fill_value=0)
    involved = matrix.sum(axis=1) + matrix.sum(axis=0)
    keep = involved[involved >= 4].index
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
    fig.suptitle(f"{team} assist matrix, LBA ({len(pairs)} assisted baskets, {100 * len(pairs) / box_ast:.0f}% of box-score assists)", **SUP_KW)
    save_fig(fig, out / "assists.png"); plt.close(fig)
    top = pairs.groupby(["passer", "scorer"]).size().sort_values(ascending=False).head(6)
    return [{"passer": a, "scorer": b, "n": int(n_)} for (a, b), n_ in top.items()]


# ── shot zones ──────────────────────────────────────────────────────────────────
def fig_zones(pbp: pd.DataFrame, games: list[int], game_id: int, out: Path, team: str = TEAM) -> dict:
    GOLD, GOLD_EDGE = team_color(team)
    s = shots_cm(pbp[pbp.game_id.isin(games)])
    ref = zone_stats(s[s.team != team])
    mine = s[s.team == team]
    this = mine[mine.game_id == game_id]
    fig, axes = plt.subplots(1, 2, figsize=(15, 8))
    mesh = plot_zone_heatmap(axes[0], mine, f"Season to date: {int(mine.made.sum())}/{len(mine)} FG in {mine.game_id.nunique()} LBA games", ref=ref)
    plot_zone_heatmap(axes[1], this, f"This game: {int(this.made.sum())}/{len(this)} FG")
    cb = fig.colorbar(mesh, ax=axes, fraction=0.02, pad=0.02); cb.set_ticks([0, 25, 50, 75, 100]); cb.set_label("FG%", fontsize=8)
    fig.suptitle(f"{team} shooting by zone, LBA (small grey text: FG% of all other LBA teams in that zone)", **SUP_KW)
    save_fig(fig, out / "zones.png"); plt.close(fig)

    # where the shots come from vs the league
    labels = lba_style.ZONE_LABELS
    zs = list(labels)
    share = lambda d: d.zone.value_counts(normalize=True).reindex(zs).fillna(0) * 100
    sm, sl, sg = share(mine), share(s[s.team != team]), share(this)
    fig, ax = plt.subplots(figsize=(10, 4.8))
    x = np.arange(len(zs)); w = 0.27
    ax.bar(x - w, sm, w, color=GOLD, edgecolor=GOLD_EDGE, linewidth=0.6, label=f"{team}, season")
    ax.bar(x, sg, w, color=GOLD, alpha=0.45, edgecolor=GOLD_EDGE, linewidth=0.6, label=f"{team}, this game")
    ax.bar(x + w, sl, w, color=LEAGUE, label="other LBA teams")
    ax.set_xticks(x, [labels[z] for z in zs], rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("% of field-goal attempts"); ax.legend(fontsize=8)
    style_axes(ax, "y")
    ax.set_title("Shot distribution by zone: where the attempts come from", loc="left", **TITLE_KW)
    save_fig(fig, out / "zone_share.png"); plt.close(fig)
    return {"season": {z: round(float(v), 1) for z, v in sm.items()}, "league": {z: round(float(v), 1) for z, v in sl.items()}}


# ── TS% vs PIR ──────────────────────────────────────────────────────────────────
def ts_pir_table(box: pd.DataFrame, min_mpg: float) -> pd.DataFrame:
    p = box[(box.row_type == "player") & (box.sec > 0)]
    g = p.groupby(["team", "player_surname"]).agg(GP=("game_id", "nunique"), sec=("sec", "sum"), pts=("pts", "sum"), val=("val", "sum"),
                                                  fga=("fg2a", "sum"), fg3a=("fg3a", "sum"), fta=("fta", "sum")).reset_index()
    g["fga"] = g.fga + g.fg3a
    g["MPG"] = g.sec / 60 / g.GP; g["PIR"] = g.val / g.GP
    g["TS"] = 100 * g.pts / (2 * (g.fga + 0.44 * g.fta)).replace(0, np.nan)
    g["Player"] = g.player_surname.str.title()
    return g[g.MPG >= min_mpg].dropna(subset=["TS"])


def fig_ts_pir(box: pd.DataFrame, comp: str, out: Path, min_mpg: float = 10, team: str = TEAM) -> dict:
    """PIR (x) vs TS% (y), bubble = minutes per game; one competition only. Other teams' players in grey."""
    GOLD, GOLD_EDGE = team_color(team)
    d = ts_pir_table(box[box.competition == comp], min_mpg)
    mine, other = d[d.team == team], d[d.team != team]
    name = {"LBA": "LBA", "EC": "EuroCup"}[comp]
    size = lambda mpg: mpg / 36 * 420 + 40
    fig, ax = plt.subplots(figsize=(12, 7.5))
    ax.scatter(other.PIR, other.TS, s=size(other.MPG), c=LEAGUE, alpha=0.4, edgecolors="none", zorder=2,
               label=f"other {name} players")
    ax.scatter(mine.PIR, mine.TS, s=size(mine.MPG), c=GOLD, edgecolors=GOLD_EDGE, linewidths=0.8, zorder=3, label=team)
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
    fname = "ts_pir_lba.png" if comp == "LBA" else "ts_pir_eurocup.png"
    save_fig(fig, out / fname); plt.close(fig)
    return {"file": fname, "players": len(mine), "others": len(other), "games": games}
