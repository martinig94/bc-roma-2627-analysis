"""Three seasons of one player's shots (Synergy): zones, pick-and-roll / isolation / transition situations, and a triangle per season.

    python notebooks/synergy_player_history.py data/synergy/players_2026-10-25 --out weekly/games/2026-10-27 [--players Atic,Domask]

Reads `players_shots.csv` and `players_games.csv` of the data folder (see its README.md) and writes, per player, into --out:
  10_player_<name>_zones_by_season.png   field-goal attempts per game and FG% by zone, one bar per season
  10b_player_<name>_situations.png       P&R ball handler by side, isolation by location, transition by role (and the action after it)
  10c_player_<name>_triangles.png        3PT / paint / mid-range split of the attempts, one dot per game, one triangle per season
  10d_player_<name>_drives.png           finishes at the basket left or right of the rim (P&R ball handler, isolation, both), by season
  10e_player_<name>_pnr_shots.png        P&R ball handler: share of threes, drives and mid-range shots, and each by side of the floor, by season
  10f_player_<name>_pnr_iso_courts.png   P&R screen (left / high / right) and isolation start (left / top / right) on a half court, plus one bar per season

Descriptive only, based solely on the data (field-goal attempts: possessions ending in a turnover, a foul or a pass are not in the
shot list). Every figure carries the date and the author (weekly/config.json). Exhibitions and third-division games are left out.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.axes import Axes
from matplotlib.patches import Arc, Circle, Patch, Polygon, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent))
import weekly_config
from tendency_triangles import CORNERS, GRID_N, density_levels, to_xy   # noqa: E402  (same triangle as the individual-tendencies page)

EXCLUDE = ['Exhibitions', 'German League Division 3']   # competitions left out of every figure (substring match: also 'Exhibitions-Italian Serie A', 'Italian Serie A League Exhibitions')
NSEASONS = {1: 'one season', 2: 'two seasons', 3: 'three seasons', 4: 'four seasons', 5: 'five seasons'}
MIN_TRIANGLE_FGA = 3                                       # attempts of a game for it to be a dot in the triangle
ZONES = ['Paint', 'Mid-range', 'Corner 3', 'Wing 3', 'Top 3']
SEASON_COLORS = {'2023-24': '#DDE7F3', '2024-25': '#B9CFEA', '2025-26': '#4F7FBF', '2026-27': '#1F3A5F'}   # light to dark: oldest to current
YELLOW, GREY, GRID, TEXT, TEXT2, TEXT3 = '#F2B705', '#8A8F98', '#e3e4ea', '#222', '#444', '#666'
COMP_COLORS = {'Spanish ACB League': '#B04A3A', 'FIBA Europe Cup': '#2E7D6B', 'Adriatic League (ABA)': '#3E6DA8', 'EuroCup': '#F2B705',
               'German League': '#4C4C4C', 'German Cup': '#8A8F98', 'BNXT League': '#7FA6D6',
               'Italian Serie A League': '#2E7D6B', 'Italian Serie A Cup': '#8CC7B8', 'VTB United League': '#7A3E9D', 'Winline Cup': '#C9A7E0',
               'Basketball Africa League': '#D9822B', 'FIBA Champions League': '#C2559C', 'Adriatic League Supercup': '#9DB7D5'}
SITUATIONS = {   # play type (Synergy chain) -> (panel title, sub-type order (first token after the play type), action order (next token))
    'P&R Ball Handler': ('P&R ball handler', ['High P&R', 'Left P&R', 'Right P&R'], ['Dribble Off Pick', 'Go Away from Pick', 'Takes Early Jump Shot']),
    'ISO': ('Isolation', ['Top', 'Left', 'Right'], ['Early Jumper', 'Drives Left', 'Drives Right']),
    'Transition': ('Transition', ['Ballhandler', 'Left Wing', 'Right Wing', 'Leak Outs', 'Trailer', 'First Middle'], ['To Basket', 'Jumper']),
}
ACTION_LABEL = {'Dribble Off Pick': 'Dribbles off the pick', 'Go Away from Pick': 'Goes away from the pick', 'Takes Early Jump Shot': 'Early jump shot',
                'Early Jumper': 'Early jumper', 'Drives Left': 'Drives left', 'Drives Right': 'Drives right', 'To Basket': 'To the basket', 'Jumper': 'Jumper',
                'Ballhandler': 'Ball handler', 'Left Wing': 'Left wing', 'Right Wing': 'Right wing', 'Leak Outs': 'Leak out', 'Trailer': 'Trailer',
                'First Middle': 'First middle', 'High P&R': 'High', 'Left P&R': 'Left', 'Right P&R': 'Right'}
plt.rcParams.update({'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': '#BBBBBB', 'font.family': 'DejaVu Sans',
                     'figure.constrained_layout.use': False, 'axes.facecolor': 'white'})   # lba_style (via tendency_triangles) turns these on


def zone(z: str) -> str:
    """Synergy 11-zone name -> one of ZONES (same grouping as the team folders)."""
    if z == 'Z11-01-2pt': return 'Paint'
    if z.endswith('2pt'): return 'Mid-range'
    if z in ('Z11-12-3pt', 'Z11-16-3pt'): return 'Corner 3'
    if z in ('Z11-13-3pt', 'Z11-15-3pt'): return 'Wing 3'
    return 'Top 3'


def own_chain(description: str) -> list[str]:
    """The part of the Synergy chain after the shooter (the last "number Name" segment): play type, sub-type, action, ..., result."""
    seg = description.split(' > ')
    last = max(i for i, t in enumerate(seg) if re.match(r'^\d+ [A-Za-z]', t) and not re.match(r'^\d+ Pts$', t))
    return seg[last + 1:]


def load(data: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Shots (with zone, made, play type, sub-type, action, kind) and games, without the EXCLUDE competitions."""
    s = pd.read_csv(data / 'players_shots.csv')
    g = pd.read_csv(data / 'players_games.csv')
    excl = lambda c: c.fillna('').map(lambda v: any(e in v for e in EXCLUDE))
    s, g = s[~excl(s.comp)].copy(), g[~excl(g.comp)].copy()
    chain = s.description.map(own_chain)
    s['zone'] = s.zone_raw.map(zone)
    s['made'] = (s.pts_scored > 0).astype(int)
    s['pt'] = chain.str[0]
    s['sub'] = chain.str[1]
    s['action'] = [c[2] if len(c) > 2 else '' for c in chain]
    s.loc[s.pt == 'Transition', 'action'] = ['To Basket' if 'To Basket' in c else 'Jumper' for c in chain[s.pt == 'Transition']]
    s.loc[(s.pt == 'P&R Ball Handler') & s['sub'].isin(['Left P&R', 'Right P&R']), 'action'] = \
        [c[3] if len(c) > 3 else '' for c in chain[(s.pt == 'P&R Ball Handler') & s['sub'].isin(['Left P&R', 'Right P&R'])]]   # Side/Baseline comes first
    s['kind'] = np.where(s.pts_att == 3, '3PT', np.where(s.zone == 'Paint', 'Paint', 'Mid-range'))
    return s, g


class Ctx:
    def __init__(self, out: Path, author: str, day: str):
        self.out = out
        out.mkdir(parents=True, exist_ok=True)
        self.foot_prefix = f'{author} · {day} · Source: Synergy Sports (shot list, all competitions except {", ".join(EXCLUDE).lower()}) · '

    def save(self, fig, name: str, note: str) -> None:
        fig.text(.01, .008, self.foot_prefix + note, fontsize=7, color=TEXT3)
        fig.savefig(self.out / name, dpi=150)
        from imgopt import shrink_png
        shrink_png(self.out / name)
        plt.close(fig)


def season_line(p: str, s: pd.DataFrame, g: pd.DataFrame) -> str:
    """'2024-25: 26 games, 130 FGA (Spanish ACB League) · ...' for the subtitle."""
    parts = []
    for se, gg in g[g.player == p].groupby('season'):
        names = [c.replace(' (ABA)', '').replace(' League', '') for c in gg.comp.value_counts().index]
        comps = ', '.join(names[:2]) + (f' +{len(names) - 2}' if len(names) > 2 else '')   # most-played two, so the subtitle fits the figure
        parts.append(f'{se}: {gg.game_id.nunique()} games, {len(s[(s.player == p) & (s.season == se)])} FGA ({comps})')
    line = ' · '.join(parts)
    if len(line) > 150:   # four seasons with long competition lists: two lines
        half = len(parts) // 2 + len(parts) % 2
        line = ' · '.join(parts[:half]) + '\n' + ' · '.join(parts[half:])
    return line


def pct_label(fgm: int, fga: int) -> str:
    return f'{fgm}/{fga}' if fga else ''


def fig_zones(c: Ctx, p: str, s: pd.DataFrame, g: pd.DataFrame) -> None:
    d = s[s.player == p]
    seasons = [se for se in SEASON_COLORS if se in set(d.season)]
    gp = g[g.player == p].groupby('season').game_id.nunique()
    t = d.groupby(['season', 'zone']).agg(fga=('made', 'size'), fgm=('made', 'sum')).reindex(
        pd.MultiIndex.from_product([seasons, ZONES], names=['season', 'zone']), fill_value=0).reset_index()
    t['per_game'] = t.fga / t.season.map(gp)
    t['pct'] = np.where(t.fga > 0, 100 * t.fgm / t.fga.replace(0, 1), np.nan)
    w = .8 / len(seasons)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.4))
    fig.subplots_adjust(left=.06, right=.98, top=.78, bottom=.2, wspace=.25)
    x = np.arange(len(ZONES))
    for i, se in enumerate(seasons):
        r = t[t.season == se].set_index('zone').loc[ZONES]
        pos = x + (i - (len(seasons) - 1) / 2) * w
        a1.bar(pos, r.per_game, w, color=SEASON_COLORS[se], label=se)
        for xx, v, n in zip(pos, r.per_game, r.fga):
            a1.text(xx, v + .04, f'{v:.1f}', ha='center', fontsize=7.5, color=TEXT2)
        a2.bar(pos, r.pct, w, color=SEASON_COLORS[se], label=se)
        for xx, v, m, n in zip(pos, r.pct, r.fgm, r.fga):
            if n: a2.text(xx, v + 1.2, pct_label(int(m), int(n)), ha='center', fontsize=7, color=TEXT2, rotation=90 if len(seasons) > 2 else 0, va='bottom')
    for ax, title, yl in ((a1, 'Field-goal attempts per game, by zone', 'FGA per game'), (a2, 'FG% by zone (made/attempted)', 'FG%')):
        ax.set_xticks(x); ax.set_xticklabels(ZONES, fontsize=9); ax.set_ylabel(yl, fontsize=9); ax.set_title(title, fontsize=10.5, color=TEXT2, pad=10)
        ax.grid(axis='y', color=GRID, lw=.7); ax.set_axisbelow(True)
    a2.set_ylim(0, 112)
    a1.set_ylim(0, t.per_game.max() * 1.18)
    a1.legend(fontsize=8.5, loc='upper right')
    fig.text(.02, .935, f'{p}: shooting volume and percentages by zone, {NSEASONS[len(seasons)]}', fontsize=14, fontweight='bold')
    fig.text(.02, .885, season_line(p, s, g), fontsize=8.5, color=TEXT2)
    note = ('Zones: Synergy 11-zone chart grouped as Paint (incl. rim), Mid-range (other two-point zones), Corner 3, Wing 3, Top 3. '
            'Per-game values use the games the player appeared in. 2026-27 = season to date.')
    fig.text(.02, .085, note, fontsize=7, color=TEXT3)
    c.save(fig, f'10_player_{p.lower()}_zones_by_season.png', 'free throws excluded')


def fig_situations(c: Ctx, p: str, s: pd.DataFrame, g: pd.DataFrame) -> None:
    d = s[s.player == p]
    seasons = [se for se in SEASON_COLORS if se in set(d.season)]
    tot = d.groupby('season').size()
    h = .8 / len(seasons)
    fig, axs = plt.subplots(2, 3, figsize=(14, 8.6))
    fig.subplots_adjust(left=.12, right=.98, top=.78, bottom=.1, wspace=.55, hspace=.55)
    for j, (pt, (title, subs, actions)) in enumerate(SITUATIONS.items()):
        x = d[d.pt == pt]
        n_se = x.groupby('season').size().reindex(seasons, fill_value=0)
        for row, (col, order, what) in enumerate((('sub', subs, 'by ' + ('side' if pt == 'P&R Ball Handler' else 'location' if pt == 'ISO' else 'role')),
                                                   ('action', actions, 'what follows' if pt != 'Transition' else 'finish'))):
            ax = axs[row, j]
            x3 = x.assign(m3=((x.made == 1) & (x.pts_att == 3)).astype(int))
            t = x3.groupby(['season', col]).agg(fga=('made', 'size'), fgm=('made', 'sum'), m3=('m3', 'sum')).reset_index()
            y = np.arange(len(order))[::-1]
            for i, se in enumerate(seasons):
                r = t[t.season == se].set_index(col).reindex(order).fillna(0)
                share = 100 * r.fga / max(int(n_se[se]), 1)
                pos = y + (i - (len(seasons) - 1) / 2) * h
                ax.barh(pos, share, h, color=SEASON_COLORS[se], label=se)
                for yy, sh, m, n, m3 in zip(pos, share, r.fgm, r.fga, r.m3):
                    if n:
                        efg = 100 * (m + .5 * m3) / n
                        ax.text(sh + 1.5, yy, f'{int(m)}/{int(n)}  eFG {efg:.0f}%', va='center', fontsize=7, color=TEXT2)
            ax.set_yticks(y); ax.set_yticklabels([ACTION_LABEL.get(o, o).replace(' the pick', '\nthe pick') for o in order], fontsize=8.5)
            ax.set_xlim(0, 100 * 1.45); ax.set_xticks([0, 25, 50, 75, 100]); ax.tick_params(axis='x', labelsize=8)
            ax.set_xlabel(f'% of the {title.lower()} attempts', fontsize=8)
            ax.grid(axis='x', color=GRID, lw=.7); ax.set_axisbelow(True); ax.spines['left'].set_visible(False); ax.tick_params(axis='y', length=0)
            head = f'{title}, {what}'
            if row == 0:
                head += '\n' + ' · '.join(f'{int(n_se[se])}' for se in seasons) + ' FGA (' + ' · '.join(f'{100 * n_se[se] / tot[se]:.0f}%' for se in seasons) + ' of all)'
            ax.set_title(head, fontsize=8.5, color=TEXT2, pad=8, loc='left')
    fig.legend(handles=[Patch(fc=SEASON_COLORS[se], label=se) for se in seasons], loc='upper right', ncol=4, fontsize=8.5, bbox_to_anchor=(.98, .96))
    fig.text(.02, .955, f'{p}: pick-and-roll, isolation and transition shots, {NSEASONS[len(seasons)]}', fontsize=14, fontweight='bold')
    fig.text(.02, .88, 'Top row: where the situation happens (% of the attempts of that play type; under the title, the attempts per season and their share of all the '
             'player\'s attempts); bottom row: what the player does in it.', fontsize=8.5, color=TEXT2)
    fig.text(.02, .915, season_line(p, s, g), fontsize=8.5, color=TEXT2)
    note = ('Field-goal attempts only, as logged by Synergy (shooter > play type > sub-type > action). Labels: made/attempted and eFG%. '
            'High / Left / Right P&R and Top / Left / Right isolation are Synergy\'s own sub-types (side of the pick, location of the isolation).')
    fig.text(.02, .035, note, fontsize=7, color=TEXT3)
    c.save(fig, f'10b_player_{p.lower()}_situations.png', 'free throws excluded')


def draw_triangle(ax, xy: np.ndarray, colors: list[str], avg: np.ndarray, title: str) -> None:
    top, left, right = (CORNERS[k] for k in CORNERS)
    ax.add_patch(Polygon([top, left, right], closed=True, facecolor='white', edgecolor=TEXT2, lw=1.1, zorder=1))
    for t in (0.2, 0.4, 0.6, 0.8):
        for a, b, cc in ((top, left, right), (left, right, top), (right, top, left)):
            p1 = np.array(a) * t + np.array(b) * (1 - t); q = np.array(a) * t + np.array(cc) * (1 - t)
            ax.plot([p1[0], q[0]], [p1[1], q[1]], color=GRID, lw=.7, zorder=2)
    ax.text(top[0], top[1] + .03, '3PT', ha='center', va='bottom', fontsize=9, fontweight='bold', color=TEXT)
    ax.text(left[0] - .02, left[1] - .03, 'Paint', ha='center', va='top', fontsize=9, fontweight='bold', color=TEXT)
    ax.text(right[0] + .02, right[1] - .03, 'Mid-range', ha='center', va='top', fontsize=9, fontweight='bold', color=TEXT)
    if len(xy) >= 3:
        gx, gy, dens, (lo, hi) = density_levels(xy, (0.8, 0.5))
        for level, upper, alpha in ((lo, hi, .28), (hi, np.nanmax(dens) * 1.01, .5)):
            ax.contourf(gx, gy, dens, levels=[level, upper], colors=[YELLOW], alpha=alpha, zorder=3)
            ax.contour(gx, gy, dens, levels=[level], colors=['#B08D00'], linewidths=.9, alpha=.8, zorder=3)
    ax.scatter(xy[:, 0], xy[:, 1], s=46, c=colors, edgecolor='white', linewidth=.8, zorder=5)
    ax.scatter(*to_xy(avg[None, :])[0], marker='s', s=60, color='#111118', edgecolor='white', linewidth=.8, zorder=6)
    ax.set_title(title, fontsize=9.5, fontweight='bold', color=TEXT, pad=12)
    ax.set_xlim(-.12, 1.12); ax.set_ylim(-.12, 1.0); ax.set_aspect('equal'); ax.axis('off')


def fig_triangles(c: Ctx, p: str, s: pd.DataFrame, g: pd.DataFrame) -> None:
    d = s[s.player == p]
    seasons = [se for se in SEASON_COLORS if se in set(d.season)]
    fig, axs = plt.subplots(1, len(seasons), figsize=(4.6 * len(seasons), 5.6), squeeze=False)
    fig.subplots_adjust(left=.02, right=.98, top=.76, bottom=.2, wspace=.1)
    comps_used = []
    for ax, se in zip(axs[0], seasons):
        x = d[d.season == se]
        n = x.groupby(['game', 'date', 'comp', 'kind']).size().unstack(fill_value=0).reindex(columns=list(CORNERS), fill_value=0)
        n = n[n.sum(axis=1) >= MIN_TRIANGLE_FGA]
        shares = n.div(n.sum(axis=1), axis=0)
        comps = [i[2] for i in n.index]; comps_used += comps
        avg = x.kind.value_counts().reindex(list(CORNERS), fill_value=0).to_numpy(); avg = avg / avg.sum()
        draw_triangle(ax, to_xy(shares.to_numpy()), [COMP_COLORS.get(cc, GREY) for cc in comps], avg,
                      f'{se}\n{len(n)} games with {MIN_TRIANGLE_FGA}+ FGA, {len(x)} FGA\navg {avg[0]*100:.0f}% 3PT · {avg[1]*100:.0f}% paint · {avg[2]*100:.0f}% mid-range')
    items = [Line2D([], [], marker='o', ls='', color=COMP_COLORS.get(cc, GREY), label=cc) for cc in dict.fromkeys(comps_used)]
    items += [Line2D([], [], marker='s', ls='', color='#111118', label='average of all shots'),
              Patch(fc=YELLOW, alpha=.5, label='densest 50% of the games'), Patch(fc=YELLOW, alpha=.28, label='densest 80%')]
    fig.legend(handles=items, loc='lower center', ncol=min(len(items), 5), fontsize=8, bbox_to_anchor=(.5, .06))
    fig.text(.02, .93, f'{p}: where the shots come from, game by game, {NSEASONS[len(seasons)]}', fontsize=14, fontweight='bold')
    fig.text(.02, .875, season_line(p, s, g), fontsize=8.5, color=TEXT2)
    c.save(fig, f'10c_player_{p.lower()}_triangles.png', 'corners: 3-point, paint (Synergy rim/paint zone) and mid-range (other two-point) attempts; one dot per game')


RIM_X = 250                                                 # Synergy court coordinates of court/2/shots: rim at (250, 330); x < 250 = offense's right side
SIDE_COLORS = {'left': '#4F7FBF', 'right': '#1F3A5F'}
DRIVE_PANELS = [('P&R ball handler', ['P&R Ball Handler']), ('Isolation', ['ISO']), ('P&R ball handler + isolation', ['P&R Ball Handler', 'ISO'])]


def fig_drives(c: Ctx, p: str, s: pd.DataFrame, g: pd.DataFrame) -> None:
    """Finishes at the basket, left or right of the rim: P&R ball handler, isolation, both — one pair of bars per season."""
    d = s[(s.player == p) & s.description.str.contains('To Basket', regex=False) & (s.pts_att == 2) & s.x.notna()].copy()
    d['side'] = np.where(d.x < RIM_X, 'right', 'left')
    seasons = [se for se in SEASON_COLORS if se in set(s[s.player == p].season)]
    fig, axs = plt.subplots(1, 3, figsize=(14, 5.6))
    fig.subplots_adjust(left=.06, right=.98, top=.68, bottom=.19, wspace=.25)
    w = .36
    for ax, (title, pts) in zip(axs, DRIVE_PANELS):
        x = d[d.pt.isin(pts)]
        t = x.groupby(['season', 'side']).agg(fga=('made', 'size'), fgm=('made', 'sum'))
        for i, side in enumerate(('left', 'right')):
            pos = np.arange(len(seasons)) + (i - .5) * w
            n = [int(t.fga.get((se, side), 0)) for se in seasons]
            m = [int(t.fgm.get((se, side), 0)) for se in seasons]
            ax.bar(pos, n, w * .94, color=SIDE_COLORS[side], label=f'{side} of the rim')
            for xx, nn, mm in zip(pos, n, m):
                if nn:
                    ax.text(xx, nn + .8, f'{mm}/{nn}\n{100 * mm / nn:.0f}%', ha='center', va='bottom', fontsize=7.5, color=TEXT2)
        tot = x.groupby('season').size().reindex(seasons, fill_value=0)
        right = x[x.side == 'right'].groupby('season').size().reindex(seasons, fill_value=0)
        ax.set_title(title + '\n' + ' · '.join(f'{100 * right[se] / tot[se]:.0f}% right' if tot[se] else '–' for se in seasons), fontsize=9, color=TEXT2, loc='left', pad=8)
        ax.set_xticks(np.arange(len(seasons))); ax.set_xticklabels(seasons, fontsize=8.5)
        ax.grid(axis='y', color=GRID, lw=.7); ax.set_axisbelow(True); ax.tick_params(axis='y', labelsize=8); ax.tick_params(axis='x', length=0)
    axs[0].set_ylabel('finishes at the basket (attempts)', fontsize=8.5, color=TEXT2)
    for ax in axs: ax.set_ylim(0, max(ax.get_ylim()[1], 10) * 1.18)
    fig.legend(handles=[Patch(fc=SIDE_COLORS[k], label=f'{k.capitalize()} of the rim') for k in ('left', 'right')], loc='upper right', ncol=2, fontsize=8.5, bbox_to_anchor=(.98, .99))
    fig.text(.02, .955, f'{p}: drives to the basket, left or right of the rim, {NSEASONS[len(seasons)]}', fontsize=14, fontweight='bold')
    fig.text(.02, .895, season_line(p, s, g), fontsize=8.5, color=TEXT2)
    fig.text(.02, .865, 'Shots logged "To Basket" out of the pick-and-roll (ball handler) and the isolation, split by the side of the rim where the shot is taken (left / right from the '
             'offense\'s point of view).\nLabels: made/attempted and FG%; under each title, the share of the finishes taken on the right side, season by season.',
             fontsize=8.5, color=TEXT2, va='top')
    note = ('Side of the rim from the x coordinate of the shot in the Synergy shot chart (rim at the centre). Finishes at the rim only: pull-ups, floaters logged as jumpers, '
            'free throws and possessions without a shot are not counted. Small samples per season and side: tendencies, not rules.')
    fig.text(.02, .06, note, fontsize=7, color=TEXT3)
    c.save(fig, f'10d_player_{p.lower()}_drives.png', 'free throws excluded')


PNR_TYPES = ['Three', 'Drive to the basket', 'Mid-range']
PNR_COLORS = {'Three': '#F2B705', 'Drive to the basket': '#1F3A5F', 'Mid-range': '#4F7FBF', 'Other': '#CCCCCC'}


def pnr_shot_type(chain_text: pd.Series, pts_att: pd.Series, zone_name: pd.Series) -> pd.Series:
    """Shot type out of the pick-and-roll: drive to the basket, three, mid-range, else (paint jumpers, floaters) 'Other'."""
    return pd.Series(np.select([chain_text.str.contains('To Basket', regex=False), pts_att == 3, zone_name == 'Mid-range'],
                               ['Drive to the basket', 'Three', 'Mid-range'], 'Other'), index=chain_text.index)


def fig_pnr(c: Ctx, p: str, s: pd.DataFrame, g: pd.DataFrame) -> None:
    """Pick-and-roll ball handler: how often he shoots a three, drives to the basket or takes a mid-range shot, and from which side."""
    d = s[(s.player == p) & (s.pt == 'P&R Ball Handler') & s.x.notna()].copy()
    d['type'] = pnr_shot_type(d.description, d.pts_att, d.zone)
    d['side'] = np.where(d.x < RIM_X, 'right', 'left')
    seasons = [se for se in SEASON_COLORS if se in set(d.season)]
    fig = plt.figure(figsize=(14, 7.4))
    gs = fig.add_gridspec(2, 3, left=.06, right=.98, top=.76, bottom=.1, hspace=.62, wspace=.25, height_ratios=[.8, 1.2])
    top = fig.add_subplot(gs[0, :])
    tot = d.groupby('season').size().reindex(seasons)
    for i, se in enumerate(seasons):
        left = 0
        for k in PNR_TYPES + ['Other']:
            n = int((d[d.season == se].type == k).sum())
            if n:
                top.barh(i, 100 * n / tot[se], left=left, color=PNR_COLORS[k], height=.62, label=k if i == 0 else None)
                if 100 * n / tot[se] >= 6:
                    top.text(left + 50 * n / tot[se], i, f'{n}\n{100 * n / tot[se]:.0f}%', ha='center', va='center', fontsize=8.5,
                             color='#222' if k in ('Three', 'Other') else 'white')
                left += 100 * n / tot[se]
        top.text(101, i, f'{tot[se]} shots', va='center', fontsize=8.5, color=TEXT2)
    top.set_yticks(range(len(seasons))); top.set_yticklabels(seasons, fontsize=9); top.invert_yaxis()
    top.set_xlim(0, 112); top.set_xticks([0, 25, 50, 75, 100]); top.set_xticklabels([f'{v}%' for v in (0, 25, 50, 75, 100)], fontsize=8)
    top.tick_params(axis='y', length=0); top.set_title('What he shoots out of the pick-and-roll (share of his P&R shots)', fontsize=10, loc='left', color=TEXT2)
    top.legend(ncol=4, fontsize=8.5, loc='lower right', bbox_to_anchor=(1, 1.0), frameon=False)
    w = .38
    for j, k in enumerate(PNR_TYPES):
        ax = fig.add_subplot(gs[1, j])
        x = d[d.type == k]
        t = x.groupby(['season', 'side']).agg(a=('made', 'size'), m=('made', 'sum'))
        for i, side in enumerate(('left', 'right')):
            pos = np.arange(len(seasons)) + (i - .5) * w
            n = [int(t.a.get((se, side), 0)) for se in seasons]
            m = [int(t.m.get((se, side), 0)) for se in seasons]
            ax.bar(pos, n, w * .94, color=SIDE_COLORS[side], label=f'{side} side')
            for xx, nn, mm in zip(pos, n, m):
                if nn:
                    ax.text(xx, nn + max(n + [1]) * .02, f'{mm}/{nn}\n{100 * mm / nn:.0f}%', ha='center', va='bottom', fontsize=7.5, color=TEXT2)
        r = x.groupby('season').side.apply(lambda v: f'{100 * (v == "right").mean():.0f}%').reindex(seasons).fillna('-')
        ax.set_title(f'{k}: by side\nshare on the right: ' + ' · '.join(r), fontsize=9, loc='left', color=TEXT2)
        ax.set_xticks(np.arange(len(seasons))); ax.set_xticklabels(seasons, fontsize=8)
        ax.set_ylim(0, max(ax.get_ylim()[1], 8) * 1.2); ax.grid(axis='y', color=GRID, lw=.7); ax.set_axisbelow(True)
        ax.tick_params(axis='y', labelsize=8); ax.tick_params(axis='x', length=0)
        if j == 0:
            ax.set_ylabel('shots (made/attempted, FG%)', fontsize=8.5, color=TEXT2)
            ax.legend(handles=[Patch(fc=SIDE_COLORS[q], label=f'{q.capitalize()} side of the floor') for q in ('left', 'right')], fontsize=8, loc='upper left', frameon=False)
    fig.text(.02, .955, f'{p}: three, drive or mid-range out of the pick-and-roll', fontsize=14, fontweight='bold')
    fig.text(.02, .915, season_line(p, s, g), fontsize=8.5, color=TEXT2, va='top')
    fig.text(.02, .84, 'Every field-goal attempt where he is the P&R ball handler. Drive = shot logged "To Basket"; three = any three; mid-range = other two-point shots outside the paint; '
             '"Other" = jumpers and floaters in the paint.\n'
             'Side = left or right of the rim (offense\'s point of view) from the shot coordinates, so a pull-up three from the right wing counts on the right.',
             fontsize=8.5, color=TEXT2, va='top')
    fig.text(.02, .04, 'Possessions ending in a pass, a turnover or a foul are not in the shot list. 2023-25: US college; small samples per season, side and type: tendencies, not rules.', fontsize=7, color=TEXT3)
    c.save(fig, f'10e_player_{p.lower()}_pnr_shots.png', 'free throws excluded')


COURT_ZONES = {   # play type -> (title, sub-types left to right as the offense sees the court, label of each)
    'P&R Ball Handler': ('Pick-and-roll: where is the screen?', ['Left P&R', 'High P&R', 'Right P&R'], ['Left', 'High (centre)', 'Right']),
    'ISO': ('Isolation: where does it start?', ['Left', 'Top', 'Right'], ['Left', 'Top', 'Right']),
}


def draw_half_court(ax: Axes) -> None:
    """Half court seen from behind the offense, in feet: basket at the top (the project's shot-chart orientation, see lba_style.ROTATE_COURT),
    the offense's left on the left of the picture, its right on the right (Synergy x < 250 is the offense's right)."""
    line = dict(color='#888888', lw=1.2, zorder=3)
    ax.add_patch(Rectangle((-25, 0), 50, 34, fill=False, **line))
    ax.add_patch(Rectangle((-8, 0), 16, 19, fill=False, **line))
    ax.add_patch(Arc((0, 19), 12, 12, theta1=0, theta2=180, **line))
    ax.add_patch(Arc((0, 5.25), 47.5, 47.5, theta1=22, theta2=158, **line))
    ax.plot([-22, -22], [0, 14], **line); ax.plot([22, 22], [0, 14], **line)
    ax.add_patch(Circle((0, 5.25), .75, fill=False, **line))
    ax.set_xlim(-26, 26); ax.set_ylim(35, -1); ax.set_aspect('equal'); ax.axis('off')   # y reversed: basket at the top, as in every shot chart of the project


def fig_courts(c: Ctx, p: str, s: pd.DataFrame, g: pd.DataFrame) -> None:
    """P&R screen location and isolation start, left / centre / right: a half court (pro seasons) over one bar per season."""
    from matplotlib.colors import to_rgba
    seasons = [se for se in SEASON_COLORS if se in set(s[s.player == p].season)]
    pro = [se for se in seasons if se in ('2025-26', '2026-27')]
    fig = plt.figure(figsize=(14, 9))
    gs = fig.add_gridspec(2, 2, left=.05, right=.97, top=.74, bottom=.09, hspace=.18, wspace=.12, height_ratios=[1.25, 1])
    for j, (pt, (title, subs, labels)) in enumerate(COURT_ZONES.items()):
        d = s[(s.player == p) & (s.pt == pt) & s['sub'].isin(subs)]
        cc = fig.add_subplot(gs[0, j]); draw_half_court(cc)
        dp = d[d.season.isin(pro)]
        n = len(dp)
        for k, (sub, lab) in enumerate(zip(subs, labels)):
            x = dp[dp['sub'] == sub]
            share = len(x) / n if n else 0
            x0, x1 = (-25, -8) if k == 0 else ((-8, 8) if k == 1 else (8, 25))
            cc.add_patch(Rectangle((x0, 0), x1 - x0, 34, fc=to_rgba('#1F3A5F', .12 + .78 * share), ec='none', zorder=1))
            fg = f'{100 * x.made.sum() / len(x):.0f}% FG\n({int(x.made.sum())}/{len(x)})' if len(x) else ''
            cc.text((x0 + x1) / 2, 13, f'{100 * share:.0f}%', ha='center', va='center', fontsize=26, fontweight='bold',
                    color='white' if share > .35 else TEXT, zorder=5)
            cc.text((x0 + x1) / 2, 20, lab, ha='center', va='center', fontsize=10.5, color='white' if share > .35 else TEXT, zorder=5)
            cc.text((x0 + x1) / 2, 26, fg, ha='center', va='center', linespacing=1.3, fontsize=8.5, color='white' if share > .35 else TEXT2, zorder=5)
        cc.set_title(f'{title}\n{" + ".join(pro)} ({n} shots)', fontsize=11, loc='left', color=TEXT, pad=8)
        bar = fig.add_subplot(gs[1, j])
        for i, se in enumerate(seasons):
            t = d[d.season == se]['sub'].value_counts().reindex(subs, fill_value=0)
            tot = int(t.sum()); left = 0
            for sub, shade in zip(subs, ('#4F7FBF', '#1F3A5F', '#B9CFEA')):
                v = 100 * t[sub] / tot if tot else 0
                bar.barh(i, v, left=left, color=shade, height=.62, label=labels[subs.index(sub)] if i == 0 else None)
                if v >= 7:
                    bar.text(left + v / 2, i, f'{v:.0f}%', ha='center', va='center', fontsize=9, color='white' if shade != '#B9CFEA' else TEXT)
                left += v
            bar.text(101, i, f'{tot} shots', va='center', fontsize=8.5, color=TEXT2)
        bar.set_yticks(range(len(seasons))); bar.set_yticklabels(seasons, fontsize=9); bar.invert_yaxis()
        bar.set_xlim(0, 112); bar.set_xticks([0, 50, 100]); bar.set_xticklabels(['0%', '50%', '100%'], fontsize=8)
        bar.tick_params(axis='y', length=0); bar.set_title('By season (share of his shots)', fontsize=9.5, loc='left', color=TEXT2)
        bar.legend(ncol=3, fontsize=8, loc='lower right', bbox_to_anchor=(1, 1.0), frameon=False)
    fig.text(.02, .955, f'{p}: pick-and-roll screen and isolation, left, centre or right', fontsize=14, fontweight='bold')
    fig.text(.02, .915, season_line(p, s, g), fontsize=8.5, color=TEXT2, va='top')
    fig.text(.02, .85, 'Court seen from behind the offense: left is the offense\'s left. Darker = bigger share of his shots of that play type. P&R side is Synergy\'s own tag '
             '(High = screen in the centre, Left / Right = side screen);\n'
             'isolation Top / Left / Right is where the isolation starts.',
             fontsize=8.5, color=TEXT2, va='top')
    fig.text(.02, .035, 'Shots only (possessions ending in a pass, a turnover or a foul are not in the shot list). Court shading and FG% use his two professional seasons together; small samples on the sides.',
             fontsize=7, color=TEXT3)
    c.save(fig, f'10f_player_{p.lower()}_pnr_iso_courts.png', 'free throws excluded')


LR_GROUPS = [('All shots', None), ('Threes', '3PT'), ('Mid-range', 'Mid-range'), ('Paint', 'Paint')]
LR_ROWS = [('All seasons', None), ('Antwerp + Virtus', ('2025-26', '2026-27'))]


def fig_left_right(c: Ctx, p: str, s: pd.DataFrame, g: pd.DataFrame) -> None:
    """Does he shoot more from the left or from the right of the floor? All shots, threes, mid-range and paint, cumulative."""
    d = s[(s.player == p) & s.x.notna()].copy()
    d['side'] = np.where(d.x < RIM_X, 'right', 'left')
    fig, axs = plt.subplots(2, 2, figsize=(14, 6.8))
    fig.subplots_adjust(left=.11, right=.97, top=.75, bottom=.1, hspace=.6, wspace=.18)
    for ax, (title, kind) in zip(axs.flat, LR_GROUPS):
        x = d if kind is None else d[d.kind == kind]
        for i, (row_name, seasons) in enumerate(LR_ROWS):
            r = x if seasons is None else x[x.season.isin(seasons)]
            left = 0
            for side in ('left', 'right'):
                t = r[r.side == side]
                share = 100 * len(t) / len(r) if len(r) else 0
                ax.barh(i, share, left=left, color=SIDE_COLORS[side], height=.62)
                fg = f'{100 * t.made.sum() / len(t):.0f}% FG' if len(t) else ''
                ax.text(left + share / 2, i, f'{share:.0f}%\n{fg} ({int(t.made.sum())}/{len(t)})', ha='center', va='center', fontsize=8.5,
                        color='white' if side == 'right' else TEXT)
                left += share
        ax.set_yticks(range(len(LR_ROWS))); ax.set_yticklabels([n for n, _ in LR_ROWS] if ax in axs[:, 0] else [], fontsize=9)
        ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xticks([0, 50, 100]); ax.set_xticklabels(['0%', '50%', '100%'], fontsize=8)
        ax.tick_params(axis='y', length=0)
        ax.set_title(f'{title} ({len(x)} shots)', fontsize=10.5, loc='left', color=TEXT, pad=6)
    fig.legend(handles=[Patch(fc=SIDE_COLORS[k], label=f'{k.capitalize()} of the floor') for k in ('left', 'right')], loc='upper right', ncol=2, fontsize=9,
               bbox_to_anchor=(.97, .985), frameon=False)
    fig.text(.02, .955, f'{p}: more to the left or to the right?', fontsize=14, fontweight='bold')
    fig.text(.02, .915, season_line(p, s, g), fontsize=8.5, color=TEXT2, va='top')
    fig.text(.02, .835, 'Every field-goal attempt, all play types, by the side of the floor (left or right of the basket, from the offense\'s point of view) where it is taken.',
             fontsize=8.5, color=TEXT2, va='top')
    fig.text(.02, .04, 'Shots only. Side from the shot coordinates in the Synergy shot chart; a shot right under the basket counts on the side of its coordinate. '
             '2023-25 are US college games.', fontsize=7, color=TEXT3)
    c.save(fig, f'10g_player_{p.lower()}_left_right.png', 'free throws excluded')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('data', type=Path); ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--players', default=None, help='comma-separated surnames (default: all in the data)')
    ap.add_argument('--date', default=f'{date.today():%d %b %Y}'); ap.add_argument('--author', default=weekly_config.load()['author'])
    a = ap.parse_args()
    s, g = load(a.data)
    c = Ctx(a.out, a.author, a.date)
    for p in (a.players.split(',') if a.players else sorted(s.player.unique())):
        fig_zones(c, p, s, g); fig_situations(c, p, s, g); fig_triangles(c, p, s, g); fig_drives(c, p, s, g); fig_pnr(c, p, s, g); fig_courts(c, p, s, g); fig_left_right(c, p, s, g)
        print(p, '->', a.out / f'10*_player_{p.lower()}_*.png')


if __name__ == '__main__':
    main()
