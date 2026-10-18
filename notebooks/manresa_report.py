"""Scouting report on Kids&Us Manresa (Liga Endesa + EuroCup): top-10 players by minutes and lineups.

    python notebooks/manresa_fetch.py     # refresh data/manresa/ first
    python notebooks/manresa_report.py

Writes reports/matchup_Kids_Us_Manresa_scouting_before_<date>/ (README.md + PNGs); then run
notebooks/build_site.py to publish it. Samples are tiny early in the season: read as tendencies.
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import lba_style
from lba_style import (BLUE, GREEN, RED, SUP_KW, TEXT, TEXT2, draw_half_court, save_fig,
                       style_axes)
from lineups_report import fig_lineups
from manresa_fetch import player_key

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "manresa"
TOP_N = 10
MIN_UNIT_SECS = 180
ROLE_EN = {"Base": "PG", "Escolta": "SG", "Alero": "SF", "Ala-pívot": "PF", "Pívot": "C"}
POS_EN = {"Guard": "G", "Forward": "F", "Center": "C"}
STAT_SUMS = ["pts", "fg2m", "fg2a", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb", "ast", "stl", "tov",
             "plus_minus"]


def load() -> tuple[pd.DataFrame, ...]:
    """Read the fetched CSVs and give every player one merged key and display name."""
    games, box, events, heights, assists, shots = (
        pd.read_csv(DATA / f"{n}.csv") for n in ("games", "box", "events", "heights", "assists", "shots"))
    for df in (box, events, heights):
        df["key"] = df.player.map(lambda n: player_key(n) if isinstance(n, str) and n else "")
    names = box.sort_values("comp", ascending=False).drop_duplicates("key").set_index("key").player
    for df in (box, events):
        df["player"] = df.key.map(names).fillna(df.player)
    for df, cols in ((assists, ("passer", "scorer")), (shots, ("player",))):
        for col in cols:
            df[col] = df[col].map(lambda n: names.get(player_key(n), n))
    for df in (box, events, games, assists):
        df["game_id"] = df.game_id.astype(str)
    return games, box, events, heights, assists, shots


def player_table(box: pd.DataFrame, heights: pd.DataFrame) -> pd.DataFrame:
    """Per-player season line over both competitions, top N by total minutes."""
    total = box.groupby("key")[STAT_SUMS + ["sec"]].sum()
    total["gp"] = box.groupby("key").size()
    per_comp = box.pivot_table(index="key", columns="comp", values="pts", aggfunc="mean")
    roles = box[box.role_es != ""].dropna(subset=["role_es"]).groupby("key").role_es.first()
    table = total.sort_values("sec", ascending=False).head(TOP_N).copy()
    table["player"] = box.drop_duplicates("key").set_index("key").player.reindex(table.index)
    table["role"] = roles.map(ROLE_EN).reindex(table.index)
    hh = heights.drop_duplicates("key").set_index("key")
    table["height"] = hh.height_cm.reindex(table.index)
    table["role"] = table.role.fillna(hh.position_en.map(POS_EN).reindex(table.index))
    g = table.gp
    table["mpg"] = table.sec / 60 / g
    for col in ("pts", "reb", "ast", "stl", "tov", "plus_minus"):
        table[f"{col}_pg"] = (table.oreb + table.dreb if col == "reb" else table[col]) / g
    table["fg_pct"] = (table.fg2m + table.fg3m) / (table.fg2a + table.fg3a) * 100
    table["fg3_pct"] = table.fg3m / table.fg3a * 100
    table["ft_pct"] = table.ftm / table.fta * 100
    table["fg3a_pg"] = table.fg3a / g
    table["ppg_acb"] = per_comp.get("Liga Endesa").reindex(table.index)
    table["ppg_eur"] = per_comp.get("EuroCup").reindex(table.index)
    return table


def lineup_stints(events: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """Five-man stints from substitution events, with elapsed seconds and plus/minus.

    Raises:
        ValueError: if a game's stints do not add up to its length or final margin.
    """
    rows = []
    for gid, ev in events.groupby("game_id"):
        on: set[str] = set()
        last_t, last_score = 0, (0, 0)
        for t, grp in ev.groupby("elapsed", sort=True):
            if t > last_t and len(on) == 5:
                rows.append({"game_id": gid, "lineup": tuple(sorted(on)), "secs": t - last_t,
                             "pm": (grp.man.iloc[0] - grp.opp.iloc[0]) - (last_score[0] - last_score[1])})
            if t > last_t:
                last_t, last_score = t, (grp.man.iloc[0], grp.opp.iloc[0])
            for kind, player in zip(grp.kind, grp.player):
                if kind == "OUT":
                    on.discard(player)
                elif kind in ("START", "IN"):
                    on.add(player)
    stints = pd.DataFrame(rows)
    for gid, g in stints.groupby("game_id"):
        row = games[games.game_id == gid].iloc[0]
        if g.secs.sum() < 2400 or g.pm.sum() != row.man_pts - row.opp_pts:
            raise ValueError(f"game {gid}: {g.secs.sum()}s, pm {g.pm.sum()} vs "
                             f"{row.man_pts - row.opp_pts}")
    return stints


def aggregate_units(stints: pd.DataFrame) -> pd.DataFrame:
    """One row per five-man unit with minutes, plus/minus and net rating per 40."""
    agg = stints.groupby("lineup").agg(secs=("secs", "sum"), pm=("pm", "sum"), stints=("secs", "size"),
                                       games=("game_id", "nunique")).reset_index()
    agg["lineup"] = agg.lineup.map(lambda unit: tuple(name.split()[-1].title() for name in unit))
    agg["net40"] = agg.pm / agg.secs * 2400
    return agg


def fig_players(table: pd.DataFrame, out: Path) -> Path:
    """Table figure of the top-10 players."""
    cols = ["Player", "Pos", "Ht", "GP", "MPG", "PPG", "RPG", "APG", "TOV", "STL", "FG%", "3P%", "FT%"]
    cells = [[r.player, r.role or "-", f"{r.height:.0f}" if pd.notna(r.height) else "-", int(r.gp),
              f"{r.mpg:.1f}", f"{r.pts_pg:.1f}", f"{r.reb_pg:.1f}", f"{r.ast_pg:.1f}", f"{r.tov_pg:.1f}",
              f"{r.stl_pg:.1f}", f"{r.fg_pct:.0f}", f"{r.fg3_pct:.0f}" if r.fg3a else "-", f"{r.ft_pct:.0f}"]
             for r in table.itertuples()]
    fig, ax = plt.subplots(figsize=(11, 0.42 * len(cells) + 1.4))
    ax.axis("off")
    tab = ax.table(cellText=cells, colLabels=cols, loc="center", cellLoc="center")
    tab.auto_set_font_size(False)
    tab.set_fontsize(9.5)
    tab.scale(1, 1.5)
    for (row, col), cell in tab.get_celld().items():
        cell.set_edgecolor(lba_style.GRID)
        if row == 0:
            cell.set_facecolor(lba_style.GOLD)
            cell.set_text_props(fontweight="bold", color=TEXT)
        if col == 0:
            cell._loc = "left"
            cell.set_text_props(ha="left")
    tab.auto_set_column_width(range(len(cols)))
    fig.suptitle("Kids&Us Manresa: top 10 by minutes, Liga Endesa + EuroCup 2026/27", **SUP_KW)
    path = out / "01_top10_players.png"
    save_fig(fig, path)
    plt.close(fig)
    return path


def starters_table(box: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """One row per game with the five starters (alphabetical surnames) and the result."""
    rows = []
    for g in games.itertuples():
        five = sorted(p.split()[-1] for p in box[(box.game_id == g.game_id) & (box.starter == 1)].player)
        rows.append({"comp": g.comp, "opponent": g.opponent, "home": "H" if g.home else "A",
                     "score": f"{g.man_pts}-{g.opp_pts}", "starters": " / ".join(five)})
    return pd.DataFrame(rows)


def fig_assists(assists: pd.DataFrame, out: Path) -> tuple[Path, pd.DataFrame]:
    """Passer (rows) by scorer (columns) heatmap of assisted field goals, all 7 games."""
    matrix = assists.pivot_table(index="passer", columns="scorer", values="pts", aggfunc="size", fill_value=0)
    players = (matrix.sum(axis=1).add(matrix.sum(axis=0), fill_value=0)).sort_values(ascending=False)
    players = players[players >= 5].index
    matrix = matrix.reindex(index=players, columns=players, fill_value=0)
    order = matrix.sum(axis=1).sort_values(ascending=False).index
    matrix = matrix.loc[order, order]
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.imshow(matrix.values, cmap="YlOrBr", vmin=0)
    for (i, j), val in np.ndenumerate(matrix.values):
        if val:
            ax.text(j, i, val, ha="center", va="center", fontsize=10, color=TEXT)
    labels_x = [f"{c}\n({int(matrix[c].sum())})" for c in matrix.columns]
    labels_y = [f"{r.split()[-1]} ({int(matrix.loc[r].sum())})" for r in matrix.index]
    ax.set_xticks(range(len(labels_x)), labels_x, fontsize=8.5, rotation=45, ha="left")
    ax.set_yticks(range(len(labels_y)), labels_y, fontsize=9)
    ax.xaxis.tick_top()
    ax.set_xlabel("scorer (assisted baskets received)", labelpad=8)
    ax.xaxis.set_label_position("top")
    ax.set_ylabel("passer (assists given)")
    fig.suptitle(f"Kids&Us Manresa assist matrix, Liga Endesa + EuroCup ({len(assists)} assisted baskets)",
                 fontsize=13, fontweight="bold", color=TEXT)
    path = out / "02_assist_matrix.png"
    save_fig(fig, path)
    plt.close(fig)
    return path, matrix


DIST_BINS = [("At the rim (0-1.5 m)", 0, 150), ("Close (1.5-3 m)", 150, 300),
             ("Mid-range (3-4.5 m)", 300, 450), ("Long 2 (4.5 m+)", 450, 10_000)]
DIST_LABELS = [b[0] for b in DIST_BINS] + ["3-pointers"]


def shot_zones(shots: pd.DataFrame) -> pd.DataFrame:
    """Add distance (m) and a distance bin (2-pointers by distance from the rim, 3-pointers apart)."""
    shots = shots.copy()
    shots["dist"] = np.hypot(shots.x, shots.y) / 100
    shots["bin"] = "3-pointers"
    for label, lo, hi in DIST_BINS:
        shots.loc[(shots.three == 0) & (shots.dist * 100 >= lo) & (shots.dist * 100 < hi), "bin"] = label
    return shots


def distance_table(shots: pd.DataFrame, scorers: list[str]) -> pd.DataFrame:
    """Share of attempts and FG% per distance bin for the team and each main scorer."""
    cols = {}
    for label, group in [("Team", shots)] + [(p, shots[shots.player == p]) for p in scorers]:
        att = group.bin.value_counts().reindex(DIST_LABELS, fill_value=0)
        made = group.groupby("bin").made.sum().reindex(DIST_LABELS, fill_value=0)
        cols[label] = pd.DataFrame({"share": att / att.sum() * 100, "fg": made / att.replace(0, np.nan) * 100,
                                    "att": att, "made": made})
    return pd.concat(cols, axis=1)


def attempt_split(shots: pd.DataFrame, scorers: list[str]) -> pd.DataFrame:
    """Per distance bin: each main scorer's share of the team's attempts, plus the rest (sums to 100)."""
    who = shots.player.where(shots.player.isin(scorers), "Rest of the team")
    counts = pd.crosstab(shots.bin, who).reindex(index=DIST_LABELS, columns=scorers + ["Rest of the team"],
                                                 fill_value=0)
    return counts.div(counts.sum(axis=1), axis=0) * 100, counts.sum(axis=1)


def fig_distance(split: pd.DataFrame, totals: pd.Series, out: Path) -> Path:
    """Stacked bars per distance: who takes the team's shots (main scorers + rest = 100%)."""
    palette = [BLUE, GREEN, "#e08c52", "#b46aa5", "#c9ccd8"]
    fig, ax = plt.subplots(figsize=(12, 5.8))
    bottom = np.zeros(len(split))
    for color, name in zip(palette, split.columns):
        ax.bar(range(len(split)), split[name], bottom=bottom, color=color, label=name, width=0.62,
               edgecolor="white", linewidth=0.8)
        for i, val in enumerate(split[name]):
            if val >= 6:
                ax.text(i, bottom[i] + val / 2, f"{val:.0f}%", ha="center", va="center", fontsize=9,
                        color=TEXT)
        bottom += split[name].values
    ax.set_xticks(range(len(split)), [f"{label}\n{int(totals[label])} FGA" for label in split.index])
    ax.set_ylim(0, 100)
    ax.set_ylabel("share of the team's attempts at that distance (%)")
    style_axes(ax, "y")
    ax.legend(ncols=len(split.columns), loc="upper center", bbox_to_anchor=(0.5, -0.14), fontsize=8.5)
    fig.suptitle("Who takes the shots at each distance from the rim, EuroCup games", **SUP_KW)
    path = out / "03_shot_distance.png"
    save_fig(fig, path)
    plt.close(fig)
    return path


def fig_shot_charts(shots: pd.DataFrame, scorers: list[str], out: Path) -> Path:
    """One half-court chart per main scorer (EuroCup games only: ACB publishes no locations)."""
    fig, axes = plt.subplots(1, len(scorers), figsize=(4.6 * len(scorers), 4.6))
    for ax, player in zip(np.atleast_1d(axes), scorers):
        draw_half_court(ax)
        mine = shots[shots.player == player]
        for made, color, marker in ((0, RED, "x"), (1, GREEN, "o")):
            sel = mine[mine.made == made]
            ax.scatter(sel.x, sel.y, s=34, c=color, marker=marker, linewidths=1.4 if made == 0 else 0.6,
                       edgecolors="white" if made else None, alpha=0.9, zorder=3)
        ax.set_ylim(-200, 900)
        pct = mine.made.mean() * 100
        ax.set_title(f"{player}: {int(mine.made.sum())}/{len(mine)} FG ({pct:.0f}%)", fontsize=11)
    fig.suptitle("Shot charts of the main scorers, EuroCup games (green = made, red x = missed)", **SUP_KW)
    path = out / "04_shot_charts.png"
    save_fig(fig, path)
    plt.close(fig)
    return path


def tag(row: pd.Series) -> str:
    """One data-driven sentence on a player."""
    bits = []
    if row.pts_pg >= 14:
        bits.append("primary scorer")
    if row.ast_pg >= 4:
        bits.append("main creator")
    if row.reb_pg >= 6:
        bits.append("rebounder")
    if row.fg3a_pg >= 4:
        bits.append(f"volume shooter from 3 ({row.fg3a_pg:.1f} att, {row.fg3_pct:.0f}%)")
    if row.tov_pg >= 2.5:
        bits.append(f"turnover-prone ({row.tov_pg:.1f})")
    if row.ft_pct < 65 and row.fta / row.gp >= 2:
        bits.append(f"weak at the line ({row.ft_pct:.0f}%)")
    return ", ".join(bits) if bits else "role player"


def team_summary(games: pd.DataFrame) -> pd.DataFrame:
    """Record and scoring per competition plus overall."""
    g = games.assign(win=games.man_pts > games.opp_pts)
    out = g.groupby("comp").agg(gp=("win", "size"), w=("win", "sum"), ppg=("man_pts", "mean"),
                                opp=("opp_pts", "mean"))
    total = g.agg({"win": ["size", "sum"], "man_pts": "mean", "opp_pts": "mean"})
    out.loc["Total"] = [total.win["size"], total.win["sum"], total.man_pts["mean"], total.opp_pts["mean"]]
    return out


def extra_sections(starters: pd.DataFrame, assists: pd.DataFrame, matrix: pd.DataFrame,
                   dist: pd.DataFrame, scorers: list[str], shots: pd.DataFrame) -> list[str]:
    """README lines for starting fives, assist matrix, shot distances and shot charts."""
    L = ["## Starting fives", "", "| Comp | Opponent | H/A | Score | Starters |", "|---|---|---|---|---|"]
    L += [f"| {r.comp} | {r.opponent} | {r.home} | {r.score} | {r.starters} |" for r in starters.itertuples()]
    counts = starters.starters.value_counts()
    L += ["", f"{len(counts)} different starting fives in {len(starters)} games"
          + (f"; the most used ({counts.iloc[0]} games): {counts.index[0]}." if counts.iloc[0] > 1 else "."), ""]
    pairs = assists.groupby(["passer", "scorer"]).size().sort_values(ascending=False).head(5)
    L += ["## Assist matrix", "", "![assist matrix](02_assist_matrix.png)", "",
          f"Passer (rows) to scorer (columns), {len(assists)} assisted baskets linked from the play-by-play "
          "(about 90% of the box-score assists; the rest could not be matched to a basket). "
          "Players with 5+ assists given plus received.", "", "Most frequent combinations:", ""]
    L += [f"- {p} to {s}: {n}" for (p, s), n in pairs.items()]
    L += ["", "## Shot distribution by distance from the rim", "", "![distance](03_shot_distance.png)", "",
          "EuroCup games only (3 games, "
          f"{len(shots)} attempts): ACB does not publish shot locations. Main scorers = top 4 by total points. "
          "Table: share of each player's own attempts / FG%. The chart shows who takes the team's attempts at each distance.", "",
          "| Distance | " + " | ".join(dist.columns.get_level_values(0).unique()) + " |",
          "|---|" + "---|" * len(dist.columns.get_level_values(0).unique())]
    for label in DIST_LABELS:
        cells = [f"{dist[n].share[label]:.0f}% / " + (f"{dist[n].fg[label]:.0f}%" if dist[n].att[label] else "-")
                 for n in dist.columns.get_level_values(0).unique()]
        L.append(f"| {label} | " + " | ".join(cells) + " |")
    L += ["", "## Shot charts of the main scorers", "", "![shot charts](04_shot_charts.png)", ""]
    return L


def write_readme(out: Path, title_date: str, games: pd.DataFrame, table: pd.DataFrame,
                 units: pd.DataFrame, team: pd.DataFrame, extra: list[str]) -> None:
    """Write README.md (picked up by build_site.py)."""
    from lineups_report import pick

    L = ["# Kids&Us Manresa scouting report (Liga Endesa + EuroCup)", "",
         f"*Prepared for BC Roma. Data as of {title_date}: {len(games)} games "
         f"({(games.comp == 'Liga Endesa').sum()} Liga Endesa, {(games.comp == 'EuroCup').sum()} EuroCup). "
         "Sources: acb.com live stats, EuroLeague live API. Small sample, read as tendencies.*", "",
         "## Team snapshot", "", "| | GP | W-L | PPG | Opp PPG |", "|---|---|---|---|---|"]
    for comp, r in team.iterrows():
        L.append(f"| {comp} | {int(r.gp)} | {int(r.w)}-{int(r.gp - r.w)} | {r.ppg:.1f} | {r.opp:.1f} |")
    L += ["", "## Results", "", "| Comp | Opponent | H/A | Score |", "|---|---|---|---|"]
    for r in games.itertuples():
        L.append(f"| {r.comp} | {r.opponent} | {'H' if r.home else 'A'} | {r.man_pts}-{r.opp_pts} |")
    L += ["", "## Top 10 by total minutes", "", "![top 10](01_top10_players.png)", "",
          "Height in cm (EuroLeague roster), position from ACB role / EuroLeague roster. "
          "PPG split: Liga Endesa / EuroCup.", ""]
    for r in table.itertuples():
        ht = f"{r.height:.0f} cm" if pd.notna(r.height) else "height n/a"
        three = f"{r.fg3_pct:.0f}%" if r.fg3a else "-"
        L.append(f"- **{r.player}** ({r.role}, {ht}, {int(r.gp)} GP): {r.mpg:.1f} min, **{r.pts_pg:.1f} pts**, "
                 f"{r.reb_pg:.1f} reb, {r.ast_pg:.1f} ast, FG {r.fg_pct:.0f}% / 3P {three} / "
                 f"FT {r.ft_pct:.0f}%; PPG {r.ppg_acb:.1f} ACB / {r.ppg_eur:.1f} EC. "
                 f"{tag(pd.Series(r._asdict())).capitalize()}.")
    L += ["", "## Lineups", "", "![lineups](lineups_Kids_Us_Manresa.png)", "",
          f"Five-man units rebuilt from substitutions, both competitions combined; best/worst need "
          f"{MIN_UNIT_SECS // 60}+ minutes together. Net rating = point differential per 40 minutes. "
          f"{len(units)} different units in {units.secs.sum() / 60:.0f} minutes.", ""]
    used, best, worst = (df for _, df in pick(units, MIN_UNIT_SECS, 5))
    for label, df in (("Most used", used), ("Most effective", best), ("Least effective", worst)):
        L += [f"**{label}**", ""]
        L += [f"- {' / '.join(r.lineup)}: {r.secs / 60:.1f} min, {r.pm:+.0f} ({r.net40:+.0f} per 40), "
              f"{r.games} game{'s' if r.games > 1 else ''}" for r in df.itertuples()]
        L.append("")
    L += extra
    (out / "README.md").write_text("\n".join(L), encoding="utf-8")


def main() -> None:
    """Build the report."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", default=f"{date.today():%Y-%m-%d}")
    args = ap.parse_args()
    out = ROOT / "reports" / f"matchup_Kids_Us_Manresa_scouting_before_{args.before}"
    out.mkdir(parents=True, exist_ok=True)
    lba_style.SOURCE_NOTE = "acb.com + EuroLeague live API"
    games, box, events, heights, assists, shots = load()
    table = player_table(box, heights)
    scorers = box.groupby("player").pts.sum().loc[table.player].nlargest(4).index.tolist()
    shots = shot_zones(shots)
    dist = distance_table(shots, scorers)
    starters = starters_table(box, games)
    _, matrix = fig_assists(assists, out)
    split, totals = attempt_split(shots, scorers)
    fig_distance(split, totals, out)
    fig_shot_charts(shots, scorers, out)
    units = aggregate_units(lineup_stints(events, games))
    fig_players(table, out)
    fig_lineups(units, "Kids&Us Manresa", MIN_UNIT_SECS, 5, out, "2026/27", league="Liga Endesa + EuroCup")
    (out / "lineups_Kids&Us_Manresa.png").replace(out / "lineups_Kids_Us_Manresa.png")
    write_readme(out, args.before, games, table, units, team_summary(games),
                 extra_sections(starters, assists, matrix, dist, scorers, shots))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
