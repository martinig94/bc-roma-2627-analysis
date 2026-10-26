# How to edit a game page

Each game has two pages you can write on. Work only in `weekly/games/<date>/`:

| page | file |
|---|---|
| the opponent analysis (e.g. Varese) | `weekly/games/<date>/analysis.md` |
| BC Roma before the game | `weekly/games/<date>/snapshot.md` |

Example: Varese vs BC Roma is `weekly/games/2026-10-24/analysis.md`.
Every analysis has the same sections in the same order (the structure of the Varese page): Key points, results and standings, the
two teams compared, roster, starting five and bench, scoring sources / tendencies / shooting maps, key players, assists, turnovers,
lineups, defensive attitude, what to expect (with the metrics to check), clips suggested, other suggested checks. A section that is
still empty shows a grey box *"This section will be filled when the game is reviewed"* (the line `{{ pending }}`): replace that line with
your text and plots. The Synergy plots of the opponent go in the same folder (`python notebooks/synergy_scouting_plots.py data/synergy/<folder> --out ...`,
then copy the PNGs next to `analysis.md`); the page shows them, in the order of the Varese page, when they are there.

Every analysis also has three pages that go deeper, in the same folder; they are created with the analysis (also for the earlier games)
and linked from the end of the analysis ("More analysis"). They are yours, never overwritten:

| subpage | file |
|---|---|
| individual tendencies (triangle plots of the shot attempts, energy indices, rotation by player) | `weekly/games/<date>/individual_tendencies.md` |
| defense tendencies | `weekly/games/<date>/defense_tendencies.md` |
| offense tendencies | `weekly/games/<date>/offense_tendencies.md` |

They are plain markdown: text, `{{ figure: name }}` blocks and your own images (same folder, `![caption](file.png)`). A subpage you delete is not
linked (and is created again the next time the analysis is generated).

Never edit `docs/` or `reports/`: they are generated and get overwritten (`docs/` is not even committed). Your file is never overwritten.

## Steps

1. `git pull`
2. Open the file and write:
   * text under the `##` headings (text in `<!-- comments -->` is not published)
   * `==text==` to highlight
   * a line like `{{ roster }}` or `{{ figure: 07_key_players }}` is an automatic block: move the line to move the block, delete it to remove it
3. Your own image: copy it into the same folder and write `![caption](my_plot.png)` where you want it.
4. Preview: `python notebooks/weekly.py --no-build` then `python notebooks/build_site.py`, and open `docs/index.html`.
5. When finished set `reviewed: yes` at the top (and `title:` for the name in the Opponents dropdown).
6. Commit and push. GitHub Actions rebuilds and republishes the site by itself.

Tip: `python notebooks/weekly.py --page <date>` prints the paths of the page files of a game.
Text only? Use the "Edit the text of this page" link on the published page.
