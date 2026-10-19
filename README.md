# LBA Serie A 2026/27 — game-by-game data

Incremental collector for the Italian basketball league (Lega Basket Serie A) 2026/27 season,
built on the undocumented JSON API behind [legabasket.it](https://www.legabasket.it).
It runs every Monday morning on GitHub Actions, collects any newly finished games, and commits
the updated dataset — so `data/` grows on its own through the season.

Season context: 16 teams, 30 rounds (andata/ritorno). Two Rome teams — **BC Roma** (team_id 1761,
ex Vanoli Cremona) and **Maxima Roma** (team_id 1762, ex Germani Brescia).

## Data

| file | grain | notes |
|---|---|---|
| `data/games.csv` | one row per game (all 240 scheduled) | scores, quarter scores, venue, attendance, coaches; `game_status` 2 = finished |
| `data/box_scores.csv` | one row per player per game, plus `team` and `total` rows | minutes, pts, FG2/FG3/FT made+attempted, reb (O/D), ast, stl, tov, blk, fouls, `val` (LBA efficiency), `oer`, `plus_minus`, `starter` |
| `data/pbp.csv` | one row per play-by-play event | period, clock, running score, player, event type (Italian: "2 punti segnato", "Rimbalzo difensivo", "Ingresso"/"Uscita" = substitutions…), shot type qualifier, **x/y court coordinates (0–100)**, zone |
| `data/teams.csv` | teams of the season | team ids are re-issued each season — don't join across seasons on id |
| `data/raw/<game_id>/*.json` | untouched API payloads | lets you rebuild the CSVs offline (`python -m lba_data.rebuild`) |

Coordinates: `x` runs along the length of the court (each team attacks one half; `side`
flips per team/half), `y` across the width. Percent of court, not metres — calibrate
against the 3pt line (~6.75 m) before computing distances.

## Run locally

```bash
pip install -r requirements.txt
python -m lba_data.collect            # pull whatever is new
python -m lba_data.collect --limit 2  # test run
python -m pytest -q                   # unit tests against a real Round 1 payload
```

## Analysis starter

```python
import pandas as pd
box = pd.read_csv("data/box_scores.csv")
players = box[box.row_type == "player"]
roma = players[players.team.isin(["BC Roma", "Maxima Roma"])]
roma.groupby(["team", "player_surname"])[["pts", "reb", "ast", "val", "plus_minus"]].mean()
```

See `notebooks/` for more.

## Weekly report (landing page)

The landing page `docs/index.html` lists one report per round (newest first); pre-match analyses are at `docs/prematch.html`.
Each report mixes an automatic part and your text. Team, season, author and the EuroCup file are set in `weekly/config.json`.

**Every week** (the Monday GitHub Action already collects the games, generates the new reports and rebuilds `docs/`):

```bash
python notebooks/weekly.py --collect   # pull new games, generate every round without a report yet, build docs/
# write your text in weekly/round-NN/notes.md (created empty for each new round, never overwritten)
git add -A && git commit && git push
```

`python notebooks/weekly.py --round 4` regenerates one round (stats corrections); your notes are kept. The command lists the rounds
that have no text yet. Single steps: `notebooks/weekly_report.py --round N` (figures + `auto.json`), `notebooks/build_site.py` (pages).

* Automatic: score and quarters, margin chart, team numbers (eFG%, TOV%, OREB%, FT rate), PIR vs season average, playing-time flag
  (8'+ played and +7' or +30% vs the average before), box scores, roster with photos, assist matrix, shot zones, TS% vs PIR (LBA only,
  EuroCup only), round results, standings, season trend, next fixture.
* Written by you: `weekly/round-NN/notes.md` (markdown; sections `key_points`, `story`, `tactics`, `players`, `roster`, `assists`,
  `zones`, `efficiency`, `next`; empty sections are left out; put images in the same folder).
* Roster positions and heights: fill in `data/roster.csv` (new players are appended blank). Photos: `data/photos/` (fetched automatically).
* Layout: `weekly/template/page.md.j2` (page order and automatic sections), `weekly/template/site.html.j2` (look).
  To add a section: add a `## newkey` to `weekly/template/notes.md` and an `{% if n.newkey %}...{% endif %}` block to the page template,
  or add a figure in `weekly_sections.py`, put its numbers in `auto` (`weekly_report.py`) and reference its PNG in the template.
* Another team or season: change `weekly/config.json` (the code has no team name in it) and add that season's EuroCup file if any.

## Pre-match analyses site (GitHub Pages)

`docs/` is a static page with a drop-down of the pre-match analyses (`reports/matchup_*_before_*`).
After generating a new report (`matchup_report.py` plus `lineups_report.py`, both with `--before <date>`),
run `python notebooks/build_site.py` and commit `docs/`.
Every page starts with an **LBA so far: results and standings** section (all results before the match
plus the current table, `00_standings.png` + `standings.md`, written by `notebooks/standings.py` and
automatically by `matchup_report.py`); paste `standings.md` under the page intro and mention both
teams' positions in "Where the two teams are". Enable it once in the repository settings:
Pages, source "Deploy from a branch", branch `master`, folder `/docs`.

## Caveats

* Not an official API. Endpoints were mapped from the site's network traffic in Sept 2026 and can
  change without notice — if a run fails, check `lba_data/api.py` first.
* Be polite: the collector sleeps between games and only fetches games it hasn't stored yet.
* Box scores appear within minutes of the final buzzer, but stats can be corrected in the days
  after. The collector doesn't re-fetch a game once stored; delete `data/raw/<game_id>` and
  re-run to refresh one.
* Playoffs are a separate championship id; add it with `--champ <id>` when the time comes.
