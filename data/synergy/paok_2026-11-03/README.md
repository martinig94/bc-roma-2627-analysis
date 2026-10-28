# Synergy pull: PAOK Thessaloniki (EuroCup 2026-27), before PAOK vs BC Roma, 3 Nov 2026

Pulled on 28 Oct 2026 from the Synergy Sports web app (apps.synergysports.com/basketball), through the same
JSON calls the app makes (`possessionreports`, `court/2/shots`, cumulative box page), filtered to the **EuroCup**
competition (5 games each, after round 5). Input for

    python notebooks/synergy_scouting_plots.py data/synergy/paok_2026-11-03

Same columns as `data/synergy/varese_2026-10-20/` (see its README for the meaning of every file). Differences:

* `league_team_offense.csv` / `league_team_defense.csv`: the 32 EuroCup teams, with a `name` column. Round 5 was split
  over 27 and 28 Oct: at pull time 12 teams had 5 games and 20 had 4 (per-game and per-possession values are comparable).
* `context_all_games.csv`: all non-exhibition games played (PAOK 11 = 5 EuroCup + 6 in other competitions; BC Roma 10 = 5 EuroCup + 5 LBA); `gp` column added.
* The play-type tables are computed from the raw possession counts (PPP, eFG%, TO%, %FT, SSQ, PPS, SSM, TS%, TSA, Score%
  reproduce the app's columns); `ppp_rating` is empty; `pct_time` = share of all possessions.
* `opp_players_shottype_within_playtype.csv`: player/play-type pairs with at least 8 attempts (the plots keep the ≥10 rule).
* `shots.csv` (extra): every PAOK field-goal attempt in the EuroCup (302, same as FG ATT of the cumulative box) with game, period,
  game clock remaining, shooter, play type of the shooter, shot type and zone.
* `opp_players_cumulative_box.csv`: the "Cumulative Box" tab of the team page (EuroCup), 58 columns, last row `TEAM TOTAL`.
* No players excluded from the lineups (`exclude_players` empty): PAOK has used 15 players; Iatridis has 1 game (0 possessions),
  Persidis 2. Note the two different players with number 20 (Motiejunas, Iatridis).

Shot zones: Synergy 11-zone chart grouped as Paint (Z11-01), Mid-range (Z11-07..11), Corner 3 (Z11-12, 16), Wing 3 (Z11-13, 15), Top 3 (Z11-14).
