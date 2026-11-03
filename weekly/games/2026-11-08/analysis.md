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
- Highlight with ==text==. When you are done, set "reviewed: yes" at the top of the file.
Blocks of this page: {{ header }} {{ standings }} {{ comparison }} {{ roster }} {{ assists }} {{ turnovers }} {{ lineups }} {{ pending }} and
{{ figure: name }} for any generated image (01_results_timeline, 02_starters_bench, 03_minutes, 04_scoring_sources, 05_shooting,
06_hot_spots, {{ shot_charts }} (06b: one chart per player), 07_key_players, 08_shot_distribution, 09_basic_stats, 10_major_factors, 11_starting_fives, 13_rotation_by_minute: who is on the court at each minute, with the next options).
The three pages that go deeper (individual_tendencies.md, defense_tendencies.md, offense_tendencies.md, same folder) are linked at the top of this page ({{ more_analysis }}) when they exist: shot charts are on the individual page; play types, assists and turnovers on the offense page; what the team allows on the defense page.
THE STRUCTURE OF THIS PAGE IS THE STANDARD FOR EVERY ANALYSIS (same sections, same order); only the content changes.
-->

# Pallacanestro Trieste vs BC Roma

{{ header }}

{{ more_analysis }}

## Key points

Based on the data only (6 LBA games for Trieste, round 6 at Virtus Bologna included, and 6 for BC Roma; Synergy pull of 3 Nov 2026 for play types, shots and lineups; LBA box scores for the rest). Play-type ranks in the LBA are not recalculated after round 6 (the league leaderboard is from 1 Nov): where a rank appears it is from that date.

- Trieste is 3-3 (lost to Milano, Venezia and Varese by 4, 5 and 1 points; beat Cantù by 20, Verona by 9 and, on 2 Nov, Virtus Bologna away by 7, 100-93). It scores 90.8 points a game (5th in the LBA) and allows 86.5 (7th). By PPP it is 5th on offense (1.004) and 8th on defense (0.954 allowed); BC Roma is 1st on offense (1.095) and 13th on defense (1.043).
- Trieste's offense runs through Ross: 55 of its 92 P&R ball-handler possessions (1.09 PPP) and 6.8 assists a game. As a team the P&R ball handler is its best play type (1.207 PPP, 65.2% eFG) and it has the lowest turnover rate in the LBA (10.7% of possessions, league 14.4%).
- Most of the rest is below average: P&R roll man 0.736 PPP, isolations 0.722, post-ups 0.789, off-screen plays 0.800. Transition recovered with the Bologna game (1.063 PPP; it was 0.956, last in the LBA, before it). Trieste shoots 51.8% eFG (11th), 32.7% from three (199 attempts of 410).
- The defense is strongest against the roll man (0.708 PPP; 1st in the LBA at the 1 Nov leaderboard) and isolations (0.476) and weakest against cuts (1.186) and put-backs (1.273); the P&R ball handler scores 1.012 (59.3% eFG). It allows few free throws on spot-ups and faces a lot of them (27.9% of possessions, 0.954 PPP; the most in the LBA on 1 Nov).
- Short rotation: eight players cover the minutes (Galloway 31', McDermott 31', Jones 29', Ross 26'). The starting five has been the same for five games. The bench scores 21.2 points a game, 10 of them at Bologna.
- BC Roma's transition defense allows 1.415 PPP (last in the LBA) and Trieste's transition offense is also last (0.956): the one matchup where the weaker side of both teams meets. Jones is the exception (25 possessions, 1.32 PPP); McDermott (15, 0.60) and Galloway (18, 0.72) are not.

## LBA so far: results and standings

{{ standings }}

### Results timeline

{{ figure: 01_results_timeline }}

## BC Roma and Trieste compared

{{ comparison }}

### The two teams at a glance

{{ figure: 09_basic_stats }}

![Team z-scores vs the 16 LBA teams, LBA games only (Synergy)](01b_team_radar_zscore_competition_only.png)

- Offense: BC Roma is 1st in the LBA in PPP (1.095), eFG% (61.4%) and Score% (49.5%); Trieste is 5th, 11th and 9th (1.004, 51.8%, 45.8%). Trieste's strength is ball security: 10.7% turnovers against 14.5% for BC Roma and 14.4% for the league.
- Defense: BC Roma is 13th in PPP allowed (1.043) and eFG% (55.8%); Trieste is 8th in PPP (0.954) and 6th in eFG% (51.1%). Both force fewer turnovers than the league (BC Roma 13.3%, Trieste 12.3%, league 14.4%). BC Roma concedes the second-highest rate of possessions ending in free throws (16.4%); Trieste's offense draws them on 15.3% (4th).
- Pace is similar: 90.3 possessions a game for Trieste, 91.0 for BC Roma (league 89.2).

## Trieste roster

{{ roster }}

## Starting five and bench

- Same five for five games: Ross, McDermott, Galloway, Jones, Brajkovic (since round 2). In round 1 (Milano) Candussi and DeAngeli started in place of Jones and Brajkovic.
- Bench scoring: 21.2 points a game (20, 30, 20, 25, 22, 10); the starters score 69.7. Ruzzier (21', 5.5 PPG, 3.3 assists), DeAngeli (23', 7.3 PPG) and Candussi (20', 9.8 PPG) are the three regulars off the bench; Canka and Paiano play 3-5' a game. At Bologna Galloway (24), McDermott (23), Jones (21) and Ross (18) scored 86 of the 100.
- Minutes: Galloway 31', McDermott 31', Jones 29', Ross 26', DeAngeli 23', Ruzzier 21', Candussi 20', Brajkovic 17' (5 games). Two games were decided early (Cantù +20, Verona with 108 points), which lowers the starters' averages.
- Brajkovic (the rim finisher: 11/16 from two, 6.2 PPG) plays the least of the five starters; the lineups with Candussi at the five have the best defensive numbers (see Lineups).

{{ figure: 02_starters_bench }}

{{ figure: 03_minutes }}

{{ figure: 11_starting_fives }}

{{ figure: 13_rotation_by_minute }}

## Shot selection

Where the shots come from, shot clock, who takes them.

- Trieste takes 410 shots in six games, 199 of them threes (49%; BC Roma 46%), at 32.7% from three and 54.5% from two. By zone (Synergy): paint 185 attempts at 57.8%, mid-range 26 at 30.8%, corner threes 64 at 43.8%, wing threes 67 at 32.8%, top threes 68 at 22.1%.
- The corner is the productive three (28/64); the top of the key is the weak one (15/68). Ross takes 21 of his 29 threes from the top (7 made), Galloway 15 of his 45 (3 made).
- Trieste goes to the line on 5% of spot-up possessions and 16% on P&R ball handler: its free throws come mostly from Ross (38 attempts of the team's 160, 33 made), Candussi (20) and Brajkovic (18).

{{ figure: 04_scoring_sources }}

{{ figure: 05_shooting }}

{{ figure: 06_hot_spots }}

## Key players

### Shooting

Possessions used and efficiency (Synergy, LBA games, six games unless noted):

- Ross: 99 possessions (16.5 a game), 1.121 PPP, 56.5% eFG, 18.5 PPG, 6.8 assists and 1.8 turnovers a game. 34/69 from the field, 10/29 from three (7 of the 21 top threes), 24/40 from two; 33/38 from the line. On the P&R ball handler: 18 pull-up threes, 7 made; 12/20 at the basket.
- Jones: 96 possessions, 1.010 PPP, 50.0% eFG, 16.2 PPG, 8.8 rebounds (13 offensive). 14/40 from three (6/13 in the corner), 19/40 from two; best in transition (25 possessions, 1.320 PPP).
- Galloway: 94 possessions, 0.989 PPP, 50.6% eFG, 15.5 PPG; 16/45 from three (9/17 in the corner), 15/32 from two; 2.8 assists. Best as a spot-up (22 possessions, 1.32 PPP).
- Candussi: 61 possessions, 0.967 PPP, 48.9% eFG, 9.8 PPG; 15/24 from two, 5/22 from three; 20 free-throw attempts.
- McDermott: 74 possessions, 1.014 PPP, 53.3% eFG, 12.5 PPG; 12/38 from three (31.6%) and 14/22 from two (22 spot-up possessions at 1.27, 15 transition possessions at 0.60). 23 points at Bologna.
- DeAngeli: 43 possessions, 1.023 PPP, 56.3% eFG; 6/14 from three.
- Ruzzier: 42 possessions, 0.786 PPP, 37.0% eFG; 20 assists and 7 turnovers.
- Brajkovic: 29 possessions in 5 games, 1.069 PPP, 68.8% eFG (11/16, all two-pointers).

Samples are small: nobody beyond Ross, Jones, Galloway, McDermott and Candussi has used more than 60 possessions.

{{ figure: 07_key_players }}

![Players volume and efficiency](04_players_volume_efficiency.png)

{{ figure: 08_shot_distribution }}

### Other stats

{{ figure: 10_major_factors }}

## What to expect

From the numbers only (6 LBA games each, so tendencies, not predictions):

- **The P&R ball handler, both ways.** Trieste's best offense (1.207 PPP, Ross 55 possessions at 1.09) meets BC Roma's 13th-ranked defense against it (0.954 allowed on 109 possessions, 1 Nov); on the other side BC Roma (1.052, 2nd on 1 Nov) meets Trieste's 1.012 allowed. Trieste forces turnovers on 21.7% of those possessions, so the possessions are decided on turnovers as much as on shots.
- **Transition.** BC Roma's defense allows 1.415 PPP in transition (last), Trieste's offense scores 1.063 (0.956 before Bologna) — Jones (1.320) is the one to watch; McDermott and Galloway are poor in the open court. BC Roma's own transition (94 possessions, 1.202) meets a defense that allows 1.028.
- **Roll man.** Trieste's defense allows 0.708 against the roll man (the league's best on 1 Nov); BC Roma's roll man scores 1.158 (66 points on 57 possessions).
- **Cuts and put-backs.** BC Roma's cuts (1.657 PPP, 82.8% FG) against 1.186 allowed. On the boards, BC Roma concedes 1.406 PPP on put-backs (last in the LBA) and Trieste's offense scores 1.129 on them (31 possessions); Jones has 13 offensive rebounds in six games.
- **Turnovers.** Trieste turns it over on 10.7% of possessions, BC Roma forces 13.3%; BC Roma loses it on 14.5%, Trieste forces 12.3%.
- **Free throws.** BC Roma's defense sends opponents to the line on 16.4% of possessions (second most); Trieste is 33/38 with Ross and 75.0% as a team (120/160).
- **Rotation.** Eight players, same starting five for five games, a bench scoring 21.2: fatigue and fouls on Ross, Galloway and McDermott (30'+) are the lever.

### Metrics to check during/after the game

- BC Roma's PPP allowed on Trieste's P&R ball-handler possessions (Ross) and the number of turnovers forced there.
- Trieste's transition points and who finishes them (Jones against McDermott/Galloway).
- Trieste's put-backs and second-chance points, and Jones's offensive rebounds.
- Ross's pull-up threes and drives to the basket (18 pull-up threes, 7 made, in six games) and his free throws.
- Free-throw attempts for both teams.
- BC Roma's cuts and roll-man finishes against Trieste's roll-man defense.
- Minutes of Ross, Galloway and McDermott and Trieste's bench points.

### Other checks

- Data caveat: the Synergy pull is hand-extracted from the web app and the samples are small (6 games); read the figures as descriptive. Check the review notes in `data/synergy/trieste_2026-11-08/README.md`.
- Trieste won round 6 at Virtus Bologna (100-93, 2 Nov) and the game is in the numbers: the starters played 27' to 33' (Brajkovic 21') and the bench scored 10.
- BC Roma's EuroCup game at PAOK (3 Nov) comes five days earlier: check minutes and availability in the snapshot before the game.

## Clips suggested

Game clock from the Synergy shot list (time remaining in the period):

**Ross pull-up threes off the P&R** (7/18 made): at Bologna Q1 8:24 (made), Q2 8:01 (made), Q4 8:34, Q4 4:12, Q4 2:47; vs Verona Q1 8:55 (made), Q3 3:31, Q4 3:59, Q4 2:39; vs Cantù Q2 3:14; at Varese Q2 2:23, Q3 2:51; vs Venezia Q3 8:11; at Milano Q1 2:19 (made), Q2 5:19 (made), Q2 4:46, Q3 0:39 (made) and one more in Q3.

**Jones in transition** (12 made field goals in 21 attempts): at Bologna Q1 5:39, Q2 3:15, Q3 3:57; vs Cantù Q1 5:56 (three), Q3 7:36, Q3 9:02 (three); at Varese Q2 2:50, Q4 4:00, Q4 4:16 (three); vs Venezia Q2 5:37, Q4 1:29, Q4 1:04.
