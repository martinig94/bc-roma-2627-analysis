title: Bosna (EuroCup, 27 Oct)
reviewed: no
generated: 1bb9281f06

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
06_hot_spots, {{ shot_charts }} (06b: one chart per player), 07_key_players, 08_shot_distribution, 09_basic_stats, 10_major_factors, 11_starting_fives).
The three pages that go deeper (individual_tendencies.md, defense_tendencies.md, offense_tendencies.md, same folder) are linked at the end of this page when they exist.
THE STRUCTURE OF THIS PAGE IS THE STANDARD FOR EVERY ANALYSIS (same sections, same order); only the content changes.
-->

# BC Roma vs Bosna Bh Telecom Sarajevo

{{ header }}

<!-- Draft written on 23 Oct 2026 from the data only (EuroLeague API: 4 EuroCup games each; Synergy Sports: Bosna's 4 EuroCup games, BC Roma's 4 EuroCup games, 32 EuroCup teams as reference). No comments on plays or tactics. Small samples: tendencies, not predictions. -->

## Key points

- Bosna is 1-3 but every game was close: 72-75 at Lietkabelis, 72-75 vs PAOK, 93-102 at Ulm, 86-77 vs Bahcesehir (the group leader) last week. Point difference -6 in four games, BC Roma -23.
- Two scorers at 14.2 points a game: ==Perry== (64 possessions used in 4 games, 8.0 rebounds of which 3.5 offensive, 5 fouls drawn a game, 0.89 PPP) and ==Pipes== (48 possessions, 1.19 PPP, 19/20 from the line, 3 turnovers in 94 minutes). Gholston adds 10.0 (1.00 PPP, 5/6 at the rim in transition), Domask 8.8 in 16 minutes off the bench (1.13 PPP, eFG% 61).
- Turnovers on both sides: Bosna loses the ball on 20.1% of its possessions, second-highest of the 32 EuroCup teams (17 a game; Browne 11 in 46 minutes), BC Roma 19.0% (third-highest). Neither forces many: 14.5% and 15.5% forced.
- Bosna shoots inside: 115 of 235 field-goal attempts in the paint (49%) at 62%, only 21 threes a game at 29.4%. Its threes come from the corners (11/21) much more than from the top (3/21, 14%) or the wings (12/43).
- Bench: 36 points a game (44%), BC Roma 27 (32%). Bosna's bench scored 43 at Ulm and 34 vs Bahcesehir.
- What Bosna's defense gives up: spot-ups (79 possessions, the most, 1.06 PPP, opponents 20/51 from three on them) and transition (51 possessions at 1.22 PPP, 23/27 on twos). What it takes away: the P&R ball handler (0.80 PPP allowed on 69 possessions) and isolations (0.73).

## EuroCup so far: results and standings

{{ standings }}

### Results timeline

{{ figure: 01_results_timeline }}

## BC Roma and Bosna compared

{{ comparison }}

### The two teams at a glance

{{ figure: 09_basic_stats }}

![Team z-scores vs the 32 EuroCup teams, EuroCup games only (Synergy)](01b_team_radar_zscore_competition_only.png)

- In the EuroCup both offenses are around the league mean (0.93 and 0.94 PPP against 0.95), both with a turnover problem: Bosna 20.1% (z -2.0, only Cluj is worse), BC Roma 19.0% (z -1.5). Bosna shoots the better percentages (FG% 48.1 vs 45.6, eFG% 53.6 vs 52.0), BC Roma takes 6 more threes a game (27 vs 21) at the same 29.4%.
- Bosna's defense is around the mean (0.95 PPP allowed): better than the league on opponents' eFG% (51.0 against 52.5) and free throws conceded, worse on turnovers forced (14.5%); BC Roma's is below on eFG% allowed (54.1) and above only on free throws conceded (10.4% of opponents' possessions, among the lowest in the competition).
- Over all games played (EuroCup plus ABA for Bosna, EuroCup plus LBA for BC Roma; 01_team_radar_zscore_all_games.png) the two offenses are identical, 1.01 PPP; Bosna's defense allows 0.96, BC Roma's 1.01.
- Same slow pace: 75.6 possessions per 40' for Bosna, 78.7 for BC Roma (EuroLeague API).

## Bosna roster

{{ roster }}

- 12 players used. Popovic (211 cm, 8.0 points and 5.0 rebounds in 18' when he played) started the first two games and missed the last two; Banks (208 cm) appeared only in the last game (16', 6 points, 3/3); Islamovic (208) 15' at Ulm and 0' vs Bahcesehir. Which of the three bigs is available behind Perry is the thing to check before the game.

## Starting five and bench

- Three fixed starters in all four games: Talic, Gholston, Hawkins. Pipes started the first three and came off the bench vs Bahcesehir (23', 20 points); Perry started the last two games (Popovic the first two); Atic started vs Bahcesehir.
- Minutes are spread: nine players between 11' and 25' a game (Talic 25.0, Perry 23.9, Pipes 23.5, Gholston 22.7, Vrabac 21.7, Atic 21.3, Hawkins 17.5, Domask 16.0, Browne 11.6). Nobody has played 30' in a game except Talic (30') vs Bahcesehir.
- Bench scoring 36 a game (44% of the total, league 35), starters 45 (league 48). The bench scored 43 at Ulm (Domask 26', Vrabac 26') and 34 vs Bahcesehir (Pipes 20).
- First substitution in Q1 (game clock): 2:59 at Lietkabelis (three at once: Domask, Perry, Atic for Pipes, Popovic, Gholston), 4:49 vs PAOK (Atic and Vrabac for Gholston and Hawkins), 5:42 at Ulm (Browne for Talic, then Domask and Atic at 3:16), 5:31 vs Bahcesehir (Pipes for Gholston, then Banks at 3:37 and Domask at 1:53). Atic and Domask are among the first substitutes in three games out of four.
- Fouls: 20 committed a game (80 in 4); Perry 11, Vrabac 13 (3.2 a game in 22'), Talic 10.

{{ figure: 11_starting_fives }}

{{ figure: 02_starters_bench }}

{{ figure: 03_minutes }}

## Scoring sources, tendencies and shooting maps

- Points come from inside: 87 two-point makes against 26 threes; 17/20 at the rim and 64/121 in the rest of the paint (EuroLeague zones). Perry alone takes 28 of his 44 shots in the paint (15 made).
- From three Bosna takes 21 a game and makes 29.4%: corners 11/21 (Pipes 3/4, Domask 2/4, Browne 2/2, Hawkins 2/2), wings 12/43 (Hawkins 1/8, Talic 0/6, Pipes 2/10), top of the arc 3/21 (Gholston 0/5).
- Second chances: 10.2 offensive rebounds a game, OREB% 32.3 (BC Roma 34.5; DREB% 68.9 vs 63.6). Put-backs produce 1.12 PPP on 26 possessions, 10 of them Perry's (11 points).
- Free throws: FT rate 38.1 (BC Roma 36.4) at 80%; Perry 19 attempts, Pipes 20 (19 made), Talic 12 (11), Gholston 12 (10).

{{ figure: 04_scoring_sources }}

{{ figure: 05_shooting }}

{{ figure: 06_hot_spots }}

### Shot charts by player

{{ shot_charts }}

![Bosna play types run and faced (Synergy, EuroCup)](02_opponent_playtypes.png)
![Offensive PPP by play type, BC Roma vs Bosna (Synergy, EuroCup)](03_playtype_ppp_ref_vs_opp.png)

- Bosna's offense (344 possessions in 4 EuroCup games): P&R ball handler 76 possessions (22%, 0.90 PPP), spot-up 69 (20%, 1.00 PPP, 48 of the 61 shots are threes), transition 49 (14%, 0.98 PPP but 20% turnovers), P&R roll man 29 (1.00), put-backs 26 (1.12), cuts 23 (1.13), post-ups 19 (0.47 PPP, 4/12 FG, 6 turnovers), isolations 14 (1.14). 28 possessions (8%) are "miscellaneous" and end in a turnover 64% of the time.
- Compared to BC Roma's EuroCup offense: BC Roma is far better on the P&R ball handler (1.11 vs 0.90 PPP), transition (1.21 vs 0.98) and cuts (1.16 vs 1.13), far worse on spot-ups (0.74 PPP on 85 possessions, 13/45 from three, against Bosna's 1.00). Put-backs and roll man are similar (1.04 vs 1.12, 1.00 vs 1.00).
- P&R ball handler shots (45 in 4 games): 24 to the basket (12 made), 9 pull-up threes (4 made: Pipes, Gholston, Talic and Atic one each), 6 mid-range pull-ups (4 made), 4 short pull-ups (0 made).
- Bosna's defense faces mostly spot-ups (79 possessions, 1.06 PPP allowed, 20/51 from three) and P&R ball handlers (69, 0.80 allowed, 6/24 from three); opponents' transition yields 1.22 PPP (23/27 on twos) and the roll man 1.33 (24 shots, 14 made, 3/7 from three).

![Bosna players: possessions used by play type (Synergy, EuroCup)](06_players_playtype_mix.png)

- The P&R ball handler possessions are shared: Talic 16, Pipes 15, Gholston 15, Atic 12, Browne 12 (0.58 PPP), Domask 5. Pipes is the most productive of them (19 points on 15 possessions, 1.27 PPP), Gholston 0.73, Browne 0.58.
- Perry is the roll man (16 of the 29 roll-man possessions, 0.94 PPP; 9 shots to the basket, 6 made, and 4 pick-and-pop threes, 0 made) and the put-back man (10 of 26); Popovic had 7 roll-man possessions in two games.
- Transition is Pipes (12 possessions) and Gholston (9, 13 points, 1.44 PPP); Perry runs too (9 possessions, 7 points).
- Spot-ups: Domask 10 possessions, 14 points (1.40 PPP), Gholston 10 (0.80), Hawkins 9 (1.00, 3/9 from three), Pipes 8, Talic 7, Perry 7 (1.29), Browne 6 (1.50), Atic 5 (0 points, 0/5).

## Key players

### Shooting

{{ figure: 07_key_players }}
![Bosna players, possessions used vs eFG% (Synergy, EuroCup)](04_players_volume_efficiency.png)

Bosna has:
- ==Perry== (centre): 16 possessions and 14.2 points a game, eFG% 48.9, 54% on twos and 1/7 from three; 8.0 rebounds (3.5 offensive), 5 fouls drawn a game, 10 turnovers (2.5 a game, 15.6% of his possessions). 28 of his 44 shots are in the paint (15 made), 9 mid-range (5 made). In the two games he started he played 25' and 23'.
- ==Pipes== (guard): 12 possessions and 14.2 points a game at 1.19 PPP, eFG% 51.4, TS% 62.2, 19/20 free throws, 3 turnovers in 94 minutes (6.3%), 9 assists. 18 threes (6 made): 12 catch-and-shoot (4 made), 6 off the dribble (2 made); 19 of his 37 shots are twos (10 made), 8/14 in the paint. 20 points off the bench vs Bahcesehir (23').
- ==Gholston== (guard): 10 possessions and 10.0 points a game, eFG% 53.6, 4/11 from three (4/5 from the wings, 0/5 from the top); 8 turnovers, 0.25 assist-to-turnover. 6/8 in transition, 5/6 of them at the rim.
- ==Domask== (wing, bench): 8 possessions and 8.8 points in 16 minutes, 1.13 PPP, eFG% 61.4, 3/7 from three, 8/11 in the paint; 7 assists against 5 turnovers.
- ==Talic== (point guard): 8 possessions a game, 0.88 PPP, 2/9 from three, 6/7 in the paint; 13 assists and 8 turnovers, 11/12 free throws, 25 minutes a game (the most).
- ==Atic== (guard, bench, 21'): 8 possessions a game, 0.73 PPP, 2/11 from three and 0/5 on spot-ups, but 7/10 in the paint; 14 assists (the most on the team), 4.5 rebounds, 1.5 offensive.
- Hawkins (starter, 17'): 5 possessions a game, 3/10 from three (1/8 from the wings), 4.0 rebounds. Browne (bench, 12'): 6 possessions a game, 4/5 from three, but 11 turnovers in 46 minutes (44% of his possessions). Vrabac (bench, 22'): 4.5 possessions a game, 1/5 from three, 3.2 fouls a game.

{{ figure: 08_shot_distribution }}

![Perry shot profile](05_player_perry_shot_profile.png)
![Perry shot types by play type](05c_player_perry_shot_types.png)
![Pipes shot profile](05_player_pipes_shot_profile.png)
![Pipes shot types by play type](05c_player_pipes_shot_types.png)
![Gholston shot profile](05_player_gholston_shot_profile.png)
![Domask shot profile](05_player_domask_shot_profile.png)
![Talic shot profile](05_player_talic_shot_profile.png)
![Atic shot profile](05_player_atic_shot_profile.png)
![Hawkins shot profile](05_player_hawkins_shot_profile.png)
![Browne shot profile](05_player_browne_shot_profile.png)
![Vrabac shot profile](05_player_vrabac_shot_profile.png)
![Popovic shot profile](05_player_popovic_shot_profile.png)

### Other stats

{{ figure: 10_major_factors }}

## Ball movement

### Assists

- 15.8 assists a game; the main pairs are Atic to Perry (5), Atic to Domask (3), Domask to Perry (3), Talic to Perry (3), Pipes to Popovic (3). Perry is the finisher of 11 of the top-pair assists.

{{ assists }}

### Turnovers

- 69 turnovers in 4 games (17.2 a game, 20.1% of possessions): Browne 11 (5 at Lietkabelis), Perry 10 (4 at Ulm), Talic 8, Gholston 8, Atic 8. Pipes 3.
- BC Roma forced 15.5% turnovers in the EuroCup (league 15.7%). Bosna turned 6 of its 22 steals into points within 12 seconds.

{{ turnovers }}

## Lineups

![Bosna lineups, usage vs PPP (Synergy, EuroCup)](07_lineups_usage_vs_ppp.png)

In the four EuroCup games Bosna used 44 different five-man lineups on offense; 24 had at least 5 possessions.

- The most-used lineup, Talic, Pipes, Gholston, Hawkins, Popovic (51 offensive and 45 defensive possessions, 0.98 scored, 0.96 allowed), is the starting five of the first two games and ==cannot be used while Popovic is out==.
- The current starting five, Talic, Gholston, Atic, Hawkins, Perry (18 off. / 19 def. possessions, 1.00 scored, 0.74 allowed), has the best defensive numbers among lineups with 15+ possessions on both sides.
- The second unit, Vrabac, Atic, Domask, Browne, Perry (24 / 22 possessions): 0.75 scored, 1.14 allowed, 29% turnovers. With Pipes instead of Browne (21 / 20 possessions) it scored 1.19 and allowed 0.75.
- Vrabac, Gholston, Talic, Banks, Pipes (13 / 15 possessions, only vs Bahcesehir): 1.54 scored, 0.73 allowed, 4/6 from three.

![Bosna lineups, scoring vs allowing (Synergy, EuroCup)](08_lineups_offense_vs_defense.png)
![Bosna lineups, style profile (Synergy, EuroCup)](09_lineups_style_profile.png)

- Lineups with Browne lose the ball most (29% with Vrabac/Atic/Domask/Perry, 29% with Vrabac/Atic/Perry/Pipes); the current starters 6%.
- Three-point rate is highest with Hawkins, Gholston, Talic, Perry, Pipes (0.71, 1/5 made) and lowest with the two Vrabac/Atic/Perry units (0.14 and 0.33).

{{ lineups }}

## What to expect

From the numbers only (4 EuroCup games each, so tendencies, not predictions):

- **Turnovers.** The largest gap between the two teams is in what they give away, not in what they force: Bosna 17 turnovers a game (20.1%), BC Roma 19.0%, against defenses that force below the league average (14.5% and 15.5%). Browne (11 in 46'), Perry (10) and the three ball handlers Talic, Gholston, Atic (8 each) lose most of them.
- **Perry inside, Pipes outside.** Perry ends 16 possessions a game, 28 of 44 shots in the paint, 3.5 offensive rebounds and 5 fouls drawn a game; BC Roma's DREB% in the EuroCup is 63.6 (Bosna's 68.9) and it concedes the fewest free throws in the competition (10.4% of possessions). Pipes ends 12 possessions a game at 1.19 PPP with almost no turnovers and 95% from the line; 12 of his 18 threes are catch-and-shoot.
- **Spot-ups.** The play type Bosna's defense faces most (79 possessions) and defends worst (1.06 PPP, 20/51 from three) is the one BC Roma has run worst in the EuroCup: 85 possessions at 0.74 PPP, 13/45 from three. BC Roma's best play types, P&R ball handler (1.11) and transition (1.21), meet a Bosna defense that allows 0.80 on the ball handler and 1.22 in transition.
- **Three-point volume and location.** Bosna takes 21 threes a game at 29.4% and makes them from the corners (11/21); from the top of the arc 3/21 and from the wings 12/43 (Hawkins 1/8). BC Roma takes 27 at the same 29.4%.
- **Pace and the bench.** Both teams are slow (75.6 and 78.7 possessions per 40'). Bosna's bench scores 36 a game (44%), BC Roma's 27: Domask (8.8 in 16', 1.13 PPP) and Atic (14 assists) are the first two in.
- **Rotation.** Popovic out for the last two games; Banks played his first game vs Bahcesehir; nobody plays 30'.

Not covered here: BC Roma's defense by play type (the Synergy pull has Bosna's defense but only BC Roma's offense), so the matchup between Bosna's P&R and BC Roma's defense is read from the EuroLeague numbers only.

### Metrics to check during/after the game
- Bosna turnovers (17 a game so far) and BC Roma's own (19.0%)
- Perry: offensive rebounds and free-throw attempts (3.5 and 4.8 a game)
- Pipes: possessions and threes, catch-and-shoot vs off the dribble
- Bench points for Bosna (36 a game)
- BC Roma spot-up threes (13/45 in the EuroCup so far)

## Clips suggested

Clips to look up (game clock from the Synergy shot list, checked against the EuroLeague play-by-play on the Bahcesehir game):

**Pipes** — the P&R finishes: vs PAOK Q1 7:33 to the basket and Q1 8:26 mid-range pull-up; vs Bahcesehir Q2 8:42 mid-range pull-up, Q4 9:01 pull-up three, Q4 5:10 to the basket (and-one). Transition: at Ulm Q1 4:33 and Q4 6:56; vs Bahcesehir Q4 0:03. Catch-and-shoot threes: at Ulm Q1 8:56 (wing, made) and Q4 4:52 (corner, made); at Lietkabelis Q1 4:48 off a flare screen and Q3 2:49 off screen (both made).

**Perry** — the roll to the basket: vs Bahcesehir Q1 5:17 and Q1 3:56 (both from Talic/Atic drives); at Ulm Q2 4:30, Q4 4:32 and Q4 3:57. The put-backs: vs PAOK Q2 4:03 and Q3 3:12 (made), Q3 0:01 and Q3 1:49 (missed). The post-ups to check for the 0.47 PPP: at Lietkabelis Q2 9:44, Q3 0:31 and Q3 2:16; vs PAOK Q3 3:12 drop step. Turnovers: at Ulm Q1 9:31, Q1 7:00, Q3 8:15, Q4 1:48; vs PAOK Q1 0:14, Q2 9:41, Q4 7:01.

**Gholston** — transition to the basket: vs Bahcesehir Q1 7:02 and Q3 1:57; at Ulm Q3 3:34 and Q3 8:54 (and-one); vs PAOK Q3 7:04 (leak out). Pull-up threes: vs Bahcesehir Q3 4:07 (made) and Q3 3:18 (missed); at Lietkabelis Q4 0:55 (made, isolation).

**Domask** — spot-up threes at Ulm: Q2 5:43 (open, wing), Q2 6:11 (guarded, corner), Q4 7:57 (open, corner), all made; Q3 2:14 guarded corner missed. Drives: at Ulm Q4 9:39 drive and-one, Q4 3:22 to the basket, Q2 5:04 isolation; vs Bahcesehir Q4 1:27 pull-up.

**Browne turnovers** (11 in 46'): at Lietkabelis Q2 8:40, 8:30, 7:39 (three in one minute), Q3 4:15, 3:42; vs PAOK Q2 5:34, Q3 1:05, Q4 8:47; at Ulm Q1 3:31, Q3 6:16; vs Bahcesehir Q2 9:22.

**Lineup stretch**: Talic, Gholston, Atic, Hawkins, Perry vs Bahcesehir (the current starting five: 1.00 scored, 0.74 allowed in 18/19 possessions), from the tip to the first substitution at Q1 5:31.

## Other suggested checks
- Which big backs up Perry (Popovic's availability; Banks after one game).
- Pipes' shooting hand and preferred direction off the pick (9 of 15 P&R possessions end in a shot, 5 to the basket).
- Shot takers after time-outs and out-of-bounds plays (28 "miscellaneous" possessions with 64% turnovers).
