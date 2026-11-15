# Synergy pull for the Key numbers tab: Bahcesehir College Istanbul (EuroCup 2026-27), before BC Roma vs Bahcesehir, EuroCup round 8, home, Tue 17 Nov 2026

Pulled on 15 Nov 2026 from the Synergy Sports web app with `synergy/key_numbers_pull.js` (same calls as `webapp_pull.js`:
`possessionreports`, `possessionreports ... group game` with play-by-play stats, `court/2/shots`), **EuroCup games only**:
Bahcesehir College Istanbul 7 EuroCup games (last game logged 11 Nov 2026 (round 7)), BC Roma 7; every one of the 32 teams of the competition, so each number can be ranked.
Synergy team id `5b0e907a9559b26e7e9859b6`, abbreviation `BKI`.

    python notebooks/key_numbers.py data/synergy/key_numbers_bahcesehir_2026-11-17

writes `weekly/games/2026-11-17/key_numbers.md`, the "Key numbers" tab of the opponent analysis (overwritten on every run).

* `teams.csv`: one row per team and side (`off` = its offense, `def` = what it allows): possessions, points, shooting, turnovers,
  play types (`poss_`/`pts_`/`to_` + pnrbh, roll, trans, iso, post, spot, putback, cut, handoff, offscreen, misc), rebounds
  (`offreb` = offensive rebounds of the offense, `defreb` = defensive rebounds of the defense, on that side's possessions), assists, steals,
  and shot aggregates: `rim` (2-pointers within 6 ft), `paint` (rest of zone Z11-01), `mid`, `three`; `cs3` catch-and-shoot threes
  ("No Dribble Jumper"), `jump_tag` / `jump_open` catch-and-shoot jumpers tagged guarded or open, `drive_fga` shots whose description
  contains a drive, `sq_tot` / `sq_n` Synergy shot quality.
* `zones.csv`: FGA / FGM per team, side and Synergy zone (Z11-01 paint, Z11-07..11 mid-range, Z11-12..16 threes), mean x / y.
* `players.csv`: Bahcesehir College Istanbul players, possessions and points (all plays and by play type) and the same shot aggregates, drives by side
  attributed to the driver (`drive_l`, `drive_r`, `drive_s`).
* `defenders.csv`: BC Roma defenders, possessions / points / FGA / turnovers by play type on the possessions that end on him.
* `opp_shots.csv`, `ref_def_shots.csv`: every Bahcesehir College Istanbul FGA (440, = FG ATT of the cumulative box) and every FGA BC Roma allowed.
* `box.csv`: Bahcesehir College Istanbul cumulative box (team page, More, Cumulative Box), last row `TEAM TOTAL`.
* `meta.json`: pull time, last game, config of the pull. `config.json`: names, game label, date and author for the page.
