# Synergy defensive pull: Virtus Bologna (2026-27), before Serie A round 9, away, Sun 22 Nov 2026

Pulled on 20 Nov 2026 with `synergy/defense_pull.js` (Synergy web app API, logged in), once per competition:

* `seriea/`: Italian Serie A, Virtus Bologna 8 games (round 8 at Trento, 15 Nov, included), 16 teams.
* `euroleague/`: Euroleague, Virtus Bologna 13 games (Panathinaikos 17 Nov and at Valencia 19 Nov included), 20 teams.
  Competition key `54457dce300969b132fcfb3f:COMP:560100ac8dc7a24394b9563d`.

Input for the text of `weekly/games/2026-11-22/defense_tendencies.md`. Same files in both folders; counts are raw totals
(`possessions, pointMade, shotAttempt, shotMade, shot3Attempt, shot3Made, turnover, ftTimes, ftAttempt, shotFoul, score`):

* `situations.csv`: one row per team of the competition (as the defense) and situation, so every situation can be ranked. Situations:
  `all`, `halfcourt`, the eleven play types (`pnrbh, roll, trans, iso, post, spot, putback, cut, handoff, offscreen, misc`),
  scheme (`man`, `zone`: half-court possessions; `press`, `press_trans`, `press_halfcourt`), game situations (`ato` after time-outs,
  `eob` / `sob` out of bounds end / side, `shortclock` last 4 seconds of the shot clock), plays including passes and help
  (`pnr_passes`, `pnr_commit` defense commits, `pnr_trap`, `pnrbh_off_pick`, `pnrbh_away_pick`, `pnrbh_split`, `pnrbh_early_jumper`,
  `iso_passes`, `iso_commit`, `post_passes`, `post_commit`, `post_hard_double`), `drives` (`_left`, `_right`) and shot types
  (`cs` catch-and-shoot, `cs_guarded`, `cs_open`, `dribble_jumper`, `jump_short` / `jump_medium` / `jump_long`, `runner`, `hook`,
  `at_rim`, `sq_low` / `sq_medium` / `sq_high` Synergy shot quality). The expressions are those of the app's own Situations tables
  (listed in the script). A team without a possession in a situation has no row (few teams play zone).
* `defenders.csv`: Virtus Bologna defenders by play type (possessions that end on him; transition, cuts and put-backs have no defender).
* `periods.csv`: allowed per period (5 = overtime). `games.csv`: allowed per game: all, half court, transition, zone, press.
* `lineups.csv`: defensive lineups. `shots.csv`: every FGA allowed, with game, period and `clock` (tenths of a second left in
  the period, empty when not logged), zone, coordinates and the Synergy description chain.
* `meta.json`: pull time and config.
