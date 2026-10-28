# Synergy pull: Moore and Nevels (Scafati), shots of the last seasons (2023-24 / 2024-25 to 2026-27 to date)

Pulled on 28 Oct 2026 from the Synergy Sports web app (`court/2/shots` with `playerId` + `seasonId`, no competition filter,
and `possessionreports ... group game` for the game list). Input for

    python notebooks/synergy_player_history.py data/synergy/players_2026-10-28 --out weekly/games/2026-10-31

Synergy keeps one player record per team/season, so a player has several ids (`pid`):

| player | season | pid | team (competitions) |
|---|---|---|---|
| Moore (Charles "Charlie") | 2023-24 | 64eb41c9e50fa03532343bce | Pistoia (Italian Serie A, Italian Cup, exhibitions) — 36 games |
| Moore | 2024-25 | 66f96dd62ad906d28cddd022 | Breogan (Spanish ACB League) — 10 games |
| Moore | 2025-26 | 6a11a7ee0e290048c40d3abc | Al Ahly Benghazi (Basketball Africa League) — 4 games |
| Moore | 2026-27 | 6ab6e197eade15487e9acfa1 | Scafati (Italian Serie A, exhibitions) |
| Nevels (Garrett) | 2024-25 | 66d76f7bc8fcce5ed2e0c5f8 | Parma Perm (VTB United League, exhibitions) |
| Nevels | 2025-26 | 64fc9f94ecbb45b92d435a9a | Uralmash Ekaterinburg (VTB United League, Winline Cup, exhibitions) |
| Nevels | 2026-27 | 6ab6e2c2eade15487e9ad794 | Scafati (Italian Serie A, exhibitions) |

Moore has a fourth season (2023-24, Pistoia) because his 2024-25 and 2025-26 samples are small: in 2025-26 he played
for Kuwait SC (West Asia Super League), which is not in the "International" league of this Synergy account, before the
4 BAL games with Al Ahly Benghazi.

The script leaves out every competition whose name contains "Exhibitions" and the German Division 3 games (list `EXCLUDE`).

## Files

* `players_shots.csv` — every field-goal attempt (2,002): `player, season, pid, date, game, comp, period, clock` (tenths of a second
  remaining in the period, empty when not logged), `pts_att` (2/3), `pts_scored`, `zone_raw` (Synergy 11-zone chart), `x, y`
  (court coordinates of the app), `dist` (inches), `description` (the Synergy chain: shooter > play type > sub-type > ... > result).
* `players_games.csv` — one row per player, season and game with the competition, possessions used, FGA and points.

Same columns, zones and sub-type reading as `data/synergy/players_2026-10-25/` (see its README). All of it covers
field-goal attempts only: possessions that end in a turnover, a foul or a pass are not in the shot list.
