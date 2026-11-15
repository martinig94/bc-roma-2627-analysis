# Synergy pull for the Key numbers tab: Virtus Bologna (Italian Serie A 2026-27), before Virtus Bologna vs BC Roma, LBA round 9, away, Sun 22 Nov 2026

Pulled on 15 Nov 2026 from the Synergy Sports web app with `synergy/key_numbers_pull.js` (same calls as `webapp_pull.js`:
`possessionreports`, `possessionreports ... group game` with play-by-play stats, `court/2/shots`), **Italian Serie A games only**:
Virtus Bologna 7 LBA games (last game logged 9 Nov 2026 (round 7, vs Verona)), BC Roma 8; every one of the 16 teams of the competition, so each number can be ranked.
Synergy team id `54457df0300969b132fd0dca`, abbreviation `VOB`. Pulled before LBA round 8 was played (Trento vs Virtus, Sun 15 Nov 19:00): re-pull after the round and after BC Roma's EuroCup game of 17 Nov for the final numbers. BC Roma has 8 LBA games (Verona, 14 Nov, included).

    python notebooks/key_numbers.py data/synergy/key_numbers_virtus-bologna_2026-11-22

writes `weekly/games/2026-11-22/key_numbers.md`, the "Key numbers" tab of the opponent analysis (overwritten on every run).

* `teams.csv`: one row per team and side (`off` = its offense, `def` = what it allows): possessions, points, shooting, turnovers,
  play types (`poss_`/`pts_`/`to_` + pnrbh, roll, trans, iso, post, spot, putback, cut, handoff, offscreen, misc), rebounds
  (`offreb` = offensive rebounds of the offense, `defreb` = defensive rebounds of the defense, on that side's possessions), assists, steals,
  and shot aggregates: `rim` (2-pointers within 6 ft), `paint` (rest of zone Z11-01), `mid`, `three`; `cs3` catch-and-shoot threes
  ("No Dribble Jumper"), `jump_tag` / `jump_open` catch-and-shoot jumpers tagged guarded or open, `drive_fga` shots whose description
  contains a drive, `sq_tot` / `sq_n` Synergy shot quality.
* `zones.csv`: FGA / FGM per team, side and Synergy zone (Z11-01 paint, Z11-07..11 mid-range, Z11-12..16 threes), mean x / y.
* `players.csv`: Virtus Bologna players, possessions and points (all plays and by play type) and the same shot aggregates, drives by side
  attributed to the driver (`drive_l`, `drive_r`, `drive_s`).
* `defenders.csv`: BC Roma defenders, possessions / points / FGA / turnovers by play type on the possessions that end on him.
* `opp_shots.csv`, `ref_def_shots.csv`: every Virtus Bologna FGA (483, = FG ATT of the cumulative box) and every FGA BC Roma allowed.
* `box.csv`: Virtus Bologna cumulative box (team page, More, Cumulative Box), last row `TEAM TOTAL`.
* `meta.json`: pull time, last game, config of the pull. `config.json`: names, game label, date and author for the page.
