# Work plan

Where the project is and what comes next. The idea: the site publishes everything **automatically first**, and each page is then
**reviewed and improved by hand**; comments from other users go in the box at the bottom of every page.

## Weekly routine

| When | What | Who |
|---|---|---|
| Every morning, 06:40 UTC | the GitHub Action collects finished LBA games, fetches the EuroCup data, regenerates what changed and rebuilds the site | automatic |
| Before each game | open the next games on the home page; read the opponent analysis and the BC Roma snapshot; write key points, comparison and what to expect in the notes; set `reviewed: yes` | analyst |
| After each game | check the post-game review, write the story of the game and the tactical notes; the draft flags and the "games before" banners go away by themselves | analyst |
| When asked | read the comments left on the pages and answer, or fold them into the text | analyst |

## Status

| Area | Status |
|---|---|
| Daily collection of LBA games, tests, automatic rebuild | done |
| Opponent analysis per game, with the comparison against BC Roma and the roster with photos | done |
| BC Roma snapshot before every game, in both competitions | done |
| Post-game reviews (LBA) | done |
| Compare the situation of two games (landing page and *Compare* page) | done |
| Flags: games before this one, automatic draft / work in progress | done |
| EuroCup standings of the group, from the EuroLeague results | written, **waiting for the first real run** to confirm the data |
| EuroCup headshots and rosters from the EuroLeague API | written, waiting for the first real run |
| Comments from other users | on the pages; needs the utterances app installed once on the repository |
| Positions and heights of the players | to fill in (`data/roster.csv`) |

## Next steps

1. **First real EuroCup run.** After the next daily run, check `data/eurocup/` and the EuroCup table of the Manresa snapshot; fix
   column names or the headshot field if the API differs from what was assumed.
2. **Written content.** Review the upcoming games first (Manresa, then Varese), then the past games' notes that are still empty.
3. **Positions and heights.** Fill in `data/roster.csv` for BC Roma and for the opponents that matter.
4. **EuroCup box scores without hand entry.** Use the EuroLeague API (box scores, play-by-play, shots) so that the EuroCup file and the
   EuroCup-only limits (no assist matrix, no zones) go away.
5. **EuroCup opponents.** Generate the opponent analysis for EuroCup games like the LBA ones, instead of a hand-made page per club.
6. **Reviews of EuroCup games** with the same structure as the LBA reviews.

## Ideas, not scheduled

- A season page: BC Roma's trends across the season, both competitions.
- Player pages with the history of each player's numbers and minutes.
- Official EuroCup tie-breaks in the standings.

Suggestions and corrections are welcome as comments on any page.
