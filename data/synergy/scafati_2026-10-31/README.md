# Synergy pull: Givova Scafati (LBA 2026-27), before BC Roma vs Scafati, 31 Oct 2026

Pulled on 26 Oct 2026 from the Synergy Sports web app (apps.synergysports.com/basketball), through the same
JSON calls the app makes (`possessionreports`, `court/2/shots`, cumulative box page; `synergy/webapp_pull.js`), filtered to the
**Italian Serie A** competition (5 games each: Scafati 5 LBA games, BC Roma 5 LBA games). Input for

    python notebooks/synergy_scouting_plots.py data/synergy/scafati_2026-10-31

Same columns as `data/synergy/varese_2026-10-20/` (see its README for the meaning of every file) and same conventions as
`data/synergy/bosna_2026-10-27/`. Notes:

* `league_team_offense.csv` / `league_team_defense.csv`: the 16 LBA teams (5 games each), with a `name` column. Scafati's Synergy abbreviation is `LS`.
* `context_all_games.csv`: all non-exhibition games played (Scafati 5 = 5 LBA; BC Roma 9 = 5 LBA + 4 EuroCup); `gp` column added.
* `ppp_rating` is empty (not read from the page); `pct_time` = share of all possessions.
* `opp_players_shottype_within_playtype.csv`: player/play-type pairs with at least 8 attempts (the plots keep the ≥10 rule).
* `shots.csv` (extra): every Scafati field-goal attempt in the LBA (319) with game, period, game clock remaining, shooter, play type of the shooter, shot type and zone.
* `opp_players_cumulative_box.csv`: 11 players used plus the `TEAM TOTAL` row; Spinelli 1 game, Ceron 2, Johnson and McGruder 3, Moore 4.
* No players excluded from the lineups (`exclude_players` empty).

Shot zones: Synergy 11-zone chart grouped as Paint (Z11-01), Mid-range (Z11-07..11), Corner 3 (Z11-12, 16), Wing 3 (Z11-13, 15), Top 3 (Z11-14).
