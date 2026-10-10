"""Key-player cards for a team: stats, shot map, shot habits, when they play, who feeds whom.

    python notebooks/players_report.py --team "BC Roma" --n 5 --out reports/
    python notebooks/players_report.py --team "Maxima Roma" --players Bilan Holiday Lemar

One PNG per player (<surname>.png) with four panels — shot chart, shot types / habits, minutes by quarter,
stat lines — plus `connections.png` (assist matrix: who passes to whom) and `habits_summary.png`
(one row per key player: assisted share, drives, threes, fast breaks, fouls drawn, turnover types).

Shot maps and habits come from the Legabasket play-by-play (LBA games only — they carry coordinates,
shot types and assist links). Stat lines use all competitions when the EuroCup file is present.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from game_report import game_clock, stints
from lba_style import (BLUE, DPI, GOLD, GREEN, LEAGUE, RED, SUP_KW, TEXT, TEXT2, TITLE_KW, ZONE_LABEL_POS,
                       assign_zone_arr, draw_half_court, shots_cm, style_axes, team_color)
from matchup_report import parse_eurocup, player_table

SHOT_TYPES = ["Tiro in sospensione", "Arresto e tiro", "Tiro in Step Back", "Tiro in fadeaway", "Da penetrazione",
              "Appoggio a canestro", "Schiacciata", "Alley-oop", "Gancio", "Giro e Tiro", "Tiro in corsa"]
SHOT_EN = {"Tiro in sospensione": "jump shot", "Arresto e tiro": "pull-up", "Tiro in Step Back": "step-back",
           "Tiro in fadeaway": "fadeaway", "Da penetrazione": "drive", "Appoggio a canestro": "layup",
           "Schiacciata": "dunk", "Alley-oop": "alley-oop", "Gancio": "hook", "Giro e Tiro": "turnaround", "Tiro in corsa": "runner"}
TOV_EN = {"Passaggio sbagliato": "bad pass", "Palleggio": "lost dribble", "Doppio Palleggio": "double dribble", "Passi": "travel",
          "Fuori dal campo": "out of bounds", "Infrazione di campo": "backcourt", "3 secondi": "3 seconds", "5 secondi": "5 seconds",
          "Interferenza a canestro in attacco": "off. goaltending", "Altro": "other", "Altro ": "other"}


# ── per-player event tables ─────────────────────────────────────────────────────
def player_events(pbp: pd.DataFrame, team: str, surname: str) -> dict:
    """All the habit numbers for one player from the LBA play-by-play."""
    tp = pbp[pbp.team == team]
    me = tp[tp.player_surname.str.upper() == surname.upper()]
    shots = shots_cm(me)
    makes = me[me.event.isin(["2 punti segnato", "3 punti segnato"])]
    assists_on_me = tp[(tp.event == "Assist") & tp.linked_seq.isin(makes.seq)]
    my_assists = tp[(tp.event == "Assist") & (tp.player_surname.str.upper() == surname.upper())]
    scored = tp[tp.seq.isin(my_assists.linked_seq)]
    fouls_drawn = me[me.event == "Fallo Subito"]
    fouls_drawn_shooting = tp[(tp.event == "Fallo commesso") & (tp.qualifier_1 == "tiro")]  # by opponents, see below
    opp = pbp[(pbp.game_id.isin(tp.game_id.unique())) & (pbp.team != team)]
    shooting_fouls_on_me = opp[(opp.event == "Fallo commesso") & (opp.qualifier_1 == "tiro")]
    shooting_fouls_on_me = me[(me.event == "Fallo Subito") & me.linked_seq.isin(shooting_fouls_on_me.seq)]
    tov = me[me.event == "Palla persa"]
    return dict(
        shots=shots, n_games=me.game_id.nunique(),
        assisted=len(assists_on_me), makes=len(makes),
        assisted_by=assists_on_me.player_surname.str.title().value_counts(),
        assists_to=scored.player_surname.str.title().value_counts(),
        fouls_drawn=len(fouls_drawn), shooting_fouls_drawn=len(shooting_fouls_on_me),
        tov_types=tov.qualifier_1.map(lambda q: TOV_EN.get(q, q)).value_counts(),
        fastbreak=int((shots.qualifier_2 == "contropiede").sum()),
        fastbreak_made=int(((shots.qualifier_2 == "contropiede") & shots.made).sum()),
        by_period=shots.groupby("period").agg(att=("made", "size"), made=("made", "sum")),
        steals=int((me.event == "Palla recuperata").sum()), blocks=int((me.event == "Stoppata").sum()),
        oreb=int((me.event == "Rimbalzo offensivo").sum()), dreb=int((me.event == "Rimbalzo difensivo").sum()),
    )


def minutes_by_quarter(pbp, box, team, surname) -> tuple[np.ndarray, np.ndarray]:
    """Seconds on court in each quarter (summed over games) and the team's +/- while on court per quarter."""
    secs, pm = np.zeros(4), np.zeros(4)
    for gid in box[(box.team == team) & (box.row_type == "total")].game_id.unique():
        gp = pbp[pbp.game_id == gid].sort_values("seq")
        gb = box[box.game_id == gid]
        if gb.empty:
            continue
        p_st, _ = stints(gp, gb, team)
        mine = p_st[p_st.player.str.upper() == surname.upper()]
        gp2 = gp.copy(); gp2["t"] = game_clock(gp2)
        home = bool(gb[gb.team == team].home.iloc[0])
        gp2["margin"] = ((gp2.score_home - gp2.score_away) * (1 if home else -1)).ffill().fillna(0)
        for _, s in mine.iterrows():
            for q in range(4):
                a, b = max(s.start, q * 600), min(s.end, (q + 1) * 600)
                if b > a:
                    secs[q] += b - a
                    m0 = gp2.loc[gp2.t <= a, "margin"].iloc[-1] if (gp2.t <= a).any() else 0
                    m1 = gp2.loc[gp2.t <= b, "margin"].iloc[-1]
                    pm[q] += m1 - m0
    return secs, pm


# ── figures ─────────────────────────────────────────────────────────────────────
def player_card(pbp, box, team, surname, pt_row, ev, out, color):
    fill, edge = color
    fig = plt.figure(figsize=(16, 9.5))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.3, 1, 1], height_ratios=[1.3, 1])
    ax_court = fig.add_subplot(gs[:, 0]); ax_types = fig.add_subplot(gs[0, 1]); ax_q = fig.add_subplot(gs[0, 2])
    ax_txt = fig.add_subplot(gs[1, 1:]); ax_txt.axis("off")

    # 1. shot chart with zone FG% labels
    s = ev["shots"]
    draw_half_court(ax_court)
    ax_court.scatter(s[~s.made].cx, s[~s.made].cy, s=70, facecolors="none", edgecolors=RED, linewidths=1.4, zorder=3, label=f"missed ({int((~s.made).sum())})")
    ax_court.scatter(s[s.made].cx, s[s.made].cy, s=70, c=fill, edgecolors=edge, linewidths=0.8, zorder=4, label=f"made ({int(s.made.sum())})")
    zs = s.groupby("zone").agg(att=("made", "size"), mk=("made", "sum"))
    for z, (cx, cy) in ZONE_LABEL_POS.items():
        if z in zs.index:
            ax_court.text(cx, cy + 90, f"{int(zs.loc[z].mk)}/{int(zs.loc[z].att)}", ha="center", fontsize=8, color=TEXT2, zorder=5,
                          bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.7))
    two, three = s[s.pts == 2], s[s.pts == 3]
    ax_court.set_title(f"Shot chart (LBA only, {ev['n_games']} games)\n2pt {int(two.made.sum())}/{len(two)} · 3pt {int(three.made.sum())}/{len(three)}", **TITLE_KW)
    ax_court.legend(loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=2, fontsize=9)

    # 2. shot types
    st = s.groupby("qualifier_1").agg(att=("made", "size"), mk=("made", "sum")).reindex(SHOT_TYPES).dropna()
    st = st[st.att > 0].sort_values("att", ascending=True)
    y = np.arange(len(st))
    ax_types.barh(y, st.att, color=LEAGUE, height=0.6, label="attempts")
    ax_types.barh(y, st.mk, color=fill, edgecolor=edge, linewidth=0.6, height=0.6, label="made")
    for yi, (a, m) in enumerate(zip(st.att, st.mk)):
        ax_types.text(a + 0.3, yi, f"{int(m)}/{int(a)}", va="center", fontsize=8.5, color=TEXT2)
    ax_types.set_yticks(y); ax_types.set_yticklabels([SHOT_EN.get(k, k) for k in st.index], fontsize=9)
    ax_types.set_xlim(0, (st.att.max() if len(st) else 1) * 1.3)
    ast_share = 100 * ev["assisted"] / ev["makes"] if ev["makes"] else 0
    ax_types.set_title(f"Shot types (LBA only, {ev['n_games']} games)\n{ast_share:.0f}% of makes assisted · fast-break shots {ev['fastbreak_made']}/{ev['fastbreak']}", **TITLE_KW)
    ax_types.legend(fontsize=8, loc="lower right"); style_axes(ax_types, "x")

    # 3. minutes by quarter + plus/minus
    secs, pm = minutes_by_quarter(pbp, box, team, surname)
    mpq = secs / 60 / max(ev["n_games"], 1)
    x = np.arange(4)
    ax_q.bar(x, mpq, 0.6, color=fill, edgecolor=edge, linewidth=0.6)
    for xi, (m, p) in enumerate(zip(mpq, pm)):
        ax_q.text(xi, m + 0.2, f"{m:.1f}'\n{p:+.0f}", ha="center", fontsize=8.5, color=GREEN if p > 0 else RED if p < 0 else TEXT2, fontweight="bold")
    bp = ev["by_period"].reindex([1, 2, 3, 4]).fillna(0)
    ax_q.set_xticks(x); ax_q.set_xticklabels([f"Q{i}\n{int(a)} FGA" for i, a in zip(range(1, 5), bp.att)])
    ax_q.set_ylim(0, 11.5); ax_q.set_ylabel("minutes per game")
    ax_q.set_title(f"When he plays (LBA only, {ev['n_games']} games)\nminutes per quarter · team +/- while on court", **TITLE_KW); style_axes(ax_q, "y")

    # 4. stat lines
    r = pt_row
    per40 = 40 / r.MPG if r.MPG else 0
    lines = [
        f"LBA+EC ({int(r.GP)} games, {int(r.GS)} starts): {r.MPG:.1f} min · {r.PPG:.1f} pts · {r.RPG:.1f} reb · {r.APG:.1f} ast · PIR {r.PIR:.1f} · TS {r['TS%']:.0f}% · 3P {r['3P']} · +/- {r.pm:+.0f}",
        f"Per 40 min (LBA+EC): {r.PPG * per40:.1f} pts · {r.RPG * per40:.1f} reb · {r.APG * per40:.1f} ast · {r.tov / r.GP * per40:.1f} tov",
        f"LBA only ({ev['n_games']} games): {ev['fouls_drawn']} fouls drawn ({ev['shooting_fouls_drawn']} shooting) · {ev['steals']} stl · {ev['blocks']} blk · {ev['oreb']} oreb / {ev['dreb']} dreb",
        "Turnovers (LBA only): " + (", ".join(f"{int(v)} {k}" for k, v in ev["tov_types"].items()) if len(ev["tov_types"]) else "none"),
        "Assisted by (LBA only): " + (", ".join(f"{k} ({int(v)})" for k, v in ev["assisted_by"].head(4).items()) if len(ev["assisted_by"]) else "—"),
        "Assists to (LBA only): " + (", ".join(f"{k} ({int(v)})" for k, v in ev["assists_to"].head(4).items()) if len(ev["assists_to"]) else "—"),
    ]
    ax_txt.text(0, 0.95, "\n\n".join(lines), va="top", ha="left", fontsize=10.5, color=TEXT, wrap=True, transform=ax_txt.transAxes)
    fig.suptitle(f"{team} — {surname.title()}", **SUP_KW)
    fig.savefig(out / f"{surname.lower()}.png", dpi=DPI, bbox_inches="tight"); plt.close(fig)


def fig_connections(pbp, team, players, out, color):
    tp = pbp[pbp.team == team]
    makes = tp[tp.event.isin(["2 punti segnato", "3 punti segnato"])][["seq", "player_surname"]].rename(columns={"player_surname": "scorer"})
    ast = tp[tp.event == "Assist"][["linked_seq", "player_surname"]].rename(columns={"player_surname": "passer"})
    pairs = ast.merge(makes, left_on="linked_seq", right_on="seq")
    pairs["passer"] = pairs.passer.str.title(); pairs["scorer"] = pairs.scorer.str.title()
    names = [p.title() for p in players]
    extra = [n for n in pd.unique(pd.concat([pairs.passer, pairs.scorer])) if n not in names]
    order = names + sorted(extra)
    mat = pairs.groupby(["passer", "scorer"]).size().unstack(fill_value=0).reindex(index=order, columns=order, fill_value=0)
    fig, ax = plt.subplots(figsize=(9, 8))
    im = ax.imshow(mat.values, cmap="YlOrBr", vmin=0)
    ax.set_xticks(range(len(order))); ax.set_xticklabels(order, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(order))); ax.set_yticklabels(order, fontsize=9)
    for i in range(len(order)):
        for j in range(len(order)):
            v = mat.values[i, j]
            if v:
                ax.text(j, i, int(v), ha="center", va="center", fontsize=9, color="white" if v >= mat.values.max() * 0.6 else TEXT)
    ax.set_xlabel("scorer"); ax.set_ylabel("passer")
    tot_ast = int(mat.values.sum()); tot_mk = len(makes)
    ax.set_title(f"{team} — who feeds whom (LBA only): {tot_ast} assists on {tot_mk} field goals ({100 * tot_ast / tot_mk:.0f}% assisted)", **TITLE_KW)
    ax.tick_params(length=0)
    fig.savefig(out / "connections.png", dpi=DPI, bbox_inches="tight"); plt.close(fig)
    return mat


def fig_habits_summary(evs: dict, pts: pd.DataFrame, team, out, color):
    fill, edge = color
    rows = []
    for name, ev in evs.items():
        s = ev["shots"]; n = len(s)
        rows.append(dict(player=name.title(),
                         assisted=100 * ev["assisted"] / ev["makes"] if ev["makes"] else 0,
                         drives=100 * s.qualifier_1.isin(["Da penetrazione", "Appoggio a canestro", "Schiacciata", "Alley-oop"]).sum() / n if n else 0,
                         jumpers=100 * s.qualifier_1.isin(["Tiro in sospensione", "Arresto e tiro", "Tiro in Step Back", "Tiro in fadeaway"]).sum() / n if n else 0,
                         threes=100 * (s.pts == 3).sum() / n if n else 0,
                         left=100 * (s.cx < -100).sum() / n if n else 0, right=100 * (s.cx > 100).sum() / n if n else 0,
                         fouls=ev["fouls_drawn"] / max(ev["n_games"], 1), fga=n / max(ev["n_games"], 1)))
    d = pd.DataFrame(rows)
    cols = [("assisted", "% of makes assisted"), ("drives", "% of FGA at the rim\n(drive/layup/dunk)"), ("jumpers", "% of FGA jump shots"),
            ("threes", "% of FGA from three"), ("left", "% of FGA left of the key\n(as drawn)"), ("right", "% of FGA right of the key\n(as drawn)"), ("fouls", "fouls drawn / game"), ("fga", "FGA / game")]
    fig, axes = plt.subplots(1, len(cols), figsize=(2.3 * len(cols), 0.55 * len(d) + 2.2), sharey=True)
    y = np.arange(len(d))
    for ax, (c, lab) in zip(axes, cols):
        ax.barh(y, d[c], color=fill, edgecolor=edge, linewidth=0.6, height=0.6)
        for yi, v in zip(y, d[c]):
            ax.text(v + d[c].max() * 0.03, yi, f"{v:.0f}" if c not in ("fouls", "fga") else f"{v:.1f}", va="center", fontsize=8.5, color=TEXT2)
        ax.set_title(lab, fontsize=9.5, color=TEXT, fontweight="bold"); ax.set_xlim(0, d[c].max() * 1.35 + 1e-9); style_axes(ax, "x")
    axes[0].set_yticks(y); axes[0].set_yticklabels(d.player, fontsize=9.5); axes[0].invert_yaxis()
    fig.suptitle(f"{team} — on-court habits of the key players (LBA only)", **SUP_KW)
    fig.savefig(out / "habits_summary.png", dpi=DPI, bbox_inches="tight"); plt.close(fig)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", required=True)
    ap.add_argument("--players", nargs="*", help="surnames; default: top --n by PIR with >= 15 min per game")
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--data", default=str(Path(__file__).resolve().parent.parent / "data"))
    ap.add_argument("--eurocup", default=None); ap.add_argument("--no-eurocup", action="store_true")
    ap.add_argument("--out", default="reports")
    a = ap.parse_args()
    data = Path(a.data)
    out = Path(a.out) / f"players_{a.team.replace(' ', '_')}"; out.mkdir(parents=True, exist_ok=True)
    games = pd.read_csv(data / "games.csv")
    box = pd.read_csv(data / "box_scores.csv"); box["competition"] = "LBA"
    box["date"] = box.match_datetime.str[:10]
    pbp = pd.read_csv(data / "pbp.csv")
    ec_path = Path(a.eurocup) if a.eurocup else data / "eurocup_2026_raw.txt"
    box_all = box
    if not a.no_eurocup and ec_path.exists():
        ec_box, _ = parse_eurocup(ec_path)
        box_all = pd.concat([box, ec_box[ec_box.team == a.team]], ignore_index=True)
    pt = player_table(box_all, a.team).set_index("player_surname")
    if a.players:
        players = [p.upper() for p in a.players]
    else:
        players = pt[pt.MPG >= 15].sort_values("PIR", ascending=False).head(a.n).index.tolist()
    color = team_color(a.team)
    evs = {}
    for sn in players:
        if sn not in pt.index:
            print(f"skip {sn}: not in box scores"); continue
        ev = player_events(pbp, a.team, sn); evs[sn] = ev
        player_card(pbp, box, a.team, sn, pt.loc[sn], ev, out, color)
        print(f"{sn.title()}: {ev['n_games']} LBA games, {len(ev['shots'])} FGA, {ev['assisted']}/{ev['makes']} makes assisted, "
              f"{ev['fouls_drawn']} fouls drawn, tov {dict(ev['tov_types'])}")
    mat = fig_connections(pbp, a.team, players, out, color)
    hab = fig_habits_summary(evs, pt, a.team, out, color)
    print(hab.round(1).to_string(index=False)); print(mat.to_string()); print(f"figures in {out}")


if __name__ == "__main__":
    main()
