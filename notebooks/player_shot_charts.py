"""Shot charts of a team's players, up to three players per image.

    python notebooks/player_shot_charts.py --team "Openjobmetis Varese" --players Hale Duke Nikolic --before 2026-10-24 \
        --out weekly/games/2026-10-24

Writes shot_chart_<n>_<surnames>.png (made = filled, missed = red ring). LBA games only: they carry the shot coordinates.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from lba_style import RED, SUP_KW, TITLE_KW, draw_half_court, save_fig, shots_cm, team_color

PER_IMAGE = 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", required=True)
    ap.add_argument("--players", nargs="+", required=True, help="surnames, in the order they should appear")
    ap.add_argument("--data", default=str(Path(__file__).resolve().parent.parent / "data"))
    ap.add_argument("--before", default=None, help="YYYY-MM-DD: only games before this date")
    ap.add_argument("--out", default="reports")
    a = ap.parse_args()
    data = Path(a.data); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    pbp = pd.read_csv(data / "pbp.csv")
    if a.before:
        import lba_style
        from datetime import date as _d
        lba_style.STAMP_NOTE = f"games before {_d.fromisoformat(a.before):%d %b %Y}"
        box = pd.read_csv(data / "box_scores.csv")
        pbp = pbp[pbp.game_id.isin(box[box.match_datetime.str[:10] < a.before].game_id.unique())]
    pbp = pbp[pbp.team == a.team]
    fill, edge = team_color(a.team, 1)
    for k in range(0, len(a.players), PER_IMAGE):
        group = a.players[k:k + PER_IMAGE]
        fig, axes = plt.subplots(1, len(group), figsize=(6.2 * len(group), 6.6), squeeze=False)
        for ax, sn in zip(axes[0], group):
            me = pbp[pbp.player_surname.str.upper() == sn.upper()]
            s = shots_cm(me)
            draw_half_court(ax)
            miss, make = s[~s.made], s[s.made]
            ax.scatter(miss.cx, miss.cy, s=60, facecolors="none", edgecolors=RED, linewidths=1.3, zorder=3)
            ax.scatter(make.cx, make.cy, s=60, c=fill, edgecolors=edge, linewidths=0.8, zorder=4)
            two, three = s[s.pts == 2], s[s.pts == 3]
            ax.set_title(f"{sn.title()}  ({me.game_id.nunique()} games)\nFG {len(make)}/{len(s)} · 2pt {int(two.made.sum())}/{len(two)} · 3pt {int(three.made.sum())}/{len(three)}", **TITLE_KW)
        fig.suptitle(f"{a.team} — shot charts (filled = made, ring = missed)", **SUP_KW)
        name = f"shot_chart_{k // PER_IMAGE + 1}_{'_'.join(p.lower() for p in group)}.png"
        save_fig(fig, out / name); plt.close(fig)
        print(out / name)


if __name__ == "__main__":
    main()
