title: 
reviewed: no
generated: 4e7658fe31

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
The three pages that go deeper (individual_tendencies.md, defense_tendencies.md, offense_tendencies.md, same folder) are linked at the end of this page when they exist.
THE STRUCTURE OF THIS PAGE IS THE STANDARD FOR EVERY ANALYSIS (same sections, same order); only the content changes.
-->

# BC Roma vs Longobardi Scafati Basket

{{ header }}

## Key points

Based on the data only (5 LBA games each; Synergy pull of 26 Oct 2026 for the play types, shots and lineups; LBA box scores for the rest).

- Same record (1-4), different games: BC Roma loses high-scoring games (99.6 scored, 97.8 allowed), Scafati low-scoring ones (78.4 scored, 90.0 allowed). Scafati's offense is 13th in the LBA by PPP (0.907), its defense 14th (1.061 allowed); BC Roma is 2nd on offense (1.078) and 15th on defense (1.063).
- Scafati's defense gives up the highest eFG% in the league (60.7%, 16th of 16) and is weakest against transition (1.39 PPP allowed, 15th), roll men (1.35, 15th) and isolations (1.43, 16th). What it does well: force turnovers (17.8% forced TOV%, 4th in the LBA; BC Roma forces 14.2%, 15th) and defend the P&R ball handler (0.89 PPP, 8th).
- Scafati's two main play types go in opposite directions: spot-ups are 23% of its possessions at 1.04 PPP (5th in the LBA, 27/62 from three), the P&R ball handler is 21% at 0.67 PPP (15th). Mascolo (32 possessions, 0.53 PPP, 4/20 from the field) and Nevels (18, 0.56) are the ball handlers that struggle; Moore (34, 0.85, 5/10 on pull-up threes) is the one that works.
- Transition is Scafati's most efficient offense (1.22 PPP, 5th) and Offurum its main runner (17 possessions, 9/11 at the rim). BC Roma's transition defense allows 1.42 PPP, last in the LBA.
- Short bench and short roster: Scafati's bench scores 17.6 a game (lowest in the LBA; BC Roma 37), 11 players have scored, three of them under 2 points a game. Moore missed the Virtus game, McGruder did not play against Trento.
- Free throws: Scafati shoots 61.3% from the line (Onyema 7/15, Lever 1/4) and draws a lot of them (FT rate 33.4, BC Roma 29.4). Mascolo alone has 30 attempts in five games.

## LBA so far: results and standings

{{ standings }}

### Results timeline

{{ figure: 01_results_timeline }}

## BC Roma and Scafati compared

{{ comparison }}

### The two teams at a glance

{{ figure: 09_basic_stats }}

![Team z-scores vs the 16 LBA teams, LBA games only (Synergy)](01b_team_radar_zscore_competition_only.png)

- Offense: BC Roma is above the league on every efficiency metric (eFG% 60.7 vs league 53.3, PPP 1.078); Scafati is below on all of them (PPP 0.907, Score% 41.9 vs league 44.9), with the turnover rate the only one close to average (15.3%, league 14.5%).
- Defense: both are below average in PPP allowed (Scafati 1.061, BC Roma 1.063, league 0.983). The profiles differ: Scafati allows the worst eFG% in the league (60.7%) but forces turnovers (16.1% of possessions, above the 14.5% average) and sends opponents to the line less than anyone (11.1% of possessions end in free throws); BC Roma forces few turnovers (11.9%) and fouls more (16.3% of possessions end in free throws).
- Pace: BC Roma plays faster (92.0 possessions a game in Synergy's count, Scafati 86.4; LBA pace 78.2 vs 75.3 per 40').

## Scafati roster

{{ roster }}

Johnson joined for round 3 and has started the three games since. Moore (0' at Virtus Bologna) and McGruder (0' vs Trento) each have a game without minutes. Brancaccio and Toro are 2009-born players with 1' between them.

## Starting five and bench

- Three fixed starters in all five games: Offurum, Onyema and, until round 4, Nevels (bench against Trento, 24'). The other spots rotate: Moore 4 starts, Johnson 3 (all his games), Mascolo 2 (the last two), Lever 1, McGruder 1.
- Bench scoring is the lowest in the LBA: 17.6 points a game (league teams range from 17.6 to 47.8; BC Roma 37.0). The starters score 61 of the 78 points. The best bench game was 27 points against Verona.
- Eight players above 18' a game; Iannuzzi (6'), Spinelli (3.6', but 18' at Virtus Bologna when Moore was out), Ceron (3.8') and the two 2009-born players fill the rest.
- Minutes trend: Onyema 25' → 35' and Moore 34' in the last game (the win against Trento); Lever 22-24' in the first four games, 14' against Trento; Offurum 16' against Verona, 30' and 27' since.
- Scafati averages 18.2 fouls a game, fewest in the LBA (BC Roma 25.6), and 7.0 steals (7th; BC Roma 5.0, 14th).

{{ figure: 02_starters_bench }}

{{ figure: 03_minutes }}

{{ figure: 11_starting_fives }}

{{ figure: 13_rotation_by_minute }}

## Scoring sources, tendencies and shooting maps

{{ figure: 04_scoring_sources }}

{{ figure: 05_shooting }}

{{ figure: 06_hot_spots }}

- Scafati takes 23.4 threes a game at 38.5% (BC Roma 31.4 at 37.6%): 37% of its field-goal attempts are threes, 46% for BC Roma. By zone (Synergy, 319 attempts): paint 150 attempts at 52.7%, mid-range 51 at 33.3%, wing threes 75 at 34.7%, corner threes 21 at 47.6%, top threes 22 at 40.9%.
- Mid-range volume is concentrated in two players: Nevels (16 attempts, 8 made) and Mascolo (14, 2 made).
- Two-point shooting is the gap: Scafati 48.0% from two (BC Roma 63.7%); Onyema (27/42, all in the paint) is the only player above 55% inside the arc among the regulars.

### Shot charts by player

{{ shot_charts }}

![Scafati play types](02_opponent_playtypes.png)
![Scafati play types and PPP](03_playtype_ppp_ref_vs_opp.png)

- Spot-up (23% of possessions, 1.04 PPP) and P&R ball handler (21%, 0.67 PPP) are Scafati's two main play types; BC Roma scores 1.02 PPP on the P&R ball handler, 5th in the league, where Scafati is 15th.
- Transition is Scafati's best play type (11% of possessions, 1.22 PPP, 65% eFG) and put-backs the second (1.14 PPP on 22 possessions, Onyema).
- Post-ups (31 possessions, 0.61 PPP, 33% eFG) and cuts (33, 0.85) are below BC Roma's numbers (1.31 and 1.68 PPP, 1st in the league on both).
- Compared to BC Roma, Scafati plays more post-ups (7% of possessions vs 3%) and fewer roll-man finishes (6% vs 10%).

![Scafati play types per player](06_players_playtype_mix.png)

- The P&R ball handler possessions are split three ways: Moore 34, Mascolo 32, Nevels 18. Moore is the only efficient one (0.85 PPP; Mascolo 0.53, Nevels 0.56).
- Spot-ups are spread: Nevels 23 (1.17 PPP), Offurum 17 (1.00), Johnson 14 (1.50, 7/12 from three), Lever 13 (0.92), McGruder 12 (1.17).
- Onyema's possessions are cuts (16) and roll-man finishes (12, 1.25 PPP); Lever's are spot-ups (13), roll-man (9, 0/6 from three on pick-and-pops) and post-ups (8).
- Isolations: Mascolo 10 (0.90 PPP), Nevels 6, the rest under 4.

## Key players

### Shooting

{{ figure: 07_key_players }}

![Players volume and efficiency](04_players_volume_efficiency.png)

Possessions used and efficiency (Synergy, LBA games):

- Mascolo, 70 possessions in 5 games (14 a game), 0.76 PPP, 39.8% eFG, 10.6 PPG; 30 free-throw attempts (18 made) and 4.6 assists a game. He ends the most possessions of the team with the lowest efficiency among the regulars.
- Moore, 69 possessions in 4 games (17 a game), 0.93 PPP, 57.6% eFG, 16.0 PPG, 7.0 assists; 9/21 from three, 5/13 on pull-ups. The highest usage and the highest turnover count (16 in 4 games, 4 a game, TO% 24.6).
- Offurum, 66 possessions (13 a game), 1.02 PPP, 57.4% eFG, 13.2 PPG; 20/32 in the paint, 4/10 from three.
- Nevels, 66 possessions (13 a game), 0.88 PPP, 47.0% eFG, 11.6 PPG; 9/26 from three (3/11 on pull-ups), 8/16 mid-range; 11/12 from the line.
- Onyema, 55 possessions (11 a game), 1.11 PPP, 64.3% eFG, 12.2 PPG, 7.4 rebounds (2.4 offensive), 8 blocks; no attempt outside the paint; 7/15 from the line.
- Lever, 43 possessions (9 a game), 0.77 PPP, 42.1% eFG, 6.6 PPG; 6/19 from three, 7/17 in the paint.
- Johnson, 24 possessions in 3 games, 1.17 PPP, 67.5% eFG, 9.3 PPG; 7/14 from three (5/8 open), 7 steals in 3 games.
- McGruder, 25 possessions in 3 games, 0.80 PPP, 36.4% eFG; 4/11 from three, 2/11 from two.

{{ figure: 08_shot_distribution }}

![Moore shot profile](05_player_moore_shot_profile.png)
![Moore shot types](05c_player_moore_shot_types.png)
![Mascolo shot profile](05_player_mascolo_shot_profile.png)
![Mascolo shot types](05c_player_mascolo_shot_types.png)
![Nevels shot profile](05_player_nevels_shot_profile.png)
![Nevels shot types](05c_player_nevels_shot_types.png)
![Offurum shot profile](05_player_offurum_shot_profile.png)
![Offurum shot types](05c_player_offurum_shot_types.png)
![Onyema shot profile](05_player_onyema_shot_profile.png)
![Onyema shot types](05c_player_onyema_shot_types.png)
![Johnson shot profile](05_player_johnson_shot_profile.png)
![Johnson shot types](05c_player_johnson_shot_types.png)
![Lever shot profile](05_player_lever_shot_profile.png)
![Lever shot types](05c_player_lever_shot_types.png)
![McGruder shot profile](05_player_mcgruder_shot_profile.png)

### Other stats

{{ figure: 10_major_factors }}

## Assists

{{ assists }}

Moore to Offurum (9) is the main pair; Mascolo distributes to Lever, Offurum and Onyema (4-5 each).

## Turnovers

{{ turnovers }}

Moore (16 in 4 games) and the two other ball handlers, Nevels and Mascolo (11 each), account for 38 of Scafati's 61 turnovers. Synergy: TO% on P&R ball-handler possessions 22.5%, on isolations 21.7%.

## Defensive attitude

From Synergy's defensive play types (5 LBA games):

- Scafati allows 1.061 PPP overall (14th in the LBA) and the league's worst eFG% (60.7%), while forcing turnovers on 16.1% of possessions (4th).
- By play type, Scafati is weakest against transition (74 possessions faced, 17.5% of the total, 1.39 PPP allowed, 76.7% eFG), the P&R roll man (29 possessions, 1.35 PPP, 76.1% eFG) and isolations (14 possessions, 1.43 PPP). It is average or better against the P&R ball handler (81 possessions, 0.89 PPP, 8th) and cuts (1.09 PPP, 4th).
- Spot-ups are 24% of what Scafati defends, at 1.08 PPP allowed (14th): opponents are 26/68 from three on them.
- Opponents go to the line on only 11.1% of possessions against Scafati, the lowest share in the LBA, consistent with its 18.2 fouls a game (fewest in the league).

{{ pending }}

## What to expect

From the numbers only (5 LBA games each, so tendencies, not predictions):

- **Transition, both ways.** Scafati's best offense (1.22 PPP, Offurum 9/11 at the rim) meets the league's worst transition defense (BC Roma 1.42 PPP allowed); BC Roma's transition (73 possessions, 1.12 PPP) meets a defense that allows 1.39. Both teams' defenses are 15th-16th here.
- **The P&R ball handler.** 21% of Scafati's possessions at 0.67 PPP, with Mascolo (4/20 from the field) and Nevels (0.56 PPP) below 0.6; Moore (0.85, 5/10 on pull-up threes) is the exception. On the other side BC Roma's P&R ball handler scores 1.02 PPP (5th) against a Scafati defense that allows 0.89 (8th), its best defensive play type.
- **Roll man and cuts.** BC Roma's roll man (46 possessions, 1.17 PPP) and cuts (28, 1.68 PPP, best in the LBA) against a Scafati defense that allows 1.35 on roll men (15th) and 1.09 on cuts.
- **Turnovers.** Scafati forces turnovers on 17.8% of possessions (4th in the LBA) and BC Roma loses the ball on 16.8% (LBA) / 15.0% (Synergy); BC Roma forces only 14.2%. Scafati's own ball handlers turn it over at 22.5% on P&R possessions, Moore 4 a game.
- **Shot quality.** Scafati allows 60.7% eFG, BC Roma shoots 60.4% eFG (LBA) / 60.7% (Synergy): the matchup of the league's best offense by eFG% against its worst defense by the same metric.
- **Free throws.** Scafati shoots 61.3% from the line and draws them at a high rate (33.4 FTA/FGA; Mascolo 30 attempts, Offurum 19, Moore 16); it commits the fewest fouls in the league (18.2 a game), BC Roma 25.6.
- **Rotation.** 8-man rotation with a 17.6-point bench (BC Roma 37.0); Moore and Onyema over 34' in the last game.

### Metrics to check during/after the game

- Transition points for both teams and PPP on Scafati's transition possessions.
- BC Roma turnovers and the share of Scafati's points that follow them.
- Scafati's P&R ball-handler possessions by player (Moore vs Mascolo/Nevels) and their PPP.
- Scafati free-throw attempts and percentage.
- Bench points for Scafati.

## Clips suggested

Game clock from the Synergy shot list (time remaining in the period):

**Moore pull-up threes** (5/13 made).

**Offurum in transition** (9/11 at the rim).  

**Onyema as roll man** (6/9).

**Johnson's spot-up threes** (7/14).

**Mascolo's P&R possessions** (4/20): the short pull-ups and the rim attempts.

