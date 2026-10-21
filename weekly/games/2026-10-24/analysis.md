title: 
reviewed: no
generated: deb1cf3795

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
06_hot_spots, 07_key_players, 08_shot_distribution, 09_basic_stats, 10_major_factors, 11_starting_fives).
THE STRUCTURE OF THIS PAGE IS THE STANDARD FOR EVERY ANALYSIS (same sections, same order); only the content changes.
-->

# Openjobmetis Varese vs BC Roma

{{ header }}

## Key points

{{ pending }}

## LBA so far: results and standings

{{ standings }}


### Results timeline

{{ figure: 01_results_timeline }}

## BC Roma and Varese compared

{{ comparison }}
### The two teams at a glance
{{ figure: 09_basic_stats }}

![Team z-scores vs the 16 LBA teams, all LBA games played (Synergy)](01b_team_radar_zscore_competition_only.png)

- BC Roma has a more productive and efficient offense than Varese, except for the number of possessions ending with free throws.
- Varese has a more effective defense than BC Roma. When facing them, opposing teams have a higher turnover rate. ➡️ ⚠ check Varese's steals

## Varese roster

{{ roster }}

**Out: Della Valle is expected to miss the next game**

## Starting five and bench

{{ pending }}

{{ figure: 02_starters_bench }}

{{ figure: 03_minutes }}

{{ figure: 11_starting_fives }}
## Scoring sources, tendencies and shooting maps

<!-- Scoring sources, shooting and hot spots. -->

{{ figure: 04_scoring_sources }}

{{ figure: 05_shooting }}

![Varese play types](02_opponent_playtypes.png)
![Varese play types and PPP ](03_playtype_ppp_ref_vs_opp.png)

- Compared to BC Roma: Varese plays more P&R where the ball handler ends the action (shot, FD or lost ball) with 0.86 PPP compared to 1.10 of Bc Roma
- The second more common conclusion for Varese is spot up (PPP 0.7)
- Varese is efficient on offensive rebounds (PPP 1.35 compared to 1.00 for BC Roma) ➡️ ⚠️ check main offensive rebounders
![Varese play types per players ](06_players_playtype_mix.png)
- Isolation situations are mainly played by Hale who is the player with the highest number of possessions of the team
- Put backs are mainly distributed among Kamagate, Renfro, Duke. Alvit, Nikolic, Libbrizi and Roby have a lower share. 

{{ figure: 06_hot_spots }}

## Key players

### Shooting
<!-- Key players and shot distribution. -->

{{ figure: 07_key_players }}
![Players volume efficiency](04_players_volume_efficiency.png)
Varese has:
- Hale with 22.25 possessions per game, 20.8 points per game below 50% eFG%
- Duke with 14.25 possessions per game, 11.2 points per game with around 40 eFG%
- Nikolic, Renfro, Kamagate an Alviti with similar statistics (PPG between 6.8 and 9.8, around 7 possessions per game, high eFG%)

{{ figure: 08_shot_distribution }}

![Hale radar plot](05_player_hale_shot_profile.png)
![Duke radar plot](05_player_duke_shot_profile.png)
![Renfro radar plot](05_player_renfro_shot_profile.png)
![Alviti radar plot](05_player_alviti_shot_profile.png)
![Libbrizi radar plot](05_player_librizzi_shot_profile.png)
![Roby radar plot](05_player_roby_shot_profile.png)
![Kamagate radar plot](05_player_kamagate_shot_profile.png)
### Other stats


{{ figure: 10_major_factors }}


## Ball movement
### Assists

<!-- Assists: ball movement and the main passer-scorer pairs. -->

{{ assists }}

### Turnovers

<!-- Turnovers: who loses the ball and when. -->

{{ turnovers }}

## Lineups

![lineups1](07_lineups_usage_vs_ppp.png)

In the first 4 LBA games, Varese used 22 different lineups with at least 5 offensive possessions, excluding the ones with Della Valle.

The most-used lineup is:
- Hale, Duke, Alviti, Nikolic, Kamagate (1). With 0.7 points per possession scored and 0.64 allowed, it was used more than twice as much as any other lineup.

The most productive lineup is:
- Alviti, Librizzi, Duke, Nikolic, Kamagate — used for only 5 possessions. This lineup is also the least effective in 
defense (1.60 Points allowed per possession)➡️ ⚠ Check if they play significant minutes

![lineups2](08_lineups_offense_vs_defense.png)
Other lineups to be investigated are:
- Alviti, Hale, Villa, Nikolic, Renfro (1.38 scored, 1.18 allowed)
- Alviti, Duke, Hale, Nikolic, Renfro (1.00 scored, 1.24 allowed)
- Alviti, Nikolic, Renfro, Hale, Librizzi (4) (0.47 scored, 0.57 allowed) - best defensive lineup with considerable number of possessions
➡️⚠️ Check clips and investigate play types and shot selections.
![lineups2](09_lineups_style_profile.png)
Playing tendencies differ greatly between lineups:
- 62% FGA of lineup 4 are 3FGA, while is 37% for lineup 1.
- Alviti, Duke, Ale, Renfro, Roby have the highest eFG% and second TO% (0.33)  
- Duke, Kamagate, Librizzi, Ikangi, Roby have the highest TO% (0.36)

{{ lineups }}

## What to expect

{{ pending }}

## Highlights

{{ pending }}
