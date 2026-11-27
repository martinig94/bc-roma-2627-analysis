"""Key numbers of one opponent, from Synergy only: the "Key numbers" tab of the opponent analysis.

    python notebooks/key_numbers.py data/synergy/key_numbers_<opponent>_<game date>

Reads the folder written from `synergy/key_numbers_pull.js` and its config.json, and writes weekly/games/<game date>/key_numbers.md:
the opponent page of the SkillCorner game-preparation report (same layout, same look, same Season / Last 3 games switch), limited to
what Synergy logs: no box-outs, blow-bys, closeouts or pick-and-roll coverages (see the Read with care list at the end of the page).
The file is generated: running the script again overwrites it. Based solely on the data: no comments on plays.

Last 3 games = the opponent's and BC Roma's three most recent games of the competition, ranked against the season values of every
other team of the competition (as on the SkillCorner page); minimum samples are cut to 30% of the season ones.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd

from kn_css import CSS, JS

ROOT = Path(__file__).resolve().parents[1]
GAMES = ROOT / "weekly" / "games"
RIM_FT = 60                     # "at the rim" = 2-point attempts within 6 ft (Synergy shotDistance is in tenths of a foot)
ZONE_DIFF = 3.0                 # zone colour: FG% this many points above / below the competition average
MIN = {"season": {"zone": 12, "def": 5, "drive_side": 12, "three": 10, "iso": 5, "pnr": 10, "roll": 6},
       "last": {"zone": 4, "def": 2, "drive_side": 4, "three": 3, "iso": 2, "pnr": 3, "roll": 2}}
PT = ["pnrbh", "roll", "trans", "iso", "post", "spot", "putback", "cut", "handoff", "offscreen", "misc"]
PLAY = {"pnrbh": "Pick and roll, ball handler", "roll": "Pick and roll, roll man", "iso": "Isolation", "post": "Post-up",
        "spot": "Spot-up", "offscreen": "Off screen", "handoff": "Handoff", "cut": "Cut", "trans": "Transition", "putback": "Putback"}
MATCHUP_PLAYS = ["pnrbh", "iso", "post", "spot", "offscreen", "handoff", "roll"]   # play types that can get a "Who defends it for us" row


# ── shots ─────────────────────────────────────────────────────────────────────
def is_player(t: str) -> bool:
    return bool(re.match(r"^\d+ [A-Za-z]", t)) and not re.match(r"^\d+ Pts$", t)


def parse_shot(r) -> dict:
    """Same reading of the Synergy description as key_numbers_pull.js."""
    seg = str(r["description"]).split(" > ")
    last = max([i for i, t in enumerate(seg) if is_player(t)] or [0])
    after = seg[last + 1:]
    cur, drives = None, []
    for t in seg:
        if is_player(t):
            cur = re.sub(r"^\d+ ", "", t)
        m = re.match(r"^Drives? (Left|Right|Straight|Baseline)$", t)
        if m:
            drives.append((cur, m.group(1)))
    three = int(r["pointsAttempted"]) == 3
    rim = (not three) and float(r["shotDistance"]) <= RIM_FT
    zone = "three" if three else "rim" if rim else ("paint" if r["zoneName"] == "Z11-01-2pt" else "mid")
    return {"shooter": re.sub(r"^\d+ ", "", seg[last]), "three": three, "made": int(r["made"]) == 1, "zone": zone,
            "cs": "No Dribble Jumper" in after, "open": "Open" in after, "guarded": "Guarded" in after, "drives": drives}


def shot_aggregates(shots: pd.DataFrame) -> dict:
    a = {k: 0 for k in ["rim_a", "rim_m", "paint_a", "paint_m", "mid_a", "mid_m", "three_a", "three_m", "cs3_a", "cs3_m", "jump_tag",
                        "jump_open", "drive_fga", "drive_l", "drive_r"]}
    a["shots"] = len(shots)
    for _, r in shots.iterrows():
        p = parse_shot(r)
        a[p["zone"] + "_a"] += 1
        a[p["zone"] + "_m"] += p["made"]
        if p["cs"] and p["three"]:
            a["cs3_a"] += 1
            a["cs3_m"] += p["made"]
        if p["open"] or p["guarded"]:
            a["jump_tag"] += 1
            a["jump_open"] += p["open"]
        if p["drives"]:
            a["drive_fga"] += 1
            d = p["drives"][0][1]
            a["drive_l"] += d == "Left"
            a["drive_r"] += d == "Right"
    return a


# the 12 zones of the SkillCorner court; Synergy x < 250 is the offense's right = the right of the picture (basket at the top)
def zone12(r) -> str:
    z, three = r["zoneName"], int(r["pointsAttempted"]) == 3
    if not three and z == "Z11-01-2pt":
        return "rim" if float(r["shotDistance"]) <= RIM_FT else "paint"
    return {"Z11-07-2pt": "base_r", "Z11-11-2pt": "base_l", "Z11-08-2pt": "wing_r", "Z11-10-2pt": "wing_l", "Z11-09-2pt": "top_mid",
            "Z11-12-3pt": "c3_r", "Z11-16-3pt": "c3_l", "Z11-13-3pt": "w3_r", "Z11-15-3pt": "w3_l", "Z11-14-3pt": "t3"}.get(z, "top_mid" if not three else "t3")


SYN12 = {"Z11-07-2pt": "base_r", "Z11-11-2pt": "base_l", "Z11-08-2pt": "wing_r", "Z11-10-2pt": "wing_l", "Z11-09-2pt": "top_mid",
         "Z11-12-3pt": "c3_r", "Z11-16-3pt": "c3_l", "Z11-13-3pt": "w3_r", "Z11-15-3pt": "w3_l", "Z11-14-3pt": "t3"}
ZONE_SHAPES = {   # SkillCorner geometry (viewBox 500 x 440): (kind, args), label position
    "c3_l": ("rect", (0, 0, 50, 110), (25, 55)), "c3_r": ("rect", (450, 0, 50, 110), (475, 55)),
    "w3_l": ("rect", (0, 110, 175, 330), (62, 310)), "t3": ("rect", (175, 110, 150, 330), (250, 345)), "w3_r": ("rect", (325, 110, 175, 330), (438, 310)),
    "base_l": ("crect", (50, 0, 125, 110), (112, 55)), "wing_l": ("crect", (50, 110, 125, 200), (116, 170)),
    "base_r": ("crect", (325, 0, 125, 110), (388, 55)), "wing_r": ("crect", (325, 110, 125, 200), (384, 170)),
    "top_mid": ("crect", (175, 190, 150, 130), (250, 222)), "paint": ("crect", (175, 0, 150, 190), (250, 140)),
    "rim": ("cpath", "M205 0 L205 50 A45 45 0 0 0 295 50 L295 0 Z", (250, 72)),
}


# ── team numbers ──────────────────────────────────────────────────────────────
def div(a, b, k=1.0):
    if np.isscalar(a) and np.isscalar(b):
        return k * float(a) / float(b) if b else float("nan")
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return np.where(b > 0, k * a / np.where(b > 0, b, 1), np.nan)


def metrics(t: pd.DataFrame) -> pd.DataFrame:
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
    for k in PT:
        m[f"ppp_{k}"] = div(t[f"pts_{k}"], t[f"poss_{k}"])
        m[f"per100_{k}"] = div(t[f"poss_{k}"], t.possessions, 100)
    return m


# label, key, format, higher is better for the team that owns the number (offense: scores more; defense rows are read as "allowed")
ITEMS = {
    "ppp100": ("Points per 100 possessions", "{:.1f}", True), "pnr_ppp": ("Points per pick and roll", "{:.2f}", True),
    "ppp_iso": ("Points per isolation", "{:.2f}", True), "ppp_post": ("Points per post-up", "{:.2f}", True),
    "ppp_spot": ("Points per spot-up", "{:.2f}", True), "trans_pts_pg": ("Transition points per game", "{:.1f}", True),
    "three_pct": ("3PT%", "{:.1f}%", True), "cs3_pct": ("Catch-and-shoot 3PT%", "{:.1f}%", True),
    "rim_pct": ("FG% at the rim", "{:.1f}%", True), "paint_pts_pg": ("Points in the paint per game", "{:.1f}", True),
    "to_pct": ("Turnover %", "{:.1f}%", False), "oreb_pct": ("Offensive rebound %", "{:.1f}%", True),
    "putback_pts_pg": ("Putback points per game", "{:.1f}", True), "open_pct": ("Catch-and-shoot jump shots taken open", "{:.1f}%", True),
    "ft_rate": ("Free throws per 100 shots", "{:.1f}", True), "drive_per100": ("Shots after a drive per 100 possessions", "{:.1f}", True),
    "rim_share": ("Share of shots at the rim", "{:.1f}%", True), "three_share": ("Share of shots from three", "{:.1f}%", True),
}
DEF_LABEL = {"ppp100": "Points allowed per 100 possessions", "three_pct": "Opponent 3PT%", "rim_pct": "Opponent FG% at the rim",
             "oreb_pct": "Opponent offensive rebound %", "to_pct": "Turnovers forced %", "open_pct": "Opponent catch-and-shoot jump shots open",
             "rim_share": "Opponent share of shots at the rim", "three_share": "Opponent share of shots from three",
             "paint_pts_pg": "Points in the paint allowed per game", "trans_pts_pg": "Transition points allowed per game",
             "putback_pts_pg": "Putback points allowed per game", "cs3_pct": "Opponent catch-and-shoot 3PT%", "ft_rate": "Opponent free throws per 100 shots",
             "pnr_ppp": "Points allowed per pick and roll", "ppp_iso": "Points allowed per isolation", "ppp_post": "Points allowed per post-up",
             "ppp_spot": "Points allowed per spot-up", "drive_per100": "Opponent shots after a drive per 100"}
OFF_SET = ["ppp100", "pnr_ppp", "ppp_iso", "ppp_post", "ppp_spot", "trans_pts_pg", "three_pct", "cs3_pct", "rim_pct", "paint_pts_pg", "to_pct",
           "oreb_pct", "putback_pts_pg", "open_pct", "ft_rate", "drive_per100", "rim_share", "three_share"]
DEF_SET = ["ppp100", "pnr_ppp", "ppp_iso", "ppp_post", "ppp_spot", "trans_pts_pg", "three_pct", "rim_pct", "paint_pts_pg", "to_pct",
           "oreb_pct", "putback_pts_pg", "open_pct", "rim_share"]
STYLE = [("Possessions per game", "poss_pg", "{:.1f}"), ("Chances in transition", "trans_share", "{:.1f}%"),
         ("Shots from three", "three_share", "{:.1f}%"), ("Shots at the rim", "rim_share", "{:.1f}%"),
         ("Pick and rolls per 100 possessions", "pnr_per100", "{:.1f}"), ("Isolations per 100 possessions", "per100_iso", "{:.1f}"),
         ("Post-ups per 100 possessions", "per100_post", "{:.1f}"), ("Spot-ups per 100 possessions", "per100_spot", "{:.1f}"),
         ("Off screen per 100 possessions", "per100_offscreen", "{:.1f}"), ("Handoffs per 100 possessions", "per100_handoff", "{:.1f}"),
         ("Shots after a drive per 100 possessions", "drive_per100", "{:.1f}"), ("Assisted field goals", "ast_pct", "{:.1f}%")]


def better_high(key: str, side: str) -> bool | None:
    """True when a higher value is better for the team that owns the row (None = style)."""
    hb = ITEMS[key][2] if key in ITEMS else None
    if hb is None:
        return None
    return hb if side == "off" else (not hb if key != "to_pct" else True)


def fmt(f: str, v) -> str:
    return "–" if v is None or (isinstance(v, float) and math.isnan(v)) else f.format(v)


def ordinal(n) -> str:
    n = int(n)
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


class Board:
    """Season rows of every team + this scope's rows of the opponent and of BC Roma; ranks within the competition."""

    def __init__(self, season: pd.DataFrame, own: dict[tuple[str, str], pd.Series]):
        self.season = season
        self.own = own                     # (team_id, side) -> metrics row used for that team in this scope
        self.n = int((season.side == "off").sum())

    def val(self, tid: str, side: str, key: str) -> float:
        if (tid, side) in self.own:
            return float(self.own[(tid, side)][key])
        r = self.season[(self.season.team_id == tid) & (self.season.side == side)]
        return float(r[key].iloc[0]) if len(r) else float("nan")

    def rank(self, tid: str, side: str, key: str, style: bool = False) -> float:
        v = self.val(tid, side, key)
        if math.isnan(v):
            return float("nan")
        others = self.season[(self.season.side == side) & (self.season.team_id != tid)][key].dropna().astype(float)
        hb = True if style else better_high(key, side)
        better = (others > v).sum() if hb else (others < v).sum()
        return float(better + 1)

    def avg(self, side: str, key: str) -> float:
        return float(np.nanmean(self.season[self.season.side == side][key].astype(float)))


# ── HTML pieces (markup of the SkillCorner page) ──────────────────────────────
def width(rk: float, n: int) -> float:
    return max(0.0, 100 * (n - rk + 1) / n) if not math.isnan(rk) else 0.0


def bar(rk: float, n: int, cls: str = "") -> str:
    if math.isnan(rk):
        return '<span class="bar"><i style="width:0%"></i></span>'
    return f'<span class="bar {cls}" role="img" aria-label="Rank {int(rk)} of {n}"><i style="width:{width(rk, n):.1f}%"></i></span>'


def tier(rk: float, n: int, good_is_high: bool = True) -> str:
    """good / bad / mid colour of a rank bar from the point of view of the team that owns the number."""
    if math.isnan(rk):
        return ""
    top = rk <= n / 3
    bottom = rk > 2 * n / 3
    return "good" if top else "bad" if bottom else "mid"


def it_rank(label: str, val: str, rk: float, n: int, cls: str, sub: str = "") -> str:
    lab = f"{escape(label)}<br><span class=\"eyebrow\">{sub}</span>" if sub else escape(label)
    r = ordinal(rk) if not math.isnan(rk) else "–"
    return (f'<div class="it"><div class="h"><span>{lab}</span><b>{val}</b></div>'
            f'<div class="rr">{bar(rk, n, cls)}<span class="rk">{r}</span></div></div>')


def duel(label: str, they: str, rt: float, we: str, rw: float, n: int) -> str:
    o = lambda r: ordinal(r) if not math.isnan(r) else "–"
    return (f'<div class="it"><div class="t">{escape(label)}</div><div class="duel">'
            f'<span class="who-l">They</span><b>{they}</b>{bar(rt, n, "bad" if rt <= n / 3 else "mid" if rt <= 2 * n / 3 else "good")}<span class="rk">{o(rt)}</span>'
            f'<span class="who-l">We allow</span><b>{we}</b>{bar(rw, n, "ink")}<span class="rk">{o(rw)}</span></div></div>')


def initials(name: str) -> str:
    p = [x for x in re.split(r"[\s\-]+", name) if x and x[0].isalpha()]
    return (p[0][0] + p[-1][0]).upper() if len(p) > 1 else name[:2].upper()


def table(head: list[str], rows: list[list[str]]) -> str:
    return ('<div class="scroll"><table><tr>' + "".join(f"<th>{escape(h)}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(rows_cell(i, c) for i, c in enumerate(r)) + "</tr>" for r in rows) + "</table></div>")


def rows_cell(i: int, c: str) -> str:
    return f'<td class="p">{c}</td>' if i == 0 else f"<td>{c}</td>"


def seg_hand(left: float, right: float) -> str:
    tot = left + right
    if not tot:
        return "–"
    l = round(100 * left / tot)
    return (f'<span class="hand"><span>{l}%</span><span class="seg" role="img" aria-label="Left {l}%, right {100 - l}%">'
            f'<i class="c-left" style="width:{l}%"></i><i class="c-right" style="width:{100 - l}%"></i></span><span>{100 - l}%</span></span>')


def zones_svg(counts: dict[str, list[int]], league: dict[str, float], minz: int, uid: str, label: str, caption: str) -> str:
    total = sum(a for a, _ in counts.values()) or 1
    cls, txt = {}, []
    for z in ZONE_SHAPES:
        a, mde = counts.get(z, [0, 0])
        if a >= minz:
            p = 100 * mde / a
            d = p - league.get(z, p)
            cls[z] = "bad" if d >= ZONE_DIFF else "good" if d <= -ZONE_DIFF else "mid"
        else:
            cls[z] = "low"
        x, y = ZONE_SHAPES[z][2]
        big = f"{100 * mde / a:.0f}%" if a else "–"
        txt.append(f'<text class="fg" x="{x}" y="{y}">{big}</text><text class="sh" x="{x}" y="{y + 15}">{100 * a / total:.0f}%</text>')
    shapes_out, shapes_in = [], []
    for z, (kind, args, _) in ZONE_SHAPES.items():
        if kind == "cpath":
            shapes_in.append(f'<path class="z {cls[z]}" d="{args}"/>')
        else:
            x, y, w, h = args
            (shapes_in if kind == "crect" else shapes_out).append(f'<rect class="z {cls[z]}" x="{x}" y="{y}" width="{w}" height="{h}"/>')
    clip = f"clip-{uid}"
    return (f'<svg class="zones" viewBox="0 0 500 462" role="img" aria-label="{escape(label)}">'
            f'<defs><clipPath id="{clip}"><path d="M50 0 L50 110 A208 208 0 0 0 450 110 L450 0 Z"/></clipPath></defs>'
            + "".join(shapes_out) + f'<g clip-path="url(#{clip})">' + "".join(shapes_in) + "</g>"
            '<path class="arc" d="M50 0 L50 110 A208 208 0 0 0 450 110 L450 0"/>'
            '<line x1="225" y1="30" x2="275" y2="30" stroke="#6F7571" stroke-width="3"/>'
            '<circle cx="250" cy="42" r="7" fill="none" stroke="#6F7571" stroke-width="2"/>'
            + "".join(txt) + f'<text class="cap" x="250" y="456">{escape(caption)}</text></svg>')


# ── one scope ─────────────────────────────────────────────────────────────────
def build_scope(scope: str, d: dict) -> str:
    cfg, B = d["cfg"], d["boards"][scope]
    n, opp, ref = B.n, d["opp_id"], d["ref_id"]
    OPPN, REFN, comp = cfg["opponent"]["name"], cfg["reference"]["name"], cfg["competition"]
    mins = MIN[scope]
    P, D = d["players"][scope], d["defenders"][scope]
    gp_opp = int(B.val(opp, "off", "gp"))
    out = [f'<section class="tab{" on" if scope == "season" else ""}" data-scope="{scope}">']
    if scope == "last":
        lo, lr = d["last_games"]["opp"], d["last_games"]["ref"]
        out.append(f'<div class="recent">Last 3 {escape(comp)} games of {escape(REFN)} and {escape(OPPN)}: '
                   f'{", ".join(lr)} / {", ".join(lo)}. Ranked against the season of the other teams. Small samples.</div>')

    # hero + briefing
    hs = []
    for lab, side, key, extra in [("Points per 100 possessions", "off", "ppp100", ""), ("Points allowed per 100", "def", "ppp100", ""),
                                  ("Possessions per game", "off", "poss_pg", ", 1st = most")]:
        rk = B.rank(opp, side, key, style=(key == "poss_pg"))
        f = "{:.1f}"
        hs.append(f'<div class="hs"><div class="l">{lab}</div><div class="v num">{fmt(f, B.val(opp, side, key))}</div>'
                  f'{bar(rk, n)}<span class="rk"><b>{ordinal(rk)}</b> of {n}{extra}</span></div>')
    scope_txt = "season" if scope == "season" else "last 3 games"
    out.append(f'<div class="sec"><div class="hero"><div><div class="eyebrow">{escape(cfg["game_short"])}</div><div class="h2">{escape(OPPN)}</div>'
               f'<div class="meta">{gp_opp} {escape(comp)} games, {scope_txt}. Synergy data.</div></div><div class="three">{"".join(hs)}</div></div>')
    items = [(k, B.rank(opp, "off", k)) for k in OFF_SET]
    items = [(k, r) for k, r in items if not math.isnan(r)]
    best = sorted(items, key=lambda x: x[1])[:3]
    worst = sorted(items, key=lambda x: -x[1])[:3]
    show = lambda k: fmt(ITEMS[k][1], B.val(opp, "off", k))
    strengths = "".join(it_rank(ITEMS[k][0], show(k), r, n, "bad") for k, r in best)
    weak = "".join(it_rank(ITEMS[k][0], show(k), r, n, "good") for k, r in worst)
    pairs = []
    for k in OFF_SET:
        ro, rd = B.rank(opp, "off", k), B.rank(ref, "def", k)
        if not (math.isnan(ro) or math.isnan(rd)) and ro <= n / 2 and rd > n / 2:
            pairs.append((ro - rd, k, ro, rd))
    pairs.sort()
    above = "".join(duel(ITEMS[k][0], show(k), ro, fmt(ITEMS[k][1], B.val(ref, "def", k)), rd, n) for _, k, ro, rd in pairs[:3]) \
        or f'<div class="it"><span class="note">No item where their offense is in the top half and our defense in the bottom half.</span></div>'
    out.append(f'<div class="cols3 even"><div class="panel brief stop"><h3>Their strengths</h3><div class="sub">Offense. Bar = rank among {n} teams.</div>{strengths}</div>'
               f'<div class="panel brief allow"><h3>Their weak spots</h3><div class="sub">Offense. Short bar = bottom of the {n} teams.</div>{weak}</div>'
               f'<div class="panel brief"><h3>They rank above our defense</h3><div class="sub">Their offense against what we allow.</div>{above}</div></div></div>')

    # matchups
    freq = sorted(MATCHUP_PLAYS, key=lambda k: -(B.val(opp, "off", f"per100_{k}") or 0))
    chosen = [k for k in freq if B.rank(opp, "off", f"ppp_{k}") <= n / 2][:4] or freq[:3]
    rows = []
    for k in chosen:
        lg = d["league_ppp"][k]
        dd = D[D.get(f"poss_{k}", pd.Series(dtype=float)).fillna(0) >= mins["def"]].copy() if f"poss_{k}" in D else D.iloc[0:0]
        whos = ""
        if len(dd):
            dd["ppp"] = dd[f"pts_{k}"].fillna(0) / dd[f"poss_{k}"]
            dd = dd.sort_values("ppp")
            pick = [("good" if r.ppp < lg else "", r) for r in list(dd.head(2).itertuples())]
            if len(dd) > 2:
                r = list(dd.itertuples())[-1]
                pick.append(("bad" if r.ppp > lg else "", r))
            for c, r in pick:
                no = d["ref_numbers"].get(r.name, "")
                whos += (f'<div class="who {c}"><span class="av sm" aria-hidden="true">{initials(r.name)}</span><span class="nm">'
                         f'{f"<span class=no>{no}</span>" if no else ""}{escape(r.name)}<small>{int(getattr(r, f"poss_{k}"))}</small></span><b>{r.ppp:.2f}</b></div>')
        else:
            whos = f'<span class="note">No defender with {mins["def"]} possessions yet.</span>'
        rk = B.rank(opp, "off", f"ppp_{k}")
        rows.append(f'<div class="stop-row"><div class="a"><h3>{PLAY[k]}</h3><span class="v num">{fmt("{:.2f}", B.val(opp, "off", f"ppp_{k}"))}</span>'
                    f'<div class="rr">{bar(rk, n, "bad" if rk <= n / 3 else "mid")}<span class="rk">{ordinal(rk)}</span></div>'
                    f'<span class="note">{B.val(opp, "off", f"per100_{k}"):.1f} per 100 possessions · all-team average {lg:.2f}</span></div>'
                    f'<div class="d"><div class="eyebrow">points per possession allowed when the possession ends on him</div><div class="whos">{whos}</div></div></div>')
    # rows from the shots BC Roma allowed: Synergy credits each shot to a defender (the `player` of a defense shot)
    sd = d["ref_def_shots"][scope].dropna(subset=["player"]).copy()
    if len(sd):
        pp = [parse_shot(r) for _, r in sd.iterrows()]
        sd["cs_tag"] = [p["cs"] and (p["open"] or p["guarded"]) for p in pp]
        sd["open"] = [p["open"] for p in pp]
        sd["jump"] = ["Jumper" in str(r) for r in sd.description]
        sd["pts"] = sd.made * sd.pointsAttempted
    shot_rows = [("open_pct", "Catch-and-shoot jump shots taken open", "catch-and-shoot jump shots he left open", "cs_tag",
                  lambda g: 100 * g.open.mean(), "{:.0f}%", "low", 10),
                 ("three_pct", "Three-point shooting", "points per jump shot allowed when he is the defender", "jump",
                  lambda g: g.pts.mean(), "{:.2f}", "low", 15)]
    for key, title, eyebrow, col, fn, f, _, mn in shot_rows:
        mn = mn if scope == "season" else max(3, round(mn * .3))
        whos = ""
        if len(sd):
            g = sd[sd[col]].groupby("player")
            st = pd.DataFrame({"n": g.size(), "v": pd.Series({k: fn(v) for k, v in g})}).query("n >= @mn").sort_values("v")
            allv = fn(sd[sd[col]]) if sd[col].any() else float("nan")
            pick = [("good" if r.v < allv else "", r) for r in list(st.head(2).itertuples())]
            if len(st) > 2:
                r = list(st.itertuples())[-1]
                pick.append(("bad" if r.v > allv else "", r))
            for c, r in pick:
                no = d["ref_numbers"].get(r.Index, "")
                whos += (f'<div class="who {c}"><span class="av sm" aria-hidden="true">{initials(r.Index)}</span><span class="nm">'
                         f'{f"<span class=no>{no}</span>" if no else ""}{escape(r.Index)}<small>{int(r.n)}</small></span><b>{f.format(r.v)}</b></div>')
        whos = whos or f'<span class="note">No defender with {mn} shots yet.</span>'
        rk = B.rank(opp, "off", key)
        rows.append(f'<div class="stop-row"><div class="a"><h3>{title}</h3><span class="v num">{fmt(ITEMS[key][1], B.val(opp, "off", key))}</span>'
                    f'<div class="rr">{bar(rk, n, "bad" if rk <= n / 3 else "mid")}<span class="rk">{ordinal(rk)}</span></div></div>'
                    f'<div class="d"><div class="eyebrow">{eyebrow}</div><div class="whos">{whos}</div></div></div>')
    out.append(f'<div class="sec"><header><div class="eyebrow">Matchups</div><div class="h2">Who defends it for us</div>'
               f'<p class="note">Their most used play types where they rank in the top half. Our two lowest numbers allowed (green when below the all-team average) '
               f'and the highest (red when above). Small number = possessions that ended on him, or shots he defended.</p></header><div class="panel">{"".join(rows)}</div></div>')

    # personnel
    rot = P.sort_values("possessions", ascending=False).head(9)
    cards = []
    for r in rot.sort_values("fga", ascending=False).head(6).itertuples():
        g, pl, mi, nt = max(r.gp, 1), [], [], []
        def add(lst, cond, html):
            if cond and len(lst) < 3:
                lst.append(html)
        three_pg, fga_pg = r.three_a / g, r.fga / g
        add(pl, three_pg >= 3 and r.three_pct >= 33, f"Takes <b>{three_pg:.1f}</b> threes per game")
        add(pl, r.cs3_a >= mins["three"] and r.cs3_pct >= 40, f"Catch-and-shoot threes: <b>{r.cs3_pct:.0f}%</b>")
        add(pl, r.rim_a >= mins["three"] and r.rim_pct >= 65, f"Makes <b>{r.rim_pct:.0f}%</b> of his shots at the rim")
        add(pl, r.drives / g >= 2.5, f"Shoots after a drive <b>{r.drives / g:.1f}</b> times per game")
        add(pl, r.poss_pnrbh / g >= 3, f"Ends <b>{r.poss_pnrbh / g:.1f}</b> pick and rolls per game as ball handler")
        add(pl, r.poss_iso / g >= 1.5, f"Ends <b>{r.poss_iso / g:.1f}</b> isolations per game")
        add(pl, (r.oreb_pg or 0) >= 1.5, f"<b>{r.oreb_pg:.1f}</b> offensive rebounds per game")
        add(pl, fga_pg >= 9, f"Takes <b>{fga_pg:.1f}</b> shots per game")
        if r.three_a >= 2 * mins["three"] and r.three_pct < 30:
            mi.append(f"Shoots <b>{r.three_pct:.0f}%</b> from three")
        if r.rim_a >= mins["three"] and r.rim_pct < 50:
            mi.append(f"Makes <b>{r.rim_pct:.0f}%</b> of his shots at the rim")
        if r.possessions >= 25 * (1 if scope == "season" else .3) and r.to_pct >= 17:
            mi.append(f"Turns the ball over on <b>{r.to_pct:.0f}%</b> of his possessions")
        if r.fga >= 15 * (1 if scope == "season" else .3) and r.three_a / max(r.fga, 1) < 0.15:
            mi.append(f"Takes <b>{100 * r.three_a / r.fga:.0f}%</b> of his shots from three")
        if r.drives >= mins["drive_side"]:
            ls = 100 * r.drive_l / r.drives
            if ls >= 65 or ls <= 35:
                nt.append(f"Drives to his {'left' if ls >= 65 else 'right'} on <b>{max(ls, 100 - ls):.0f}%</b> of his drives")
        chips = f'<span class="chip">{escape(r.role)}</span>' if r.role else '<span class="none">No role tag</span>'
        no = f'<span class="no">{escape(str(r.number))}</span>' if r.number else ""
        lines = ("".join(f'<div class="ln g"><i aria-label="Does">+</i><span>{x}</span></div>' for x in pl)
                 + "".join(f'<div class="ln r"><i aria-label="Below the others">&minus;</i><span>{x}</span></div>' for x in mi[:2])
                 + "".join(f'<div class="ln n"><i aria-label="Tendency">&bull;</i><span>{x}</span></div>' for x in nt))
        cards.append(f'<div class="pc"><div class="id"><span class="av" aria-hidden="true">{initials(r.name)}</span><div><h3>{no}{escape(r.name)}</h3>'
                     f'<div class="chips">{chips}</div></div></div><div class="lines">{lines}</div></div>')
    out.append(f'<div class="sec"><header><div class="eyebrow">Personnel</div><div class="h2">Their players</div><p class="note">Six highest-volume shooters. '
               f'+ what he does, &minus; where his numbers are low, &bull; a tendency. One number per line. Tag = Synergy offensive role (season).</p></header>'
               f'<div class="people">{"".join(cards)}</div></div>')

    # reference
    cap = f"Synergy, {comp}, {'season' if scope == 'season' else 'last 3 games'}, up to {d['last_date']} · {cfg['author']} · {cfg['date']}"
    zo, zr = d["zones"][scope]
    svg1 = zones_svg(zo, d["league_zone"], mins["zone"], f"{scope}-them", f"Shot zones of {OPPN}", cap)
    svg2 = zones_svg(zr, d["league_zone"], mins["zone"], f"{scope}-us", f"Shot zones allowed by {REFN}", cap)
    dl = lambda k, label=None: duel(label or ITEMS[k][0], fmt(ITEMS[k][1], B.val(opp, "off", k)), B.rank(opp, "off", k),
                                    fmt(ITEMS[k][1], B.val(ref, "def", k)), B.rank(ref, "def", k), n)
    threes = rot[rot.three_a >= 1].sort_values("three_a", ascending=False).head(5)
    trows = []
    for r in threes.itertuples():
        c = "bad" if r.three_pct >= 38 else "good" if r.three_pct < 30 else "mid"
        trows.append([escape(r.name), f"{r.three_a / r.gp:.1f}", f'<b class="val {c}">{r.three_pct:.0f}%</b>',
                      f'{fmt("{:.0f}%", r.cs3_pct)} <span class="of">{int(r.cs3_a)}</span>', fmt("{:.0f}%", div(r.jump_open, r.jump_tag, 100))])
    fold_shoot = (f'<details class="fold"><summary>Shooting: where they shoot, what we allow</summary><div class="in"><div class="cols2">'
                  f'<div class="panel"><h3>Where {escape(OPPN)} shoot</h3>{svg1}</div><div class="panel"><h3>What {escape(REFN)} allow</h3>{svg2}</div></div>'
                  f'<div><p class="note">Big number = FG% in the zone, small = share of all shots. Left and right as seen from center court facing the basket. '
                  f'Zones need {mins["zone"]} shots to be colored.</p><div class="key"><span><i class="k-hi"></i>FG% 3 points or more above the average</span>'
                  f'<span><i class="k-lo"></i>3 points or more below</span><span><i class="k-mid"></i>Within 3 points of the average</span>'
                  f'<span><i class="k-low"></i>Too few shots</span></div></div>'
                  f'<div class="cols2"><div class="panel">{dl("three_pct")}{dl("open_pct", "Catch-and-shoot jump shots open")}{dl("paint_pts_pg")}{dl("rim_pct")}</div>'
                  f'<div class="panel"><h3>Who shoots the three</h3><p class="note">Top 3PT volume. Red = 38% or more, green = under 30%. C&S = catch-and-shoot. Open = share of his '
                  f'catch-and-shoot jump shots tagged open.</p>{table(["Player", "3PA per game", "3PT%", "C&S 3PT%", "Open"], trows)}</div></div></div></details>')
    cov = []
    for k, lab in [("pnrbh", "Ball handler"), ("roll", "Roll man")]:
        lg = d["league_ppp"][k]
        def l(who, side, cls):
            share = B.val(opp if side == "off" else ref, side, f"per100_{k}")
            ppp = B.val(opp if side == "off" else ref, side, f"ppp_{k}")
            c = "bad" if ppp >= lg + .07 else "good" if ppp <= lg - .07 else "mid"
            return (f'<div class="l"><span class="who-l">{who}</span><span class="bar {cls}"><i style="width:{min(share, 100):.0f}%"></i></span>'
                    f'<span class="s">{share:.0f}%</span><b class="val {c}">{fmt("{:.2f}", ppp)}</b></div>')
        cov.append(f'<div class="cov"><div class="h">{lab}<span>average {lg:.2f}</span></div>{l("They use it", "off", "ink")}{l("We allow", "def", "")}</div>')
    hand = rot[rot.poss_pnrbh >= mins["pnr"]].sort_values("poss_pnrbh", ascending=False).head(4)
    rollm = P[P.poss_roll >= mins["roll"]].sort_values("poss_roll", ascending=False).head(4)
    prow = [[escape(r.name), f"{r.poss_pnrbh / r.gp:.1f}", fmt("{:.2f}", div(r.pts_pnrbh, r.poss_pnrbh)), "Ball handler"] for r in hand.itertuples()] + \
           [[escape(r.name), f"{r.poss_roll / r.gp:.1f}", fmt("{:.2f}", div(r.pts_roll, r.poss_roll)), "Roll man"] for r in rollm.itertuples()]
    fold_pnr = (f'<details class="fold"><summary>Pick and roll: by role</summary><div class="in"><p class="note">Synergy does not log the coverage (soft, show, '
                f'switch, over, under), so this is by role. Bar = share of possessions that end with a pick and roll by that role. Number = points per possession. '
                f'Red / green = 0.07 or more above / below the all-team average.</p><div class="cols2"><div class="panel">{"".join(cov)}</div>'
                f'<div class="panel">{dl("pnr_ppp")}<h3 style="margin-top:12px">Who runs it</h3>{table(["Player", "Per game", "Points per possession", "Role"], prow)}</div></div></div></details>')
    dr = rot[rot.drives >= mins["drive_side"] / 2].sort_values("drives", ascending=False).head(5)
    drows = [[escape(r.name), f"<b>{r.drives / r.gp:.1f}</b>", seg_hand(r.drive_l, r.drive_r) if r.drive_l + r.drive_r >= mins["drive_side"] / 2 else "–",
              f"{r.poss_iso / r.gp:.1f}", fmt("{:.2f}", div(r.pts_iso, r.poss_iso)) if r.poss_iso >= mins["iso"] else "–"] for r in dr.itertuples()]
    fold_dr = (f'<details class="fold"><summary>Drives and 1-on-1: who drives, to which side</summary><div class="in"><div class="panel"><h3>Who drives, and to which side</h3>'
               f'<p class="note">Dark = drives to the left, grey = to the right. Synergy tags a drive only when the play ends in a shot (his or after his pass); '
               f'it does not log whether the driver beats his defender.</p>'
               f'{table(["Player", "Shots after a drive per game", "Left / right", "Isolations per game", "Points per isolation"], drows)}</div>'
               f'<div class="panel">{dl("drive_per100")}{dl("ppp_iso")}</div></div></details>')
    ob = rot[rot.oreb_pg.fillna(0) > 0].sort_values("oreb_pg", ascending=False).head(5)
    mx = float(ob.oreb_pg.max()) if len(ob) else 1
    orows = [[escape(r.name), f'<span class="mt"><span class="mbar"><i style="width:{100 * r.oreb_pg / mx:.0f}%"></i></span><b class="val">{r.oreb_pg:.1f}</b></span>',
              f"{int(r.oreb)}"] for r in ob.itertuples()]
    fold_gl = (f'<details class="fold"><summary>Rebound and transition</summary><div class="in"><div class="cols2"><div class="panel">'
               f'{dl("oreb_pct")}{dl("putback_pts_pg", "Second-chance points per game (putbacks)")}{dl("trans_pts_pg")}</div>'
               f'<div class="panel"><h3>Offensive rebound: who to box out</h3><p class="note">Offensive rebounds per game ({d["oreb_note"][scope]}). '
               f'Synergy does not log box-outs or who crashes the glass.</p>{table(["Player", "Off. reb. per game", "Total"], orows)}</div></div></div></details>')
    allr = [(B.rank(opp, "off", k), k, "off") for k in OFF_SET] + [(B.rank(opp, "def", k), k, "def") for k in DEF_SET]
    allr = [x for x in allr if not math.isnan(x[0])]
    def lab(k, side):
        return (ITEMS[k][0] if side == "off" else DEF_LABEL.get(k, ITEMS[k][0]))
    well = "".join(it_rank(lab(k, s), fmt(ITEMS[k][1], B.val(opp, s, k)), r, n, "bad", "Offense" if s == "off" else "Defense")
                   for r, k, s in sorted(allr)[:5])
    poor = "".join(it_rank(lab(k, s), fmt(ITEMS[k][1], B.val(opp, s, k)), r, n, "good", "Offense" if s == "off" else "Defense")
                   for r, k, s in sorted(allr, key=lambda x: -x[0])[:5])
    style = "".join(it_rank(lb, fmt(f, B.val(opp, "off", k)), B.rank(opp, "off", k, style=True), n, "ink") for lb, k, f in STYLE)
    pn = []
    for r in rot.sort_values("fga", ascending=False).head(6).itertuples():
        g = max(r.gp, 1)
        s = max(r.fga, 1)
        rim, three = round(100 * r.rim_a / s), round(100 * r.three_a / s)
        mid = 100 - rim - three
        c = "bad" if r.three_a >= mins["three"] and r.three_pct >= 38 else "good" if r.three_a >= mins["three"] and r.three_pct < 30 else ""
        p3 = f"{r.three_pct:.0f}%" if r.three_a >= mins["three"] else "-"
        side = ""
        if r.drive_l + r.drive_r >= mins["drive_side"] / 2:
            l = round(100 * r.drive_l / (r.drive_l + r.drive_r))
            side = (f'<div class="split"><div class="lab"><span>Drives left {l}%</span><span>Right {100 - l}%</span></div><div class="seg" role="img" aria-label="Drive side">'
                    f'<i class="c-left" style="width:{l}%"></i><i class="c-right" style="width:{100 - l}%"></i></div></div>')
        pn.append(f'<div class="pc"><h3>{escape(r.name)}</h3><div class="big4"><div><b>{r.fga / g:.1f}</b><span>Shots</span></div>'
                  f'<div><b class="val {c}">{p3}</b><span>3PT% ({r.three_a / g:.1f})</span></div><div><b>{r.drives / g:.1f}</b><span>Drives</span></div>'
                  f'<div><b>{fmt("{:.1f}", r.oreb_pg)}</b><span>Off. reb.</span></div></div><div class="note">{fmt("{:.0f}", r.min_pg)} minutes per game · {int(r.gp)} games</div>'
                  f'<div class="split"><div class="lab"><span>Rim {rim}%</span><span>Mid {mid}%</span><span>Three {three}%</span></div><div class="seg" role="img" aria-label="Shot mix">'
                  f'<i class="c-rim" style="width:{rim}%"></i><i class="c-mid" style="width:{mid}%"></i><i class="c-three" style="width:{three}%"></i></div></div>{side}</div>')
    fold_all = (f'<details class="fold"><summary>All their numbers: offense, defense and style</summary><div class="in"><div class="cols2">'
                f'<div class="panel brief stop"><h3>What they do well</h3>{well}</div><div class="panel brief allow"><h3>What they do poorly</h3>{poor}</div></div>'
                f'<div class="panel"><h3>Style</h3><p class="note">Bar = rank among {n} teams, longest = most.</p>{style}</div>'
                f'<div class="stack-v"><h3>Player numbers</h3><div class="people">{"".join(pn)}</div></div></div></details>')
    out.append(f'<div class="sec"><header><div class="eyebrow">Reference</div><div class="h2">The detail</div></header><div class="folds">'
               f'{fold_shoot}{fold_pnr}{fold_dr}{fold_gl}{fold_all}</div></div>')
    out.append("</section>")
    return "".join(out)


# ── data ──────────────────────────────────────────────────────────────────────
def load(folder: Path) -> dict:
    cfg = json.loads((folder / "config.json").read_text(encoding="utf-8"))
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    opp, ref = cfg["opponent"]["team_id"], cfg["reference"]["team_id"]
    t = pd.read_csv(folder / "teams.csv")
    season = metrics(t)
    lg_off = t[t.side == "off"].fillna(0)
    league_ppp = {k: float(lg_off[f"pts_{k}"].sum() / lg_off[f"poss_{k}"].sum()) for k in PT}
    zones = pd.read_csv(folder / "zones.csv")
    zl = zones[zones.side == "off"].groupby("zone")[["fga", "fgm"]].sum()
    league_zone = {SYN12[z]: 100 * r.fgm / r.fga for z, r in zl.iterrows() if z in SYN12}
    league_zone["rim"] = 100 * lg_off.rim_m.sum() / lg_off.rim_a.sum()
    league_zone["paint"] = 100 * lg_off.paint_m.sum() / lg_off.paint_a.sum()

    shots = {k: pd.read_csv(folder / f) for k, f in [("opp_off", "opp_shots.csv"), ("opp_def", "opp_def_shots.csv"), ("ref_def", "ref_def_shots.csv")]}
    games = pd.read_csv(folder / "games.csv")
    games["date"] = games["date"].astype(str).str[:10]
    last_ids, last_lab = {}, {}
    for who in ("opp", "ref"):
        g = games[(games.who == who) & (games.side == "off")].sort_values("date").tail(3)
        last_ids[who] = list(g.game_id)
        last_lab[who] = [f"{r.date} {r.vs}" for r in g.sort_values("date", ascending=False).itertuples()]

    def last_row(who: str, tid: str, side: str) -> pd.Series:
        g = games[(games.who == who) & (games.side == side) & games.game_id.isin(last_ids[who])]
        num = g.select_dtypes("number").sum()
        row = {**num.to_dict(), "team_id": tid, "name": "", "side": side, "gp": len(g)}
        sk = {("opp", "off"): "opp_off", ("opp", "def"): "opp_def", ("ref", "def"): "ref_def"}.get((who, side))
        if sk:
            row.update(shot_aggregates(shots[sk][shots[sk].gameId.isin(last_ids[who])]))
        else:      # BC Roma offense is not shown on the opponent page: shot items left empty
            row.update({k: np.nan for k in ["shots", "rim_a", "rim_m", "paint_a", "paint_m", "mid_a", "mid_m", "three_a", "three_m", "cs3_a",
                                            "cs3_m", "jump_tag", "jump_open", "drive_fga", "drive_l", "drive_r"]})
        df = pd.DataFrame([row])
        for c in t.columns:
            if c not in df:
                df[c] = 0
        return metrics(df).iloc[0]

    own_last = {(opp, "off"): last_row("opp", opp, "off"), (opp, "def"): last_row("opp", opp, "def"),
                (ref, "off"): last_row("ref", ref, "off"), (ref, "def"): last_row("ref", ref, "def")}
    boards = {"season": Board(season, {}), "last": Board(season, own_last)}

    def zone_counts(df: pd.DataFrame) -> dict:
        c = {}
        for _, r in df.iterrows():
            z = zone12(r)
            c.setdefault(z, [0, 0])
            c[z][0] += 1
            c[z][1] += int(r["made"])
        return c
    zs = {"season": (zone_counts(shots["opp_off"]), zone_counts(shots["ref_def"])),
          "last": (zone_counts(shots["opp_off"][shots["opp_off"].gameId.isin(last_ids["opp"])]),
                   zone_counts(shots["ref_def"][shots["ref_def"].gameId.isin(last_ids["ref"])]))}

    box = pd.read_csv(folder / "box.csv")
    box = box[box["PLAYER"].notna() & ~box["PLAYER"].astype(str).str.strip().isin(["", "TEAM TOTAL"])].copy()
    box["name"] = box["PLAYER"].str.replace(r"^#\S+\s+", "", regex=True)
    box["number"] = box["PLAYER"].str.extract(r"^#(\S+)")[0]
    def find(name: str, col: str):
        hit = box[box.name == name]
        if not len(hit):
            hit = box[box.name.str.split().str[-1] == name.split()[-1]]
        return hit[col].iloc[0] if len(hit) else None

    def players(pl: pd.DataFrame, shots_df: pd.DataFrame, game_ids: list) -> pd.DataFrame:
        pl = pl.copy().fillna(0)
        for k in PT:
            for c in (f"poss_{k}", f"pts_{k}"):
                if c not in pl:
                    pl[c] = 0
        agg = {}
        for _, s in shots_df.iterrows():
            p = parse_shot(s)
            a = agg.setdefault(p["shooter"], {k: 0 for k in ["fga", "rim_a", "rim_m", "paint_a", "mid_a", "three_a", "three_m", "cs3_a", "cs3_m",
                                                               "jump_tag", "jump_open", "drive_l", "drive_r", "drive_s"]})
            a["fga"] += 1
            a[p["zone"] + "_a"] += 1
            if p["zone"] in ("rim", "three"):
                a[p["zone"] + "_m"] += p["made"]
            if p["cs"] and p["three"]:
                a["cs3_a"] += 1
                a["cs3_m"] += p["made"]
            if p["open"] or p["guarded"]:
                a["jump_tag"] += 1
                a["jump_open"] += p["open"]
            for who, dirn in p["drives"]:
                dd = agg.setdefault(who or p["shooter"], {k: 0 for k in a})
                dd["drive_l" if dirn == "Left" else "drive_r" if dirn == "Right" else "drive_s"] += 1
        def match(name):
            if name in agg:
                return agg[name]
            for k, v in agg.items():
                if k.split()[-1] == name.split()[-1]:
                    return v
            return {}
        rows = []
        for r in pl.to_dict("records"):
            a = match(r["name"])
            r.update({k: a.get(k, 0) for k in ["fga", "rim_a", "rim_m", "paint_a", "mid_a", "three_a", "three_m", "cs3_a", "cs3_m", "jump_tag",
                                                 "jump_open", "drive_l", "drive_r", "drive_s"]})
            rows.append(r)
        out = pd.DataFrame(rows)
        out["drives"] = out.drive_l + out.drive_r + out.drive_s
        out["three_pct"] = div(out.three_m, out.three_a, 100)
        out["cs3_pct"] = div(out.cs3_m, out.cs3_a, 100)
        out["rim_pct"] = div(out.rim_m, out.rim_a, 100)
        out["to_pct"] = div(out.turnover, out.possessions, 100)
        out["role"] = [str(find(x, "OFFENSIVE ROLE") or "").replace("nan", "") for x in out.name]
        out["number"] = [find(x, "number") or "" for x in out.name]
        bx = box_games[box_games.game_id.isin(game_ids) & (box_games.seconds > 0)]
        agg_b = bx.groupby("player").agg(oreb=("offReb", "sum"), sec=("seconds", "sum"), games=("game_id", "nunique"))
        def bget(name, col):
            if name in agg_b.index:
                return float(agg_b.loc[name, col])
            hit = [i for i in agg_b.index if i.split()[-1] == name.split()[-1]]
            return float(agg_b.loc[hit[0], col]) if hit else np.nan
        out["oreb"] = [bget(x, "oreb") for x in out.name]
        out["min_pg"] = [bget(x, "sec") / 60 / max(bget(x, "games"), 1) for x in out.name]
        out["oreb_pg"] = out.oreb / out.gp.clip(lower=1)
        return out[out.gp > 0]

    box_games = pd.read_csv(folder / "box_games.csv")
    all_opp = list(games[(games.who == "opp") & (games.side == "off")].game_id)
    pls = pd.read_csv(folder / "players.csv")
    pl_last = pd.read_csv(folder / "players_last.csv")
    players_by = {"season": players(pls, shots["opp_off"], all_opp),
                  "last": players(pl_last, shots["opp_off"][shots["opp_off"].gameId.isin(last_ids["opp"])], last_ids["opp"])}
    oreb_note = {"season": "Synergy game box scores, season", "last": "Synergy game box scores, last 3 games"}
    ref_def_by = {"season": shots["ref_def"], "last": shots["ref_def"][shots["ref_def"].gameId.isin(last_ids["ref"])]}
    defenders = {"season": pd.read_csv(folder / "defenders.csv"), "last": pd.read_csv(folder / "defenders_last.csv")}
    ref_numbers = {}
    if (folder / "ref_numbers.csv").exists():
        rn = pd.read_csv(folder / "ref_numbers.csv")
        ref_numbers = {r.name: str(r.number) for r in rn.itertuples()}
    return {"cfg": cfg, "meta": meta, "opp_id": opp, "ref_id": ref, "boards": boards, "league_ppp": league_ppp, "league_zone": league_zone,
            "zones": zs, "players": players_by, "ref_def_shots": ref_def_by, "defenders": defenders, "ref_numbers": ref_numbers, "oreb_note": oreb_note,
            "last_games": last_lab, "last_date": str(meta.get("last_game", ""))[:10]}


def page(folder: Path) -> tuple[Path, str]:
    d = load(folder)
    cfg = d["cfg"]
    n = d["boards"]["season"].n
    care = [f"Source: Synergy Sports (web app API), {cfg['competition']} games of the 2026-27 season up to {d['last_date']}, pulled {cfg['date']}. "
            f"Based solely on the data: no comments on plays.",
            f"Ranks compare the {n} teams of the {cfg['competition']}, each on all of its games in it.",
            "Rank bars: the longer the bar, the higher the team ranks on that item (1st = best value for that team; for possessions per game and style "
            "items, 1st = most). On this page a long red bar is an item where the opponent ranks high.",
            "Last 3 games: only the three most recent games of BC Roma and of the opponent in this competition, ranked against the season values of every "
            "other team. Minimum samples are cut to 30% of the season ones. Three games move a lot from one game to the next.",
            "Who defends it for us: points per possession on the possessions that end on the defender Synergy logs for the last action "
            f"(season: at least {MIN['season']['def']} possessions). It does not adjust for who they guarded or for help defense.",
            "At the rim = 2-point attempts within 6 ft. Points in the paint = field goals only. Open = catch-and-shoot jump shots Synergy tags as open "
            "(it tags open / guarded on catch-and-shoot jump shots only). Drives = shots whose Synergy description contains a drive.",
            f"Shot zones need {MIN['season']['zone']} shots to be colored ({MIN['last']['zone']} on the last 3 games). Synergy's 11 zones, with the paint split "
            "into the rim (6 ft) and the rest.",
            "Shot defenders: Synergy credits every shot allowed to one defender; catch-and-shoot jump shots left open and points per jump shot "
            "are counted on those shots (season: at least 10 and 15 shots). Player minutes and offensive rebounds come from Synergy's game box scores.",
            "Offensive rebound % = offensive rebounds / (offensive + opponent defensive rebounds), from Synergy's play-by-play stats.",
            "Not in Synergy (they come from tracking): box-outs, blow-bys, closeouts, contest levels, crashing the glass, passes per chance, "
            "pick-and-roll coverages. Those blocks of the SkillCorner page are left out or replaced (pick and roll by role)."]
    body = (f'<div class="kn2"><style>{CSS}</style>'
            f'<div class="topbar"><div class="note">{escape(cfg["opponent"]["name"])} · {escape(cfg["game"])} · Synergy · {escape(cfg["author"])}, {escape(cfg["date"])}</div>'
            f'<div class="scopes" role="group" aria-label="Games used"><button type="button" data-scope="season" aria-pressed="true">Season</button>'
            f'<button type="button" data-scope="last" aria-pressed="false">Last 3 games</button></div></div>'
            + build_scope("season", d) + build_scope("last", d)
            + '<div class="readcare"><div class="h2">Read with care</div><ul>' + "".join(f"<li>{escape(x)}</li>" for x in care) + "</ul></div>"
            + f"<script>{JS}</script></div>")
    body = re.sub(r"\n\s*\n", "\n", body)
    assert "{{" not in body and "==" not in body.replace("!==", ""), "text the site would expand"
    md = (f"title: Key numbers\ngenerated_by: notebooks/key_numbers.py\n\n"
          f"<!-- Generated by `python notebooks/key_numbers.py {folder.relative_to(ROOT).as_posix()}`: running it again overwrites this file. -->\n\n"
          f"# Key numbers\n\n{body}\n")
    return GAMES / cfg["game_date"] / "key_numbers.md", md


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("folder", type=Path)
    a = ap.parse_args()
    folder = (a.folder if a.folder.is_absolute() else Path.cwd() / a.folder).resolve()
    out, text = page(folder)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
