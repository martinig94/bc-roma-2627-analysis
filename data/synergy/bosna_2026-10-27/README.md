# Synergy pull: KK Bosna (EuroCup 2026-27), before BC Roma vs Bosna, 27 Oct 2026

Pulled on 23 Oct 2026 from the Synergy Sports web app (apps.synergysports.com/basketball), through the same
JSON calls the app makes (`possessionreports`, `court/2/shots`, cumulative box page), filtered to the **EuroCup**
competition (4 games each: Bosna 1-3, BC Roma 2-2). Input for

    python notebooks/synergy_scouting_plots.py data/synergy/bosna_2026-10-27

Same columns as `data/synergy/varese_2026-10-20/` (see its README for the meaning of every file). Differences:

* `league_team_offense.csv` / `league_team_defense.csv`: the 32 EuroCup teams (4 games each), with a `name` column.
* `context_all_games.csv`: all non-exhibition games played (Bosna 7 = 4 EuroCup + 3 ABA; BC Roma 8 = 4 EuroCup + 4 LBA); `gp` column added.
* The play-type tables are computed from the raw possession counts (PPP, eFG%, TO%, %FT, SSQ, PPS, SSM, TS%, TSA, Score%
  reproduce the app's columns exactly); `ppp_rating` is filled only for Bosna's offense (read from the page), `pct_time` = share of all possessions.
* `opp_players_shottype_within_playtype.csv`: player/play-type pairs with at least 8 attempts (the plots keep the ≥10 rule).
* `shots.csv` (extra): every Bosna field-goal attempt in the EuroCup with game, period, game clock remaining (checked against the EuroLeague play-by-play on the Bahcesehir game), shooter, play type of the shooter, shot type and zone.
* No players excluded from the lineups (`exclude_players` empty): Bosna has used 12 players; Islamovic and Banks have 1 game each.

Shot zones: Synergy 11-zone chart grouped as Paint (Z11-01), Mid-range (Z11-07..11), Corner 3 (Z11-12, 16), Wing 3 (Z11-13, 15), Top 3 (Z11-14).
