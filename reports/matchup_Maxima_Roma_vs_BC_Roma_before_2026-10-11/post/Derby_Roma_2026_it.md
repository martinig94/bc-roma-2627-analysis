---
layout: post
title: Il derby della Capitale, in numeri
description: Maxima Roma – BC Roma, LBA 2026-27 — un'anteprima dati costruita sul play-by-play del campionato
image: assets/images/derby_2026/06_hot_spots.png
nav-menu: false
show_tile: false
---

*Pubblicato l'11 ottobre 2026, poche ore prima della palla a due. [English version](/about_me/Derby_Roma_2026.html). I numeri sono quelli della stagione fin qui: due partite di LBA per squadra più due di EuroCup ciascuna, quindi vanno letti come tendenze iniziali, non come certezze. Codice e dati: [lba-2627-data](https://github.com/martinig94/lba-2627-data).*

## Perché questa partita

Roma ha di nuovo due squadre in Serie A. BC Roma e Maxima Roma sono nate quest'estate rilevando e trasferendo due società esistenti (Vanoli Cremona e Germani Brescia), e stasera al PalaEur, con i primi due anelli esauriti, la città ritrova un derby di massima serie che mancava dal 1979-80. Entrambe giocano anche l'EuroCup, quindi ci sono già quattro partite a testa da leggere.

Kelly Olynyk, firmato da BC Roma il 3 ottobre, non è stato tesserato in tempo e salta la partita. Flowers, assente nelle due gare di EuroCup, è disponibile. Sul fronte Maxima non risultano assenze.

## I dati

Il sito di Legabasket pubblica per ogni partita un play-by-play in JSON: ogni tiro con coordinate e tipo di conclusione, ogni assist legato al suo canestro, ogni fallo, ogni cambio. Un piccolo collettore scarica le partite concluse ogni lunedì (GitHub Actions) e alcuni script ne ricavano con un comando i report di partita, squadra, confronto e giocatori. I dati EuroCup vengono dall'API live dell'EuroLeague; il riferimento al campionato sono sempre le altre quattordici squadre di LBA nelle stesse giornate.

Un limite va detto subito: l'analisi si basa esclusivamente su questi dati. Mostrano da dove arrivano i tiri, chi li prende, chi è in campo e chi serve chi; non mostrano come un possesso è stato costruito. In questa pagina non c'è quindi nessun commento su schemi difensivi, uso e coperture del pick and roll, giochi o spaziature, che possono venire solo dal video.

## Dove sono le due squadre

Maxima è 0–2 in campionato e 1–1 in EuroCup, e le sconfitte si somigliano: in partita o avanti all'intervallo, poi un quarto perso male (12–26 nel terzo contro Napoli, 21–33 nel quarto a Bologna, 12–32 nel quarto ad Ankara dopo essere stata avanti 65–60). In LBA subisce 96 punti a partita, con gli avversari al 40% da tre.

BC Roma è 1–1 e 1–1: una sconfitta a Treviso decisa da un terzo quarto da 22–27, un 108–70 su Tortona (prima vittoria del club in Serie A), una sconfitta a Istanbul e un 92–87 sul Lietkabelis. Segna 93 punti e ne subisce 89. Gli avversari tirano solo col 27% da tre contro di lei, ma vanno in lunetta 28,5 volte a partita, molto sopra la media del campionato (22).

![risultati](assets/images/derby_2026/01_results_timeline.png)

## Due attacchi opposti

È il contrasto più netto del confronto. BC Roma gioca dentro-fuori: 38 punti a partita entro 4,5 metri dal ferro (la media del campionato), 67% da due, 37/45 in area in LBA, 18/23 in penetrazione. Tira anche 30 triple a partita, il 47% delle sue conclusioni, concentrate sull'ala sinistra e in punta.

Maxima segna 25 punti dentro, 13 sotto la media, converte il 52% sotto canestro contro un 65% di campionato, e in due partite di LBA ha tentato 11 penetrazioni. A tenere in piedi l'attacco è la lunetta: 26 liberi a partita con l'82,5%, compreso un 30/30 contro Napoli. Le sue triple arrivano quasi tutte dalla punta, dove tira col 29%.

![fonti dei punti](assets/images/derby_2026/04_scoring_sources.png)

![zone calde](assets/images/derby_2026/06_hot_spots.png)

## Condiviso contro concentrato

Maxima ha la rotazione più profonda tra quelle analizzate: dodici giocatori utilizzati, nessuno sopra i 25 minuti, i primi sette in campo per il 74% dei minuti e il 45% dei punti dalla panchina, contro una media LBA del 32%. La leadership è condivisa quasi ovunque: tre marcatori nel giro di tre punti (Bilan 17% dei punti, Lemar 16%, Alibegovic 14%), due passatori (Holiday 29% degli assist, Moon 26%), Bilan e Brown che si dividono i rimbalzi offensivi.

BC Roma gioca con sette uomini per l'85% dei minuti e un quintetto base da 65 punti a partita. Con la palla in mano ha un solo regista: Mannion prende il 19% dei tiri della squadra e un terzo degli assist, e nove dei suoi diciassette assist vanno a Simonovic, che segna il 93% dei suoi canestri su passaggio e tira il 71% delle sue conclusioni sotto il ferro. Stevenson è lo sbocco per il tiro dal palleggio altrui (78% delle sue conclusioni da tre, il 72% da un solo lato del campo).

![quintetto e panchina](assets/images/derby_2026/02_starters_bench.png)

![chi regge ogni categoria](assets/images/derby_2026/10_major_factors.png)

![chi serve chi, BC Roma](assets/images/derby_2026/connections_bc_roma.png)

## Statistiche di base, stessa base dati

Solo sulle partite di LBA, le due squadre giocano allo stesso ritmo (76 e 75 possessi a partita). BC Roma segna molto più spesso su assist (33 assist ogni 100 possessi contro i 20 di Maxima e i 23 del campionato) e vince entrambi i tabelloni; Maxima è sotto la media in ogni voce di rimbalzi e passaggi, ha una stoppata in due partite ed è davanti solo nei falli subiti, 38 ogni 100 possessi contro i 29 del campionato.

![statistiche di base](assets/images/derby_2026/09_basic_stats.png)

## Cosa aspettarsi

Due duelli dovrebbero decidere la partita. Il primo: se Maxima riesce a tenere i penetratori di BC Roma fuori dall'area, dove BC Roma prende un terzo dei suoi tiri e segna con l'82% e dove gli avversari di Maxima stanno tirando 34/45. Il secondo: se BC Roma riesce a difendere senza fare falli, perché i suoi 28,5 liberi concessi a partita vanno dritti contro la miglior squadra del campionato in lunetta.

Le tendenze dicono che BC Roma controlla area e rimbalzi (12,8 rimbalzi offensivi a partita contro 9,5) e che Maxima resta in partita con i liberi e le triple della panchina. L'abitudine di Maxima a perdere un terzo o un quarto periodo, contro una BC Roma che un terzo quarto l'ha buttato via a sua volta, rende l'inizio del secondo tempo il momento da guardare. Una lettura ragionevole dei numeri è una vittoria di BC Roma di pochi punti in una partita intorno agli 85-90; l'atmosfera del derby e la profondità di Maxima sono i motivi principali per cui potrebbe andare diversamente, e senza Olynyk i falli di Simonovic sarebbero la singola variabile più pesante.

## Avvertenze

Quattro partite sono un campione sottile e alcuni numeri individuali sono già rumorosi (una serata da 1/1 compare come 125% di true shooting). Le coordinate dei tiri sono i clic del refertista: tutte le triple risultano tra 6,8 e 8,0 metri dal ferro e tutti i tiri da due sotto i 6,5, quindi la scala è corretta, ma le singole posizioni hanno forse mezzo metro di rumore, che va bene per le zone e non per le distanze esatte. I dati EuroCup contengono tabellini e zone di tiro ma non i tipi di tiro né i collegamenti degli assist, quindi i grafici sulle abitudini sono solo LBA e lo dichiarano.

*Una versione post-partita di questa pagina, con il confronto tra quello che è successo e le attese qui sopra, seguirà appena il play-by-play finale sarà raccolto.*
