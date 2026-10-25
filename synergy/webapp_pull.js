// Synergy web app pull for one scouting folder (data/synergy/<opponent>_<date>/).
// Run in the browser console (or Claude's browser pane) on any page of https://apps.synergysports.com/basketball
// while logged in: the app keeps its bearer token in localStorage and the calls below are the ones the app itself makes.
// Edit the CONFIG block, paste the whole file, then read `window.__out` (one CSV string per file) and save each one.
// Ids (2026-27): season 69bba845d0611197290c7acc; league "International" 54457dce300969b132fcfb3f;
// competitions: EuroCup ...:COMP:560100ac8dc7a24394b95656, Italian Serie A ...:COMP:560106aa8dc7a233b47b74bb.
// Team ids: GET https://basketball.synergysportstech.com/api/leagues/<league>/teamswithstats?seasonId=<season> (BC Roma 54457df1300969b132fd0e16, Bosna 54457df0300969b132fd0d8d).
// Play ids: 400 Spot Up, 136 P&R Ball Handler, 418 Transition, 235 P&R Roll Man, 3 Cut, 415 Put Backs, 50 Isolation, 259 Post-Up,
// 11 Handoffs, 85 Off Screen, 452 Miscellaneous, 1 = all, 453 = half court. Shot filters: shot eq 428 jump shot, distance eq 1/2/3, result in [3..8] = FGA.
// The cumulative box (per-player table with AST, REB, STL...) is read from the "Cumulative Box" tab of the team page (table -> CSV), not from here.
const CONFIG = {
  S: '69bba845d0611197290c7acc',
  C: '54457dce300969b132fcfb3f:COMP:560100ac8dc7a24394b95656',   // competition of the pull
  OPP: '54457df0300969b132fd0d8d', REF: '54457df1300969b132fd0e16', // opponent, reference team
  OPP_NAME: 'Bosna', REF_NAME: 'BC Roma',
};
(async () => {
const {S, C, OPP, REF, OPP_NAME, REF_NAME} = CONFIG;
const tok = () => JSON.parse(localStorage.getItem('oidc.user:https://auth.synergysportstech.com:client.basketball.teamsite')).access_token;
const post = async (u, b) => (await fetch(u, {method: 'POST', headers: {Authorization: 'Bearer ' + tok(), 'Content-Type': 'application/json'}, body: JSON.stringify(b)})).json();
const q = async (expr) => { const r = await post('https://basketball.synergysportstech.com/api/possessionreports', {expressions: [expr], includePartiallyLoggedGames: false, includePlayByPlayStats: false}); return Array.isArray(r) ? r : (r.result || []); };
const PT = [['Spot Up','play eq 400'],['P&R Ball Handler','play eq 1 and play eq 136'],['Transition','play eq 418'],['P&R Roll Man','play eq 235'],['Cut','play eq 3'],['Offensive Rebounds (Put Backs)','play eq 415'],['Isolation','play eq 50'],['Post-Up','play eq 1 and play eq 259'],['Handoffs','play eq 11'],['Off Screen','play eq 85'],['Miscellaneous Plays','play eq 1 and play eq 452']];
const f1 = x => Math.round(x * 10) / 10, f2 = x => Math.round(x * 100) / 100, f3 = x => Math.round(x * 1000) / 1000;
const csv = (cols, rows) => [cols.join(','), ...rows.map(r => cols.map(c => { let v = r[c]; v = (v === undefined || v === null) ? '' : String(v); return /[,"]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }).join(','))].join('\n');
const agg = rows => { const s = {}; for (const x of rows) for (const [k, v] of Object.entries(x)) if (typeof v === 'number') s[k] = (s[k] || 0) + v; return s; };
const met = s => { const poss = s.possessions || 0, fga = s.shotAttempt || 0, fgm = s.shotMade || 0, m3 = s.shot3Made || 0, fta = s.ftAttempt || 0, pts = s.pointMade || 0; const tsa = fga + 0.44 * fta; return {poss, pts, ppp: poss ? f3(pts / poss) : '', fga, fgm, fg_miss: fga - fgm, fg_pct: fga ? f1(100 * fgm / fga) : '', efg_pct: fga ? f1(100 * (fgm + 0.5 * m3) / fga) : '', ssq: s.shotQualityAttempt ? f2(s.shotQualityTotal / s.shotQualityAttempt) : '', pps: fga ? f2((2 * (fgm - m3) + 3 * m3) / fga) : '', ssm: (fga && s.shotQualityAttempt) ? f2((2 * (fgm - m3) + 3 * m3) / fga - s.shotQualityTotal / s.shotQualityAttempt) : '', ts_pct: tsa ? f1(100 * pts / (2 * tsa)) : '', tsa: f1(tsa), to_pct: poss ? f1(100 * (s.turnover || 0) / poss) : '', ft_pct: poss ? f1(100 * (s.ftTimes || 0) / poss) : '', fta_per_fga: fga ? f2(fta / fga) : '', sf_pct: poss ? f1(100 * (s.shotFoul || 0) / poss) : '', score_pct: poss ? f1(100 * (s.score || 0) / poss) : '', fg2a: s.shot2Attempt || 0, fg2m: s.shot2Made || 0, fg2_miss: (s.shot2Attempt || 0) - (s.shot2Made || 0), fg2_pct: s.shot2Attempt ? f1(100 * s.shot2Made / s.shot2Attempt) : '', fg3a: s.shot3Attempt || 0, fg3m: m3, fg3_miss: (s.shot3Attempt || 0) - m3, fg3_pct: s.shot3Attempt ? f1(100 * m3 / s.shot3Attempt) : '', fg3a_per_fga: fga ? f2((s.shot3Attempt || 0) / fga) : ''}; };
const out = {};
// league tables (competition only)
const lt = rows => rows.map(x => { const m = met(x); return {team: x.team.abbr, name: x.team.name, gp: x.gp, poss_pg: f1(x.possessions / x.gp), pts_pg: f1(x.pointMade / x.gp), ppp: m.ppp, fg: m.fg_pct, efg: m.efg_pct, to: m.to_pct, ft: m.ft_pct, score: m.score_pct}; });
const lcols = ['team','gp','poss_pg','pts_pg','ppp','fg','efg','to','ft','score','name'];
out.league_team_offense = csv(lcols, lt(await q(`season eq oid(${S}) and competitiondefinitionkey eq compkey(${C}) and (play eq 1) group offensiveteam`)));
out.league_team_defense = csv(lcols, lt(await q(`season eq oid(${S}) and competitiondefinitionkey eq compkey(${C}) and (play eq 1) group defensiveteam`)));
// context: all non-exhibition games
const ctx = [];
for (const [name, id] of [[OPP_NAME, OPP], [REF_NAME, REF]]) for (const side of ['offense', 'defense']) {
  const rows = (await q(`season eq oid(${S}) and ${side === 'offense' ? 'offensiveteam' : 'defensiveteam'} eq oid(${id}) and (play eq 1) group game`)).filter(x => !/^Exhibitions/.test(x.game.competition.name));
  const s = agg(rows), m = met(s), gp = rows.length;
  for (const [k, v] of [['PPP', m.ppp], ['Possessions/game', f1(s.possessions / gp)], ['eFG%', m.efg_pct], ['TO%', m.to_pct], ['%FT', m.ft_pct], ['Score%', m.score_pct], ['FG%', m.fg_pct]]) ctx.push({team: name, side, metric: k, value: v, gp});
}
out.context_all_games = csv(['team','side','metric','value','gp'], ctx);
// play types
const ptcols = ['play_type','poss','pct_time','pts','ppp','ppp_rating','fga','fgm','fg_miss','fg_pct','efg_pct','ssq','pps','ssm','ts_pct','tsa','to_pct','ft_pct','fta_per_fga','sf_pct','score_pct','fg2a','fg2m','fg2_miss','fg2_pct','fg3a','fg3m','fg3_miss','fg3_pct','fg3a_per_fga'];
const ptable = async (field, id) => { const all = agg(await q(`season eq oid(${S}) and competitiondefinitionkey eq compkey(${C}) and ${field} eq oid(${id}) and (play eq 1) group game`)); const rows = []; for (const [name, ex] of PT) { const s = agg(await q(`season eq oid(${S}) and competitiondefinitionkey eq compkey(${C}) and ${field} eq oid(${id}) and (${ex}) group game`)); rows.push({play_type: name, pct_time: f1(100 * (s.possessions || 0) / all.possessions), ppp_rating: '', ...met(s)}); } return rows.sort((a, b) => b.poss - a.poss); };
out.opp_playtypes_offense = csv(ptcols, await ptable('offensiveteam', OPP));
out.opp_playtypes_defense = csv(ptcols, await ptable('defensiveteam', OPP));
out.ref_playtypes_offense = csv(ptcols, await ptable('offensiveteam', REF));
// players by play type
const pp = [];
for (const [name, ex] of PT) for (const x of await q(`season eq oid(${S}) and competitiondefinitionkey eq compkey(${C}) and offensiveteam eq oid(${OPP}) and (${ex}) group offensiveplayer`))
  pp.push({player: x.player.name.split(' ').slice(-1)[0], full: x.player.name, play_type: name, poss: x.possessions || 0, pts: x.pointMade || 0, ppp: x.possessions ? f3((x.pointMade || 0) / x.possessions) : '', fga: x.shotAttempt || 0, fgm: x.shotMade || 0});
out.opp_players_playtypes_offense = csv(['player','play_type','poss','pts','ppp','full'], pp.sort((a, b) => a.player.localeCompare(b.player) || b.poss - a.poss));
// shots (every FGA with the Synergy description chain)
const sh = (await post('https://basketball.synergysportstech.com/api/court/2/shots', {defense: false, zonesBreakdown: 1, seasonId: S, competitionDefinitionKey: C, teamId: OPP, skip: 0, take: 1000, zoneNames: []})).result;
const ZONE = z => z === 'Z11-01-2pt' ? 'Paint' : z.endsWith('2pt') ? 'Mid-range' : (z === 'Z11-12-3pt' || z === 'Z11-16-3pt') ? 'Corner 3' : (z === 'Z11-13-3pt' || z === 'Z11-15-3pt') ? 'Wing 3' : 'Top 3';
const PTMAP = {'Spot-Up': 'Spot Up', 'P&R Ball Handler': 'P&R Ball Handler', 'Transition': 'Transition', 'P&R Roll Man': 'P&R Roll Man', 'Cut': 'Cut', 'Offensive Rebound': 'Offensive Rebounds (Put Backs)', 'ISO': 'Isolation', 'Off Screen': 'Off Screen', 'Post-Up': 'Other', 'Hand Off': 'Other', 'No Play Type': 'Other'};
const parsed = sh.map(s => { const seg = s.description.split(' > '); let last = 0; seg.forEach((t, i) => { if (/^\d+ [A-Za-z]/.test(t) && !/^\d+ Pts$/.test(t)) last = i; }); const shooter = seg[last].replace(/^\d+ /, ''); const pt = seg[last + 1]; const rest = seg.slice(last + 2); const dist = rest.find(t => /Long\/3pt|Medium|Short to/.test(t)); const d = dist ? (/Long/.test(dist) ? '3PT' : /Medium/.test(dist) ? 'mid-range' : 'short (<17 ft)') : (s.pointsAttempted === 3 ? '3PT' : null); let st; if (rest.some(t => /To Basket|At Basket|^Basket$|Rolls to Basket|Drop Step|Dunk|Layup/.test(t))) st = 'To basket'; else if (rest.includes('Dribble Jumper')) st = 'Dribble jumper' + (d ? ', ' + d : ''); else if (rest.includes('No Dribble Jumper') || rest.includes('Takes Early Jump Shot') || rest.includes('Early Jumper')) { const g = rest.includes('Guarded') ? 'Guarded' : rest.includes('Open') ? 'Open' : 'No-dribble jumper'; st = g + (d ? ', ' + d : ''); } else if (rest.some(t => /Hook/.test(t))) st = 'Hook'; else if (rest.some(t => /Scoring Attempt|Put Back|Tip/.test(t))) st = 'Put-back attempt'; else st = 'Other' + (d ? ', ' + d : ''); const c = s.clock == null ? '' : `${Math.floor(s.clock / 600)}:${String(Math.floor((s.clock / 10) % 60)).padStart(2, '0')}`; return {date: s.gameDate.slice(0, 10), game: s.gameName, period: s.period, clock: c, player: shooter, sur: shooter.split(' ').slice(-1)[0], play_type: PTMAP[pt] || 'Other', shot_type: st, zone: ZONE(s.zoneName), made: /Make \d Pts/.test(rest.join(' ')) ? 1 : 0, description: s.description}; });
out.shots = csv(['date','game','period','clock','player','play_type','shot_type','zone','made','description'], parsed);   // clock = time remaining in the period
const zp = {}; for (const p of parsed) { const k = p.sur + '|' + p.zone; zp[k] = zp[k] || {player: p.sur, dimension: 'shot_location', category: p.zone, fgm: 0, fga: 0}; zp[k].fga++; zp[k].fgm += p.made; }
const byP = {}; for (const r of pp) { const cat = ['Post-Up', 'Handoffs', 'Miscellaneous Plays'].includes(r.play_type) ? 'Other' : r.play_type; const k = r.player + '|' + cat; byP[k] = byP[k] || {player: r.player, dimension: 'play_type', category: cat, fgm: 0, fga: 0}; byP[k].fga += r.fga; byP[k].fgm += r.fgm; }
out.opp_players_fg_by_zone_and_playtype = csv(['player','dimension','category','fgm','fga'], [...Object.values(zp), ...Object.values(byP)].filter(r => r.fga > 0).sort((a, b) => a.player.localeCompare(b.player) || a.dimension.localeCompare(b.dimension)));
const cnt = {}; for (const p of parsed) { const k = p.sur + '|' + p.play_type; cnt[k] = (cnt[k] || 0) + 1; }
const stm = {}; for (const p of parsed) { if (cnt[p.sur + '|' + p.play_type] < 8) continue; const k = p.sur + '|' + p.play_type + '|' + p.shot_type; stm[k] = stm[k] || {player: p.sur, play_type: p.play_type, shot_type: p.shot_type, fga: 0, fgm: 0}; stm[k].fga++; stm[k].fgm += p.made; }
out.opp_players_shottype_within_playtype = csv(['player','play_type','shot_type','fga','fgm'], Object.values(stm).sort((a, b) => a.player.localeCompare(b.player) || a.play_type.localeCompare(b.play_type) || b.fga - a.fga));
// lineups
const lmet = x => { const m = met(x); return {ids: x.lineup.map(p => p.iid).sort().join('-'), lineup: x.lineup.map(p => p.lastName).join(' / '), poss: m.poss, pts: m.pts, ppp: m.ppp, fgm: m.fgm, fga: m.fga, tpm: m.fg3m, tpa: m.fg3a, ftm: x.ftMade || 0, fta: x.ftAttempt || 0, to: x.turnover || 0, to_pct: m.to_pct, efg: m.fga ? f3((m.fgm + 0.5 * m.fg3m) / m.fga) : '', ts: m.ts_pct, ssq: m.ssq, pps: m.pps, ssm: m.ssm, tpa_rate: m.fga ? f3(m.fg3a / m.fga) : '', ft_rate: m.fga ? f3((x.ftAttempt || 0) / m.fga) : '', score_pct: m.score_pct, sf_pct: m.sf_pct}; };
const lo = (await q(`offensiveteam eq oid(${OPP}) and season eq oid(${S}) and competitiondefinitionkey eq compkey(${C}) and play eq 1 group offensiveteam, offensivelineup`)).map(lmet).sort((a, b) => b.poss - a.poss);
const ld = (await q(`defensiveteam eq oid(${OPP}) and season eq oid(${S}) and competitiondefinitionkey eq compkey(${C}) and play eq 1 group defensiveteam, defensivelineup`)).map(lmet).sort((a, b) => b.poss - a.poss);
const dm = {}; for (const d of ld) dm[d.ids] = d; const om = {}; for (const o of lo) om[o.ids] = o;
const merged = [...new Set([...lo.map(x => x.ids), ...ld.map(x => x.ids)])].map(k => { const o = om[k], d = dm[k] || {}; return {...(o || {ids: k, lineup: d.lineup}), def_poss: d.poss ?? '', opp_pts: d.pts ?? '', opp_ppp: d.ppp ?? '', opp_to: d.to ?? '', opp_fgm: d.fgm ?? '', opp_fga: d.fga ?? ''}; }).sort((a, b) => (b.poss || 0) - (a.poss || 0));
const lucols = ['ids','lineup','poss','pts','ppp','fgm','fga','tpm','tpa','ftm','fta','to','to_pct','efg','ts','ssq','pps','ssm','tpa_rate','ft_rate','score_pct','sf_pct'];
out.opp_lineups_offense_all = csv(lucols, lo);
out.opp_lineups_defense_all = csv(['ids','lineup','poss','opp_pts','opp_ppp','opp_to','opp_fgm','opp_fga'], ld.map(d => ({ids: d.ids, lineup: d.lineup, poss: d.poss, opp_pts: d.pts, opp_ppp: d.ppp, opp_to: d.to, opp_fgm: d.fgm, opp_fga: d.fga})));
out.opp_lineups_off_def = csv([...lucols, 'def_poss','opp_pts','opp_ppp','opp_to','opp_fgm','opp_fga'], merged);
window.__out = out;
console.log(Object.fromEntries(Object.entries(out).map(([k, v]) => [k, v.split('\n').length - 1 + ' rows'])));
})();
