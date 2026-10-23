# Synergy defensive ratings workbook (EuroCup, one tab per play type)

`DEFENSIVE_RATINGS_EUROCUP_221026.xls` is the Synergy export (Numbers → Excel) with a **Leaderboard** tab added as the first sheet:
one row per team (same order as the PPP tab), overall GP / Poss / PPP / rank, then Poss, PPP and rank for each play type (rank 1 = lowest PPP allowed).

The tab is made of formulas that read the play-type tabs. After each EuroCup or LBA game, paste the new Synergy export over those tabs
(same layout: header on row 2, teams from row 3, PPP tab sorted by PPP) and the Leaderboard recalculates. Room for 40 teams, so it works for the LBA too.
To add the tab to a fresh export: `python notebooks/synergy_leaderboard.py IN.xls OUT.xls`.
