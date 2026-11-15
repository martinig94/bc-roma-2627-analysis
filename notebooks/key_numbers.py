"""Key numbers of one opponent, from Synergy only: the "Key numbers" tab of the opponent analysis.

    python notebooks/key_numbers.py data/synergy/key_numbers_<opponent>_<game date>

Reads the folder written from `synergy/key_numbers_pull.js` (teams.csv, zones.csv, players.csv, defenders.csv, opp_shots.csv,
ref_def_shots.csv, box.csv, meta.json) and its config.json, and writes weekly/games/<game date>/key_numbers.md: one page of numbers
with ranks within the competition, built like the SkillCorner game-preparation page but limited to what Synergy logs
(no box-outs, blow-bys, closeouts or pick-and-roll coverages). The file is generated: running the script again overwrites it.
Based solely on the data: no comments on plays.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import date
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GAMES = ROOT / "weekly" / "games"
MIN_DEF_POSS = 5          # defender numbers need this many possessions of the play type ending on him
MIN_ZONE_FGA = 5          # zone FG% needs this many attempts
ZONE_DIFF = 3.0           # zone colour: FG% this many points above / below the competition average
RIM_FT = 60               # "at the rim" = 2-point attempts within 6 ft (Synergy shotDistance is in tenths of a foot)
PLAY = {"pnrbh": "Pick and roll, ball handler", "roll": "Pick and roll, roll man", "iso": "Isolation", "post": "Post-up",
        "spot": "Spot-up", "offscreen": "Off screen", "handoff": "Handoff", "cut": "Cut", "trans": "Transition", "putback": "Putback"}
GOLD = "#F2C300"
# label position of each Synergy zone on the drawn court (basket at the top; offense's right = right of the picture)
POS = {"Z11-01-2pt": (250, 112), "Z11-07-2pt": (390, 70), "Z11-11-2pt": (110, 70), "Z11-08-2pt": (372, 168), "Z11-10-2pt": (128, 168),
       "Z11-09-2pt": (250, 238), "Z11-12-3pt": (477, 52), "Z11-16-3pt": (23, 52), "Z11-13-3pt": (436, 262), "Z11-15-3pt": (64, 262),
       "Z11-14-3pt": (250, 322)}


# ── numbers ───────────────────────────────────────────────────────────────────
def div(a, b, k=1.0):
    if np.isscalar(a) and np.isscalar(b):
        return k * float(a) / float(b) if b else float("nan")
    return np.where(np.asarray(b, dtype=float) > 0, k * np.asarray(a, dtype=float) / np.where(np.asarray(b, dtype=float) > 0, b, 1), np.nan)


def team_metrics(t: pd.DataFrame) -> pd.DataFrame:
    t = t.fillna(0).copy()
    m = pd.DataFrame({"team_id": t.team_id, "name": t.name, "side": t.side, "gp": t.gp})
    m["ppp100"] = div(t.pointMade, t.possessions, 100)
    m["poss_pg"] = div(t.possessions, t.gp)
    m["to_pct"] = div(t.turnover, t.possessions, 100)
    m["three_pct"] = div(t.three_m, t.three_a, 100)
    m["rim_pct"] = div(t.rim_m, t.rim_a, 100)
    m["cs3_pct"] = div(t.cs3_m, t.cs3_a, 100)
    m["open_pct"] = div(t.jump_open, t.jump_tag, 100)
    m["rim_share"] = div(t.rim_a, t.shots, 100)
    m["three_share"] = div(t.three_a, t.shots, 100)
    m["mid_share"] = div(t.mid_a, t.shots, 100)
    m["oreb_pct"] = div(t.offreb, t.offreb + t.defreb, 100)
    m["ft_rate"] = div(t.ftAttempt, t.shotAttempt, 100)
    m["ast_pct"] = div(t.assist, t.shotMade, 100)
    m["paint_pts_pg"] = div(2 * (t.rim_m + t.paint_m), t.gp)
    m["trans_pts_pg"] = div(t.pts_trans, t.gp)
    m["trans_share"] = div(t.poss_trans, t.possessions, 100)
    m["putback_pts_pg"] = div(t.pts_putback, t.gp)
    m["drive_per100"] = div(t.drive_fga, t.possessions, 100)
    m["pnr_per100"] = div(t.poss_pnrbh + t.poss_roll, t.possessions, 100)
    m["pnr_ppp"] = div(t.pts_pnrbh + t.pts_roll, t.poss_pnrbh + t.poss_roll)
    for k in PLAY:
        m[f"ppp_{k}"] = div(t[f"pts_{k}"], t[f"poss_{k}"])
        m[f"per100_{k}"] = div(t[f"poss_{k}"], t.possessions, 100)
    m["ssq"] = div(t.sq_tot, t.sq_n)
    return m


# label, key, format, higher is better on offense (None = style, ranked by "most")
OFF = [("Points per 100 possessions", "ppp100", "{:.1f}", True), ("Points per pick and roll (ball handler + roll man)", "pnr_ppp", "{:.2f}", True),
       ("Points per isolation", "ppp_iso", "{:.2f}", True), ("Points per post-up", "ppp_post", "{:.2f}", True),
       ("Points per spot-up", "ppp_spot", "{:.2f}", True), ("Transition points per game", "trans_pts_pg", "{:.1f}", True),
       ("3PT%", "three_pct", "{:.1f}%", True), ("Catch-and-shoot 3PT%", "cs3_pct", "{:.1f}%", True),
       ("FG% at the rim", "rim_pct", "{:.1f}%", True), ("Points in the paint per game (field goals)", "paint_pts_pg", "{:.1f}", True),
       ("Turnover %", "to_pct", "{:.1f}%", False), ("Offensive rebound %", "oreb_pct", "{:.1f}%", True),
       ("Putback points per game", "putback_pts_pg", "{:.1f}", True), ("Catch-and-shoot jumpers taken open", "open_pct", "{:.1f}%", True),
       ("Free throws per 100 field-goal attempts", "ft_rate", "{:.1f}", True)]
STYLE = [("Possessions per game", "poss_pg", "{:.1f}"), ("Transition share of possessions", "trans_share", "{:.1f}%"),
         ("Shots from three", "three_share", "{:.1f}%"), ("Shots at the rim", "rim_share", "{:.1f}%"),
         ("Pick and rolls per 100 possessions", "pnr_per100", "{:.1f}"), ("Isolations per 100 possessions", "per100_iso", "{:.1f}"),
         ("Post-ups per 100 possessions", "per100_post", "{:.1f}"), ("Spot-ups per 100 possessions", "per100_spot", "{:.1f}"),
         ("Off-screen plays per 100 possessions", "per100_offscreen", "{:.1f}"), ("Handoffs per 100 possessions", "per100_handoff", "{:.1f}"),
         ("Shots after a drive per 100 possessions", "drive_per100", "{:.1f}"), ("Assisted field goals", "ast_pct", "{:.1f}%")]


def ranks(m: pd.DataFrame, side: str, key: str, higher_better: bool | None) -> pd.Series:
    """Rank of every team on `key` within the side (1 = best; for style, 1 = most). Ties share the rank."""
    s = m[m.side == side].set_index("team_id")[key]
    asc = False if higher_better is None else (not higher_better if side == "off" else higher_better)
    return s.rank(ascending=asc, method="min")


def fmt(f: str, v) -> str:
    return "–" if v is None or (isinstance(v, float) and math.isnan(v)) else f.format(v)


def ordinal(n: int) -> str:
    n = int(n)
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


# ── HTML pieces ───────────────────────────────────────────────────────────────
CSS = """<style>
.kn{font-size:.95rem}
.kn .muted{color:#5e584b;font-size:.85rem}
.kn table{border-collapse:collapse;width:100%;margin:.4rem 0 1rem}
.kn th,.kn td{padding:.25rem .45rem;border-bottom:1px solid #e7e1d3;text-align:right;white-space:nowrap}
.kn th:first-child,.kn td:first-child{text-align:left}
.kn th{font-weight:600;color:#5e584b;font-size:.82rem}
.kn .tiles{display:flex;gap:.8rem;flex-wrap:wrap;margin:.5rem 0 1rem}
.kn .tile{flex:1 1 11rem;border:1px solid #e7e1d3;border-radius:8px;padding:.6rem .8rem;background:#faf7ef}
.kn .tile .v{font-size:1.6rem;font-weight:700}
.kn .tile .l{color:#5e584b;font-size:.85rem}
.kn .row{display:grid;grid-template-columns:minmax(12rem,1.6fr) 5rem 3.5rem minmax(6rem,2fr);gap:.5rem;align-items:center;padding:.2rem 0;border-bottom:1px solid #f0ebdf}
.kn .bar{height:.55rem;background:#eee8da;border-radius:4px;overflow:hidden}
.kn .bar i{display:block;height:100%;background:#9aa0b4}
.kn .bar i.top{background:#1e7b45}.kn .bar i.bottom{background:#b3302f}.kn .bar i.gold{background:#F2C300}
.kn .vs{display:grid;grid-template-columns:minmax(12rem,1.6fr) 1fr 1fr;gap:.5rem;padding:.25rem 0;border-bottom:1px solid #f0ebdf}
.kn .tag{display:inline-block;font-size:.75rem;padding:.05rem .4rem;border-radius:10px;background:#f5ebcb;margin:.1rem .2rem .1rem 0}
.kn .cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(17rem,1fr));gap:.8rem}
.kn .card{border:1px solid #e7e1d3;border-radius:8px;padding:.6rem .8rem}
.kn .card h4{margin:0 0 .3rem}
.kn .card ul{list-style:none;padding:0;margin:.3rem 0 0}
.kn .card li{padding:.1rem 0}
.kn .plus{color:#1e7b45;font-weight:700}.kn .minus{color:#b3302f;font-weight:700}
.kn .good{color:#1e7b45;font-weight:600}.kn .bad{color:#b3302f;font-weight:600}
.kn .courts{display:grid;grid-template-columns:repeat(auto-fit,minmax(18rem,1fr));gap:1rem}
.kn svg{width:100%;height:auto}
</style>"""


def bar(rank: float, n: int, cls: str = "") -> str:
    if rank is None or (isinstance(rank, float) and math.isnan(rank)):
        return '<div class="bar"></div>'
    w = 100 * (n - rank + 1) / n
    tier = cls or ("top" if rank <= n / 3 else "bottom" if rank > 2 * n / 3 else "")
    return f'<div class="bar"><i class="{tier}" style="width:{w:.0f}%"></i></div>'


def rank_rows(items: list[tuple[str, str, float, float]], n: int, cls: str = "") -> str:
    """items: (label, value text, rank, -); one grid row per item with the rank bar (longest = best)."""
    out = []
    for label, val, rk in items:
        r = "–" if rk is None or math.isnan(rk) else ordinal(rk)
        out.append(f'<div class="row"><span>{escape(label)}</span><strong>{val}</strong><span class="muted">{r}</span>{bar(rk, n, cls)}</div>')
    return "".join(out)


def table(cols: list[str], rows: list[list[str]], first_left: bool = True) -> str:
    head = "".join(f"<th>{escape(c)}</th>" for c in cols)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def court_svg(zones: dict[str, tuple[int, int]], league: dict[str, float], title: str, caption: str,
              accent: str = "#9aa0b4") -> str:
    """Half court with the basket at the top (Synergy coordinates rotated 180 degrees: left and right as seen from center court facing
    the basket), one label per Synergy zone: FG% (big) and share of the team's shots (small), coloured against the competition average."""
    total = sum(a for a, _ in zones.values()) or 1
    W, H, B = 500, 420, 382     # B: baseline in Synergy y
    X = lambda x: 500 - x
    Y = lambda y: B - y + 10
    lines = [f'<rect x="0" y="10" width="500" height="{H - 50}" fill="#fbf8f0" stroke="#5b5f78" stroke-width="2"/>',
             f'<rect x="170" y="10" width="160" height="190" fill="none" stroke="#5b5f78" stroke-width="1.5"/>',
             f'<circle cx="250" cy="200" r="60" fill="none" stroke="#5b5f78" stroke-width="1.5"/>',
             f'<line x1="220" y1="49" x2="280" y2="49" stroke="#5b5f78" stroke-width="3"/>',
             f'<circle cx="250" cy="62" r="7.5" fill="none" stroke="#5b5f78" stroke-width="2"/>',
             f'<path d="M 209 62 A 41 41 0 0 0 291 62" fill="none" stroke="#5b5f78" stroke-width="1.2"/>',
             f'<path d="M 34 10 L 34 108.7 A 221 221 0 0 0 466 108.7 L 466 10" fill="none" stroke="#5b5f78" stroke-width="1.5"/>']
    labels = []
    for z, (cx, cy) in POS.items():
        a, made = zones.get(z, (0, 0))
        w = 44 if z in ("Z11-12-3pt", "Z11-16-3pt") else 60
        if a >= MIN_ZONE_FGA:
            p = 100 * made / a
            d = p - league.get(z, p)
            fill = "#f4c7c3" if d >= ZONE_DIFF else "#cfe6d8" if d <= -ZONE_DIFF else "#ffffff"
            big, small = f"{p:.0f}%", f"{100 * a / total:.0f}%"
        else:
            fill, big, small = "#eeeeee", "–", f"{100 * a / total:.0f}%"
        labels.append(f'<g><rect x="{cx - w / 2}" y="{cy - 20}" width="{w}" height="38" rx="7" fill="{fill}" stroke="#5b5f78" stroke-width=".8"/>'
                      f'<text x="{cx}" y="{cy}" text-anchor="middle" font-size="17" font-weight="700" fill="#1f1b14">{big}</text>'
                      f'<text x="{cx}" y="{cy + 14}" text-anchor="middle" font-size="11" fill="#5e584b">{small}</text></g>')
    return (f'<figure><svg viewBox="0 0 {W} {H}" role="img" aria-label="{escape(title)}">'
            f'<rect x="0" y="0" width="500" height="6" fill="{accent}"/>' + "".join(lines) + "".join(labels) +
            f'<text x="250" y="{H - 24}" text-anchor="middle" font-size="15" font-weight="700" fill="#1f1b14">{escape(title)}</text>'
            f'<text x="250" y="{H - 7}" text-anchor="middle" font-size="10.5" fill="#5e584b">{escape(caption)}</text></svg></figure>')


# ── page ──────────────────────────────────────────────────────────────────────
def build(folder: Path) -> tuple[Path, str]:
    cfg = json.loads((folder / "config.json").read_text(encoding="utf-8"))
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    opp_id, ref_id = cfg["opponent"]["team_id"], cfg["reference"]["team_id"]
    OPPN, REFN = cfg["opponent"]["name"], cfg["reference"]["name"]
    comp, author, pulled = cfg["competition"], cfg["author"], cfg["date"]
    t = pd.read_csv(folder / "teams.csv")
    m = team_metrics(t)
    n = int((m.side == "off").sum())
    get = lambda tid, side, k: float(m[(m.team_id == tid) & (m.side == side)][k].iloc[0])
    rk = lambda tid, side, k, hb: float(ranks(m, side, k, hb).get(tid, np.nan))
    avg = lambda side, k: float(np.nanmean(m[m.side == side][k]))
    gp_opp, gp_ref = int(get(opp_id, "off", "gp")), int(get(ref_id, "off", "gp"))
    last = meta.get("last_game", "")[:10]

    P = pd.read_csv(folder / "players.csv").fillna(0)
    box = pd.read_csv(folder / "box.csv")
    box = box[box["PLAYER"].notna() & ~box["PLAYER"].astype(str).str.strip().isin(["", "TEAM TOTAL"])].copy()
    box["name"] = box["PLAYER"].str.replace(r"^#\S+\s+", "", regex=True)
    box["number"] = box["PLAYER"].str.extract(r"^#(\S+)")[0]
    oreb = {r["name"]: (float(r["OFF REB"]), int(r["GP"]), str(r.get("OFFENSIVE ROLE", "") or "")) for _, r in box.iterrows()}
    nums = {r["name"]: r["number"] for _, r in box.iterrows()}
    def boxinfo_num(name):
        if name in nums:
            return nums[name]
        hit = [v for k, v in nums.items() if k.split()[-1] == name.split()[-1]]
        return hit[0] if hit else ""
    def boxinfo(name):
        if name in oreb:
            return oreb[name]
        last_n = name.split()[-1]
        for k, v in oreb.items():
            if k.split()[-1] == last_n:
                return v
        return (np.nan, 0, "")
    P["oreb"] = [boxinfo(x)[0] for x in P.name]
    P["number"] = [str(boxinfo_num(x)) for x in P.name]
    P["role"] = [boxinfo(x)[2] if boxinfo(x)[2] not in ("nan", "-") else "" for x in P.name]
    P = P[P.gp > 0].copy()
    g = P.gp
    P["fga_pg"], P["three_pg"], P["drives"] = P.fga / g, P.three_a / g, P.drive_l + P.drive_r + P.drive_s
    P["drives_pg"], P["iso_pg"], P["pnr_pg"], P["oreb_pg"], P["to_pg"] = P.drives / g, P.poss_iso / g, P.poss_pnrbh / g, P.oreb / g, P.turnover / g
    P["ppp"] = div(P.pointMade, P.possessions)
    P["three_pct"] = div(P.three_m, P.three_a, 100)
    P["cs3_pct"] = div(P.cs3_m, P.cs3_a, 100)
    P["rim_pct"] = div(P.rim_m, P.rim_a, 100)
    P["to_pct"] = div(P.turnover, P.possessions, 100)
    rot = P[(P.gp >= max(2, gp_opp / 2))].sort_values("possessions", ascending=False).head(9)

    D = pd.read_csv(folder / "defenders.csv").fillna(0)
    zones = pd.read_csv(folder / "zones.csv")
    zl = zones[zones.side == "off"].groupby("zone")[["fga", "fgm"]].sum()
    league_zone = (100 * zl.fgm / zl.fga).to_dict()
    zget = lambda tid, side: {r.zone: (int(r.fga), int(r.fgm)) for r in zones[(zones.team_id == tid) & (zones.side == side)].itertuples()}

    md = []
    md.append(f"---\ntitle: Key numbers\ngenerated_by: notebooks/key_numbers.py\n---\n")
    md.append(f"<!-- Generated by `python notebooks/key_numbers.py {folder.relative_to(ROOT).as_posix()}`: running it again overwrites this file. -->\n")
    md.append(f"# Key numbers\n")
    md.append(CSS + "\n")
    md.append(f'<div class="kn"><p><strong>{escape(OPPN)}</strong> · {escape(cfg["game"])}. Synergy data, {escape(comp)} games only, up to {last}: '
              f'{escape(OPPN)} {gp_opp} games, {escape(REFN)} {gp_ref}. Ranks among the {n} {escape(comp)} teams (1st = best; for style, 1st = most). '
              f'Based solely on the data, with no comments on plays. Pulled {escape(pulled)} · {escape(author)}.</p>'
              f'<div class="tiles">'
              f'<div class="tile"><div class="v">{get(opp_id, "off", "ppp100"):.1f}</div><div class="l">Points per 100 possessions · {ordinal(rk(opp_id, "off", "ppp100", True))} of {n}</div></div>'
              f'<div class="tile"><div class="v">{get(opp_id, "def", "ppp100"):.1f}</div><div class="l">Points allowed per 100 · {ordinal(rk(opp_id, "def", "ppp100", True))} of {n}</div></div>'
              f'<div class="tile"><div class="v">{get(opp_id, "off", "poss_pg"):.1f}</div><div class="l">Possessions per game · {ordinal(rk(opp_id, "off", "poss_pg", None))} of {n}, 1st = most</div></div>'
              f'</div></div>\n')

    # strengths and weak spots
    items = [(lab, fmt(f, get(opp_id, "off", k)), rk(opp_id, "off", k, hb)) for lab, k, f, hb in OFF]
    items = [i for i in items if not math.isnan(i[2])]
    best = sorted(items, key=lambda i: i[2])[:3]
    worst = sorted(items, key=lambda i: -i[2])[:3]
    md.append("## Their strengths and weak spots\n")
    md.append(f'<div class="kn"><h3>Strengths</h3><p class="muted">Offense. Bar = rank among the {n} {comp} teams, longest = best.</p>{rank_rows(best, n)}'
              f'<h3>Weak spots</h3><p class="muted">Offense. Short bar = bottom of the {n} teams.</p>{rank_rows(worst, n)}</div>\n')

    # they rank above our defense
    pairs = []
    for lab, k, f, hb in OFF:
        ro, rd = rk(opp_id, "off", k, hb), rk(ref_id, "def", k, hb)
        if math.isnan(ro) or math.isnan(rd):
            continue
        pairs.append((ro - rd, lab, k, f, ro, rd))
    hits = [p for p in sorted(pairs) if p[4] <= n / 2 and p[5] > n / 2][:4]
    md.append(f"## Where their offense meets our defense\n")
    if hits:
        rows = "".join(f'<div class="vs"><span>{escape(lab)}</span><span>They <strong>{fmt(f, get(opp_id, "off", k))}</strong> <span class="muted">{ordinal(ro)}</span></span>'
                       f'<span>We allow <strong>{fmt(f, get(ref_id, "def", k))}</strong> <span class="muted">{ordinal(rd)}</span></span></div>'
                       for _, lab, k, f, ro, rd in hits)
        md.append(f'<div class="kn"><p class="muted">Numbers where their offense is in the top half of the {comp} teams and {escape(REFN)}\'s defense in the bottom half, '
                  f'largest gap first.</p>{rows}</div>\n')
    else:
        md.append(f'<div class="kn"><p>No number where their offense is in the top half and {escape(REFN)}\'s defense in the bottom half.</p></div>\n')

    # matchups: who defends it for us
    plays = ["pnrbh", "iso", "post", "spot", "offscreen", "handoff", "roll"]
    freq = sorted(plays, key=lambda k: -get(opp_id, "off", f"per100_{k}"))
    chosen = [k for k in freq if rk(opp_id, "off", f"ppp_{k}", True) <= n / 2][:3] or freq[:3]
    blocks = []
    for k in chosen:
        lg = float(np.nansum(t[t.side == "off"][f"pts_{k}"]) / np.nansum(t[t.side == "off"][f"poss_{k}"]))
        d = D[D[f"poss_{k}"] >= MIN_DEF_POSS].copy()
        d["ppp"] = d[f"pts_{k}"] / d[f"poss_{k}"]
        d = d.sort_values("ppp")
        pick = list(d.head(2).itertuples()) + ([list(d.itertuples())[-1]] if len(d) > 2 else [])
        rows = []
        for i, r in enumerate(pick):
            cls = "good" if i < 2 and r.ppp < lg else "bad" if (i == 2 or r.ppp > lg) else ""
            rows.append([escape(r.name), f"{int(getattr(r, f'poss_{k}'))}", f'<span class="{cls}">{r.ppp:.2f}</span>'])
        body = table(["Defender", "Poss.", "PPP"], rows) if rows else f'<p class="muted">No defender with {MIN_DEF_POSS} possessions yet.</p>'
        blocks.append(f'<div class="card"><h4>{PLAY[k]}</h4><p class="muted">They: {get(opp_id, "off", f"per100_{k}"):.1f} per 100 possessions, '
                      f'{get(opp_id, "off", f"ppp_{k}"):.2f} points per possession ({ordinal(rk(opp_id, "off", f"ppp_{k}", True))}). '
                      f'{escape(REFN)} allows {get(ref_id, "def", f"ppp_{k}"):.2f} ({ordinal(rk(ref_id, "def", f"ppp_{k}", True))}). Competition average {lg:.2f}.</p>{body}</div>')
    md.append("## Matchups: who defends it for us\n")
    md.append(f'<div class="kn"><p class="muted">PPP = points per possession. Their most used play types where they rank in the top half (or simply the most used). {escape(REFN)} defenders, {comp} games: '
              f'points per possession on the possessions that end on him (Synergy logs the defender of the last action only), at least {MIN_DEF_POSS} possessions. '
              f'Our two lowest numbers (green when below the competition average) and the highest (red when above). Small samples.</p>'
              f'<div class="cards">{"".join(blocks)}</div></div>\n')

    # personnel
    cards = []
    team_rank = lambda col, asc=False, mask=None: (rot if mask is None else rot[mask])[col].rank(ascending=asc, method="min")
    for r in rot.sort_values("fga", ascending=False).head(6).itertuples():
        tags = [r.role] if r.role else []
        pl, mi = [], []
        def add(lst, cond, text):
            if cond and len(lst) < 2:
                lst.append(text)
        add(pl, r.three_pg >= 3 and r.three_pct >= 33, f"Takes {r.three_pg:.1f} threes per game")
        add(pl, r.cs3_a >= 10 and r.cs3_pct >= 40, f"Catch-and-shoot threes: {r.cs3_pct:.0f}% on {int(r.cs3_a)}")
        add(pl, r.rim_a >= 10 and r.rim_pct >= 65, f"Makes {r.rim_pct:.0f}% of his shots at the rim")
        add(pl, r.drives_pg >= 2.5, f"{r.drives_pg:.1f} shots after a drive per game")
        add(pl, r.pnr_pg >= 3, f"{r.pnr_pg:.1f} pick and rolls as ball handler per game")
        add(pl, r.iso_pg >= 1.5, f"{r.iso_pg:.1f} isolations per game")
        add(pl, r.oreb_pg >= 1.5, f"{r.oreb_pg:.1f} offensive rebounds per game")
        add(pl, r.fga_pg >= 9, f"Takes {r.fga_pg:.1f} shots per game")
        if r.three_a >= 12 and r.three_pct < 30:
            mi.append(f"Shoots {r.three_pct:.0f}% from three on {r.three_pg:.1f} attempts per game")
        if r.rim_a >= 10 and r.rim_pct < 50:
            mi.append(f"Makes {r.rim_pct:.0f}% of his shots at the rim")
        if r.possessions >= 25 and r.to_pct >= 17:
            mi.append(f"Turns the ball over on {r.to_pct:.0f}% of his possessions")
        if r.fga >= 15 and r.three_a / max(r.fga, 1) < 0.15:
            mi.append(f"Takes {100 * r.three_a / r.fga:.0f}% of his shots from three")
        side_lines = []
        if r.drives >= 12:
            lshare = 100 * r.drive_l / r.drives
            if lshare >= 65 or lshare <= 35:
                side_lines.append(f"Drives to his {'left' if lshare >= 65 else 'right'} on {max(lshare, 100 - lshare):.0f}% of his drives")
        num = f"#{r.number} " if isinstance(r.number, str) and r.number else ""
        lis = ("".join(f'<li><span class="plus">+</span> {escape(x)}</li>' for x in pl) + "".join(f'<li><span class="minus">&minus;</span> {escape(x)}</li>' for x in mi[:2])
               + "".join(f'<li><span class="muted">&bull;</span> {escape(x)}</li>' for x in side_lines))
        cards.append(f'<div class="card"><h4>{escape(num + r.name)}</h4>{"".join(f"<span class=tag>{escape(x)}</span>" for x in tags)}<ul>{lis}</ul>'
                     f'<p class="muted">{r.fga_pg:.1f} shots, {r.possessions / r.gp:.1f} possessions, {r.ppp:.2f} points per possession · {int(r.gp)} GP</p></div>')
    md.append("## Personnel\n")
    md.append(f'<div class="kn"><p class="muted">Their six highest-volume shooters. Tag = Synergy offensive role. + what he does, &minus; where his numbers are low. One number per line.</p>'
              f'<div class="cards">{"".join(cards)}</div></div>\n')

    # shooting
    cap = f"Synergy, {comp}, games up to {last} · {author} · {pulled}"
    c1 = court_svg(zget(opp_id, "off"), league_zone, f"Where {OPPN} shoot", cap)
    c2 = court_svg(zget(ref_id, "def"), league_zone, f"What {REFN} allow", cap, GOLD)
    vs = lambda lab, k, f, hb: (f'<div class="vs"><span>{lab}</span><span>They <strong>{fmt(f, get(opp_id, "off", k))}</strong> <span class="muted">{ordinal(rk(opp_id, "off", k, hb))}</span></span>'
                                f'<span>We allow <strong>{fmt(f, get(ref_id, "def", k))}</strong> <span class="muted">{ordinal(rk(ref_id, "def", k, hb))}</span></span></div>')
    three = rot[rot.three_a > 0].sort_values("three_a", ascending=False).head(6)
    trows = []
    for r in three.itertuples():
        cls = "bad" if r.three_pct >= 38 else "good" if r.three_pct < 30 else ""
        trows.append([escape(r.name), f"{r.three_pg:.1f}", f'<span class="{cls}">{r.three_pct:.0f}%</span>',
                      f"{fmt('{:.0f}%', r.cs3_pct)} <span class=muted>({int(r.cs3_a)})</span>",
                      fmt("{:.0f}%", div(r.jump_open, r.jump_tag, 100))])
    md.append("## Shooting: where they shoot, what we allow\n")
    md.append(f'<div class="kn"><div class="courts">{c1}{c2}</div><p class="muted">Big number = FG% in the zone, small = share of the team\'s shots. '
              f'Red = {ZONE_DIFF:.0f} points or more above the {comp} average in that zone, green = {ZONE_DIFF:.0f} or more below, white = within. '
              f'Grey = fewer than {MIN_ZONE_FGA} attempts. Basket at the top; left and right as seen from center court facing the basket.</p>'
              + vs("3PT%", "three_pct", "{:.1f}%", True) + vs("FG% at the rim", "rim_pct", "{:.1f}%", True)
              + vs("Catch-and-shoot jumpers taken open", "open_pct", "{:.1f}%", True) + vs("Points in the paint per game (field goals)", "paint_pts_pg", "{:.1f}", True)
              + '<h3>Who shoots the three</h3><p class="muted">Top 3PT volume. Red = 38% or more, green = under 30%. Open = share of his catch-and-shoot jumpers '
              'Synergy tags as open.</p>' + table(["Player", "3PA per game", "3PT%", "Catch-and-shoot 3PT% (att.)", "Open"], trows) + '</div>\n')

    # pick and roll
    hand = rot[rot.poss_pnrbh >= 10].sort_values("poss_pnrbh", ascending=False).head(4)
    roll = P[P.poss_roll >= 6].sort_values("poss_roll", ascending=False).head(4)
    hrows = [[escape(r.name), f"{r.poss_pnrbh / r.gp:.1f}", f"{div(r.pts_pnrbh, r.poss_pnrbh):.2f}"] for r in hand.itertuples()]
    rrows = [[escape(r.name), f"{r.poss_roll / r.gp:.1f}", f"{div(r.pts_roll, r.poss_roll):.2f}"] for r in roll.itertuples()]
    md.append("## Pick and roll\n")
    md.append(f'<div class="kn"><p class="muted">Synergy does not log the coverage (drop, show, switch...): numbers are by role only. '
              f'Points per possession on the pick and rolls that end the possession.</p>'
              + vs("Pick and rolls per 100 possessions", "pnr_per100", "{:.1f}", None)
              + vs("Points per pick and roll, ball handler", "ppp_pnrbh", "{:.2f}", True) + vs("Points per pick and roll, roll man", "ppp_roll", "{:.2f}", True)
              + '<h3>Ball handlers</h3>' + table(["Player", "Per game", "Points per possession"], hrows)
              + '<h3>Roll men</h3>' + table(["Player", "Per game", "Points per possession"], rrows) + '</div>\n')

    # drives and isolation
    dr = rot[rot.drives >= 5].sort_values("drives_pg", ascending=False).head(6)
    drows = []
    for r in dr.itertuples():
        side = r.drive_l + r.drive_r
        drows.append([escape(r.name), f"{r.drives_pg:.1f}", f"{100 * r.drive_l / side:.0f}% / {100 * r.drive_r / side:.0f}%" if side else "–",
                      f"{r.iso_pg:.1f}", fmt("{:.2f}", div(r.pts_iso, r.poss_iso) if r.poss_iso >= 5 else np.nan)])
    md.append("## Drives and isolation\n")
    md.append(f'<div class="kn"><p class="muted">Synergy tags a drive only when the play ends in a shot (by the driver or after his pass), so these are '
              f'shots after a drive, not every drive; Synergy does not log whether the driver beats his defender. Left / right as seen by the driver.</p>'
              + vs("Shots after a drive per 100 possessions", "drive_per100", "{:.1f}", None)
              + vs("Points per isolation", "ppp_iso", "{:.2f}", True)
              + table(["Player", "Shots after a drive per game", "Left / right", "Isolations per game", "Points per isolation (5+)"], drows) + '</div>\n')

    # rebound and transition
    ob = rot[rot.oreb > 0].sort_values("oreb_pg", ascending=False).head(5)
    orows = [[escape(r.name), f"{r.oreb_pg:.1f}", f"{int(r.oreb)}", f"{int(r.gp)}"] for r in ob.itertuples()]
    md.append("## Rebound and transition\n")
    md.append('<div class="kn">' + vs("Offensive rebound %", "oreb_pct", "{:.1f}%", True) + vs("Putback points per game", "putback_pts_pg", "{:.1f}", True)
              + vs("Transition points per game", "trans_pts_pg", "{:.1f}", True) + vs("Transition share of possessions", "trans_share", "{:.1f}%", None)
              + '<h3>Offensive rebound: who to box out</h3><p class="muted">Offensive rebounds per game (Synergy cumulative box). Synergy does not log box-outs '
              'or who crashes the glass.</p>' + table(["Player", "Off. reb. per game", "Total", "GP"], orows) + '</div>\n')

    # all their numbers
    def alltable(side: str, spec, hb_default=True):
        rows = []
        for it in spec:
            lab, k, f = it[0], it[1], it[2]
            hb = it[3] if len(it) > 3 else None
            r = rk(opp_id, side, k, hb)
            rows.append([escape(lab), fmt(f, get(opp_id, side, k)), ordinal(r) if not math.isnan(r) else "–", fmt(f, avg(side, k))])
        return table(["", "Value", "Rank", f"{comp} average"], rows)
    best_def = sorted([(rk(opp_id, "def", k, hb), lab) for lab, k, f, hb in OFF if not math.isnan(rk(opp_id, "def", k, hb))])
    md.append("## All their numbers: offense, defense and style\n")
    md.append(f'<div class="kn"><p>Defense, best ranks: {"; ".join(f"{escape(l)} {ordinal(r)}" for r, l in best_def[:3])}. '
              f'Worst: {"; ".join(f"{escape(l)} {ordinal(r)}" for r, l in best_def[-3:][::-1])}.</p></div>\n\n<!-- more -->\n')
    md.append(f'<div class="kn"><h3>Offense</h3>{alltable("off", OFF)}<h3>Defense (what they allow)</h3><p class="muted">Rank 1st = best defense.</p>'
              f'{alltable("def", OFF)}<h3>Style</h3><p class="muted">Rank 1st = most.</p>{alltable("off", STYLE)}</div>\n')

    # player numbers
    prow = []
    for r in rot.itertuples():
        s = max(r.fga, 1)
        side = r.drive_l + r.drive_r
        prow.append([escape(r.name), f"{int(r.gp)}", f"{r.fga_pg:.1f}", f"{fmt('{:.0f}%', r.three_pct)} ({r.three_pg:.1f})",
                     f"{100 * r.rim_a / s:.0f} / {100 * (r.mid_a + r.paint_a) / s:.0f} / {100 * r.three_a / s:.0f}",
                     f"{r.drives_pg:.1f}", f"{100 * r.drive_l / side:.0f}% / {100 * r.drive_r / side:.0f}%" if side >= 5 else "–",
                     fmt("{:.1f}", r.oreb_pg), f"{r.to_pg:.1f}", fmt("{:.2f}", r.ppp)])
    md.append("## Player numbers\n")
    md.append(f'<div class="kn"><p class="muted">Per game, {comp} games. Shots: share at the rim / other 2-pointers / threes.</p>'
              + table(["Player", "GP", "Shots", "3PT% (3PA)", "Rim / 2P / 3P %", "Shots after a drive", "Drives L / R", "Off. reb.", "TO", "Points per possession"], prow)
              + '</div>\n')

    # sources
    md.append("## Sources and definitions\n")
    md.append(f"Synergy Sports (Synergy web app API), {comp} games of the 2026-27 season up to {last}, pulled {pulled}; folder "
              f"`{folder.relative_to(ROOT).as_posix()}`. Based solely on the data: no comments on plays.\n\n"
              f"* **Ranks**: among the {n} {comp} teams; ties share the rank. Defense ranks: 1st = allows the least.\n"
              f"* **At the rim**: 2-point attempts within 6 ft of the basket. **Points in the paint**: field goals only (no free throws).\n"
              f"* **Open**: catch-and-shoot jumpers that Synergy tags as open (it tags open / guarded only on catch-and-shoot jumpers).\n"
              f"* **Shots after a drive**: field-goal attempts whose Synergy description contains a drive (Drives Left / Right / Straight).\n"
              f"* **Offensive rebound %**: offensive rebounds / (offensive + opponent defensive rebounds), from Synergy's play-by-play stats.\n"
              f"* **Defenders**: possessions that end on the defender (Synergy's defensive player), so small samples.\n"
              f"* Not in Synergy (tracking only): box-outs, blow-bys, closeouts, crashing the glass, passes per chance, pick-and-roll coverages.\n")
    day = cfg["game_date"]
    out = GAMES / day / "key_numbers.md"
    return out, "\n".join(md)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("folder", type=Path)
    a = ap.parse_args()
    folder = a.folder if a.folder.is_absolute() else (Path.cwd() / a.folder)
    out, text = build(folder.resolve())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
