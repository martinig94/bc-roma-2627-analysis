# Synergy pull: Ratiopharm Ulm (EuroCup 2026-27), before BC Roma vs Ulm, 11 Nov 2026

Pulled on 7 Nov 2026 from the Synergy Sports web app (apps.synergysports.com/basketball), through the same
JSON calls the app makes (`possessionreports`, `court/2/shots`, cumulative box page; `synergy/webapp_pull.js`), filtered to the
**EuroCup** competition (Ulm 6 games, round 6 at home to Bahcesehir of 3 Nov included; BC Roma 6 EuroCup games). Input for

    python notebooks/synergy_scouting_plots.py data/synergy/ulm_2026-11-11

Same columns and conventions as `data/synergy/paok_2026-11-03/` (see its README and the Varese one). Notes:

* Ulm's Synergy abbreviation is `RAT`, team id `54457df2300969b132fd0e3e`.
* `league_team_offense.csv` / `league_team_defense.csv`: the 32 EuroCup teams, every team at 6 games.
* `context_all_games.csv`: all non-exhibition games played (Ulm 15 = 6 EuroCup + 9 in other competitions; BC Roma 12 = 6 EuroCup + 6 LBA).
* `ppp_rating` is empty; `pct_time` = share of all possessions.
* `shots.csv` (extra): every Ulm field-goal attempt in the EuroCup (386) with game, period, game clock remaining, shooter, play type, shot type and zone.
* `opp_players_cumulative_box.csv`: the "Cumulative Box" tab of the team page (EuroCup), 58 columns, 12 players plus `TEAM TOTAL`;
  Fischer 3 games, Koroma 5, Schmidt 5, the other nine 6.
* No players excluded from the lineups (`exclude_players` empty).

Shot zones: Synergy 11-zone chart grouped as Paint (Z11-01), Mid-range (Z11-07..11), Corner 3 (Z11-12, 16), Wing 3 (Z11-13, 15), Top 3 (Z11-14).
