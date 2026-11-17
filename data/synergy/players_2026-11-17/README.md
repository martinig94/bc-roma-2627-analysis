# Synergy pull: Rasheed Bello (Virtus Bologna), four seasons of shots (2023-24 to 2026-27 to date)

Pulled on 17 Nov 2026 from the Synergy Sports web app (`court/2/shots` with `playerId` + `seasonId`, no competition filter,
and `possessionreports ... group game` for the game list). Input for

    python notebooks/synergy_player_history.py data/synergy/players_2026-11-17 --out weekly/games/2026-11-22 --players Bello

| season | pid | team (competitions) |
|---|---|---|
| 2023-24 | 6530178f87dd5f1be1e5c2c2 | Purdue Fort Wayne (US college, 36 games) |
| 2024-25 | 6530178f87dd5f1be1e5c2c2 | Purdue Fort Wayne (US college, 32 games) |
| 2025-26 | 68cd2357ceb2397804dd4074 | Antwerp (BNXT League, FIBA Europe Cup, Champions League, Belgium Cup; 52 games) |
| 2026-27 | 6a9c9780c69f19cdbfc48095 | Virtus Bologna (Euroleague, Italian Serie A, SuperCup, exhibitions; 19 games, 15 without exhibitions) |

His 2021-23 Wisconsin-Parkside seasons are not in the pull.

Same files and columns as `data/synergy/players_2026-11-04/` (see its README), with two differences: the shot list has no
`clock` (empty) and `pts_scored` is read from the "Make N Pts" end of the description (empty for a miss).
