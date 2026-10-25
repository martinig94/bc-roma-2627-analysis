# Synergy pull: Atic and Domask, three seasons of shots (2024-25, 2025-26, 2026-27 to date)

Pulled on 25 Oct 2026 from the Synergy Sports web app (`court/2/shots` with `playerId` + `seasonId`, no competition filter,
and `possessionreports ... group game` for the game list). Input for

    python notebooks/synergy_player_history.py data/synergy/players_2026-10-25 --out weekly/games/2026-10-27

Synergy keeps one player record per team/season, so a player has several ids (`pid`):

| player | season | pid | team (competitions) |
|---|---|---|---|
| Atic | 2024-25 | 66f973b32ad906d28ce17d8e | Breogan (Spanish ACB League) |
| Atic | 2025-26 | 68ba28c2ac6156e28b1ab0fa | Bosna (ABA, FIBA Europe Cup, exhibitions) |
| Atic | 2026-27 | 68ba28c2ac6156e28b1ab0fa | Bosna (ABA, EuroCup, exhibitions) |
| Domask | 2024-25 | 67b0f707f9aa36ac0a55e58f | Frankfurt (German League, German Cup) — from Feb 2025 |
| Domask | 2025-26 | 69754c308215bf27d5bbd6a0 | Frankfurt 2 (German League Division 3, 2 games in Jan 2026) |
| Domask | 2025-26 | 699b2d75936c653408a33054 | Oostende (BNXT League) — from Feb 2026 |
| Domask | 2026-27 | 6aa3c17c03779c2fc9219466 | Bosna (ABA, EuroCup, exhibitions) |

Not in the pull: Domask's NBA G League games (Windy City 2024-25, Santa Cruz 2025-26), which are not in the
"International" league of this Synergy account. The script leaves out exhibitions and the Division 3 games (list `EXCLUDE`).

## Files

* `players_shots.csv` — every field-goal attempt (896): `player, season, pid, date, game, comp, period, clock` (tenths of a second
  remaining in the period, empty when not logged), `pts_att` (2/3), `pts_scored`, `zone_raw` (Synergy 11-zone chart), `x, y`
  (court coordinates of the app), `dist` (inches), `description` (the Synergy chain: shooter > play type > sub-type > ... > result).
  The shooter is the last "number Name" segment of the chain; the play type is the segment after it.
* `players_games.csv` — one row per player, season and game with the competition, possessions used, FGA and points.

Zones: Paint (Z11-01), Mid-range (Z11-07..11), Corner 3 (Z11-12, 16), Wing 3 (Z11-13, 15), Top 3 (Z11-14) — same grouping as
the team folders. Sub-types read from the chain: P&R ball handler → High P&R / Left P&R / Right P&R (then Dribble Off Pick, Go Away
from Pick, Takes Early Jump Shot); ISO → Top / Left / Right (then Drives Left / Drives Right / Early Jumper); Transition →
Ballhandler / Left Wing / Right Wing / Leak Outs / Trailer / First Middle. All of it covers field-goal attempts only: possessions
that end in a turnover, a foul or a pass are not in the shot list.
