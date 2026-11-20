# Synergy pull: Virtus Bologna in the Euroleague (2026-27), before Serie A round 9, away, Sun 22 Nov 2026

Pulled on 20 Nov 2026 with `synergy/key_numbers_pull.js`, `C` set to the Euroleague
(`54457dce300969b132fcfb3f:COMP:560100ac8dc7a24394b9563d`): Virtus Bologna 13 games (882 FGA), the last ones Panathinaikos (17 Nov, home)
and at Valencia (19 Nov); all 20 teams, so every number can be ranked within the Euroleague.

Same files and columns as `data/synergy/key_numbers_virtus-bologna_2026-11-22/` (see its README), without the BC Roma files
(BC Roma does not play the Euroleague: `defenders*.csv`, `ref_*.csv` are empty and not kept; `games.csv` has only `who=opp`).
`box_games_last2.csv`: Virtus Bologna player box scores of the last two games (`/api/games/<id>/playerboxscores/extended`).

Not an input of `notebooks/key_numbers.py` (the Key numbers tab stays Serie A only, where both teams can be ranked): it feeds the
Euroleague numbers in the text of `weekly/games/2026-11-22/`.
