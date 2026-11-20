title: 
reviewed: no
generated: f858ce4e9b

<!--
HOW TO EDIT THIS PAGE (this comment is not shown on the site)
- This file is yours: it is never overwritten. Reorder, delete or add sections and text freely.
- The lines like {{ comparison }} or {{ figure: 07_key_players }} are automatic blocks: they are filled in when the site is built
  and keep refreshing when the data changes. Delete a line to remove its block, move it to move the block.
- {{ pending }} is a grey box saying "This section will be filled when the game is reviewed". Replace it with your text (or your
  plots) when you write the section; a section without text and without a box is left out of the page.
- Your own plots and images: put the file in this folder (weekly/games/<date>/) and write ![caption](file.png).
  The Synergy plots (python notebooks/synergy_scouting_plots.py data/synergy/<folder>) go here by name:
  01b_team_radar_zscore_competition_only, 02_opponent_playtypes, 03_playtype_ppp_ref_vs_opp, 06_players_playtype_mix,
  04_players_volume_efficiency, 05_player_<name>_shot_profile (one per player), 07_lineups_usage_vs_ppp,
  08_lineups_offense_vs_defense, 09_lineups_style_profile.
- Highlight with ==text==. When you are done, set "reviewed: yes" at the top of the file.
Blocks of this page: {{ header }} {{ standings }} {{ comparison }} {{ roster }} {{ assists }} {{ turnovers }} {{ lineups }} {{ pending }} and
{{ figure: name }} for any generated image (01_results_timeline, 02_starters_bench, 03_minutes, 04_scoring_sources, 05_shooting,
06_hot_spots, {{ shot_charts }} (06b: one chart per player), 07_key_players, 08_shot_distribution, 09_basic_stats, 10_major_factors, 11_starting_fives, 13_rotation_by_minute: who is on the court at each minute, with the next options).
The three pages that go deeper (individual_tendencies.md, defense_tendencies.md, offense_tendencies.md, same folder) are linked at the top of this page ({{ more_analysis }}) when they exist: shot charts are on the individual page, play types, assists and turnovers on the offense page, what the team allows on the defense page.
- Every section has a short summary ("In short") and a "Details" drop-down: put an HTML comment holding the word more on its own line between the two. Each fact lives in one section; elsewhere link to it.
THE STRUCTURE OF THIS PAGE IS THE STANDARD FOR EVERY ANALYSIS (same sections, same order, summary then Details); only the content changes. Rules: .claude/skills/opponent-analysis/SKILL.md
-->

# Virtus Costa Bologna vs BC Roma

{{ header }}

{{ more_analysis }}

## Key points

Based on the data only: 8 LBA games each (Synergy and LBA box scores; ranks are within the LBA) plus Bologna's 13 Euroleague games (Synergy, pulled on 20 Nov 2026, the games of 17 and 19 Nov included).

- ==Virtus Bologna is first with 7-1 (+86)==, its only loss at home to Trieste: [standings](#lba-so-far-results-and-standings).
- ==One of the best defenses of the league with a top-three offense==: [team comparison](#bc-roma-and-virtus-bologna-compared).
- ==In the Euroleague the defense holds up and the offense does not== (18th of 20): [team comparison](#bc-roma-and-virtus-bologna-compared).
- ==Few turnovers and a lot of open-court points==: [offense](offense_tendencies.html#key-points).
- ==Mid-range is a real shot for Bologna and the rim its best finishing spot in the league==: [shot selection](#shot-selection).
- ==Bello and Alston have played only some of the games==: [roster](#roster-starting-five-and-bench).
- Where the game is decided: [what to expect](#what-to-expect).

## LBA so far: results and standings

Virtus Bologna is 1st with 7-1, level on points with Napoli; BC Roma is 13th with 2-6. Bologna won the first five, lost 93-100 at home to Trieste in round 6, then beat Verona (95-81, home) and Trento (88-75, away).

In the Euroleague Bologna is 5-8. Sunday is its third game in six days: it beat Panathinaikos 83-79 at home on 17 Nov and lost 87-91 at Valencia on 19 Nov.

<!-- more -->

{{ standings }}

{{ figure: 01_results_timeline }}

## BC Roma and Virtus Bologna compared

- Defense is the gap: Bologna allows about 14 points per 100 possessions fewer than BC Roma (ratings in the table).
- Offense: the two are close (Bologna 3rd and BC Roma 2nd in points per possession, Synergy count).
- Bologna grabs more of its own misses and goes to the line more often than BC Roma.
- Against Euroleague opponents the defense stays in the top third (7th of 20) while the offense drops to 18th of 20.

<!-- more -->

Virtus Bologna in its two competitions (Synergy; rank within each competition, 1 = best):

| | Serie A, 8 games | Rank (16) | Euroleague, 13 games | Rank (20) |
|---|---:|---:|---:|---:|
| Points per possession | 1.06 | 3 | 0.95 | 18 |
| Effective field-goal % | 55.7% | 3 | 51.1% | 18 |
| Turnovers per possession | 11.8% | 2 | 13.6% | 6 |
| Three-point % | 35.6% | | 32.2% | |
| Offensive rebounds, share of own misses | 33% | 2 | 32% | 6 |
| Points allowed per possession | 0.93 | 3 | 0.99 | 7 |
| Opponents' effective field-goal % | 50.7% | 4 | 52.7% | 6 |
| Turnovers forced per possession | 15.2% | 5 | 11.8% | 19 |
| Defensive rebounds, share of opponents' misses | 71% | 5 | 67% | 17 |

{{ comparison }}

{{ figure: 09_basic_stats }}

## Roster, starting five and bench

- Fixed starters: Diouf (8 of 8 games) and Ferrari (7 of 8); Moore has started all six games he played (he joined in round 2).
- Carr (5 starts) is the main ball handler and plays the most minutes (24' a game); Frazier and Edwards move in and out of the five.
- Bello (3 LBA games, all as starter) and Alston (4 LBA games, all as starter) have missed part of the LBA season but played all 13 Euroleague games, the last two included: check the availability before the game.
- The bench is Hackett (19' a game, never a starter), Diarra, Baldasso and Casarin.

<!-- more -->

Minutes in the last two Euroleague games (Panathinaikos 17 Nov / at Valencia 19 Nov): Frazier 25 / 26, Carr 20 / 26, Edwards 21 / 19, Moore 20 / 19, Diarra 20 / 19, Diouf 20 / 16, Hackett 17 / 19, Bello 19 / 16, Kokila 18 / 11, Alston 17 / 10, Klintman 0 / 17, Baldasso 1 / 4, Ferrari 1 / 0; Casarin did not play. In the Euroleague Kokila has played 10 games (1 in the LBA), Baldasso 6, Ferrari 5 and Casarin 1.

{{ roster }}

{{ figure: 02_starters_bench }}

{{ figure: 03_minutes }}

{{ figure: 11_starting_fives }}

{{ figure: 13_rotation_by_minute }}

## Shot selection

- Bologna finishes at the rim better than any team in the league (69%), but only about 1 shot in 3 is taken there.
- ==Mid-range is a shot it uses== (1 in 5 attempts, 4th in the LBA, 40%); about 40% of the attempts are threes (36%, 7th).
- Who takes which shots: [individual tendencies](individual_tendencies.html#shot-charts-by-player).

<!-- more -->

Same shot mix in the Euroleague (13 games, 882 attempts), lower percentages: 35% of the attempts at the rim (61% made), 17% mid-range (41%), 42% threes (32%).

{{ figure: 04_scoring_sources }}

{{ figure: 05_shooting }}

{{ figure: 06_hot_spots }}


## Key players

Carr runs the offense (most possessions, 6.6 assists a game) and creates most of the pick-and-roll shots; Frazier is the main three-point shooter (42 of his 63 attempts are threes); Alston scores the most per game when he plays (15.0); Diouf (post-ups, put-backs) and Diarra (cuts, rolls) finish at the rim. Lines per player: [individual tendencies](individual_tendencies.html#key-points).

<!-- more -->

{{ figure: 07_key_players }}

{{ figure: 08_shot_distribution }}

{{ figure: 10_major_factors }}


## What to expect

From the numbers only (8 games each, so tendencies, not predictions):

- **BC Roma's spot-ups against Bologna's spot-up defense.** BC Roma is 3rd in points per possession on spot-ups; Bologna allows the second-lowest in the LBA, but is 17th of 20 against Euroleague spot-ups.
- **Isolations and pick-and-roll ball handlers.** Bologna defends both very well (3rd and 4th best); BC Roma's isolations are the best of the league.
- **Transition and put-backs, both ways.** Bologna runs a lot (2nd in share of possessions, 4th in efficiency); BC Roma's defense allows the 3rd most points per possession in transition and the most on put-backs, Bologna's own put-back defense is 14th.
- **Free throws.** BC Roma's offense is last in free-throw rate and its defense 3rd highest in free throws allowed; Bologna's offense is 9th and its defense 5th lowest.

<!-- more -->

### Metrics to check during/after the game

- BC Roma's spot-up and isolation shots against Bologna's defense: attempts, efficiency, who takes them.
- Bologna's transition points and points off BC Roma's turnovers (Bologna turns the ball over less than all teams but one).
- Put-backs and second-chance points allowed by BC Roma.
- Free-throw attempts of both teams.
- Who starts for Bologna (Bello, Alston, Frazier or Edwards).

### Other checks

- The samples are small (8 LBA games). LBA Synergy counts are those of the pull of 16 Nov, checked again on 20 Nov with no change (ranks over the 16 teams): `data/synergy/key_numbers_virtus-bologna_2026-11-22/README.md`.
- Euroleague numbers (13 games, ranks over the 20 teams, pulled on 20 Nov): `data/synergy/key_numbers_virtus-bologna_euroleague_2026-11-22/README.md`. The opposition is of a different level, so the two competitions are shown side by side and never added together in the ranks.
- The figures and tables built from LBA box scores (standings, minutes, starters, shot charts, rotation) and the Key numbers tab cover the LBA only.
