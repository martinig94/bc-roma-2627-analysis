# Synergy pull for one scouting report (example: OpenJobMetis Varese, Italian Serie A / LBA 2026-27, 20 Oct 2026)

Extracted by hand from the Synergy Sports web app (apps.synergysports.com/basketball). Every folder of this kind is one input for

    python notebooks/synergy_scouting_plots.py data/synergy/<folder>

which writes the plots and `team_zscores_vs_league_teams.csv` to `reports/synergy_<folder>/`. To scout another team, copy this folder, replace the CSVs
with the new pull (same columns), edit `config.json`, and run the command again. Nothing in the script is tied to a team or league.

> **Review needed:** all tables here come from the Synergy Sports web app (extracted by hand, small samples), not from the LBA data in `data/`. Check a new pull against the columns below before plotting.

## config.json

| key | meaning |
|---|---|
| `opponent`, `reference` | `name` (must match the `team` column of `context_all_games.csv`), `abbr` (the code used in the league tables), `games` (games in the competition), `games_all` (all games played) |
| `league`, `competition`, `league_games_each`, `season` | wording for titles and footers; games per team in the league tables |
| `date`, `author` | printed on every figure (override with `--date`, `--author`) |
| `lineup_min_poss` | minimum possessions for a lineup to appear |
| `exclude_players` | players already left out of `opp_lineups_off_def.csv` (only used for the footnotes) |

## CSVs

| file | content |
|---|---|
| `league_team_offense.csv`, `league_team_defense.csv` | all teams of the league, competition games only: `team, gp, poss_pg, pts_pg, ppp, fg, efg, to, ft, score` (mean and SD for the z-scores) |
| `context_all_games.csv` | opponent and reference team metrics over all games played: `team, side, metric, value` for PPP, eFG%, TO%, %FT, Score%, FG% |
| `opp_playtypes_offense.csv`, `opp_playtypes_defense.csv`, `ref_playtypes_offense.csv` | Synergy play-type tables (`play_type, poss, pts, ppp, ...`) |
| `opp_players_cumulative_box.csv` | Synergy cumulative box per player (`PLAYER, GP, OFFENSIVE ROLE, POSS, PTS, PPP, EFG%, TS%, ...`); no minutes in the source |
| `opp_players_playtypes_offense.csv` | `player, play_type, poss, pts, ppp` |
| `opp_players_fg_by_zone_and_playtype.csv` | `player, dimension (shot_location or play_type), category, fgm, fga`; shot locations are the Synergy 11-zone chart grouped to Paint, Mid-range, Corner 3, Wing 3, Top 3 |
| `opp_players_shottype_within_playtype.csv` | `player, play_type, shot_type, fga, fgm` for play types with more than 10 attempts (from the shot-by-shot list) |
| `opp_lineups_off_def.csv` | 5-man lineups with offense and defense side by side: `lineup, poss, pts, ppp, efg, tpa_rate, ft_rate, to_pct, ssm, def_poss, opp_pts, opp_ppp, ...` |
| `opp_players_points_generated.csv`, `opp_lineups_offense_all.csv`, `opp_lineups_defense_all.csv` | extra tables, not used by the plots |

Possessions used by a player = possessions the player ended (shot, turnover, free-throw trip). Points generated = PTS + 2 x AST.
