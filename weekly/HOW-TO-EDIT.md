# How to edit a game page

Each game has two pages you can write on. Work only in `weekly/games/<date>/`:

| page | file |
|---|---|
| the opponent analysis (e.g. Varese) | `weekly/games/<date>/analysis.md` |
| BC Roma before the game | `weekly/games/<date>/snapshot.md` |

Example: Varese vs BC Roma is `weekly/games/2026-10-24/analysis.md`.
Every analysis has the same sections in the same order (the structure of the Varese page): Key points, results and standings, the
two teams compared, roster, starting five and bench, scoring sources / tendencies / shooting maps, key players, ball movement,
lineups, what to expect, highlights. A section that is still empty shows a grey box *"This section will be filled when the game is
reviewed"* (the line `{{ pending }}`): replace that line with your text and plots. The Synergy plots of the opponent go in the same
folder (`python notebooks/synergy_scouting_plots.py data/synergy/<folder> --out ...`, then copy the PNGs next to `analysis.md`).

Never edit `docs/` or `reports/`: they are generated and get overwritten. Your file is never overwritten.

## Steps

1. `git pull`
2. Open the file and write:
   * text under the `##` headings (text in `<!-- comments -->` is not published)
   * `==text==` to highlight
   * a line like `{{ roster }}` or `{{ figure: 07_key_players }}` is an automatic block: move the line to move the block, delete it to remove it
3. Your own image: copy it into the same folder and write `![caption](my_plot.png)` where you want it.
4. Preview: `python notebooks/weekly.py --no-build` then `python notebooks/build_site.py`, and open `docs/index.html`.
5. When finished set `reviewed: yes` at the top (and `title:` for the name in the Opponents dropdown).
6. Commit and push. The site rebuilds by itself.

Tip: `python notebooks/weekly.py --page <date>` prints the paths of the page files of a game.
Text only? Use the "Edit the text of this page" link on the published page.
