---
name: opponent-analysis
description: Write or update the opponent analysis of a game (weekly/games/<date>/analysis.md and its pages offense_tendencies.md, defense_tendencies.md, individual_tendencies.md): structure, where each fact lives, summary plus Details drop-down, links between sections, and how to refresh the numbers when new data arrives. Use when asked to write, update, lighten or review an opponent analysis, or after a new game of the opponent is in the data.
---

# Opponent analysis: structure and writing rules

The pages are plain markdown with automatic blocks (`{{ comparison }}`, `{{ figure: 07_key_players }}`, ...), merged by `notebooks/build_site.py`.
The templates are `weekly/template/page_*.md.j2` (their header comment lists the blocks); the text is yours and is never overwritten.

## 1. Every section: a summary, then a Details drop-down

* The lines before a line holding only `<!-- more -->` are the **summary**: the site draws them in a box labelled "In short". Two to four bullets or a short paragraph, the numbers a reader needs and nothing else.
* Everything after the marker goes into a **Details** drop-down (closed by default): tables, figures, secondary bullets, sample warnings, clips.
* A section that is only a summary (Key points, a pending box) needs no marker. A marker with nothing after it is ignored.
* The marker is the only comment that survives the build (`pages.expand` drops the others), so the HOW-TO comment at the top of a page must never contain the literal marker: it would close that comment early.

## 2. Every fact has one home

Write a number once, in the section that owns it, and link to it from everywhere else. Do not restate it in Key points, in What to expect or on another page.

| Fact | Home |
|---|---|
| Record, results, table | `analysis.md`, LBA so far |
| Team PPP, eFG, turnovers, free throws, pace, ranks, both teams side by side | `analysis.md`, compared |
| Starters, minutes, bench, roster table, rotation by minute | `analysis.md`, Roster, starting five and bench |
| Shot totals by zone, share of threes, free-throw sources | `analysis.md`, Shot selection |
| Opponent against our team (the matchups, what to check, clips) | `analysis.md`, What to expect (nowhere else) |
| Play types, per-player play-type mix, assists, turnovers | `offense_tendencies.md` |
| What the team allows, defensive scheme | `defense_tendencies.md` |
| Per-player lines, shot charts, energy indices, player rotation | `individual_tendencies.md` (the table of player lines is in the Details of its Key points) |

Key points (top of each page) are headlines: one line per point, at most one number, each ending with a link to the section that holds the rest. The comparison with our team belongs only in What to expect, so the offense and defense pages never compare the two teams.

## 3. Links

* Same page: `[text](#section-title)`. Other page of the game: `[text](offense_tendencies.html#section-title)`; from a sub-page to the main analysis: `./#section-title`.
* The anchor is the heading lowercased with spaces and punctuation turned into hyphens (`## Roster, starting five and bench` is `#roster-starting-five-and-bench`). Avoid linking to headings with colons.
* A link to a heading inside a closed drop-down opens it. After building, check that every `#anchor` exists (see 6).
* **Every figure type that needs explaining has a section in the Methodology page** (`weekly/pages/methodology.md`): what it shows, how it is
  built, how to read it, with a picture drawn with invented (dummy) data by `notebooks/methodology_figures.py`, using the same drawing
  functions as the real figure. Two links, both ways:
  * on the analysis page, the text that introduces the figure ends with a link to that Methodology section (`../../methodology/#anchor`
    from `docs/opponent/<folder>/`);
  * in the Methodology section, **just above each dummy figure, one short sentence with a link to the analysis page and section where
    the real figure is shown** (`../opponent/<folder>/<page>.html#section`; use the latest analysis that has the figure).
  Do this for every new figure or index of every future analysis, and give the figures their descriptive names: never "plot 1" or
  "plot 2" (in titles, notes, text or code comments).

## 3b. Figures with a court (shot charts, zones, sides)

* **Every court is drawn with the basket at the top**: the standard half court rotated by 180 degrees (`lba_style.ROTATE_COURT`, `lba_style.draw_half_court`), with the text upright. This holds for every shot chart and court figure, team or player (for example `10f_player_<name>_pnr_iso_courts.png` of `notebooks/synergy_player_history.py`), never basket at the bottom.
* **Left and right are the offense's**, seen from behind the offense: the offense's left is the left of the picture, its right the right. In the Synergy shot chart x < 250 is the offense's right, x > 250 its left (the rim is at (250, 330)).
* One figure answers one question, with the answer in the title or the first label; no more than three panels per figure, labels inside the bars, no overlapping text. After drawing, open the PNG and check it before using it.
* In a page section, one figure per sub-heading, under a short text (what it shows, how to read it), then at most three bullets. Cumulative views (all seasons, all shot types together) come after the breakdown they sum up.

## 4. Writing the numbers

* Source of every number: the Synergy pull folder (`data/synergy/<team>_<date>/`, README lists the files), `data/box_scores.csv`, `data/pbp.csv`, the `auto.json` of the matchup report. Team-level ranks come from the `league_team_*.csv` of the pull; play-type ranks only exist in the newest `data/synergy/leaderboards_<date>/`, so say "on <date>" next to any play-type rank that is older than the pull.
* Opponent side first, our side from `ref_playtypes_offense.csv` and the leaderboards. Say how many games each side has played.
* Highlight the headline of a Key point with `==text==`.
* Clips: game clock from `shots.csv` (period, time remaining), one line per theme.
* Data only, no coaching judgement presented as fact: tendencies, not predictions; small samples get a warning in Details.

## 5. Pulls and figures every analysis must have

Never publish an analysis without these; a missing one means the pull was skipped, not that the section is optional.
Synergy pulls need a browser logged in to Synergy (the user signs in); run each script in the Synergy tab (headers of the scripts).

| What | Pull / command | Output | Shown in |
|---|---|---|---|
| Scouting pull, the opponent's league | `synergy/webapp_pull.js` + the Cumulative Box tab of the team page (`/teams/<id>/boxscore`) into `data/synergy/<team>_<date>/` with `config.json` and README, then `python notebooks/synergy_scouting_plots.py data/synergy/<team>_<date>` | `02_opponent_playtypes`, `06_players_playtype_mix`, `05_player_<name>_shot_profile`, `05c_player_<name>_shot_types` | offense page, Play types and sets (02, 06); individual page, Shot charts by player (05, 05c, players by possessions) |
| Defensive pull, one folder per competition | `synergy/defense_pull.js` into `data/synergy/defense_<team>_<date>/<competition>/`, then `python notebooks/synergy_defense_plots.py <folders> --out weekly/games/<date>` | `16_defense_playtypes`, `17_defenders_playtype_mix` | defense page: What they allow (16), Defensive scheme (17) |
| Key numbers | `synergy/key_numbers_pull.js` | Key numbers tab | `key_numbers.md` |
| Energy indices | `python notebooks/energy_indices.py "<Team>"`, copy the PNG to `weekly/games/<date>/15_energy_indices.png` | `15_energy_indices` | individual page, Energy: rim activity and pace |
| Second competition (Euroleague, EuroCup) | the same pulls with that competition key; every game of both competitions is used, ranks stay per competition | tables / second panel | same sections, side by side |

Copy the PNGs into `weekly/games/<date>/` and reference them with `{{ figure: name }}`. Text stays short: the figure carries the
numbers, the summary carries three or four bullets, no table that repeats a figure.

## 6. Refreshing when the opponent plays again

1. Make sure the games are in the data: `git pull` (the morning GitHub Action collects) or `python -m lba_data.collect`; re-pull Synergy for the opponent if needed (see its README).
2. Regenerate what depends on the data: `python notebooks/synergy_scouting_plots.py data/synergy/<folder>`, `python notebooks/energy_indices.py "<Team>"` (copy the PNG to `weekly/games/<date>/15_energy_indices.png`), the matchup figures come from `weekly.py`.
3. Recompute the numbers of each section from the files above and edit the text in place: games count, record, ranks, per-player lines, clips.
4. Build and check: `cd notebooks && python build_site.py`, open `docs/opponent/<folder>/index.html`: every section shows "In short" plus Details, no raw marker, every `#anchor` link resolves (`document.getElementById`), no number is stated twice.
5. Search the pages for stale wording ("5 games", "not in the numbers", an old date).
