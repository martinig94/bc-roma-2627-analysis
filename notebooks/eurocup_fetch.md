# Refreshing the EuroCup data

`data/eurocup_2026_raw.txt` holds EuroCup box scores and per-zone shot counts for the two Rome teams,
pulled from the EuroLeague live API (same source as the `euroleague_api` package used in basketball_analytics).

Endpoints (season code `U2026` = EuroCup 2026/27):

- game list: `https://api-live.euroleague.net/v1/results/?seasonCode=U2026` (XML; `gamecode` U2026_N)
- box score: `https://live.euroleague.net/api/Boxscore?gamecode=N&seasoncode=U2026`
- shots: `https://live.euroleague.net/api/Points?gamecode=N&seasoncode=U2026` (`ID_ACTION` 2FGM/2FGA/3FGM/3FGA, `ZONE` A–J, `COORD_X/Y` in cm)

With `euroleague_api` installed, the equivalent is `BoxScoreData(competition="U").get_player_boxscore_stats_data(2026, N)`
and `ShotData(competition="U").get_game_shot_data(2026, N)`.

File format (pipe-separated, three sections):

```
BOX
gamecode|team|player|starter|min|pts|2m|2a|3m|3a|ftm|fta|oreb|dreb|ast|stl|tov|blk|pf|pf_drawn|plus_minus|val
gamecode|team|TOTAL|||pts|...                      (team totals, same columns)
gamecode|QUARTERS|TEAM:q1-q2-q3-q4;TEAM:q1-q2-q3-q4
ZONES
gamecode|teamcode|zone|action|count                 (teamcode BCR / MRO; action 2FGM, 2FGA(miss), 3FGM, 3FGA(miss))
```

Add new games by appending lines; the game date goes in `EC_DATES` in `notebooks/matchup_report.py`.
Zones A/B/C (≤4.49 m from the rim) are what the report counts as "points in the paint", matching the
4.5 m distance rule used on the Legabasket coordinates.

## 4th-quarter play-by-play (clutch report)

`data/eurocup_2026_q4_pbp.txt` holds the last 7 minutes of the 4th quarter of each EuroCup game, one event per line (`period|clock|team_code|player|playtype|score_A|score_B`, score forward-filled), fetched from `https://live.euroleague.net/api/PlayByPlay?gamecode=<N>&seasoncode=U2026` (keys FirstQuarter…ForthQuarter/ExtraTime; PLAYTYPE codes 2FGM/2FGA/3FGM/3FGA/FTM/FTA/AS/TO/ST/D/O/RV/CM/FV/AG/IN/OUT). `notebooks/clutch_report.py` reads it next to the LBA play-by-play.
