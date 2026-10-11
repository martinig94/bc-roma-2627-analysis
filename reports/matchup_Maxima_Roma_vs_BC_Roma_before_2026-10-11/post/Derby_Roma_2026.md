---
layout: post
title: Derby della Capitale, by the numbers
description: Maxima Roma vs BC Roma, LBA 2026-27 — a data preview built on the league play-by-play
image: assets/images/derby_2026/06_hot_spots.png
nav-menu: false
show_tile: false
---

*Published 11 October 2026, a few hours before tip-off. [Versione italiana](/about_me/Derby_Roma_2026_it.html). Numbers are season to date: two LBA games per team plus two EuroCup games each, so read everything as early tendencies rather than established facts. Code and data: [lba-2627-data](https://github.com/martinig94/lba-2627-data).*

## Why this game

Rome has two Serie A teams again. BC Roma and Maxima Roma arrived this summer by taking over and relocating two existing franchises (Vanoli Cremona and Germani Brescia), and tonight at the PalaEur, with the first two rings sold out, the city gets its first top-flight derby since 1979-80. Both teams also play EuroCup, so four games each are already on record.

Kelly Olynyk, signed by BC Roma on 3 October, is not registered in time and misses the game. Flowers, who sat out both EuroCup games, is available. No absences are reported on the Maxima side.

## The data

Data from both competitions (LBA and EuroCup) is collected and processed programmatically; the league reference is always the other fourteen LBA teams in the same games. For details on the data and the method, feel free to contact me ([email](mailto:martini.giulia94@gmail.com) or [LinkedIn](https://www.linkedin.com/in/giulimartini/)).

One limit should be clear from the start: the analysis is based solely on this data. It shows where shots come from, who takes them, who is on the floor and who passes to whom; it does not show how a possession was built. Nothing in this page is a comment on defensive schemes, pick-and-roll usage or coverages, set plays or spacing, which can only come from the film.

## Where the two teams are

Maxima is 0–2 in the league and 1–1 in EuroCup, and the losses share a shape: level or ahead going into the second half, then one bad quarter (12–26 against Napoli in the third, 21–33 at Bologna in the fourth, 12–32 at Ankara in the fourth after leading 65–60). In the LBA it concedes 96 points a game, with opponents shooting 40% from three against it.

BC Roma is 1–1 and 1–1: a loss at Treviso decided by a 22–27 third quarter, a 108–70 win over Tortona (the club's first in Serie A), a loss in Istanbul and a 92–87 win over Lietkabelis. It scores 93 and concedes 89. Opponents shoot only 27% from three against it but get to the line 28.5 times a game, well above the league's 22.

![results](assets/images/derby_2026/01_results_timeline.png)

## Two opposite offences

This is the clearest contrast in the matchup. BC Roma plays inside out: 38 points per game within 4.5 m of the rim (league average), 67% on twos, 37/45 in the restricted area in the LBA, 18/23 on drives. It also takes 30 threes a game, 47% of its attempts, concentrated on the left wing and the top of the arc.

Maxima scores 25 inside, 13 below the league, converts 52% at the rim against a league 65%, and has attempted 11 drives in two LBA games. What keeps the offence afloat is the free-throw line: 26 attempts a game at 82.5%, including a 30/30 night against Napoli. Its threes come overwhelmingly from the top of the arc, where it shoots 29%.

![scoring sources](assets/images/derby_2026/04_scoring_sources.png)

![hot spots](assets/images/derby_2026/06_hot_spots.png)

## Shared versus concentrated

Maxima is the deepest rotation in the data: twelve players used, nobody above 25 minutes, the top seven playing 74% of the minutes, and 45% of the points from the bench against an LBA average of 32. Its leadership is shared in almost every category: three scorers within three points of each other (Bilan 17% of the points, Lemar 16%, Alibegovic 14%), two passers (Holiday 29% of the assists, Moon 26%), Bilan and Brown splitting the offensive glass.

BC Roma rides seven players for 85% of the minutes and a starting five that scores 65 a game. On the ball it has one hub: Mannion takes 19% of the team's shots and a third of its assists, and nine of his seventeen assists go to Simonovic, who finishes 93% of his baskets off a pass and shoots 71% of his attempts at the rim. Stevenson is the catch-and-shoot outlet (78% of his attempts from three, 72% of them from one side of the floor).

![starters and bench](assets/images/derby_2026/02_starters_bench.png)

![who carries each category](assets/images/derby_2026/10_major_factors.png)

![who feeds whom, BC Roma](assets/images/derby_2026/connections_bc_roma.png)

## Basic stats, same basis

On LBA games only, both teams play at the same pace (76 and 75 possessions a game). BC Roma assists on far more of its baskets (33 assists per 100 possessions against Maxima's 20 and a league 23) and wins both backboards; Maxima is below the league on every rebounding and passing number, has one block in two games, and leads only in fouls drawn, 38 per 100 possessions against a league 29.

![basic stats](assets/images/derby_2026/09_basic_stats.png)

## What to expect

Two matchups should decide it. First, whether Maxima can keep BC Roma's drivers out of the restricted area, where BC Roma takes a third of its shots and makes 82% and Maxima's opponents are shooting 34/45. Second, whether BC Roma can defend without fouling, because its 28.5 opponent free throws a game run straight into the league's best free-throw team.

The tendencies say BC Roma controls the paint and the glass (12.8 offensive rebounds a game to Maxima's 9.5) and Maxima stays in it through free throws and bench threes. Maxima's habit of losing a third or fourth quarter, against a BC Roma that has itself collapsed in a third quarter, makes the start of the second half the moment to watch. A reasonable baseline is a BC Roma win by a handful in a game in the high eighties; the derby atmosphere and Maxima's depth are the main reasons it could go the other way, and without Olynyk, foul trouble for Simonovic would be the single biggest swing.

## Caveats

Four games is a thin sample and some of the player numbers are already noisy (a 1/1 night shows up as 125% true shooting). Shot coordinates are the league scorer's clicks: all threes come out at 6.8–8.0 m from the rim and all twos under 6.5 m, so the scaling is right, but individual positions carry perhaps half a metre of noise, fine for zones, not for exact distances. The EuroCup data carries box scores and shot zones but not shot types or assist links, so the habit charts are LBA only and say so.

*A post-game version of this page, comparing what happened with the expectations above, will follow once the final play-by-play is collected.*
