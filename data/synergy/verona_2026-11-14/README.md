# Synergy pull: Tezenis Verona (LBA 2026-27), before BC Roma vs Verona, 14 Nov 2026 (round 8, home)

Pulled on 11 Nov 2026 from the Synergy Sports web app (apps.synergysports.com/basketball), through the same
JSON calls the app makes (`possessionreports`, `court/2/shots`, cumulative box page; `synergy/webapp_pull.js`), filtered to the
**Italian Serie A** competition (Verona 7 LBA games, the round 7 game at Virtus Bologna of 9 Nov included; BC Roma 7 LBA games). Input for

    python notebooks/synergy_scouting_plots.py data/synergy/verona_2026-11-14

Same columns as `data/synergy/varese_2026-10-20/` (see its README for the meaning of every file) and same conventions as
`data/synergy/trieste_2026-11-08/`. Notes:

* `league_team_offense.csv` / `league_team_defense.csv`: the 16 LBA teams, with a `name` column; round 7 complete, every team at 7 games.
  Verona's Synergy abbreviation is `VEO`, team id `54457df2300969b132fd0e94`.
* `context_all_games.csv`: all non-exhibition games played (Verona 7 = 7 LBA; BC Roma 13 = 7 LBA + 6 EuroCup); `gp` column added.
* `ppp_rating` is empty (not read from the page); `pct_time` = share of all possessions.
* `opp_players_shottype_within_playtype.csv`: player/play-type pairs with at least 8 attempts (the plots keep the ≥10 rule).
* `shots.csv` (extra): every Verona field-goal attempt in the LBA (469, same as FG ATT of the cumulative box) with game, period,
  game clock remaining, shooter, play type of the shooter, shot type and zone.
* `opp_players_cumulative_box.csv`: 11 players plus the `TEAM TOTAL` row; Massinburg 4 games, Andrews 6, Barbitch 3,
  Mane 1 (0 possessions), the other seven 7.
* No players excluded from the lineups (`exclude_players` empty).

Shot zones: Synergy 11-zone chart grouped as Paint (Z11-01), Mid-range (Z11-07..11), Corner 3 (Z11-12, 16), Wing 3 (Z11-13, 15), Top 3 (Z11-14).