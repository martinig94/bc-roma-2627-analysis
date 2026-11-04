# Synergy pull: Ross (Trieste), four seasons of shots (2023-24 to 2026-27 to date)

Pulled on 4 Nov 2026 from the Synergy Sports web app (`court/2/shots` with `playerId` + `seasonId`, no competition filter,
`possessionreports ... group game` for the game list and, play type by play type, for the possession counts). Input for

    python notebooks/synergy_player_history.py data/synergy/players_2026-11-04 --out weekly/games/2026-11-08

Synergy keeps one player record per team/season, so the player has several ids (`pid`):

| player | season | pid | team (competitions) |
|---|---|---|---|
| Ross (Colbey) | 2023-24 | 65088d96ecbb45b92dea4d87 | Buducnost (Adriatic League, Adriatic Supercup, EuroCup) — until Dec 2023, 23 games |
| Ross | 2023-24 | 6586ff8ef8d4f68f985b86e9 | Derthona Tortona (Italian Serie A, FIBA Champions League) — from Dec 2023, 25 games (the record is named "Ross Colbey") |
| Ross | 2024-25 | 66d40549c8fcce5ed216fc01 | Trieste (Italian Serie A, exhibitions) — 25 games |
| Ross | 2025-26 | 66d40549c8fcce5ed216fc01 | Trieste (Italian Serie A, FIBA Champions League, exhibitions) — 35 games |
| Ross | 2026-27 | 66d40549c8fcce5ed216fc01 | Trieste (Italian Serie A, exhibitions) — 6 games |

The 2023-24 season is split between two teams (Buducnost, then Tortona): the figures and the analysis merge the two halves under
one season. The script leaves out every competition whose name contains "Exhibitions" (list `EXCLUDE`). Game counts are what
Synergy holds: 2024-25 has 25 Trieste LBA games (not the full 30-round season).

## Files

* `players_shots.csv` — every field-goal attempt (1,148 incl. exhibitions): `player, season, pid, date, game, comp, period, clock` (tenths of a second
  remaining in the period, empty when not logged), `pts_att` (2/3), `pts_scored`, `zone_raw` (Synergy 11-zone chart), `x, y`
  (court coordinates of the app: the rim is at (250, 330), x < 250 is the offense's right side, x > 250 its left — checked against the
  "Drives Left / Drives Right" and "Left P&R / Right P&R" tags), `dist` (inches), `description` (the Synergy chain: shooter > play type > sub-type > ... > result).
* `players_games.csv` — one row per player, season and game with the competition, possessions used, FGA and points.
* `players_playtypes_games.csv` — one row per season, game and play type (the eleven Synergy play types) with possessions, points, FGA/FGM,
  3PA/3PM, turnovers, free-throw attempts, shooting fouls drawn and scoring possessions: the basis for play-type shares and PPP over
  every possession (the shot list only holds field-goal attempts).

Same columns, zones and sub-type reading as `data/synergy/players_2026-10-25/` (see its README). Sub-types read from the chain for
this player: P&R ball handler → High P&R / Left P&R / Right P&R (a side P&R then carries Side or Baseline, then Dribble Off Pick /
Go Away from Pick / Takes Early Jump Shot); ISO → Top / Left / Right, then Drives Left / Drives Right / Early Jumper; Spot-Up →
Drives Left / Drives Right / Drives Straight / No Dribble Jumper; Hand Off → From Stationary / From Dribble, then Top / Left / Right;
Off Screen → To Shooter's Left / Right / Straight; Transition → Ballhandler / Left Wing / Right Wing / Leak Outs / Trailer / First Middle.
