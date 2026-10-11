"""Clutch report: what each player did in the last five minutes of close games (margin ≤ 5), LBA + EuroCup.

    python notebooks/clutch_report.py --teams "BC Roma" "Maxima Roma" --out reports/<matchup folder> --before 2026-10-11

Definition (NBA convention): an event is "clutch" when it happens in the last 5:00 of the 4th quarter or
overtime with the score within 5 points at that moment. Blowouts contribute nothing, so the sample is
only as big as the number of close finishes played so far — the chart says how many.

LBA events come from the legabasket.it play-by-play (data/pbp.csv); EuroCup events from
data/eurocup_2026_q4_pbp.txt, a 4th-quarter extract of live.euroleague.net/api/PlayByPlay
(see notebooks/eurocup_fetch.md). League reference = the other LBA teams' clutch events in the same rounds.

Output: 11_clutch.png (one panel per team: clutch points per player with the shooting line, assists,
turnovers) and a printed summary.
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd

import lba_style
from lba_style import LEAGUE, RED, SUP_KW, TEXT, TEXT2, TITLE_KW, save_fig, style_axes, team_color

CLUTCH_SEC, CLUTCH_MARGIN = 300, 5
EC_CODE = {"BCR": "BC Roma", "MRO": "Maxima Roma"}
EC_DATES = {6: "2026-09-30", 16: "2026-09-30", 24: "2026-10-06", 29: "2026-10-07"}
EC_NAME_FIX = {"BONACINI": "Bonaccini"}


def _clock(c: str) -> int:
    m, s = str(c).split(":")
    return int(m) * 60 + int(s)


# ── LBA ─────────────────────────────────────────────────────────────────────────
def lba_events(pbp: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """One row per clutch event: game, label, team, opp, player, kind (pts2m/pts2a/pts3m/pts3a/ftm/fta/ast/tov/stl/reb/fd)."""
    p = pbp.copy()
    p["rem"] = p.clock.map(_clock)
    p = p.sort_values(["game_id", "seq"])
    post = (p.score_home - p.score_away).abs()
    p["margin"] = post.groupby(p.game_id).shift(1).fillna(post)     # margin BEFORE the event (NBA convention)
    p = p[(p.period >= 4) & (p.rem <= CLUTCH_SEC) & (p.margin <= CLUTCH_MARGIN)]
    p = p.merge(games[["game_id", "home_team", "away_team", "home_score", "away_score", "match_datetime"]], on="game_id")
    kinds = {"2 punti segnato": "fg2m", "2 punti sbagliato": "fg2a", "3 punti segnato": "fg3m", "3 punti sbagliato": "fg3a",
             "Tiro libero segnato": "ftm", "Tiro libero sbagliato": "fta", "Assist": "ast", "Palla persa": "tov",
             "Palla recuperata": "stl", "Rimbalzo difensivo": "reb", "Rimbalzo offensivo": "reb", "Fallo Subito": "fd"}
    p = p[p.event.isin(kinds)].copy()
    p["kind"] = p.event.map(kinds)
    p["player"] = p.player_surname.fillna("").str.title()
    p["opp"] = np.where(p.team == p.home_team, p.away_team, p.home_team)
    p["label"] = p.apply(lambda r: f"{r.home_team} {r.home_score}–{r.away_score} {r.away_team} (LBA)", axis=1)
    p["competition"] = "LBA"
    return p[["game_id", "label", "competition", "team", "opp", "player", "kind", "rem"]]


# ── EuroCup ─────────────────────────────────────────────────────────────────────
def ec_events(path: Path) -> pd.DataFrame:
    rows, game, teams, prev_margin = [], None, {}, {}
    kinds = {"2FGM": "fg2m", "2FGA": "fg2a", "3FGM": "fg3m", "3FGA": "fg3a", "FTM": "ftm", "FTA": "fta", "AS": "ast",
             "TO": "tov", "ST": "stl", "D": "reb", "O": "reb", "RV": "fd"}
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.startswith("#GAME"):
            toks = ln.split()
            game = int(toks[1]); teams = dict(t.split("=", 1) for t in " ".join(toks[2:]).split(" ", 1)[0:1])
            # header is "#GAME 16 BAH=Bahcesehir College Istanbul BCR=Roma Basketball": parse codes manually
            rest = ln.split(" ", 2)[2]
            codes = [t for t in rest.replace("=", " = ").split() if t.isupper() and len(t) == 3 and t not in ("THE",)]
            teams = {}
            parts = rest.split()
            cur = None
            for t in parts:
                if "=" in t:
                    cur, nm = t.split("=", 1); teams[cur] = nm
                elif cur:
                    teams[cur] += " " + t
            order = list(teams)
            continue
        if not ln.strip() or ln.startswith("#"):
            continue
        per, clk, code, player, pt, a, b = ln.split("|")
        if pt not in kinds or not code:
            prev_margin[game] = abs(int(a) - int(b)); continue
        a, b = int(a), int(b)
        margin_pre = prev_margin.get(game, abs(a - b)); prev_margin[game] = abs(a - b)
        rem = _clock(clk)
        if rem > CLUTCH_SEC or margin_pre > CLUTCH_MARGIN:
            continue
        team = EC_CODE.get(code, teams[code].title())
        opp_code = [c for c in order if c != code][0]
        opp = EC_CODE.get(opp_code, teams[opp_code].title())
        surname = player.split(",")[0].replace(" JR.", "").replace(" JR", "").replace(" III", "").strip().title()
        surname = EC_NAME_FIX.get(surname.upper(), surname)
        nm = lambda c: EC_CODE.get(c, teams[c].title())
        rows.append(dict(game_id=f"EC{game}", label=f"{nm(order[0])} {{A}}–{{B}} {nm(order[1])} (EuroCup)",
                         competition="EC", team=team, opp=opp, player=surname, kind=kinds[pt], rem=rem, _game=game))
    df = pd.DataFrame(rows)
    return df


def final_scores_ec(path: Path) -> dict:
    """Final score per EC game from the last forward-filled row."""
    out, game = {}, None
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.startswith("#GAME"):
            game = int(ln.split()[1]); continue
        if ln.strip() and not ln.startswith("#"):
            f = ln.split("|"); out[game] = (int(f[5]), int(f[6]))
    return out


# ── aggregation ─────────────────────────────────────────────────────────────────
def per_player(ev: pd.DataFrame) -> pd.DataFrame:
    k = ev.groupby(["team", "player", "kind"]).size().unstack(fill_value=0)
    for c in ["fg2m", "fg2a", "fg3m", "fg3a", "ftm", "fta", "ast", "tov", "stl", "reb", "fd"]:
        if c not in k: k[c] = 0
    k["pts"] = 2 * k.fg2m + 3 * k.fg3m + k.ftm
    k["fgm"], k["fga"] = k.fg2m + k.fg3m, k.fg2m + k.fg2a + k.fg3m + k.fg3a
    k["fta_all"] = k.ftm + k.fta
    k["events"] = ev.groupby(["team", "player"]).size()
    return k.reset_index()


def per_team(ev: pd.DataFrame) -> pd.DataFrame:
    k = ev.groupby(["team", "kind"]).size().unstack(fill_value=0)
    for c in ["fg2m", "fg2a", "fg3m", "fg3a", "ftm", "fta", "ast", "tov"]:
        if c not in k: k[c] = 0
    k["pts"] = 2 * k.fg2m + 3 * k.fg3m + k.ftm
    k["fgm"], k["fga"] = k.fg2m + k.fg3m, k.fg2m + k.fg2a + k.fg3m + k.fg3a
    k["games"] = ev.groupby("team").game_id.nunique()
    return k


# ── figure ──────────────────────────────────────────────────────────────────────
def plot(teams: list[str], ev: pd.DataFrame, league_ev: pd.DataFrame, out: Path) -> None:
    pp = per_player(ev); tt = per_team(ev)
    lg = per_team(league_ev)
    lg_fg = lg.fgm.sum() / max(lg.fga.sum(), 1); lg_tov_per_game = lg.tov.sum() / max(lg.games.sum(), 1)
    lg_pts_per_game = lg.pts.sum() / max(lg.games.sum(), 1)
    fig, axes = plt.subplots(1, len(teams), figsize=(6.2 * len(teams), 6.4), sharex=True)
    axes = np.atleast_1d(axes)
    own = pp[pp.team.isin(teams)]; xmax = (max(int(own.pts.max()) if len(own) else 0, 5) + 2) * 1.7
    for ax, team in zip(axes, teams):
        fill, edge = team_color(team)
        d = pp[(pp.team == team) & (pp.player != "")].sort_values(["pts", "events"], ascending=[False, False])
        d = d[(d.pts > 0) | (d.fga > 0) | (d.tov > 0) | (d.ast > 0)]
        n_sit = ev[ev.team == team].game_id.nunique()
        style_axes(ax, grid="x")
        if d.empty:
            ax.text(0.5, 0.5, "no clutch minutes yet\n(no game within 5 points in the last 5:00)", ha="center", va="center",
                    transform=ax.transAxes, color=TEXT2, fontsize=11)
            ax.set_yticks([]); ax.set_title(f"{team} — 0 close finishes", **TITLE_KW); continue
        y = np.arange(len(d))[::-1]
        ax.barh(y, d.pts, color=fill, edgecolor=edge, linewidth=0.6, height=0.62, zorder=2)
        for yi, (_, r) in zip(y, d.iterrows()):
            line = f"FG {r.fgm}/{r.fga}"
            if r.fta_all: line += f" · FT {r.ftm}/{r.fta_all}"
            if r.ast: line += f" · {r.ast} ast"
            if r.tov: line += f" · {r.tov} TO"
            if r.fd: line += f" · {r.fd} FD"
            ax.text(r.pts + 0.25, yi, line, va="center", ha="left", fontsize=8.5, color=RED if r.tov >= 2 else TEXT2)
        ax.set_yticks(y); ax.set_yticklabels(d.player, fontsize=10)
        ax.set_xlim(0, xmax); ax.set_xlabel("points in clutch time"); ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        t = tt.loc[team] if team in tt.index else None
        opp_pts = per_team(ev[ev.opp == team]).pts.sum() if (ev.opp == team).any() else 0
        sub = (f"{n_sit} close finish{'es' if n_sit != 1 else ''} · team {int(t.pts)} pts, opponents {int(opp_pts)} · "
               f"FG {int(t.fgm)}/{int(t.fga)} · {int(t.tov)} TO") if t is not None else ""
        ax.set_title(f"{team}\n{sub}", **{**TITLE_KW, "fontsize": 11.5})
    labels = sorted(ev.label.unique())
    fig.suptitle("Clutch time: last 5:00 of the 4th quarter / OT, score within 5 points", **SUP_KW)
    foot = (f"Games with clutch minutes: " + "; ".join(labels) + "\n"
            f"League reference (other LBA teams, same rounds): {lg_pts_per_game:.0f} pts and {lg_tov_per_game:.1f} TO per close finish, "
            f"FG {lg_fg:.0%}. FD = fouls drawn. Red text = 2+ turnovers. Data: LBA play-by-play + EuroCup play-by-play.")
    fig.text(0.01, -0.075, foot, ha="left", va="top", fontsize=8, color=TEXT2, wrap=True)
    save_fig(fig, out / "11_clutch.png")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--teams", nargs="+", default=["BC Roma", "Maxima Roma"])
    ap.add_argument("--data", default="data")
    ap.add_argument("--eurocup", default=None, help="EC 4th-quarter pbp extract (default data/eurocup_2026_q4_pbp.txt)")
    ap.add_argument("--no-eurocup", action="store_true")
    ap.add_argument("--out", default="reports")
    ap.add_argument("--before", default=None, help="YYYY-MM-DD: use only games played before this date")
    a = ap.parse_args()
    data = Path(a.data)
    pbp = pd.read_csv(data / "pbp.csv"); games = pd.read_csv(data / "games.csv")
    games["date"] = games.match_datetime.str[:10]
    if a.before:
        lba_style.STAMP_NOTE = f"games before {date.fromisoformat(a.before):%d %b %Y} (pre-match snapshot)"
        games = games[games.date < a.before]; pbp = pbp[pbp.game_id.isin(games.game_id)]
    ev = lba_events(pbp, games)
    ec_path = Path(a.eurocup) if a.eurocup else data / "eurocup_2026_q4_pbp.txt"
    if not a.no_eurocup and ec_path.exists():
        ec = ec_events(ec_path)
        if a.before:
            ec = ec[ec._game.map(EC_DATES) < a.before]
        fs = final_scores_ec(ec_path)
        ec["label"] = ec.apply(lambda r: r.label.replace("{A}", str(fs[r._game][0])).replace("{B}", str(fs[r._game][1])), axis=1)
        ev_all = pd.concat([ev, ec.drop(columns="_game")], ignore_index=True)
    else:
        ev_all = ev
    mine = ev_all[ev_all.team.isin(a.teams) | ev_all.opp.isin(a.teams)]
    league = ev[~ev.team.isin(a.teams)]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    plot(a.teams, mine, league, out)
    pd.set_option("display.width", 200)
    print(per_team(mine[mine.team.isin(a.teams)]))
    print(per_player(mine[mine.team.isin(a.teams)]).sort_values(["team", "pts"], ascending=[True, False])
          [["team", "player", "pts", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta_all", "ast", "tov", "fd"]].to_string())
    print("league:", per_team(league)[["pts", "fgm", "fga", "tov", "games"]].sum().to_dict())
    print("->", out / "11_clutch.png")


if __name__ == "__main__":
    main()
