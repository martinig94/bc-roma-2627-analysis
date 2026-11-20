# Synergy pull for the Key numbers tab: Virtus Bologna (Italian Serie A 2026-27), before Serie A round 9, away, Sun 22 Nov 2026

Pulled on 16 Nov 2026 with `synergy/key_numbers_pull.js` (Synergy web app API, logged in), **Italian Serie A games only**: Virtus Bologna 8 games
(552 FGA), BC Roma 8; all 16 teams of the competition, so every number can be ranked. Virtus Bologna: Synergy team id `54457df0300969b132fd0dca`, abbreviation `VOB`. LBA round 8 included (at Trento, 15 Nov). `box.csv` (cumulative box, 9 Nov) is used only for shirt numbers and Synergy offensive roles.
Pulled again on 20 Nov 2026: no Serie A game since, every count identical (only Synergy's shot-quality totals moved by a few tenths), so the files are those of 16 Nov. Euroleague games: `data/synergy/key_numbers_virtus-bologna_euroleague_2026-11-22/`; defense: `data/synergy/defense_virtus-bologna_2026-11-22/`.
Last 3 games: Virtus Bologna 2026-11-02 Trieste, 2026-11-09 Verona, 2026-11-15 Trento; BC Roma 2026-10-31 Scafati, 2026-11-08 Trieste, 2026-11-14 Verona.

    python notebooks/key_numbers.py data/synergy/key_numbers_virtus-bologna_2026-11-22

writes `weekly/games/2026-11-22/key_numbers.md`, the "Key numbers" tab (Season / Last 3 games), overwritten on every run.

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
