title: 
reviewed: no
generated: 7f113f73d8

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
- Every section has a short summary, shown as "In short", and the rest inside a "Details" drop-down: put an HTML comment holding the
  word more (the same one used in the sections below) on its own line between the two. A section that is only a summary needs no marker.
  Each fact lives in one section; elsewhere link to it ([text](#section-title) on this page, [text](offense_tendencies.html#section-title) on another).
- Highlight with ==text==. When you are done, set "reviewed: yes" at the top of the file.
Blocks of this page: {{ header }} {{ standings }} {{ comparison }} {{ roster }} {{ assists }} {{ turnovers }} {{ lineups }} {{ pending }} and
{{ figure: name }} for any generated image (01_results_timeline, 02_starters_bench, 03_minutes, 04_scoring_sources, 05_shooting,
06_hot_spots, {{ shot_charts }} (06b: one chart per player), 07_key_players, 08_shot_distribution, 09_basic_stats, 10_major_factors, 11_starting_fives, 13_rotation_by_minute: who is on the court at each minute, with the next options).
The three pages that go deeper (individual_tendencies.md, defense_tendencies.md, offense_tendencies.md, same folder) are linked at the top of this page ({{ more_analysis }}) when they exist: shot charts are on the individual page; play types, assists and turnovers on the offense page; what the team allows on the defense page.
THE STRUCTURE OF THIS PAGE IS THE STANDARD FOR EVERY ANALYSIS (same sections, same order, summary then Details); only the content changes. Rules: .claude/skills/opponent-analysis/SKILL.md
-->

# Pallacanestro Trieste vs BC Roma

{{ header }}

{{ more_analysis }}

## Key points

Based on the data only: 6 LBA games each (Trieste's round 6 at Virtus Bologna included), Synergy pull of 3 Nov 2026 for play types, shots and lineups, LBA box scores for the rest. Each fact has one home: the sections below hold the numbers, this list only says where to look.

- ==Trieste is 3-3 and has won three in a row== (Cantù, Verona, and Virtus Bologna away on 2 Nov, 100-93). Results and table: [standings](#lba-so-far-results-and-standings).
- ==The offense is Ross in the pick-and-roll and the lowest turnover rate in the LBA==; the rest of the play types are average or worse. Numbers: [offense](offense_tendencies.html#play-types-and-sets), [team comparison](#bc-roma-and-trieste-compared).
- ==The defense is strong against the roll man and isolations and soft on cuts and put-backs==: [defense](defense_tendencies.html#what-they-allow).
- ==Eight-man rotation, same starting five for five games==, a short bench: [roster and rotation](#roster-starting-five-and-bench).
- ==Ross has run the high pick-and-roll for four seasons== and finishes it with a drive (mostly to the right of the rim) or a pull-up three: [four seasons of shots](individual_tendencies.html#ross-four-seasons-of-shots).
- ==Where the game is decided==: the P&R ball handler both ways, transition, cuts and put-backs: [what to expect](#what-to-expect).

## LBA so far: results and standings

Trieste is 9th with 3-3 (three wins in a row), BC Roma 12th with 2-4. Trieste lost to Milano, Venezia and Varese by 4, 5 and 1 points and beat Cantù by 20, Verona by 9 and Virtus Bologna by 7.

<!-- more -->

{{ standings }}

{{ figure: 01_results_timeline }}

## BC Roma and Trieste compared

- Offense: BC Roma is 1st in the LBA in PPP (1.095), eFG% (61.4%) and Score% (49.5%); Trieste is 5th, 11th and 9th (1.004, 51.8%, 45.8%).
- Defense: BC Roma is 13th in PPP allowed (1.043) and eFG% (55.8%); Trieste is 8th in PPP (0.954) and 6th in eFG% (51.1%).
- Trieste's edge is ball security: 10.7% turnovers (lowest in the LBA) against 14.5% for BC Roma and 14.4% for the league. Pace is similar: 90.3 possessions a game for Trieste, 91.0 for BC Roma (league 89.2).

<!-- more -->

{{ comparison }}

{{ figure: 09_basic_stats }}

![Team z-scores vs the 16 LBA teams, LBA games only (Synergy)](01b_team_radar_zscore_competition_only.png)

- Both force fewer turnovers than the league (BC Roma 13.3%, Trieste 12.3%, league 14.4%). BC Roma concedes the second-highest rate of possessions ending in free throws (16.4%); Trieste's offense draws them on 15.3% (4th).

## Roster, starting five and bench

- Same five for five games: Ross, McDermott, Galloway, Jones, Brajkovic (since round 2); in round 1 (Milano) Candussi and DeAngeli started in place of Jones and Brajkovic.
- Eight players cover the minutes: Galloway 31', McDermott 31', Jones 29', Ross 26', DeAngeli 23', Ruzzier 21', Candussi 20', Brajkovic 17' (5 games). Two games were decided early (Cantù +20, Verona with 108 points), which lowers the starters' averages.
- The bench scores 21.2 points a game (20, 30, 20, 25, 22, 10); the starters 69.7.

<!-- more -->

{{ roster }}

- Ruzzier (5.5 PPG, 3.3 assists), DeAngeli (7.3 PPG) and Candussi (9.8 PPG) are the three regulars off the bench; Canka and Paiano play 3-5' a game. At Bologna the bench scored 10 and Galloway (24), McDermott (23), Jones (21) and Ross (18) scored 86 of the 100.
- Brajkovic (the rim finisher, 6.2 PPG) plays the least of the five starters; the lineups with Candussi at the five have the best defensive numbers.

{{ figure: 02_starters_bench }}

{{ figure: 03_minutes }}

{{ figure: 11_starting_fives }}

{{ figure: 13_rotation_by_minute }}

## Shot selection

- Trieste takes 410 shots in six games, 199 of them threes (49%; BC Roma 46%), at 32.7% from three and 54.5% from two.
- The corner is the productive three (28/64, 43.8%); the top of the key is the weak one (15/68, 22.1%). Paint attempts go in at 57.8%.
- Free throws come mostly from Ross (38 attempts of the team's 160, 33 made), Candussi (20) and Brajkovic (18).

<!-- more -->

By zone (Synergy): paint 185 attempts at 57.8%, mid-range 26 at 30.8%, corner threes 64 at 43.8%, wing threes 67 at 32.8%, top threes 68 at 22.1%. Trieste goes to the line on 5% of spot-up possessions and 16% of P&R ball-handler possessions. Who takes which shots: [individual tendencies](individual_tendencies.html#shot-charts-by-player).

{{ figure: 04_scoring_sources }}

{{ figure: 05_shooting }}

{{ figure: 06_hot_spots }}

## Key players

Ross, Jones and Galloway carry the usage; nobody else has used more than 75 possessions. Per-player lines, strengths and tendencies are on [individual tendencies](individual_tendencies.html#key-points). Ross's four seasons of shots (play types, pick-and-roll sides, driving direction, zones) are on [Ross: four seasons of shots](individual_tendencies.html#ross-four-seasons-of-shots).

<!-- more -->

{{ figure: 07_key_players }}

![Players volume and efficiency](04_players_volume_efficiency.png)

{{ figure: 08_shot_distribution }}

{{ figure: 10_major_factors }}

## What to expect

From the numbers only (6 LBA games each, so tendencies, not predictions). The three matchups that decide the game:

- **The P&R ball handler, both ways.** Trieste's best offense (1.207 PPP, Ross 55 possessions at 1.09) meets BC Roma's 13th-ranked defense against it (0.954 allowed on 109 possessions, 1 Nov); BC Roma's own (1.052, 2nd on 1 Nov) meets 1.012 allowed. Trieste forces turnovers on 21.7% of those possessions, so they are decided on turnovers as much as on shots.
- **Transition.** BC Roma allows 1.415 PPP (last), Trieste scores 1.063 (0.956 before Bologna), and Jones (1.320) is the one to watch; McDermott and Galloway are poor in the open court. BC Roma's own transition (94 possessions, 1.202) meets a defense that allows 1.028.
- **Cuts and put-backs.** BC Roma's cuts (1.657 PPP, 82.8% FG) against 1.186 allowed. BC Roma concedes 1.406 PPP on put-backs (last in the LBA) and Trieste scores 1.129 on them; Jones has 13 offensive rebounds.

<!-- more -->

### Other matchups

- **Roll man.** Trieste allows 0.708 (the league's best on 1 Nov); BC Roma's roll man scores 1.158 on 57 possessions.
- **Spot-ups.** BC Roma is 4th (1.103, 45.8% from three on 83 attempts) against a defense that faces the most spot-ups in the league (28% of possessions, 0.954 PPP).
- **Turnovers.** Trieste turns it over on 10.7% of possessions, BC Roma forces 13.3%; BC Roma loses it on 14.5%, Trieste forces 12.3%.
- **Free throws.** BC Roma sends opponents to the line on 16.4% of possessions; Trieste shoots 75.0% as a team (120/160), Ross 33/38.
- **Rotation.** Fatigue and fouls on Ross, Galloway and McDermott (30'+) are the lever against an eight-man rotation and a 21-point bench.

### Metrics to check during/after the game

- BC Roma's PPP allowed on Ross's P&R ball-handler possessions and the turnovers forced there; his pull-up threes (7/18 so far) and drives (12/20 at the basket).
- Trieste's transition points and who finishes them (Jones against McDermott/Galloway); put-backs and Jones's offensive rebounds.
- BC Roma's cuts and roll-man finishes against Trieste's roll-man defense.
- Free-throw attempts for both teams; minutes of Ross, Galloway and McDermott and Trieste's bench points.

### Other checks

- The Synergy pull is hand-extracted from the web app and the samples are small (6 games): read the figures as descriptive (see `data/synergy/trieste_2026-11-08/README.md`). Play-type ranks are from the 1 Nov leaderboard.
- BC Roma's EuroCup game at PAOK (3 Nov) comes five days earlier: check minutes and availability in the snapshot before the game.

### Clips suggested

Game clock from the Synergy shot list (time remaining in the period).

**Ross pull-up threes off the P&R** (7/18 made): at Bologna Q1 8:24 (made), Q2 8:01 (made), Q4 8:34, Q4 4:12, Q4 2:47; vs Verona Q1 8:55 (made), Q3 3:31, Q4 3:59, Q4 2:39; vs Cantù Q2 3:14; at Varese Q2 2:23, Q3 2:51; vs Venezia Q3 8:11; at Milano Q1 2:19 (made), Q2 5:19 (made), Q2 4:46, Q3 0:39 (made) and one more in Q3.

**Jones in transition** (12 made field goals in 21 attempts): at Bologna Q1 5:39, Q2 3:15, Q3 3:57; vs Cantù Q1 5:56 (three), Q3 7:36, Q3 9:02 (three); at Varese Q2 2:50, Q4 4:00, Q4 4:16 (three); vs Venezia Q2 5:37, Q4 1:29, Q4 1:04.
