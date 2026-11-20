# Synergy pull: Virtus Bologna (LBA 2026-27), before Virtus Bologna vs BC Roma, 22 Nov 2026 (round 9, away)

Pulled on 20 Nov 2026 from the Synergy Sports web app with `synergy/webapp_pull.js` (cumulative box: team page, Cumulative Box tab),
filtered to the **Italian Serie A** competition (8 games each). Input for

    python notebooks/synergy_scouting_plots.py data/synergy/virtus-bologna_2026-11-22

Same columns and conventions as `data/synergy/verona_2026-11-14/` (see `data/synergy/varese_2026-10-20/README.md` for every file).

* Synergy abbreviation `VOB`, team id `54457df0300969b132fd0dca`.
* `context_all_games.csv`: all non-exhibition games (Virtus Bologna 22 = 8 LBA + 13 Euroleague + 1 SuperCup; BC Roma 16).
* `shots.csv`: the 552 Virtus Bologna field-goal attempts in the LBA.
* `opp_players_cumulative_box.csv`: 16 players plus the `TEAM TOTAL` row.
* The Euroleague games are in `data/synergy/key_numbers_virtus-bologna_euroleague_2026-11-22/`, the defense in
  `data/synergy/defense_virtus-bologna_2026-11-22/`.
