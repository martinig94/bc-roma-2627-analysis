# Synergy pull, OpenJobMetis Varese (Italian Serie A / LBA 2026-27), 20 Oct 2026

Extracted by hand from the Synergy Sports web app (apps.synergysports.com/basketball). Serie A games only: Varese 4 games, BC Roma 4 logged games.
Inputs of `notebooks/varese_synergy_plots.py`.

| file | content |
|---|---|
| `league_LBA_team_{offense,defense}_SerieA.csv` | the 16 LBA teams, 4 games each (league mean and SD for the z-scores; three teams share the abbreviation TRE) |
| `scouting_report_league_context_VAR_vs_BCR_2026-27.csv` | Varese and BC Roma team metrics over all games played (plot 01) |
| `bcroma_playtypes_offense_2026-27.csv`, `varese_LBA_playtypes_{offense,defense}.csv` | possessions and PPP by play type |
| `varese_LBA_players_cumulative_box.csv`, `varese_LBA_players_playtypes_offense.csv`, `varese_LBA_players_points_generated.csv` | player tables (no minutes in the source) |
| `varese_LBA_players_fg_by_zone_and_playtype.csv` | FGM/FGA per player by shot location (11-zone chart grouped to 5) and by play type |
| `varese_LBA_players_shottype_within_playtype_over10.csv` | shot types within play types with more than 10 attempts |
| `varese_LBA_lineups_*.csv` | 5-man lineups, at least 5 possessions, Della Valle excluded in the `noDellaValle` file |

Possessions used by a player = possessions the player ended (shot, turnover, free-throw trip). Points generated = PTS + 2 x AST.
