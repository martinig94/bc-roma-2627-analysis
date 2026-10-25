---
name: synergy-leaderboard
description: Update the Leaderboard tab of the site with the Synergy team leaderboards (offense and defense, overall and by play type, EuroCup and LBA Serie A) after a game. Use when asked to refresh/update the Synergy leaderboard, or after a EuroCup or LBA game. Needs a browser logged in to Synergy (Claude in Chrome).
---

# Update the Synergy leaderboards

The site tab **Leaderboard** (`notebooks/synergy_leaderboard.py`, built by `build_site.py`) shows the newest folder
`data/synergy/leaderboards_<YYYY-MM-DD>/` with four CSVs (`leaderboard_<eurocup|seriea>_<offense|defense>.csv`, columns in that folder's README).
They are written by `synergy/leaderboards_pull.js`, which calls Synergy's own API from the logged-in browser. Never ask for, type or store Synergy credentials; if the browser is not logged in, ask the user to log in.

## 1. Pull (browser)
1. Open any page of https://apps.synergysports.com/basketball (logged in).
2. Run the whole of `synergy/leaderboards_pull.js` in the page (console / browser pane). It fills `window.__lb` with one CSV string per file and logs the row counts
   (EuroCup: 32 teams x 12 play types, Serie A: 16 x 12).
3. Save the four strings as `leaderboard_eurocup_offense.csv`, `leaderboard_eurocup_defense.csv`, `leaderboard_seriea_offense.csv`, `leaderboard_seriea_defense.csv`
   into a new folder `data/synergy/leaderboards_<today>/` (copy the README of the previous folder and update the date and games per team).
   Check the row counts and that every team has the same `gp` as the league tables. If a season or competition id changed, fix `CONFIG` at the top of the script.

## 2. Publish
```bash
python notebooks/build_site.py          # optional preview: docs/leaderboard/index.html
git add data/synergy/leaderboards_<today> && git commit -m "Synergy leaderboards <today>" && git push
```
The site rebuilds on push. The page always uses the newest `leaderboards_*` folder; older folders stay as history.

## 3. Report
Say which date was loaded, the row counts, and the two Roma teams' overall offense and defense ranks in both competitions.
