"""LBA results so far and current standings, for the top of every matchup page.

    python notebooks/standings.py --before 2026-10-17 --team "BC Roma" --team "Umana Reyer Venezia" \
        --out reports/matchup_BC_Roma_vs_Umana_Reyer_Venezia_before_2026-10-17

Writes into --out:
  00_standings.png   standings bar chart (points, W-L, point difference), BC Roma in gold, the
                     other --team in its colour, everyone else in grey
  standings.md       markdown section "LBA so far: results and standings" (results by round +
                     standings table) to paste under the intro of the page README

matchup_report.py calls the same functions, so every new report folder gets both files.

Ranking: 2 points per win. Teams level on points are split with the head-to-head games among them
(wins, then fewest losses, re-applied to any sub-group still level), then overall point difference,
then points scored. Early in the season most tied teams have not met yet, so the order inside a
points tie is provisional and newspapers sometimes list it differently.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from lba_style import GREEN, LEAGUE, RED, SUP_KW, TEXT, TEXT2, TITLE_KW, save_fig, style_axes, team_color

SHORT = {
    "Acqua S.Bernardo Cantù": "Cantù", "APU Old Wild West Udine": "Udine", "Armani Olimpia Milano": "Milano",
    "BC Roma": "BC Roma", "Bertram Derthona Tortona": "Tortona", "Dolomiti Energia Trentino": "Trento",
    "Longobardi Scafati Basket": "Scafati", "Maxima Roma": "Maxima Roma", "Napoli Basketball": "Napoli",
    "Nutribullet Treviso Basket": "Treviso", "Openjobmetis Varese": "Varese", "Pallacanestro Trieste": "Trieste",
    "Tezenis Verona": "Verona", "Umana Reyer Venezia": "Venezia", "UNA Hotels Reggio Emilia": "Reggio Emilia",
    "Virtus Costa Bologna": "Virtus Bologna",
    # EuroCup (names as in the EuroLeague results feed)
    "Bahcesehir College Istanbul": "Bahcesehir", "Balkan Botevgrad": "Botevgrad", "Bosna Bh Telecom Sarajevo": "Bosna",
    "Kids&Us Manresa": "Manresa", "Lietkabelis Panevezys": "Lietkabelis", "Paok Thessaloniki": "PAOK", "Ratiopharm Ulm": "Ulm",
}


def short(team: str) -> str:
    return SHORT.get(team, team)


def finished(games: pd.DataFrame, before: str | None = None) -> pd.DataFrame:
    g = games[games.game_status.astype(str) == "2"].copy()
    g["date"] = g.match_datetime.str[:10]
    if before:
        g = g[g.date < before]
    return g.sort_values(["round", "match_datetime"])


def _long(g: pd.DataFrame) -> pd.DataFrame:
    h = pd.DataFrame({"team": g.home_team, "opp": g.away_team, "pf": g.home_score, "pa": g.away_score, "date": g.date})
    a = pd.DataFrame({"team": g.away_team, "opp": g.home_team, "pf": g.away_score, "pa": g.home_score, "date": g.date})
    out = pd.concat([h, a], ignore_index=True)
    out["w"] = (out.pf > out.pa).astype(int)
    return out


def _order(teams: list[str], lg: pd.DataFrame, overall: pd.DataFrame) -> list[str]:
    """Order teams level on points: head-to-head (wins desc, losses asc, recursive), then diff, then points scored."""
    if len(teams) <= 1:
        return list(teams)
    h2h = lg[lg.team.isin(teams) & lg.opp.isin(teams)]
    rec = pd.DataFrame({"team": teams}).set_index("team")
    rec["hw"] = h2h.groupby("team").w.sum().reindex(teams).fillna(0)
    rec["hl"] = h2h.groupby("team").w.apply(lambda s: (1 - s).sum()).reindex(teams).fillna(0)
    rec["key"] = list(zip(-rec.hw, rec.hl))
    groups = [list(rec[rec.key == k].index) for k in sorted(rec.key.unique())]
    if len(groups) == 1:   # head-to-head does not separate them
        o = overall.loc[teams]
        return list(o.sort_values(["diff", "pf"], ascending=False).index)
    return [t for grp in groups for t in _order(grp, lg, overall)]


def standings(games: pd.DataFrame, before: str | None = None) -> pd.DataFrame:
    g = finished(games, before)
    lg = _long(g)
    all_teams = sorted(set(games.home_team) | set(games.away_team))
    t = lg.groupby("team").agg(gp=("w", "size"), w=("w", "sum"), pf=("pf", "sum"), pa=("pa", "sum")).reindex(all_teams).fillna(0).astype(int)
    t["l"] = t.gp - t.w
    t["pts"] = 2 * t.w
    t["diff"] = t.pf - t.pa
    last = lg.sort_values("date").groupby("team").w.apply(lambda s: "".join("W" if x else "L" for x in s)).reindex(all_teams).fillna("")
    t["form"] = last
    order = [tm for p in sorted(t.pts.unique(), reverse=True) for tm in _order(list(t[t.pts == p].index), lg, t)]
    t = t.loc[order]
    t.insert(0, "pos", range(1, len(t) + 1))
    # shared position label for teams level on points, e.g. "3=" ... keep the provisional order but flag ties
    t["tied"] = t.pts.map(t.pts.value_counts()) > 1
    return t


def results_by_round(games: pd.DataFrame, before: str | None = None) -> pd.DataFrame:
    g = finished(games, before)
    return g[["round", "date", "home_team", "home_score", "away_score", "away_team"]]


def _bold(team: str, highlight: list[str], text: str | None = None) -> str:
    text = text if text is not None else short(team)
    return f"**{text}**" if team in highlight else text


def standings_md(games: pd.DataFrame, before: str | None, highlight: list[str], league: str = "LBA") -> str:
    t = standings(games, before)
    res = results_by_round(games, before)
    rounds = sorted(res["round"].unique())
    lines = [f"## {league} so far: results and standings", ""]
    rnd_txt = f"round {rounds[0]}" if len(rounds) == 1 else f"rounds {rounds[0]} to {rounds[-1]}"
    lines.append(f"All {len(res)} {league} games played before this match ({rnd_txt}); home team first.")
    lines.append("")
    for r in rounds:
        rr = res[res["round"] == r]
        cells = []
        for _, x in rr.iterrows():
            score = f"{x.home_score}-{x.away_score}"
            txt = f"{short(x.home_team)} {score} {short(x.away_team)}"
            cells.append(f"**{txt}**" if (x.home_team in highlight or x.away_team in highlight) else txt)
        lines.append(f"- **Round {r}**: " + " · ".join(cells))
    lines += ["", "![standings](00_standings.png)", "", f"**Standings after round {rounds[-1]}**", "",
              "| # | Team | Pts | W-L | Points for-against | Diff | Results |", "|---:|---|---:|:---:|:---:|---:|:---:|"]
    for tm, x in t.iterrows():
        lines.append(f"| {x.pos} | {_bold(tm, highlight)} | {x.pts} | {x.w}-{x.l} | {x.pf}-{x.pa} | {x['diff']:+d} | {x.form} |")
    lines += ["", "Two points per win. Teams level on points are ordered by the games between them, then by point "
              "difference; with so few games played most of them have not met yet, so the order inside a group "
              "on the same points is provisional (newspapers sometimes list it differently).", ""]
    return "\n".join(lines)


def fig_standings(games: pd.DataFrame, before: str | None, highlight: list[str], out: Path, title_label: str = "LBA 2026/27") -> None:
    t = standings(games, before)
    rounds = results_by_round(games, before)["round"]
    rounds_done = int(rounds.max()) if len(rounds) else 0
    n = int(t.gp.max())      # games of the team that played most: sizes the results column
    fig, ax = plt.subplots(figsize=(10, 6.4))
    y = np.arange(len(t))[::-1]
    others = [h for h in highlight if h != "BC Roma"]
    for yi, (tm, x) in zip(y, t.iterrows()):
        if tm in highlight:
            fill, edge = team_color(tm, others.index(tm) if tm in others else 0)
        else:
            fill, edge = LEAGUE, LEAGUE
        ax.barh(yi, x.pts, 0.68, color=fill, edgecolor=edge, linewidth=0.6, alpha=1 if tm in highlight else 0.55)
        label = f"{x.w}-{x.l}   {x['diff']:+d}"
        ax.text(x.pts + 0.08, yi, label, va="center", fontsize=9, color=TEXT if tm in highlight else TEXT2,
                fontweight="bold" if tm in highlight else "normal")
        for k, ch in enumerate(x.form):
            ax.text(2 * n + 1.9 + 0.32 * k, yi, ch, va="center", ha="center", fontsize=8.5, fontweight="bold",
                    color=GREEN if ch == "W" else RED)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{p}. {short(tm)}" for tm, p in zip(t.index, t.pos)], fontsize=10)
    for lbl, tm in zip(ax.get_yticklabels(), t.index):
        if tm in highlight:
            lbl.set_fontweight("bold"); lbl.set_color(TEXT)
    ax.set_xlim(0, 2 * n + 1.9 + 0.32 * n + 0.2)
    ax.set_xticks(range(0, 2 * n + 1, 2))
    ax.set_xlabel("league points (2 per win)")
    ax.text(2 * n + 1.9 + 0.32 * (n - 1) / 2, len(t) - 0.35, "results\nin order", ha="center", va="bottom", fontsize=8, color=TEXT2)
    style_axes(ax, "x")
    ax.set_title("bar label: wins-losses and point difference; teams on the same points ordered by head-to-head, then difference",
                 fontsize=9, color=TEXT2, loc="left")
    fig.suptitle(f"{title_label} standings after round {rounds_done}", **SUP_KW)
    save_fig(fig, out / "00_standings.png"); plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(Path(__file__).resolve().parent.parent / "data"))
    ap.add_argument("--before", default=None, help="YYYY-MM-DD: only games played before this date")
    ap.add_argument("--team", action="append", default=[], help="team(s) to highlight (repeatable)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    games = pd.read_csv(Path(a.data) / "games.csv")
    if a.before:
        import lba_style
        from datetime import date as _d
        lba_style.STAMP_NOTE = f"games before {_d.fromisoformat(a.before):%d %b %Y} (pre-match snapshot)"
    fig_standings(games, a.before, a.team, out)
    md = standings_md(games, a.before, a.team)
    (out / "standings.md").write_text(md, encoding="utf-8")
    print(md)
    print(standings(games, a.before).to_string())


if __name__ == "__main__":
    main()
