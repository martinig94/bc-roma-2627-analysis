# Synergy team leaderboards, 2026-27, pulled 28 Oct 2026

Offense and defense leaderboards of the two competitions BC Roma plays in, overall and by play type, pulled from the
Synergy Sports web app (apps.synergysports.com/basketball) with `synergy/leaderboards_pull.js` (same `possessionreports`
calls as the opponent pulls, grouped by team instead of by game). Same script and columns as `leaderboards_2026-10-26`
(checked there cell by cell against the app's own export).

    leaderboard_eurocup_offense.csv    32 teams x 12 play types — 12 teams with 5 games (round 5 played 27 Oct), 20 with 4
    leaderboard_eurocup_defense.csv    (round 5 games of 28 Oct not played/logged yet at pull time, Maxima Roma among them)
    leaderboard_seriea_offense.csv     16 teams x 12 play types (5 games each)
    leaderboard_seriea_defense.csv

Per-game counts make the teams with 4 and 5 games comparable; ranks mix the two until the round is complete.

One row per team and play type. `play_type` = `All` (every possession, the "PPP" sheet of the export), `Spot Up`,
`P&R Ball Handler`, `Transition`, `P&R Roll Man`, `Cut`, `Offensive Rebounds (Put Backs)`, `Isolation`, `Post-Up`,
`Handoffs`, `Off Screen`, `Miscellaneous Plays` (the last one is not on the app's leaderboard page).

Columns, as the leaderboard page of the app:

* `rank`: by PPP (3 decimals), ascending for defense (lower = better), descending for offense; ties share the rank.
  Teams with fewer than 10 possessions of a play type are not ranked by the app: they are kept here with an empty `rank`.
* `team`, `name`: Synergy abbreviation (not unique in Serie A: three `TRE`) and full name.
* `gp`: games played in the competition.
* `poss`, `pts`, `fga`, `fgm`, `fg_miss`, `fg2a`, `fg2m`, `fg2_miss`, `fg3a`, `fg3m`, `fg3_miss`: per game (totals / gp),
  as the app's "per game" view; `poss_total` is the raw number of possessions.
* `pct_time`: share of the team's possessions (%; 100 for `All`).
* `ppp`, `fg_pct`, `efg_pct`, `fg2_pct`, `fg3_pct`, `to_pct`, `ft_pct` (possessions ending in free throws), `sf_pct`
  (shooting fouls drawn), `score_pct` (possessions with a score): percentages are in 0-100.
* `ssq` (shot quality), `pps` (points per shot), `ssm` = rounded `pps` - rounded `ssq`, `fta_per_fga`, `fg3a_per_fga`.
* Empty `fg2_pct` / `fg3_pct` where there was no attempt.
