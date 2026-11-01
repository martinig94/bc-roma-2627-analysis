# Synergy pull: Pallacanestro Trieste (LBA 2026-27), before Trieste vs BC Roma, 8 Nov 2026 (round 7, away)

Pulled on 1 Nov 2026 from the Synergy Sports web app (apps.synergysports.com/basketball), through the same
JSON calls the app makes (`possessionreports`, `court/2/shots`, cumulative box page; `synergy/webapp_pull.js`), filtered to the
**Italian Serie A** competition (Trieste 5 LBA games — its round 6 game at Virtus Bologna is on Mon 2 Nov; BC Roma 6 LBA games,
the 31 Oct Scafati game included). Input for

    python notebooks/synergy_scouting_plots.py data/synergy/trieste_2026-11-08

Same columns as `data/synergy/varese_2026-10-20/` (see its README for the meaning of every file) and same conventions as
`data/synergy/scafati_2026-10-31/`. Notes:

* `league_team_offense.csv` / `league_team_defense.csv`: the 16 LBA teams, with a `name` column. Round 6 was half logged at pull
  time: 10 teams with 6 games, 6 (Trieste, Virtus Bologna, Tortona, Udine, Cantù, Milano) with 5. Trieste's Synergy abbreviation is `TRI`.
* `context_all_games.csv`: all non-exhibition games played (Trieste 5 = 5 LBA; BC Roma 11 = 6 LBA + 5 EuroCup); `gp` column added.
* `ppp_rating` is empty (not read from the page); `pct_time` = share of all possessions.
* `opp_players_shottype_within_playtype.csv`: player/play-type pairs with at least 8 attempts (the plots keep the ≥10 rule).
* `shots.csv` (extra): every Trieste field-goal attempt in the LBA (340, same as FG ATT of the cumulative box) with game, period,
  game clock remaining, shooter, play type of the shooter, shot type and zone.
* `opp_players_cumulative_box.csv`: 10 players used plus the `TEAM TOTAL` row; Canka 2 games, Paiano 3, Brajkovic 4, the other seven 5.
* No players excluded from the lineups (`exclude_players` empty).

Shot zones: Synergy 11-zone chart grouped as Paint (Z11-01), Mid-range (Z11-07..11), Corner 3 (Z11-12, 16), Wing 3 (Z11-13, 15), Top 3 (Z11-14).
