"""Scouting plots from Synergy Sports data: any opponent, any reference team, any league/competition.

    python notebooks/synergy_scouting_plots.py data/synergy/varese_2026-10-20
    python notebooks/synergy_scouting_plots.py data/synergy/<folder> --date "27 Oct 2026" --out reports/some_folder

The data folder holds a `config.json` (teams, competition, date, author) and the CSVs described in its README.md.
Plots go to reports/synergy_<folder name>/plots/ (or --out). Nothing in this file is specific to one team:
the opponent (the team being scouted) is drawn in navy, the reference team (the team you work for) in yellow.

  01   team radar, z-scores vs the league's teams, team values from all games played
  01b  same, the competition's games only (like for like)
  02   opponent play types run / faced
  03   offensive PPP by play type, reference team vs opponent
  04   opponent players, possessions used vs eFG% (number in bubble = points per game)
  05   one figure per player: FG made/attempted by shot location and by play type (05_player_<name>_shot_profile.png)
  05c  one figure per player: shot types within each play type that passes the minimum attempts / minimum share
       of the player's attempts thresholds (05c_player_<name>_shot_types.png)
  05b  player radars, percentile rank within the opponent's roster
  06   possessions used by play type, per player
  07   lineups: usage vs points per possession
  08   lineups: points scored vs allowed per possession
  09   lineups: shot-profile differences

Descriptive only, based solely on the data. Every figure carries the date and the author.

REVIEW NEEDED, DATA FROM SYNERGY
    Every function here expects tables extracted from the Synergy Sports web app (apps.synergysports.com), not from the
    official LBA/legabasket data in the rest of this repo. The extraction was done by hand in the browser, so before
    trusting a new pull check that: (1) column names and units match the README in the data folder (percentages as text
    like "47.2%" in the box table, numbers elsewhere); (2) the shot-zone and shot-type CSVs were typed from Synergy's shot
    chart and shot list and totals match the play-type counts; (3) Synergy rounds, its percentile gauges and ranks move
    between page loads, and the box table has no minutes; (4) team abbreviations in the league tables and the team names in
    context_all_games.csv match config.json; (5) lineup tables only list lineups above the minimum possessions, so
    sums over them are not team totals. Sample sizes are small (a handful of games); read the figures as descriptive.
"""
from __future__ import annotations

import argparse
import json
import warnings
import textwrap
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.transforms import Bbox

ROOT = Path(__file__).resolve().parents[1]
# Colours: this report uses its own two-team scheme (opponent navy, reference yellow), not lba_style's gold.
YELLOW, NAVY, GREY = '#F2B705', '#1F3A5F', '#8A8F98'
SPINE = '#BBBBBB'
INK, INK_2, INK_3, INK_4, INK_5, INK_6 = '#222', '#333', '#444', '#555', '#666', '#777'   # text greys, dark to light
LEADER_LINE = '#999'      # leader lines of placed labels
CALLOUT_EDGE, KEY_BOX_EDGE, KEY_BOX_BG = '#CCCCCC', '#DDDDDD', '#F7F7F7'
plt.rcParams.update({'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': SPINE})

# Sample-size cutoffs (possessions) and plotting scales
MIN_PLAYTYPE_POSS = 10      # play types with fewer possessions are left off figures 02 and 03
MIN_PLAYER_POSS = 20        # players shown in the volume-vs-efficiency scatter (04)
MIN_RADAR_POSS = 25         # players with a roster-percentile radar (05b)
MIN_MIX_POSS = 25           # players in the play-type mix bars (06)
MIN_SHOT_TYPE_FGA = 10      # a play type needs at least this many attempts for its shot-type panel (05c) ...
MIN_SHOT_TYPE_SHARE = 0.0   # ... and at least this share of the player's attempts (0-1); raise both as the sample grows
DEFAULT_LINEUP_MIN_POSS = 5   # default for config 'lineup_min_poss'
MIN_STYLE_POSS = 10         # lineups shown in the style profile (09)
LABEL_LINEUP_POSS = 12      # lineups with at least this many offensive possessions get a label (07)
LABEL_LINEUP_PPP = 1.25     # ... or at least this many points per possession
LABEL_LINEUP_PTS = 12       # lineups with at least this many points show the number in the bubble (07)
BIG_BUBBLE_POSS = 25        # lineups with this many total possessions are numbered and listed (08)
PLAYER_BUBBLE_SCALE = 70    # bubble area per point per game (04)
LINEUP_PTS_SCALE = 22       # bubble area per point scored (07)
LINEUP_POSS_SCALE = 5       # bubble area per possession (08)
Z_CLIP = 3                  # radar z-scores are clipped to +-Z_CLIP standard deviations

MET = ['PPP', 'eFG%', 'TO%', '%FT', 'Score%', 'FG%']
COL = {'PPP': 'ppp', 'eFG%': 'efg', 'TO%': 'to', '%FT': 'ft', 'Score%': 'score', 'FG%': 'fg'}
SIGN = {'offense': {'PPP': 1, 'eFG%': 1, 'TO%': -1, '%FT': 1, 'Score%': 1, 'FG%': 1},
        'defense': {'PPP': -1, 'eFG%': -1, 'TO%': 1, '%FT': -1, 'Score%': -1, 'FG%': -1}}
ZONES = ['Paint', 'Mid-range', 'Corner 3', 'Wing 3', 'Top 3']
PT_ORDER = ['Spot Up', 'Transition', 'P&R Ball Handler', 'P&R Roll Man', 'Cut', 'Offensive Rebounds (Put Backs)',
            'Isolation', 'Off Screen', 'Other']
PT_LAB = ['Spot up', 'Transition', 'P&R ball\nhandler', 'P&R roll', 'Cut', 'Put backs', 'Isolation', 'Off screen', 'Other*']
PT_SHORT = {'Spot Up': 'spot up', 'P&R Ball Handler': 'P&R ball handler', 'P&R Roll Man': 'P&R roll man', 'Isolation': 'isolation',
            'Transition': 'transition', 'Cut': 'cut', 'Off Screen': 'off screen', 'Offensive Rebounds (Put Backs)': 'put backs'}
PALETTE = ['#1F3A5F', '#3E6DA8', '#7FA6D6', '#B9CFEA', '#4C4C4C', '#8A8F98', '#C2C5CA', '#2E7D6B', '#7BB5A6', '#B04A3A', '#D99A8F']


def pct(s: pd.Series) -> pd.Series:
    """Convert percentages written as text (``'47.2%'``) to numbers; unparseable values become NaN."""
    return pd.to_numeric(s.astype(str).str.rstrip('%'), errors='coerce')


# --------------------------------------------------------------------------------------------- context
REVIEW_NOTE = ('Inputs come from Synergy Sports (hand-extracted from the web app, small samples): '
               'review the data folder against its README before using these figures. See the docstring of this file.')


class Ctx:
    """Run context shared by all plots: data folder, output folders, config and league tables."""

    def __init__(self, data_dir: Path, out_dir: Path, cfg: dict[str, Any]):
        """Read the league tables and derive the footer text from ``cfg`` (see the data folder's config.json)."""
        self.d, self.cfg = data_dir, cfg
        self.plots = out_dir / 'plots'
        self.plots.mkdir(parents=True, exist_ok=True)
        self.out = out_dir
        self.opp, self.ref = cfg['opponent'], cfg['reference']
        self.comp = cfg['competition']
        self.league = cfg['league']
        self.foot_prefix = f"{cfg['author']} · {cfg['date']} · Source: Synergy Sports, {cfg['season']} · "
        self.scope = (f"{self.comp} only: {self.opp['name']} {self.opp['games']} games, "
                      f"{self.ref['name']} {self.ref['games']} logged games")
        self.lo = pd.read_csv(data_dir / 'league_team_offense.csv')
        self.ld = pd.read_csv(data_dir / 'league_team_defense.csv')
        self.n_teams = len(self.lo)

    def read(self, name: str) -> pd.DataFrame:
        """Read one CSV from the data folder."""
        return pd.read_csv(self.d / name)

    def foot(self, fig: Figure, text: str, y: float = .008) -> None:
        """Write the author/date/source footer plus ``text`` at the bottom of ``fig``."""
        fig.text(.01, y, self.foot_prefix + text, fontsize=7, color=INK_4)

    def save(self, fig: Figure, name: str, dpi: int = 160) -> None:
        """Save ``fig`` into the plots folder, shrink the PNG and close the figure."""
        fig.savefig(self.plots / name, dpi=dpi)
        from imgopt import shrink_png   # lazy: needs Pillow, which the other plots do not
        shrink_png(self.plots / name)
        plt.close(fig)


def place_labels(fig: Figure, ax: Axes, items: Iterable[tuple[float, float, str, float]], bbox: dict | None = None,
                 fs: float = 7.5, extra_cands: Sequence[tuple[float, float, str]] = (), avoid: Iterable[Any] = (),
                 markers: Iterable[tuple[float, float, float]] = ()) -> list[Any]:
    """Greedy label placement: for each (x, y, text, radius_pt) try offsets around the marker and keep the first
    one that does not overlap an already placed label; otherwise the one with the least overlap.

    Returns the window extents of all placed labels (including ``avoid``)."""
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    placed = list(avoid)
    k = fig.dpi / 72
    mk = []
    for mx_, my_, mr_ in markers:
        px, py = ax.transData.transform((mx_, my_))
        mk.append((mx_, my_, Bbox.from_extents(px - mr_ * k, py - mr_ * k, px + mr_ * k, py + mr_ * k)))
    for x, y, text, r in items:
        r = r + 4
        cands = [(0, -r - 5, 'center'), (0, r + 5, 'center'), (r, 0, 'left'), (-r, 0, 'right'),
                 (r, r, 'left'), (-r, -r, 'right'), (r, -r, 'left'), (-r, r, 'right')] + list(extra_cands) + \
                [(r + 30, 24, 'left'), (r + 30, -24, 'left'), (-r - 30, 24, 'right'), (-r - 30, -24, 'right'),
                 (r + 45, 0, 'left'), (-r - 45, 0, 'right'), (0, r + 40, 'center'), (0, -r - 40, 'center')]
        best, best_n = None, 10 ** 9
        for dx, dy, ha in cands:
            ann = ax.annotate(text, (x, y), xytext=(dx, dy), textcoords='offset points', fontsize=fs, ha=ha, va='center',
                              bbox=bbox, arrowprops=dict(arrowstyle='-', color=LEADER_LINE, lw=.7, shrinkA=0, shrinkB=r * .6)
                              if (abs(dx) > r + 12 or abs(dy) > r + 12) else None)
            bb = ann.get_window_extent(rend)
            n = 3 * sum(bb.overlaps(p) for p in placed) + sum(bb.overlaps(m_) for mx_, my_, m_ in mk if (mx_, my_) != (x, y))
            ann.remove()
            if n < best_n:
                best, best_n = (dx, dy, ha, bb), n
            if n == 0:
                break
        dx, dy, ha, bb = best
        ax.annotate(text, (x, y), xytext=(dx, dy), textcoords='offset points', fontsize=fs, ha=ha, va='center', bbox=bbox,
                    arrowprops=dict(arrowstyle='-', color=LEADER_LINE, lw=.7, shrinkA=0, shrinkB=r * .6)
                    if (abs(dx) > r + 12 or abs(dy) > r + 12) else None)
        placed.append(bb)
    return placed


def short_keys(lineups: Iterable[str]) -> dict[str, str]:
    """Three-letter keys per player (four if two players collide), joined by '-'."""
    names = sorted({p for s in lineups for p in s.split(' / ')})
    n = 3
    while len({p.split()[0][:n] for p in names}) < len({p.split()[0] for p in names}) and n < 6:
        n += 1
    return {s: '-'.join(p.split()[0][:n] for p in s.split(' / ')) for s in lineups}


# --------------------------------------------------------------------------------------------- 01 / 01b
def team_radar(c: Ctx, getter: Callable[[str, str, str], float], fname: str, title: str, note: str) -> pd.DataFrame:
    """Draw the offense/defense z-score radar and return the z-score table.

    ``getter(team, side, metric)`` supplies each team's raw value (all games, or competition only).
    """
    # REVIEW: needs Synergy-extracted CSVs (see module docstring); check the data before using the figure.
    opp, ref = c.opp, c.ref
    fig, axs = plt.subplots(1, 2, figsize=(12.5, 6.6), subplot_kw=dict(polar=True))
    ang = np.r_[np.linspace(0, 2 * np.pi, 6, endpoint=False), 0]
    rows = []
    for ax, side in zip(axs, ['offense', 'defense']):
        df = c.lo if side == 'offense' else c.ld
        for t, col in [(ref['name'], YELLOW), (opp['name'], NAVY)]:
            z = []
            for m in MET:
                x = df[COL[m]]
                mu, sd = x.mean(), x.std(ddof=1)
                v = getter(t, side, m)
                z.append(SIGN[side][m] * (v - mu) / sd)
                rows.append((t, side, m, v, mu, sd, z[-1]))
            z = np.clip(np.array(z), -Z_CLIP, Z_CLIP)
            zz = np.r_[z, z[0]]
            ax.plot(ang, zz, color=col, lw=2.2); ax.fill(ang, zz, color=col, alpha=.18)
            ax.scatter(ang, zz, color=col, s=30, zorder=3, edgecolor='white')
        ax.set_ylim(-Z_CLIP, Z_CLIP); ax.set_yticks([-2, -1, 0, 1, 2]); ax.set_yticklabels(['-2', '-1', '0', '+1', '+2'], fontsize=7, color=INK_5)
        ax.plot(np.linspace(0, 2 * np.pi, 200), [0] * 200, color=GREY, lw=1, ls='--')
        ax.set_xticks(ang[:-1]); ax.set_xticklabels([])
        ax.set_title(side.capitalize() + '  (higher z = better for that side)', fontsize=11, pad=40)
        fmt = lambda m, v: f'{v:.2f}' if m == 'PPP' else f'{v:.1f}%'
        for a, m in zip(ang[:-1], MET):
            sn, cs = np.sin(a), np.cos(a)
            if sn > 0.25: offs, ha, dx = (46, 28, 10), 'center', 0
            elif sn < -0.25: offs, ha, dx = (-10, -28, -46), 'center', 0
            else: offs, ha, dx = (18, 0, -18), ('left' if cs > 0 else 'right'), 10 * np.sign(cs)
            chips = [(m, None, 'black'),
                     (f"{ref['abbr']} {fmt(m, getter(ref['name'], side, m))}", YELLOW, 'black'),
                     (f"{opp['abbr']} {fmt(m, getter(opp['name'], side, m))}", NAVY, 'white')]
            for k, (txt, fc, tc) in enumerate(chips):
                ax.annotate(txt, xy=(a, Z_CLIP), xycoords='data', xytext=(dx, offs[k]), textcoords='offset points', ha=ha, va='center',
                            fontsize=9.5 if k == 0 else 8, fontweight='bold' if k == 0 else 'normal', color=tc, annotation_clip=False,
                            bbox=None if fc is None else dict(boxstyle='round,pad=.25', fc=fc, ec='none'))
    fig.legend(handles=[Line2D([0], [0], color=YELLOW, lw=3, label=ref['name']), Line2D([0], [0], color=NAVY, lw=3, label=opp['name'])],
               loc='lower center', ncol=2, frameon=False, bbox_to_anchor=(.5, .045))
    fig.suptitle(title, fontsize=13, fontweight='bold', x=.02, ha='left', y=.985)
    fig.text(.02, .93, f"Radar = z-score vs the {c.n_teams} {c.league} teams (0 = {c.league} mean, one unit = one standard deviation); "
                       "values in the chips are the raw numbers.", fontsize=8.5, color=INK_3)
    fig.text(.01, .028, 'Score% = share of possessions with at least one point scored. TO% = turnovers per possession. %FT = share of '
                        'possessions ending in free throws. Defense is sign-flipped so higher is better for that side.', fontsize=7, color=INK_4)
    c.foot(fig, note); fig.tight_layout(rect=(0, .07, 1, .93))
    c.save(fig, fname)
    return pd.DataFrame(rows, columns=['team', 'side', 'metric', 'value', 'league_mean', 'league_sd', 'z_better_is_higher'])


def plot01(c: Ctx) -> None:
    """Figures 01 and 01b (team radars) plus team_zscores_vs_league_teams.csv."""
    # REVIEW: needs Synergy-extracted CSVs (see module docstring); check the data before using the figure.
    ctx = c.read('context_all_games.csv')
    abbr = {c.opp['name']: c.opp['abbr'], c.ref['name']: c.ref['abbr']}

    def all_games(team, side, m):
        return ctx[(ctx.team == team) & (ctx.side == side) & (ctx.metric == m)].value.iloc[0]

    def comp_only(team, side, m):
        df = c.lo if side == 'offense' else c.ld
        return df[df.team == abbr[team]][COL[m]].iloc[0]

    o, r = c.opp, c.ref
    base = f"{c.league} distribution: {c.n_teams} teams, {c.comp}, {c.cfg['league_games_each']} games each"
    za = team_radar(c, all_games, '01_team_radar_zscore_all_games.png',
                    f'Team tendency vs {c.league} teams, z-scores (team values: ALL games played)',
                    f"{base} · team values: all games ({o['name']} {o['games_all']}, {r['name']} {r['games_all']})")
    zs = team_radar(c, comp_only, '01b_team_radar_zscore_competition_only.png',
                    f'Team tendency vs {c.league} teams, z-scores (like for like: {c.comp} only)',
                    f"{base} · {o['name']} {o['games']} games, {r['name']} {r['games']} logged games")
    pd.concat([za.assign(basis='all_games'), zs.assign(basis='competition_only')]).round(3).to_csv(
        c.out / 'team_zscores_vs_league_teams.csv', index=False)


# --------------------------------------------------------------------------------------------- 02 / 03
def plot02_03(c: Ctx) -> None:
    """Figures 02 (opponent play types) and 03 (offensive PPP by play type, reference vs opponent)."""
    # REVIEW: needs Synergy-extracted CSVs (see module docstring); check the data before using the figure.
    o, r = c.opp['name'], c.ref['name']
    vo, vd = c.read('opp_playtypes_offense.csv'), c.read('opp_playtypes_defense.csv')
    fig, axs = plt.subplots(1, 2, figsize=(12, 5.6))
    for ax, d, t in [(axs[0], vo[vo.poss >= MIN_PLAYTYPE_POSS].sort_values('poss'), f'{o} offense: play types run'),
                     (axs[1], vd[vd.poss >= MIN_PLAYTYPE_POSS].sort_values('poss'), f'Opponents vs {o}: play types faced')]:
        ax.barh(d.play_type, d.poss, color=NAVY, height=.6)
        for i, (p, q) in enumerate(zip(d.poss, d.ppp)):
            ax.text(p + 1, i, f'{p}  ·  {q:.2f} PPP', va='center', fontsize=8)
        ax.set_xlim(0, d.poss.max() * 1.4); ax.set_title(t, fontsize=11, loc='left'); ax.set_xlabel('Possessions (label: poss · PPP)')
    fig.suptitle(f"{o} ({c.comp}, {c.opp['games']} games): possessions by play type and what they yielded",
                 fontsize=13, fontweight='bold', x=.02, ha='left')
    c.foot(fig, c.scope + f' · plays ≥{MIN_PLAYTYPE_POSS} poss'); fig.tight_layout(rect=(0, .03, 1, .94))
    c.save(fig, '02_opponent_playtypes.png')

    bo = c.read('ref_playtypes_offense.csv')
    m = bo.merge(vo, on='play_type', suffixes=('_b', '_v'))
    m = m[(m.poss_b >= MIN_PLAYTYPE_POSS) & (m.poss_v >= MIN_PLAYTYPE_POSS)].sort_values('poss_v')
    fig, ax = plt.subplots(figsize=(10, 5.8)); y = np.arange(len(m)); h = .36
    ax.barh(y + h / 2, m.ppp_b, height=h, color=YELLOW, label=f"{r} ({c.ref['games']} {c.comp} games)")
    ax.barh(y - h / 2, m.ppp_v, height=h, color=NAVY, label=f"{o} ({c.opp['games']} {c.comp} games)")
    for i, (a, b, pa, pb) in enumerate(zip(m.ppp_b, m.ppp_v, m.poss_b, m.poss_v)):
        ax.text(a + .02, i + h / 2, f'{a:.2f} ({pa})', va='center', fontsize=8)
        ax.text(b + .02, i - h / 2, f'{b:.2f} ({pb})', va='center', fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels(m.play_type)
    ax.set_xlim(0, max(m.ppp_b.max(), m.ppp_v.max()) * 1.25)
    ax.set_xlabel(f'Points per possession (possessions in brackets); sorted by {o} volume'); ax.legend(frameon=False, loc='lower right')
    ax.set_title(f'Offensive PPP by play type: {r} vs {o} ({c.comp} only)', fontsize=13, fontweight='bold', loc='left')
    c.foot(fig, c.scope + f' · plays ≥{MIN_PLAYTYPE_POSS} poss for both'); fig.tight_layout(rect=(0, .03, 1, 1))
    c.save(fig, '03_playtype_ppp_ref_vs_opp.png')


# --------------------------------------------------------------------------------------------- players
def load_box(c: Ctx) -> pd.DataFrame:
    """Load the opponent's cumulative box table without the team total and add ``ppg`` and ``surname``."""
    # REVIEW: needs Synergy-extracted CSVs (see module docstring); check the data before using the figure.
    b = c.read('opp_players_cumulative_box.csv')
    b = b[b.PLAYER != 'TEAM TOTAL'].copy()
    for col in ['EFG%', 'TO%', 'TS%', '%FT']:
        b[col] = pct(b[col])
    b['AST/TO'] = pd.to_numeric(b['AST/TO'], errors='coerce'); b['SSM'] = pd.to_numeric(b['SSM'], errors='coerce')   # '-' for players without attempts
    b['ppg'] = b.PTS / b.GP
    b['surname'] = b.PLAYER.str.split().str[-1]
    return b


def plot04(c: Ctx, b: pd.DataFrame) -> None:
    """Figure 04: possessions used vs eFG% per opponent player, bubble = points per game."""
    # REVIEW: needs Synergy-extracted CSVs (see module docstring); check the data before using the figure.
    o = c.opp['name']
    z = b[b.POSS >= MIN_PLAYER_POSS]
    lg = np.average(c.lo.efg, weights=c.lo.poss_pg)
    fig, ax = plt.subplots(figsize=(9.8, 6.2)); ax.axhline(lg, color=GREY, ls='--', lw=1.2)
    xmax = z.POSS.max() * 1.12
    ax.set_xlim(z.POSS.min() - 12, xmax)
    ax.set_ylim(min(z['EFG%'].min(), lg) - 10, max(z['EFG%'].max(), lg) + 10)
    ax.text(xmax - 1, lg + .7, f'{c.league} average eFG% {lg:.1f} ({c.n_teams} teams, possession-weighted)', fontsize=8, color=INK_4, ha='right')
    sizes = z.ppg * PLAYER_BUBBLE_SCALE
    ax.scatter(z.POSS, z['EFG%'], s=sizes, color=NAVY, alpha=.9, edgecolor='white', linewidth=1.5, zorder=3)
    for _, r in z.iterrows():
        ax.text(r.POSS, r['EFG%'], f'{r.ppg:.1f}', ha='center', va='center', color='white', fontsize=8, fontweight='bold', zorder=4)
    ax.set_xlabel(f"Possessions used ({c.comp}, {c.opp['games']} games)"); ax.set_ylabel('eFG%')
    ax.set_title(f'{o} players (≥{MIN_PLAYER_POSS} poss): volume vs efficiency, {c.comp} only', fontsize=13, fontweight='bold', loc='left')
    ax.text(.99, .02, 'number in bubble = points per game (bubble area proportional to it)', transform=ax.transAxes, ha='right', fontsize=8, color=INK_4)
    c.foot(fig, f"{c.comp} only: {o} {c.opp['games']} games · dashed line = {c.league} team-level eFG% average")
    fig.tight_layout(rect=(0, .03, 1, 1))
    place_labels(fig, ax, [(r.POSS, r['EFG%'], r.surname, np.sqrt(s) / 2) for (_, r), s in zip(z.iterrows(), sizes)], fs=9,
                 markers=[(r.POSS, r['EFG%'], np.sqrt(s) / 2) for (_, r), s in zip(z.iterrows(), sizes)])
    c.save(fig, '04_players_volume_efficiency.png')


def plot05b(c: Ctx, b: pd.DataFrame) -> None:
    """Figure 05b: per-player radars, percentile rank within the opponent's roster."""
    # REVIEW: needs Synergy-extracted CSVs (see module docstring); check the data before using the figure.
    o = c.opp['name']
    r = b[b.POSS >= MIN_RADAR_POSS].copy(); r['TOinv'] = -r['TO%']
    cols = ['PPP', 'EFG%', 'TS%', 'TOinv', 'AST/TO', '%FT', 'SSM']
    labs = ['PPP', 'eFG%', 'TS%', 'TO% (inv.)', 'AST/TO', '%FT', 'Shot making']
    R = r[cols].rank(pct=True)
    ang = np.r_[np.linspace(0, 2 * np.pi, len(cols), endpoint=False), 0]
    n = len(r); nrow = max(1, int(np.ceil(n / 4)))
    fig, axs = plt.subplots(nrow, 4, figsize=(13, 4.2 * nrow), subplot_kw=dict(polar=True)); axs = np.atleast_1d(axs)
    for ax, (i, q) in zip(axs.flat, r.iterrows()):
        v = np.r_[R.loc[i].values, R.loc[i].values[0]]
        ax.plot(ang, v, color=NAVY, lw=2); ax.fill(ang, v, color=NAVY, alpha=.2)
        ax.set_xticks(ang[:-1]); ax.set_xticklabels(labs, fontsize=6.5); ax.set_yticks([.5]); ax.set_yticklabels([]); ax.set_ylim(0, 1)
        ax.set_title(f"{q.PLAYER.split(' ', 1)[1]}\n{q['OFFENSIVE ROLE']} · {int(q.POSS)} poss", fontsize=8.5, pad=20)
    for ax in axs.flat[n:]:
        ax.axis('off')
    fig.suptitle(f'{o} players (≥{MIN_RADAR_POSS} poss, {c.comp}): percentile rank within the {o} roster, not vs league',
                 fontsize=13, fontweight='bold', x=.02, ha='left')
    c.foot(fig, c.scope + ' · ring = roster median; role labels as shown by Synergy'); fig.tight_layout(rect=(0, .03, 1, .95))
    c.save(fig, '05b_player_radars_roster_percentile.png')


def plot06(c: Ctx) -> None:
    """Figure 06: possessions used by play type, stacked per player."""
    # REVIEW: needs Synergy-extracted CSVs (see module docstring); check the data before using the figure.
    o = c.opp['name']
    pp = c.read('opp_players_playtypes_offense.csv')
    pv = pp.pivot_table(index='player', columns='play_type', values='poss', aggfunc='sum', fill_value=0)
    pv = pv[pv.sum(axis=1) >= MIN_MIX_POSS]; pv = pv.loc[pv.sum(axis=1).sort_values().index]
    order = pv.sum().sort_values(ascending=False).index; pv = pv[order]
    fig, ax = plt.subplots(figsize=(11, 5.8)); left = np.zeros(len(pv))
    for k, col in zip(order, PALETTE * 3):
        ax.barh(pv.index, pv[k], left=left, color=col, edgecolor='white', linewidth=1, label=k, height=.65); left += pv[k].values
    ax.set_xlabel('Possessions used by play type (possessions ended by the player: shot, turnover or free-throw trip; not time on court)')
    ax.legend(frameon=False, fontsize=7.5, ncol=3, loc='lower right')
    ax.set_title(f'{o} players: possessions used by play type (≥{MIN_MIX_POSS} poss, {c.comp})', fontsize=13, fontweight='bold', loc='left')
    c.foot(fig, c.scope + ' · possessions = ones the player ended (shot, TO, FT trip)'); fig.tight_layout(rect=(0, .03, 1, 1))
    c.save(fig, '06_players_playtype_mix.png')


def radar(ax: Axes, labels: Sequence[str], made_att: Sequence[tuple[int, int]], title: str) -> None:
    """Draw a polar made/attempted chart; the outer ring is the largest attempt count."""
    n = len(labels); ang = np.r_[np.linspace(0, 2 * np.pi, n, endpoint=False), 0]
    M = np.array([x[0] for x in made_att], float); A = np.array([x[1] for x in made_att], float); mx = max(A.max(), 1)
    ax.plot(ang, np.r_[A, A[0]], color=NAVY, lw=1.2); ax.fill(ang, np.r_[A, A[0]], color=NAVY, alpha=.15)
    ax.plot(ang, np.r_[M, M[0]], color=YELLOW, lw=1.6); ax.fill(ang, np.r_[M, M[0]], color=YELLOW, alpha=.55)
    ax.set_ylim(0, mx * 1.28); ax.set_xticks(ang[:-1]); ax.set_xticklabels(labels, fontsize=7.5)
    ax.set_yticks([mx]); ax.set_yticklabels([f'{int(mx)}'], fontsize=6.5, color=INK_6); ax.tick_params(axis='x', pad=14)
    for a_, m_, at in zip(ang[:-1], M, A):
        if at > 0:
            ax.text(a_, mx * 1.13, f'{int(m_)}/{int(at)}', ha='center', va='center', fontsize=7, color=INK, fontweight='bold')
    ax.set_title(title, fontsize=8, pad=14, color=INK_3)


def plot05(c: Ctx, b: pd.DataFrame) -> None:
    """Figures 05 and 05c: per player, radars by location / play type, and bars of shot types in a separate figure."""
    # REVIEW: needs Synergy-extracted CSVs (see module docstring); check the data before using the figure.
    zp = c.read('opp_players_fg_by_zone_and_playtype.csv')
    st = c.read('opp_players_shottype_within_playtype.csv')
    shot = {}
    for r in st.itertuples():
        shot.setdefault((r.player, r.play_type), []).append((r.shot_type, r.fga, r.fgm))
    meta = b.set_index('surname')

    def grp(p: str, dim: str, order: Sequence[str]) -> list[tuple[int, int]]:
        d = zp[(zp.player == p) & (zp.dimension == dim)].set_index('category')
        return [(int(d.loc[g, 'fgm']), int(d.loc[g, 'fga'])) if g in d.index else (0, 0) for g in order]

    players = sorted(zp.player.unique(), key=lambda p: -meta.loc[p, 'POSS'] if p in meta.index else 0)
    for p in players:
        pt = zp[(zp.player == p) & (zp.dimension == 'play_type')]
        fga = int(pt.fga.sum())
        keep = pt[(pt.fga >= MIN_SHOT_TYPE_FGA) & (pt.fga >= MIN_SHOT_TYPE_SHARE * max(fga, 1))].sort_values('fga', ascending=False)
        ex = [(p, k) for k in keep.category if (p, k) in shot]
        missing = [k for k in keep.category if (p, k) not in shot]
        head = f'{fga} FGA'
        if p in meta.index:
            head += f', {int(meta.loc[p, "FG MADE"])} made, {int(meta.loc[p, "POSS"])} possessions used'
        sub = f"{head} · {c.comp}, {c.opp['name']} {c.opp['games']} games"
        fname = p.lower().replace(' ', '_')

        fig = plt.figure(figsize=(12.5, 6.8))
        gs = GridSpec(1, 2, figure=fig, wspace=.6, left=.05, right=.95, top=.78, bottom=.19)
        radar(fig.add_subplot(gs[0, 0], projection='polar'), ZONES, grp(p, 'shot_location', ZONES), 'Shot location (made/attempted)')
        radar(fig.add_subplot(gs[0, 1], projection='polar'), PT_LAB, grp(p, 'play_type', PT_ORDER), 'Play type (made/attempted)')
        fig.text(.02, .955, f'{p}: field goals attempted vs made', fontsize=14, fontweight='bold', ha='left')
        fig.text(.02, .905, sub, fontsize=9, color=INK_3)
        fig.legend(handles=[Patch(fc=NAVY, alpha=.3, label='Attempted'), Patch(fc=YELLOW, alpha=.8, label='Made')],
                   loc='lower left', ncol=2, frameon=False, bbox_to_anchor=(.02, .085))
        note = ('*Other = handoffs, post-ups, miscellaneous plays. Zones: Synergy 11-zone chart grouped as Paint (incl. rim), Mid-range '
                '(other two-point zones), Corner 3, Wing 3, Top 3. Outer ring label = max attempts. Free throws excluded.')
        fig.text(.02, .075, textwrap.fill(note, width=170), fontsize=6.8, color=INK_4, va='top')
        c.foot(fig, f'{c.comp} only')
        c.save(fig, f'05_player_{fname}_shot_profile.png', dpi=150)

        if not ex:
            continue
        n = len(ex)
        fig, axs = plt.subplots(1, n, figsize=(max(6.5 * n, 8.5), 5.6), squeeze=False)
        fig.subplots_adjust(left=.3 / n, right=.97, top=.7, bottom=.27, wspace=1.0)
        for ax, k in zip(axs[0], ex):
            d = sorted(shot[k], key=lambda x: -x[1]); y = np.arange(len(d))[::-1]
            ax.barh(y, [x[1] for x in d], color=NAVY, alpha=.25, height=.62); ax.barh(y, [x[2] for x in d], color=YELLOW, height=.62)
            for yy, x in zip(y, d):
                ax.text(x[1] + .2, yy, f'{x[2]}/{x[1]}', va='center', fontsize=9, fontweight='bold')
            ax.set_yticks(y); ax.set_yticklabels([textwrap.fill(x[0], 20) for x in d], fontsize=9)
            ax.set_xlim(0, max(x[1] for x in d) * 1.25); ax.set_xlabel('Field goal attempts', fontsize=9)
            ax.set_title(f"{PT_SHORT.get(k[1], k[1].lower())[0].upper() + PT_SHORT.get(k[1], k[1].lower())[1:]}\n({sum(x[1] for x in d)} attempts; made/attempted)",
                         fontsize=10, pad=10, color=INK_3)
            ax.spines['left'].set_visible(False); ax.tick_params(axis='y', length=0)
        fig.text(.02, .955, f'{p}: shot types within play types', fontsize=14, fontweight='bold', ha='left')
        fig.text(.02, .895, sub, fontsize=9, color=INK_3)
        fig.legend(handles=[Patch(fc=NAVY, alpha=.3, label='Attempted'), Patch(fc=YELLOW, alpha=.8, label='Made')],
                   loc='lower left', ncol=2, frameon=False, bbox_to_anchor=(.02, .04))
        rule = f'Play types with at least {MIN_SHOT_TYPE_FGA} attempts'
        if MIN_SHOT_TYPE_SHARE: rule += f' and at least {MIN_SHOT_TYPE_SHARE:.0%} of the player\'s attempts'
        rule += '.'
        if missing:
            rule += ' Shot types not extracted for: ' + ', '.join(missing) + '.'
        fig.text(.02, .025, textwrap.fill(rule, width=int(max(6.5 * n, 8.5) * 13.5)), fontsize=7, color=INK_4, va='top')
        c.save(fig, f'05c_player_{fname}_shot_types.png', dpi=150)


# --------------------------------------------------------------------------------------------- lineups
def plot07_09(c: Ctx) -> None:
    """Figures 07 (lineup usage vs PPP), 08 (scored vs allowed) and 09 (shot-profile differences)."""
    # REVIEW: needs Synergy-extracted CSVs (see module docstring); check the data before using the figure.
    o = c.opp['name']; cfg = c.cfg
    mn = cfg.get('lineup_min_poss', DEFAULT_LINEUP_MIN_POSS)
    excl = cfg.get('exclude_players', [])
    excl_txt = (', excl. ' + ', '.join(excl)) if excl else ''
    m = c.read('opp_lineups_off_def.csv')
    m['k'] = m.lineup.map(short_keys(m.lineup.unique()))
    o_ = m.dropna(subset=['poss']); o_ = o_[o_.poss >= mn].copy()
    row = c.lo[c.lo.team == c.opp['abbr']].iloc[0]
    tp, tposs = row.pts_pg * row.gp, row.poss_pg * row.gp
    team_ppp = tp / tposs

    # ---- 07 usage vs PPP
    fig, ax = plt.subplots(figsize=(11.5, 6.6)); ax.axhline(team_ppp, color=INK_4, ls='--', lw=1.2)
    xr = o_.poss.max(); ax.set_xlim(0, xr * 1.15)
    ax.text(xr * 1.13, team_ppp - .035, f"{o} whole-team offense in {c.comp}: {team_ppp:.2f} points per possession\n"
            f"({tp:.0f} points in {tposs:.0f} possessions, all lineups together, including those not shown)",
            ha='right', va='top', fontsize=8.5, color=INK_2)
    sizes = o_.pts * LINEUP_PTS_SCALE
    ax.scatter(o_.poss, o_.ppp, s=sizes, color=NAVY, alpha=.85, edgecolor='white', linewidth=1.3, zorder=3)
    for _, q in o_[o_.pts >= LABEL_LINEUP_PTS].iterrows():
        ax.text(q.poss, q.ppp, f'{int(q.pts)}', ha='center', va='center', color='white', fontsize=8.5, fontweight='bold', zorder=4)
    ax.set_xlabel('Offensive possessions with the lineup on court (usage)'); ax.set_ylabel('Points per possession (lineup on court)')
    ax.set_title(f'{o} 5-man lineups ({c.comp}): usage vs scoring efficiency', fontsize=13, fontweight='bold', loc='left')
    ref_pts = sorted({int(round(o_.pts.min())), int(round(o_.pts.median())), int(round(o_.pts.max()))})
    ax.legend(handles=[Line2D([0], [0], marker='o', color='w', markerfacecolor=NAVY, markersize=np.sqrt(LINEUP_PTS_SCALE * v), label=f'{v} pts') for v in ref_pts]
              + [Line2D([0], [0], color=INK_4, ls='--', label=f'{o} whole-team offense PPP ({team_ppp:.2f})')],
              title='Bubble area = points scored by the lineup', loc='upper right', frameon=False, fontsize=8, title_fontsize=8,
              labelspacing=1.4, borderpad=1)
    ax.text(.99, .02, f'number in bubble = points scored (shown for lineups with ≥{LABEL_LINEUP_PTS} points); small samples below ~15 poss',
            transform=ax.transAxes, ha='right', fontsize=7.5, color=INK_4)
    c.foot(fig, f'{c.comp}, {o} {c.opp["games"]} games · lineups with ≥{mn} offensive possessions{excl_txt} ({len(o_)} lineups)')
    fig.tight_layout(rect=(0, .03, 1, 1))
    lab = o_[(o_.poss >= LABEL_LINEUP_POSS) | (o_.ppp >= LABEL_LINEUP_PPP)]
    place_labels(fig, ax, [(q.poss, q.ppp, q.k, np.sqrt(LINEUP_PTS_SCALE * q.pts) / 2) for _, q in lab.iterrows()],
                 markers=[(q.poss, q.ppp, np.sqrt(LINEUP_PTS_SCALE * q.pts) / 2) for _, q in o_.iterrows()])
    c.save(fig, '07_lineups_usage_vs_ppp.png')

    # ---- 08 offense vs defense
    b2 = m.dropna(subset=['poss', 'def_poss']); b2 = b2[(b2.poss >= mn) & (b2.def_poss >= mn)].copy()
    b2['tot'] = b2.poss + b2.def_poss
    fig, ax = plt.subplots(figsize=(13.2, 7.2))
    lo_, hi_ = min(b2.ppp.min(), b2.opp_ppp.min()) - .1, max(b2.ppp.max(), b2.opp_ppp.max()) + .1
    ax.plot([lo_, hi_], [lo_, hi_], color=GREY, ls='--', lw=1, zorder=1)
    ax.scatter(b2.ppp, b2.opp_ppp, s=b2.tot * LINEUP_POSS_SCALE, color=NAVY, alpha=.8, edgecolor='white', linewidth=1.3, zorder=3)
    big = b2[b2.tot >= BIG_BUBBLE_POSS].sort_values('tot', ascending=False).reset_index(drop=True)
    for i, q in big.iterrows():
        ax.text(q.ppp, q.opp_ppp, str(i + 1), ha='center', va='center', color='white', fontsize=8.5, fontweight='bold', zorder=5)
    key = f'Largest bubbles (≥{BIG_BUBBLE_POSS} total possessions)\n' + '\n'.join(
        f'{i + 1}  {q.lineup.replace(" / ", ", ")}\n     {int(q.poss)} off. / {int(q.def_poss)} def. poss · {q.ppp:.2f} scored / {q.opp_ppp:.2f} allowed'
        for i, q in big.iterrows())
    fig.text(.70, .86, key, fontsize=8, va='top', ha='left', linespacing=1.45, bbox=dict(boxstyle='round,pad=.6', fc=KEY_BOX_BG, ec=KEY_BOX_EDGE))
    ax.set_xlabel('Points scored per possession (lineup on court)'); ax.set_ylabel('Points allowed per possession (lineup on court)'); ax.invert_yaxis()
    ax.set_title(f'{o} lineups: scoring vs allowing ({c.comp})', fontsize=13, fontweight='bold', loc='left')
    ax.legend(handles=[Line2D([0], [0], color=GREY, ls='--', label='Points scored = points allowed (below the line: scores more than allows)'),
                       Line2D([0], [0], marker='o', color='w', markerfacecolor=NAVY, markersize=5,
                              label=f'Bubble area = offensive + defensive possessions ({int(b2.tot.min())} to {int(b2.tot.max())})')],
              loc='lower left', frameon=False, fontsize=8)
    fig.text(.01, .035, f'Included: lineups with at least {mn} possessions on BOTH offense and defense ({len(b2)} lineups)'
             f'{", excluding " + ", ".join(excl) if excl else ""}. Y axis inverted (better defense is higher on the chart).', fontsize=7.5, color=INK_3)
    c.foot(fig, f'{c.comp}, {o} {c.opp["games"]} games'); fig.tight_layout(rect=(0, .06, .68, 1))
    full = lambda s: ' / '.join(s.split(' / '))
    qx, qy, qm = b2.loc[b2.ppp.idxmax()], b2.loc[b2.opp_ppp.idxmax()], b2.loc[b2.opp_ppp.idxmin()]
    box = dict(boxstyle='round,pad=.3', fc='white', ec=CALLOUT_EDGE)
    callouts = []
    if qx.lineup == qy.lineup:
        callouts.append((qx.ppp, qx.opp_ppp, f'Highest x and highest y ({qx.ppp:.2f} scored / {qx.opp_ppp:.2f} allowed):\n{full(qx.lineup)}\n'
                         f'{int(qx.poss)} off. / {int(qx.def_poss)} def. poss', 0))
    else:
        callouts += [(qx.ppp, qx.opp_ppp, f'Highest x: {full(qx.lineup)} ({qx.ppp:.2f})', 0),
                     (qy.ppp, qy.opp_ppp, f'Highest y: {full(qy.lineup)} ({qy.opp_ppp:.2f})', 0)]
    callouts.append((qm.ppp, qm.opp_ppp, f'Lowest y (best defense, {qm.opp_ppp:.2f}):\n{full(qm.lineup)}\n'
                     f'{int(qm.poss)} off. / {int(qm.def_poss)} def. poss', 0))
    place_labels(fig, ax, [(x, y, t, 12) for x, y, t, _ in callouts], bbox=box, fs=8,
                 extra_cands=[(-110, -12, 'right'), (110, 12, 'left'), (-130, 10, 'right'), (130, -10, 'left')],
                 markers=[(q.ppp, q.opp_ppp, np.sqrt(q.tot * LINEUP_POSS_SCALE) / 2) for _, q in b2.iterrows()])
    c.save(fig, '08_lineups_offense_vs_defense.png')

    # ---- 09 style profile
    zz = o_[o_.poss >= MIN_STYLE_POSS].sort_values('tpa_rate')
    if len(zz):
        fig, axs = plt.subplots(1, 5, figsize=(14, max(3.5, .3 * len(zz) + 1.8)), sharey=True)
        for ax, (col, t) in zip(axs, [('tpa_rate', '3PA / FGA'), ('ft_rate', 'FTA / FGA'), ('to_pct', 'TO% (Synergy)'), ('efg', 'eFG%'), ('ssm', 'Shot making (SSM)')]):
            v = zz[col] / 100 if col == 'to_pct' else zz[col]
            ax.barh(range(len(zz)), v, color=NAVY, height=.6); ax.axvline(v.mean(), color=GREY, ls='--', lw=1); ax.set_title(t, fontsize=10)
            for i, x in enumerate(v):
                ax.text(max(x, 0), i, f' {x:.2f}', va='center', fontsize=7)
        axs[0].set_yticks(range(len(zz))); axs[0].set_yticklabels([f'{k} ({int(p)})' for k, p in zip(zz.k, zz.poss)], fontsize=7.5)
        fig.suptitle(f'Lineup shot-profile differences ({c.comp}, ≥{MIN_STYLE_POSS} off. poss; dashed = mean of these lineups; poss in brackets)',
                     fontsize=12, fontweight='bold', x=.02, ha='left')
        c.foot(fig, f'{c.comp}, {o} {c.opp["games"]} games{excl_txt}'); fig.tight_layout(rect=(0, .03, 1, .95))
        c.save(fig, '09_lineups_style_profile.png')


# --------------------------------------------------------------------------------------------- main
def main() -> None:
    """Parse the command line and write every scouting plot for the given data folder."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('data_dir', help='folder with config.json and the CSVs (see its README.md)')
    ap.add_argument('--out', help='output folder (default: reports/synergy_<data folder name>)')
    ap.add_argument('--date'); ap.add_argument('--author')
    a = ap.parse_args()
    d = Path(a.data_dir)
    d = d if d.is_absolute() else ROOT / d
    cfg = json.loads((d / 'config.json').read_text(encoding='utf-8'))
    if a.date: cfg['date'] = a.date
    if a.author: cfg['author'] = a.author
    out = Path(a.out) if a.out else ROOT / 'reports' / f'synergy_{d.name}'
    out = out if out.is_absolute() else ROOT / out
    warnings.warn(REVIEW_NOTE, stacklevel=1)
    c = Ctx(d, out, cfg)
    b = load_box(c)
    plot01(c); plot02_03(c); plot04(c, b); plot05b(c, b); plot06(c); plot05(c, b); plot07_09(c)
    print('plots written to', c.plots)


if __name__ == '__main__':
    main()
