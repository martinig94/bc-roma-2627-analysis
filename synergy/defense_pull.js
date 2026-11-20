// Synergy pull for the "Defense tendencies" page of one opponent analysis (data/synergy/defense_<opponent>_<game date>/).
// Run in the browser console (or Claude's browser pane) on any page of https://apps.synergysports.com/basketball while logged in.
// Edit CONFIG, run the file, poll `window.__df.done`, then read `window.__df.files` (one CSV string per file).
// Every team of the competition is pulled as the defense, so each situation can be ranked within the competition.
// Ids and the possession query grammar: see the header of webapp_pull.js. The situation expressions are the ones of the app's
// own "Situations" tables (man / zone / press, plays including passes, defense commits, traps, hard doubles, shot types).
// Files:
//   situations.csv   one row per team (as the defense) and situation: possessions, points, shooting, turnovers, free throws
//   defenders.csv    opponent defenders: possessions / points / FGA / FGM / turnovers by play type (possessions that end on him)
//   periods.csv      what the opponent allows per period
//   games.csv        what the opponent allows per game: all, half court, transition, zone, press
//   lineups.csv      opponent defensive lineups
//   shots.csv        every FGA allowed by the opponent, with game, period and clock (tenths of a second left in the period)
const CONFIG = {
  S: '69bba845d0611197290c7acc',
  C: '54457dce300969b132fcfb3f:COMP:560106aa8dc7a233b47b74bb',
  OPP: '54457df0300969b132fd0dca',
};
(async () => {
const {S, C, OPP} = CONFIG;
window.__df = {done: false, log: []};
const DF = window.__df;
const API = 'https://basketball.synergysportstech.com/api';
const tok = () => JSON.parse(localStorage.getItem('oidc.user:https://auth.synergysportstech.com:client.basketball.teamsite')).access_token;
const post = async (u, b) => (await fetch(u, {method: 'POST', headers: {Authorization: 'Bearer ' + tok(), 'Content-Type': 'application/json'}, body: JSON.stringify(b)})).json();
const q = async expr => { const r = await post(API + '/possessionreports', {expressions: [expr], includePartiallyLoggedGames: false, includePlayByPlayStats: false}); return Array.isArray(r) ? r : (r.result || []); };
const pool = async (jobs, n = 6) => { const out = new Array(jobs.length); let i = 0; await Promise.all(Array.from({length: n}, async () => { while (i < jobs.length) { const k = i++; out[k] = await jobs[k](); } })); return out; };
const csv = (cols, rows) => [cols.join(','), ...rows.map(r => cols.map(c => { let v = r[c]; v = (v === undefined || v === null) ? '' : String(v); return /[,"\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }).join(','))].join('\n');
const base = `season eq oid(${S}) and competitiondefinitionkey eq compkey(${C})`;
const FGA = 'result in [3,4,5,6,7,8]';
const PT = {pnrbh: 'play eq 1 and play eq 136', roll: 'play eq 235', trans: 'play eq 418', iso: 'play eq 50', post: 'play eq 1 and play eq 259',
            spot: 'play eq 400', putback: 'play eq 415', cut: 'play eq 3', handoff: 'play eq 11', offscreen: 'play eq 85', misc: 'play eq 1 and play eq 452'};
const SIT = {
  all: 'play eq 1', halfcourt: 'play eq 453', ...PT,
  man: 'play eq 453 and zone eq false', zone: 'play eq 453 and zone eq true',
  press: 'play eq 1 and press eq true', press_trans: 'play eq 418 and press eq true', press_halfcourt: 'play eq 453 and press eq true',
  ato: 'play eq 1 and ato eq true', eob: 'play eq 1 and eob eq true', sob: 'play eq 1 and sob eq true', shortclock: 'play eq 453 and shortclock eq true',
  pnr_passes: 'play eq 1 and (play eq 137 or play eq 143)', pnr_commit: 'play eq 1 and play eq 137 and doubled eq true', pnr_trap: 'play eq 1 and play eq 137 and harddoubled eq true',
  pnrbh_off_pick: 'play eq 1 and play eq 136 and plays in [17]', pnrbh_away_pick: 'play eq 1 and play eq 136 and plays in [34]',
  pnrbh_split: 'play eq 1 and play eq 136 and plays in [89]', pnrbh_early_jumper: 'play eq 1 and play eq 136 and plays in [92]',
  iso_passes: 'play eq 1 and (play eq 51 or play eq 56)', iso_commit: 'play eq 1 and (play eq 83 or play eq 84)',
  post_passes: 'play eq 1 and (play eq 260 or play eq 265)', post_commit: 'play eq 1 and play eq 260 and doubled eq true', post_hard_double: 'play eq 260 and harddoubled eq true',
  drives: 'plays in [20,21,22]', drives_left: 'plays in [20]', drives_right: 'plays in [21]',
  cs: 'play eq 457 or plays all [102, 58]', cs_guarded: 'play eq 458 or plays all [102, 58, 35]', cs_open: 'play eq 459 or plays all [102, 58, 66]',
  dribble_jumper: `plays eq 15 and ${FGA}`, jump_short: `distance eq 3 and shot eq 428 and ${FGA}`, jump_medium: `distance eq 2 and shot eq 428 and ${FGA}`,
  jump_long: `distance eq 1 and shot eq 428 and ${FGA}`, runner: `shot eq 430 and ${FGA}`, hook: `shot eq 406 and ${FGA}`,
  at_rim: `shot in [424, 423, 427] and ${FGA}`, sq_low: `shotqualitylevel eq 1 and ${FGA}`, sq_medium: `shotqualitylevel eq 2 and ${FGA}`, sq_high: `shotqualitylevel eq 3 and ${FGA}`,
};
const NUM = ['possessions', 'pointMade', 'shotAttempt', 'shotMade', 'shot3Attempt', 'shot3Made', 'turnover', 'ftTimes', 'ftAttempt', 'shotFoul', 'score'];
const nums = x => Object.fromEntries(NUM.map(k => [k, x[k] || 0]));

// 1. every team as the defense, every situation
const sit = [];
for (const [key, rows] of await pool(Object.entries(SIT).map(([key, ex]) => async () => [key, await q(`${base} and (${ex}) group defensiveteam`)])))
  for (const x of rows) sit.push({team_id: x.team.id, abbr: x.team.abbr, name: x.team.name, situation: key, gp: x.gp, ...nums(x)});
DF.log.push(`situations ${sit.length}`);
// 2. opponent defenders by play type
const opp = `${base} and defensiveteam eq oid(${OPP})`;
const def = [];
for (const [key, rows] of await pool(Object.entries({all: 'play eq 1', ...PT}).map(([key, ex]) => async () => [key, await q(`${opp} and (${ex}) group defensiveplayer`)])))
  for (const x of rows) def.push({player_id: x.player.id, name: x.player.name, play_type: key, gp: x.gp, ...nums(x)});
// 3. periods, games, lineups
const per = (await q(`${opp} and (play eq 1) group period`)).map(x => ({period: x.period, ...nums(x)}));
const games = [];
for (const key of ['all', 'halfcourt', 'trans', 'zone', 'press'])
  for (const x of await q(`${opp} and (${SIT[key]}) group game`)) {
    const vs = [x.game.homeTeam, x.game.awayTeam].find(t => t && t.id !== OPP);
    games.push({game_id: x.game.id, date: x.game.date.slice(0, 10), vs: vs ? vs.name : '', situation: key, ...nums(x)});
  }
const lineups = (await q(`${opp} and play eq 1 group defensiveteam, defensivelineup`))
  .map(x => ({lineup: x.lineup.map(p => p.lastName).sort().join(' / '), ...nums(x)})).sort((a, b) => b.possessions - a.possessions);
DF.log.push('defenders, periods, games, lineups done');
// 4. shots allowed
let shots = [], skip = 0;
for (;;) { const r = (await post(API + '/court/2/shots', {defense: true, zonesBreakdown: 1, seasonId: S, competitionDefinitionKey: C, teamId: OPP, skip, take: 1000, zoneNames: []})).result || []; shots = shots.concat(r); if (r.length < 1000) break; skip += 1000; }
const srow = s => ({game_id: s.gameId, date: s.gameDate.slice(0, 10), game: s.gameName, period: s.period, clock: s.clock, pts_att: s.pointsAttempted, pts_scored: s.pointsScored,
                    zone: s.zoneName, dist: s.shotDistance, x: s.coordinates.x, y: s.coordinates.y, shot_quality: s.shotQuality, description: s.description});
// 5. files
const ncols = NUM;
DF.files = {
  'situations.csv': csv(['team_id', 'abbr', 'name', 'situation', 'gp', ...ncols], sit.sort((a, b) => a.situation.localeCompare(b.situation) || a.name.localeCompare(b.name))),
  'defenders.csv': csv(['player_id', 'name', 'play_type', 'gp', ...ncols], def.sort((a, b) => a.play_type.localeCompare(b.play_type) || b.possessions - a.possessions)),
  'periods.csv': csv(['period', ...ncols], per.sort((a, b) => a.period - b.period)),
  'games.csv': csv(['game_id', 'date', 'vs', 'situation', ...ncols], games.sort((a, b) => a.date.localeCompare(b.date) || a.situation.localeCompare(b.situation))),
  'lineups.csv': csv(['lineup', ...ncols], lineups),
  'shots.csv': csv(['game_id', 'date', 'game', 'period', 'clock', 'pts_att', 'pts_scored', 'zone', 'dist', 'x', 'y', 'shot_quality', 'description'], shots.map(srow)),
};
DF.meta = {pulled: new Date().toISOString(), shots: shots.length, teams: new Set(sit.map(r => r.team_id)).size, config: CONFIG};
DF.sizes = Object.fromEntries(Object.entries(DF.files).map(([k, v]) => [k, v.split('\n').length - 1]));
DF.done = true;
})().catch(e => { window.__df.error = String(e && e.stack || e); window.__df.done = true; });
