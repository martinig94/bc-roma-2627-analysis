---
name: synergy-leaderboard
description: Update the Leaderboard tab of the site with the Synergy defensive team tables (all teams, by play type) after a EuroCup or LBA game. Use when asked to refresh/update the Synergy leaderboard, or after a game. Needs a browser logged in to Synergy (Claude in Chrome).
---

# Update the Synergy defensive leaderboard

Goal: the site tab **Leaderboard** shows, for every team of a competition, the defence overall and by play type. Its data is
`data/synergy/leaderboard/<eurocup|lba>/*.csv` + `meta.json`. This skill refreshes it from Synergy (apps.synergysports.com/basketball),
read in the browser by the user's logged-in Chrome. Never ask for, type or store Synergy credentials; if the browser is not logged in, ask the user to log in.

## 1. Extract (browser)
For each competition to update (EuroCup, LBA Serie A 2026-27), in Synergy's team **leaderboard / team stats**:
- Season: current; **all games of that competition** (no opponent, venue or date filters); side: **defence** (points allowed by the team's defence).
- For each play type below, open the team table of that play type and copy **every team row** (all teams of the competition, not only Roma).
  Play types: Overall (all plays, "PPP"), Transition, Isolation, Post-up, P&R ball handler, P&R roll man, Spot up, Off screen, Hand off, Cut, Off reb (putbacks).
- Save one CSV per play type into a new folder `<scratch>/synergy_pull/`, named `ppp.csv, transition.csv, iso.csv, post_up.csv,
  pnr_ball_handler.csv, pnr_roll_man.csv, spot_up.csv, off_screen.csv, hand_off.csv, cut.csv, off_reb.csv`.
  Columns as shown by Synergy: `Rank, Team, GP, Poss, %Time, Pts, PPP, FG%, eFG%, TO%, %FT, Score%, 2 FG%, 3 FG%` (more columns are fine; header names as on screen).
  Percentages may stay as text (`44.7%`). Copy the numbers exactly as shown; do not compute or fill missing values. A team that has no possessions of a play type is simply absent from that file.
- Check that the overall table has all teams of the competition (EuroCup 32, LBA 16), the same GP as the league tables, and note the date of the latest game included.

## 2. Load into the repo
```bash
python notebooks/synergy_leaderboard.py ingest <scratch>/synergy_pull --competition eurocup --date YYYY-MM-DD   # or --competition lba
python notebooks/build_site.py        # optional: preview docs/leaderboard/index.html
git add data/synergy/leaderboard && git commit -m "Synergy leaderboard: <competition> after <game>" && git push
```
`--date` is the date of the latest game in the data. The ingest stops with a message if a required column (Team, GP, Poss, PPP) is missing. Pushing rebuilds the site.

## 3. Report
Say which competition and date were loaded, how many teams, any table that could not be extracted, and the two Roma teams' overall rank.
