"""Leaderboard page of the site: Synergy team leaderboards (offense and defense, overall and by play type).

Data: the latest folder ``data/synergy/leaderboards_<YYYY-MM-DD>/`` with ``leaderboard_<eurocup|seriea>_<offense|defense>.csv``
(long format, one row per team and play type, written by ``synergy/leaderboards_pull.js`` in the browser; columns in the README of the
folder). ``build_site.py`` calls ``page_markdown()``; the date of the folder is the date of the data.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SYNERGY = ROOT / "data" / "synergy"
NAMES = SYNERGY / "team_names.csv"        # competition, synergy_name, standings_name: Synergy name -> name in games.csv / eurocup results.csv
COMPETITIONS = {"seriea": "LBA Serie A", "eurocup": "EuroCup"}      # order of the sections: LBA first, offence before defence
SIDES = {"offense": "Offence", "defense": "Defence"}
TEAM = "BCR"                                       # Synergy abbreviation of the team the site is about (BC Roma)
PLAY_TYPES = [("All", "Overall"), ("Transition", "Transition"), ("Isolation", "Isolation"), ("Post-Up", "Post-up"),
              ("P&R Ball Handler", "P&R ball handler"), ("P&R Roll Man", "P&R roll man"), ("Spot Up", "Spot up"),
              ("Off Screen", "Off screen"), ("Handoffs", "Hand off"), ("Cut", "Cut"),
              ("Offensive Rebounds (Put Backs)", "Off reb (putbacks)")]       # Miscellaneous Plays is not on the app's leaderboard page
# (column, header on the page, format); percentages are already 0-100
SHOWN = [("rank", "Rk", "{:.0f}"), ("name", "Team", None), ("pos", "Pos", None), ("wl", "W-L", None), ("poss", "Poss/g", "{:.1f}"), ("pct_time", "%Time", "{:.0f}%"),
         ("ppp", "PPP", "{:.3f}"), ("fg_pct", "FG%", "{:.1f}%"), ("efg_pct", "eFG%", "{:.1f}%"), ("to_pct", "TO%", "{:.1f}%"),
         ("score_pct", "Score%", "{:.1f}%"), ("fg2_pct", "2P%", "{:.1f}%"), ("fg3_pct", "3P%", "{:.1f}%")]


def _plain(name: str) -> str:
    return re.sub(r"\s*\(ex [^)]*\)", "", str(name)).strip()


def standings_lookup(comp: str) -> dict[str, dict]:
    """Position in the league table (LBA) or in the group table (EuroCup), as of the last finished game, by the name used in the results:
    {name: {"pos": "2" or "2=" (level on points), "wl": "3-1"}}. Empty when the results are not there."""
    import eurocup
    import standings
    try:
        if comp == "seriea":
            tables = [standings.standings(pd.read_csv(ROOT / "data" / "games.csv"))]
        else:
            res = eurocup.load_results(ROOT / "data")
            tables, seen = [], set()
            for team in sorted(set(res.home) | set(res.away)):
                if team not in seen:
                    seen |= eurocup.group_teams(res, team)
                    tables.append(standings.standings(eurocup.games_frame(res, team)))
    except (FileNotFoundError, AttributeError, KeyError):
        return {}
    return {t: {"pos": f"{r.pos}{'=' if r.tied else ''}", "wl": f"{r.w}-{r.l}"} for tb in tables for t, r in tb.iterrows()}


def with_standings(df: pd.DataFrame, comp: str) -> pd.DataFrame:
    """Add the columns ``pos`` and ``wl`` (league standing) to a leaderboard table, matching the Synergy team name to the results name
    through data/synergy/team_names.csv, else by the closest spelling."""
    import difflib
    lookup = standings_lookup(comp)
    mapped = {}
    if NAMES.exists():
        m = pd.read_csv(NAMES)
        mapped = dict(zip(m[m.competition == comp].synergy_name, m[m.competition == comp].standings_name))
    low = {n.lower(): n for n in lookup}

    def find(name: str):
        n = _plain(name)
        if n in mapped:
            return lookup.get(mapped[n])
        hit = difflib.get_close_matches(n.lower(), list(low), n=1, cutoff=0.75)
        return lookup[low[hit[0]]] if hit else None
    found = df["name"].map(find)
    df = df.copy()
    df["pos"] = found.map(lambda x: x["pos"] if x else "")
    df["wl"] = found.map(lambda x: x["wl"] if x else "")
    return df


def latest_folder() -> Path | None:
    """The newest data/synergy/leaderboards_<date> folder."""
    folders = sorted(p for p in SYNERGY.glob("leaderboards_*") if p.is_dir() and re.fullmatch(r"leaderboards_\d{4}-\d{2}-\d{2}", p.name))
    return folders[-1] if folders else None


def _cell(v, fmt: str | None) -> str:
    if pd.isna(v):
        return "–" if fmt == "{:.0f}" else ""
    if fmt is None:
        return re.sub(r"\s*\(ex [^)]*\)", "", str(v))      # "Maxima Roma (ex Germani Brescia)" -> "Maxima Roma"
    return fmt.format(v)


def _table(df: pd.DataFrame) -> str:
    """Ranked teams in rank order, then the teams the app does not rank (fewer than 10 possessions), most possessions first."""
    df = pd.concat([df[df["rank"].notna()].sort_values("rank", kind="stable"), df[df["rank"].isna()].sort_values("poss_total", ascending=False)])
    lines = ["| " + " | ".join(h for _, h, _ in SHOWN) + " |", "|" + "|".join("---" if c == "name" else "---:" for c, _, _ in SHOWN) + "|"]
    for _, r in df.iterrows():
        roma = r["team"] == TEAM            # only BC Roma is in bold
        cells = [_cell(r[c], f) for c, _, f in SHOWN]
        lines.append("| " + " | ".join(f"**{c}**" if roma and c else c for c in cells) + " |")
    return "\n".join(lines)


def page_markdown() -> str | None:
    """The markdown of the Leaderboard page (None when there is no Synergy data yet): a section per competition and side, a table per play type."""
    folder = latest_folder()
    if folder is None:
        return None
    day = date.fromisoformat(folder.name.removeprefix("leaderboards_"))
    parts = []
    for side, side_label in SIDES.items():
        for comp, comp_label in COMPETITIONS.items():
            f = folder / f"leaderboard_{comp}_{side}.csv"
            if not f.exists():
                continue
            df = with_standings(pd.read_csv(f), comp)
            order = "lowest PPP allowed" if side == "defense" else "highest PPP"
            parts.append(f"## {comp_label} · {side_label}\n\n*Synergy data up to {day.strftime('%d %B %Y')}, competition games only. Rank 1 = {order}; teams with "
                         f"fewer than 10 possessions of a play type are not ranked (– at the end). Counts per game. Pos = position in the league table (LBA) or in the group table (EuroCup) and W-L = record, as of the last game; = level on points (order inside the tie is provisional). Small samples: check Poss. BC Roma is in bold.*\n")
            for play, title in PLAY_TYPES:
                t = df[df["play_type"] == play]
                if len(t):
                    parts.append(f"### {title}\n\n{_table(t)}\n")
    if not parts:
        return None
    return "# Leaderboard\n\nSynergy team leaderboards, defence and offence, overall and by play type, updated after each EuroCup and LBA game.\n\n" + "\n".join(parts)
