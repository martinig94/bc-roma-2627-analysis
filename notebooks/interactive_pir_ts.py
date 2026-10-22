"""Interactive (hover) version of reports/season_<team>/player_pir_ts.png, written as a standalone HTML file.

Test only: needs ``pip install plotly`` (not in requirements.txt). Same data and filters as ``team_report.fig_pir_ts``.
    python notebooks/interactive_pir_ts.py [--team "BC Roma"] [--out reports]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import plotly.graph_objects as go

import team_report as tr
from lba_style import BG, GOLD, GOLD_EDGE, GRID, LEAGUE, TEXT, TEXT2

MIN_MINUTES = 10
SIZE_MAX = 28   # marker diameter (px) of the player with the most minutes per game
HOVER = ("<b>%{customdata[0]}</b> · %{customdata[1]}<br>PIR %{x:.1f} · TS%% %{y:.1f}<br>"
         "%{customdata[2]:.1f} MPG · %{customdata[3]:.1f} PPG · %{customdata[4]} GP<extra></extra>")


def trace(d, name: str, color: str, edge: str, opacity: float, size) -> go.Scatter:
    """One scatter trace; hover shows player, team, minutes, points and games."""
    return go.Scatter(
        x=d.PIR, y=d["TS%"], mode="markers", name=name, opacity=opacity,
        marker=dict(size=size(d.MPG), color=color, line=dict(color=edge, width=0.8)),
        customdata=d[["Player", "team", "MPG", "PPG", "GP"]].to_numpy(), hovertemplate=HOVER)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", default=tr.CFG["team"])
    ap.add_argument("--data", default=str(tr.ROOT / "data"))
    ap.add_argument("--out", default="reports")
    a = ap.parse_args()
    _, box, _ = tr.load(Path(a.data))
    pt = tr.player_table(box)
    d = pt[(pt.MIN >= MIN_MINUTES) & (pt.fga > 0)]
    tm, lg = d[d.team == a.team], d[d.team != a.team]
    size = lambda mpg: mpg / d.MPG.max() * SIZE_MAX + 6

    fig = go.Figure([trace(lg, "other LBA players", LEAGUE, LEAGUE, .5, size), trace(tm, a.team, GOLD, GOLD_EDGE, .95, size)])
    fig.add_vline(x=lg.PIR.median(), line=dict(color=TEXT, width=1, dash="dash"), opacity=.35,
                  annotation_text="league median PIR", annotation_font=dict(size=10, color=TEXT2))
    fig.add_hline(y=lg["TS%"].median(), line=dict(color=TEXT, width=1, dash="dash"), opacity=.35,
                  annotation_text="league median TS%", annotation_font=dict(size=10, color=TEXT2))
    fig.update_layout(
        title=f"{a.team} — {tr.SEASON_TAG} | PIR vs True Shooting% (dot size = MPG, min {MIN_MINUTES} minutes)",
        xaxis=dict(title="PIR per game (LBA valutazione)", gridcolor=GRID, zeroline=False),
        yaxis=dict(title="TS% (True Shooting %)", gridcolor=GRID, zeroline=False),
        paper_bgcolor=BG, plot_bgcolor=BG, font=dict(color=TEXT), hovermode="closest", height=750)
    out = Path(a.out) / f"season_{a.team.replace(' ', '_')}"; out.mkdir(parents=True, exist_ok=True)
    path = out / "player_pir_ts_interactive.html"
    fig.write_html(path, include_plotlyjs="cdn")
    print(path)


if __name__ == "__main__":
    main()
