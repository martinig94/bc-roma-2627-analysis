"""Synergy defensive leaderboard: from a Synergy export to the Leaderboard page of the site.

    python notebooks/synergy_leaderboard.py ingest SOURCE --competition eurocup [--date 2026-10-22]

SOURCE is a folder of CSVs extracted from the Synergy web app in the browser (one per play type, see
.claude/skills/synergy-leaderboard/SKILL.md) or an .xls export (one tab per play type: PPP, TRANSITION, ISO, ...). It writes
data/synergy/leaderboard/<competition>/<play type>.csv + meta.json (the date shown on the page). Run it again with the next
export after each EuroCup / LBA game, or write the same CSVs from a fetcher. ``build_site.py`` calls ``page_markdown()``.
Defensive tables: PPP allowed, rank 1 = lowest.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "synergy" / "leaderboard"
# export tab -> (csv name, title on the page)
PLAY_TYPES = [("PPP", "ppp", "Overall defence"), ("TRANSITION", "transition", "Transition"), ("ISO", "iso", "Isolation"),
              ("POST-UP", "post_up", "Post-up"), ("PnR BALL HANDLER", "pnr_ball_handler", "P&R ball handler"),
              ("PnR ROLL MAN", "pnr_roll_man", "P&R roll man"), ("SPOT UP", "spot_up", "Spot up"),
              ("OFF SCREEN", "off_screen", "Off screen"), ("HAND OFF", "hand_off", "Hand off"), ("CUT", "cut", "Cut"),
              ("OFF REB", "off_reb", "Off reb (putbacks)")]
COMPETITIONS = {"eurocup": "EuroCup", "lba": "LBA Serie A"}
# (column in the CSV, header on the page, format)
SHOWN = [("Rank", "Rk", "{:.0f}"), ("Team", "Team", None), ("GP", "GP", "{:.0f}"), ("Poss", "Poss", "{:.1f}"), ("%Time", "%Time", "pct0"),
         ("PPP", "PPP", "{:.3f}"), ("FG%", "FG%", "pct"), ("eFG%", "eFG%", "pct"), ("TO%", "TO%", "pct"),
         ("Score%", "Score%", "pct"), ("2 FG%", "2P%", "pct"), ("3 FG%", "3P%", "pct")]


# Synergy web-app column names (snake case, as in data/synergy/<scouting folder>/*.csv) -> names of the export tables
ALIASES = {"rank": "Rank", "team": "Team", "gp": "GP", "poss": "Poss", "pct_time": "%Time", "time": "%Time", "pts": "Pts", "ppp": "PPP",
           "fga": "FG Att", "fgm": "FG Made", "fg_pct": "FG%", "efg_pct": "eFG%", "to_pct": "TO%", "ft_pct": "%FT", "score_pct": "Score%",
           "fg2_pct": "2 FG%", "fg3_pct": "3 FG%", "fg3a_per_fga": "3PA/FGA"}
REQUIRED = ["Team", "GP", "Poss", "PPP"]


def _canon(col: str) -> str:
    key = re.sub(r"[^a-z0-9%]+", "_", col.strip().lower()).strip("_")
    return ALIASES.get(key, col.strip())


def _number(v):
    """'44.7%' -> 0.447, '+0.10' -> 0.1, '1,234' -> 1234.0; anything else unchanged."""
    if isinstance(v, str):
        t = v.strip().replace(",", "")
        try:
            return float(t[:-1]) / 100 if t.endswith("%") else float(t)
        except ValueError:
            return v.strip()
    return v


def _clean(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Canonical columns, numbers as numbers, ranked by PPP when the table has no Rank column."""
    df = df.rename(columns=_canon).dropna(how="all").dropna(axis=1, how="all")
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise SystemExit(f"{name}: missing columns {missing} (found {list(df.columns)})")
    df = df[df["Team"].notna()].apply(lambda c: c.map(_number))
    if "Rank" not in df.columns:
        df = df.sort_values("PPP")
        df.insert(0, "Rank", df["PPP"].rank(method="min"))
    return df


def _read(source: Path, tab: str, name: str) -> pd.DataFrame | None:
    """One play-type table from an .xls export (tab 'ISO - Tabella 1') or from a folder of CSVs (iso.csv, ISO.csv or 'ISO - Tabella 1.csv')."""
    if source.is_dir():
        for stem in (name, tab, f"{tab} - Tabella 1"):
            f = next((x for x in source.glob("*.csv") if x.stem.lower() == stem.lower()), None)
            if f:
                return pd.read_csv(f)
        return None
    return pd.read_excel(source, sheet_name=f"{tab} - Tabella 1", header=1)


def ingest(source: Path, competition: str, day: str | None) -> None:
    """A Synergy pull (folder of CSVs written from the browser, or an .xls export) -> data/synergy/leaderboard/<competition>/*.csv + meta.json."""
    out = DIR / competition
    out.mkdir(parents=True, exist_ok=True)
    done = []
    for tab, name, title in PLAY_TYPES:
        df = _read(source, tab, name)
        if df is None:
            print(f"  no table for {title}: left as it was")
            continue
        _clean(df, title).to_csv(out / f"{name}.csv", index=False)
        done.append(name)
    if "ppp" not in done:
        raise SystemExit("the overall (PPP) table is required")
    if day is None:       # ..._DDMMYY.xls
        m = re.search(r"(\d{2})(\d{2})(\d{2})(?=\D*$)", source.stem)
        day = date(2000 + int(m[3]), int(m[2]), int(m[1])).isoformat() if m else date.today().isoformat()
    (out / "meta.json").write_text(json.dumps({"date": day, "source": source.name}, indent=2) + "\n", encoding="utf-8")
    print(f"{competition}: {len(done)} tables, data of {day}")


def _cell(v, fmt: str | None) -> str:
    if pd.isna(v):
        return ""
    if fmt is None:
        return re.sub(r"\s*\(ex [^)]*\)", "", str(v))      # "Maxima Roma (ex Germani Brescia)" -> "Maxima Roma"
    return f"{v * 100:.0f}%" if fmt == "pct0" else f"{v * 100:.1f}%" if fmt == "pct" else fmt.format(v)


def _table(df: pd.DataFrame) -> str:
    cols = [(c, h, f) for c, h, f in SHOWN if c in df.columns]
    lines = ["| " + " | ".join(h for _, h, _ in cols) + " |", "|" + "|".join("---" if c == "Team" else "---:" for c, _, _ in cols) + "|"]
    for _, r in df.iterrows():
        roma = "roma" in str(r["Team"]).lower()
        cells = [_cell(r[c], f) for c, _, f in cols]
        lines.append("| " + " | ".join(f"=={c}==" if roma and c else c for c in cells) + " |")
    return "\n".join(lines)


def page_markdown() -> str | None:
    """The markdown of the Leaderboard page (None when there is no Synergy data yet): one section per competition and play type."""
    parts = []
    for key, label in COMPETITIONS.items():
        meta_file = DIR / key / "meta.json"
        if not meta_file.exists():
            continue
        day = date.fromisoformat(json.loads(meta_file.read_text(encoding="utf-8"))["date"])
        parts.append(f"## {label}\n\n*Synergy data up to {day.strftime('%d %B %Y')}. Points per possession (PPP) allowed by each team's defence; "
                     f"rank 1 = lowest PPP allowed. Small samples: check Poss. Both Roma teams are highlighted.*\n")
        for _, name, title in PLAY_TYPES:
            f = DIR / key / f"{name}.csv"
            if f.exists():
                parts.append(f"### {title}\n\n{_table(pd.read_csv(f))}\n")
    if not parts:
        return None
    return "# Defensive leaderboard\n\nSynergy defensive ratings of every team, overall and by play type, updated after each EuroCup and LBA game.\n\n" + "\n".join(parts)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ingest")
    p.add_argument("source", type=Path, help="folder of CSVs or an .xls export")
    p.add_argument("--competition", choices=COMPETITIONS, required=True)
    p.add_argument("--date", help="ISO date of the data (default: from the file name, DDMMYY)")
    a = ap.parse_args()
    ingest(a.source, a.competition, a.date)
