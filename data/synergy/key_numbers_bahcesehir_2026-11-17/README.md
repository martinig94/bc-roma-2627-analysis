# Synergy pull for the Key numbers tab: Bahcesehir (EuroCup 2026-27), before EuroCup round 8, home, Tue 17 Nov 2026

Pulled on 16 Nov 2026 with `synergy/key_numbers_pull.js` (Synergy web app API, logged in), **EuroCup games only**: Bahcesehir 7 games
(440 FGA), BC Roma 7; all 32 teams of the competition, so every number can be ranked. Bahcesehir: Synergy team id `5b0e907a9559b26e7e9859b6`, abbreviation `BKI`.
Last 3 games: Bahcesehir 2026-10-27 PAOK, 2026-11-03 Ulm, 2026-11-11 Lietkabelis; BC Roma 2026-10-27 Bosna, 2026-11-03 PAOK, 2026-11-11 Ulm.

    python notebooks/key_numbers.py data/synergy/key_numbers_bahcesehir_2026-11-17

writes `weekly/games/2026-11-17/key_numbers.md`, the "Key numbers" tab (Season / Last 3 games), overwritten on every run.

* `teams.csv`: one row per team and side (`off` = its offense, `def` = what it allows): possessions, points, shooting, turnovers, play types
  (`poss_`/`pts_`/`to_` + pnrbh, roll, trans, iso, post, spot, putback, cut, handoff, offscreen, misc), rebounds (`offreb` of the offense, `defreb` of the
  defense, from `group game` play-by-play stats), assists, steals, shot aggregates (`rim` = 2-pointers within 6 ft, `paint` = rest of Z11-01, `mid`,
  `three`, `cs3` catch-and-shoot threes, `jump_tag` / `jump_open` catch-and-shoot jump shots tagged guarded / open, `drive_fga`, `sq_*` shot quality).
* `zones.csv`: FGA / FGM per team, side and Synergy zone (Z11-01 paint, Z11-07..11 mid-range, Z11-12..16 threes).
* `games.csv`: per game rows of the opponent (`who=opp`) and BC Roma (`who=ref`), both sides, same columns as `teams.csv` without the shot aggregates.
* `players.csv` / `players_last.csv`: opponent players, season / last 3 games (`game in [...]`): possessions, points, turnovers, play types.
* `defenders.csv` / `defenders_last.csv`: BC Roma defenders, possessions / points / FGA / turnovers by play type on the possessions that end on him.
* `opp_shots.csv`, `opp_def_shots.csv`, `ref_def_shots.csv`: every FGA of the opponent, allowed by the opponent, allowed by BC Roma. In the two
  defense files `player` is the defender Synergy credits with the shot (empty on some putbacks and transition shots).
* `box_games.csv`: opponent game box scores (`/api/games/<id>/playerboxscores/extended`): seconds, offensive / defensive rebounds, points, possessions,
  turnovers, FGA, FTA per player and game.
* `box.csv`: cumulative box (team page, More, Cumulative Box): shirt numbers and Synergy offensive roles. `ref_numbers.csv`: BC Roma shirt numbers.
* `meta.json`: pull time, last 3 game ids, config. `config.json`: names, game label, date and author for the page.
