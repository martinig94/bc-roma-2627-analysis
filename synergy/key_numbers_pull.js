// Synergy pull for the "Key numbers" tab of one opponent analysis (data/synergy/key_numbers_<opponent>_<game date>/).
// Run in the browser console (or Claude's browser pane) on any page of https://apps.synergysports.com/basketball while logged in.
// Edit CONFIG, run the file, poll `window.__kn.done`, then read `window.__kn.files` (one CSV string per file).
// Every team of the competition is pulled (offense and defense), so each number can be ranked within the competition.
// Ids and the possession query grammar: see the header of webapp_pull.js.
// Files:
//   teams.csv      one row per team and side (off = the team's offense, def = what it allows): possessions, points, shooting,
//                  play types (poss_<pt>, pts_<pt>), rebounds (from the play-by-play stats of `group game`), shot aggregates
//   zones.csv      FGA / FGM per team, side and Synergy zone (Z11-01 paint ... Z11-16 corner three), with mean x / y of the shots
//   players.csv    opponent players: possessions, points, turnovers, play types, and shot aggregates (rim / mid / three, catch-and-shoot,
//                  open / guarded jumpers, drives by side, attributed to the driver)
//   defenders.csv  reference team (BC Roma) defenders: possessions and points allowed by play type (possessions that end on him)
//   opp_shots.csv / ref_def_shots.csv   every FGA of the opponent and every FGA allowed by the reference team (for the shot charts)
const CONFIG = {
  S: '69bba845d0611197290c7acc',
  C: '54457dce300969b132fcfb3f:COMP:560100ac8dc7a24394b95656',
  OPP: '5b0e907a9559b26e7e9859b6', REF: '54457df1300969b132fd0e16',
};
(async () => {
const {S, C, OPP, REF} = CONFIG;
window.__kn = {done: false, log: []};
const log = m => window.__kn.log.push(m);
const API = 'https://basketball.synergysportstech.com/api';
const tok = () => JSON.parse(localStorage.getItem('oidc.user:https://auth.synergysportstech.com:client.basketball.teamsite')).access_token;
const post = async (u, b) => (await fetch(u, {method: 'POST', headers: {Authorization: 'Bearer ' + tok(), 'Content-Type': 'application/json'}, body: JSON.stringify(b)})).json();
const q = async (expr, pbp = false) => { const r = await post(API + '/possessionreports', {expressions: [expr], includePartiallyLoggedGames: false, includePlayByPlayStats: pbp}); return Array.isArray(r) ? r : (r.result || []); };
const pool = async (jobs, n = 6) => { const out = new Array(jobs.length); let i = 0; await Promise.all(Array.from({length: n}, async () => { while (i < jobs.length) { const k = i++; out[k] = await jobs[k](); } })); return out; };
const csv = (cols, rows) => [cols.join(','), ...rows.map(r => cols.map(c => { let v = r[c]; v = (v === undefined || v === null) ? '' : String(v); return /[,"\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }).join(','))].join('\n');
const base = `season eq oid(${S}) and competitiondefinitionkey eq compkey(${C})`;
const PT = {pnrbh: 'play eq 1 and play eq 136', roll: 'play eq 235', trans: 'play eq 418', iso: 'play eq 50', post: 'play eq 1 and play eq 259',
            spot: 'play eq 400', putback: 'play eq 415', cut: 'play eq 3', handoff: 'play eq 11', offscreen: 'play eq 85', misc: 'play eq 1 and play eq 452'};
const SIDE = {off: 'offensiveteam', def: 'defensiveteam'};
const NUM = ['possessions', 'pointMade', 'turnover', 'shotAttempt', 'shotMade', 'shot3Attempt', 'shot3Made', 'ftAttempt', 'ftMade', 'ftTimes', 'shotFoul', 'score'];

// 1. teams: totals and play types, both sides
const T = {};
for (const side of ['off', 'def']) {
  for (const x of await q(`${base} and (play eq 1) group ${SIDE[side]}`)) {
    const r = T[x.team.id + side] = {team_id: x.team.id, abbr: x.team.abbr, name: x.team.name, side, gp: x.gp};
    for (const k of NUM) r[k] = x[k] || 0;
  }
  const res = await pool(Object.entries(PT).map(([k, ex]) => async () => [k, await q(`${base} and (${ex}) group ${SIDE[side]}`)]));
  for (const [k, rows] of res) for (const x of rows) { const r = T[x.team.id + side]; if (!r) continue; r['poss_' + k] = x.possessions || 0; r['pts_' + k] = x.pointMade || 0; r['to_' + k] = x.turnover || 0; }
}
const teams = [...new Set(Object.values(T).map(r => r.team_id))];
log(`teams ${teams.length}`);
// 2. rebounds: play-by-play stats are only given with `group game`; on the possessions of `side`, offreb = offensive rebounds of the
//    offense, defReb = defensive rebounds of the defense
await pool(teams.flatMap(id => ['off', 'def'].map(side => async () => {
  const rows = await q(`${base} and ${SIDE[side]} eq oid(${id}) group game`, true);
  const r = T[id + side]; r.offreb = 0; r.defreb = 0; r.assist = 0; r.steal = 0;
  for (const x of rows) { r.offreb += x.offreb || 0; r.defreb += x.defReb || 0; r.assist += x.assist || 0; r.steal += x.steal || 0; }
})));
log('rebounds done');
// 3. shots of every team (offense) and allowed (defense)
const getShots = async (id, defense) => { let all = [], skip = 0; for (;;) { const r = (await post(API + '/court/2/shots', {defense, zonesBreakdown: 1, seasonId: S, competitionDefinitionKey: C, teamId: id, skip, take: 1000, zoneNames: []})).result || []; all = all.concat(r); if (r.length < 1000) break; skip += 1000; } return all; };
const isPlayer = t => /^\d+ [A-Za-z]/.test(t) && !/^\d+ Pts$/.test(t);
const parse = s => {
  const seg = s.description.split(' > ');
  let last = 0; seg.forEach((t, i) => { if (isPlayer(t)) last = i; });
  const after = seg.slice(last + 1);
  let cur = null; const drives = [];
  seg.forEach(t => { if (isPlayer(t)) cur = t.replace(/^\d+ /, ''); const m = t.match(/^Drives? (Left|Right|Straight|Baseline)$/); if (m) drives.push([cur, m[1]]); });
  const three = s.pointsAttempted === 3, made = /^Make/.test(seg[seg.length - 1]) || seg.some(t => /^Make \d Pts/.test(t));
  const rim = !three && s.shotDistance <= 60;
  const zone = three ? 'three' : rim ? 'rim' : (s.zoneName === 'Z11-01-2pt' ? 'paint' : 'mid');
  return {shooter: seg[last].replace(/^\d+ /, ''), number: s.playerNumber, three, made, zone, cs: after.includes('No Dribble Jumper'),
          open: after.includes('Open'), guarded: after.includes('Guarded'), drives, transition: after[0] === 'Transition', playType: after[0] || ''};
};
const SH = {}, Z = [];
await pool(teams.flatMap(id => [false, true].map(defense => async () => {
  const shots = await getShots(id, defense), side = defense ? 'def' : 'off', r = T[id + side];
  if (id === OPP && !defense) SH.opp = shots;
  if (id === REF && defense) SH.refdef = shots;
  const a = {rim_a: 0, rim_m: 0, paint_a: 0, paint_m: 0, mid_a: 0, mid_m: 0, three_a: 0, three_m: 0, cs3_a: 0, cs3_m: 0, jump_tag: 0, jump_open: 0,
             open3_a: 0, open3_m: 0, drive_fga: 0, drive_l: 0, drive_r: 0, sq_tot: 0, sq_n: 0, shots: shots.length};
  const zones = {};
  for (const s of shots) {
    const p = parse(s);
    a[p.zone + '_a']++; if (p.made) a[p.zone + '_m']++;
    if (p.cs && p.three) { a.cs3_a++; if (p.made) a.cs3_m++; }
    if (p.open || p.guarded) { a.jump_tag++; if (p.open) a.jump_open++; }
    if (p.open && p.three) { a.open3_a++; if (p.made) a.open3_m++; }
    if (p.drives.length) { a.drive_fga++; const d = p.drives[0][1]; if (d === 'Left') a.drive_l++; if (d === 'Right') a.drive_r++; }
    if (typeof s.shotQuality === 'number') { a.sq_tot += s.shotQuality; a.sq_n++; }
    const z = zones[s.zoneName] = zones[s.zoneName] || {a: 0, m: 0, x: 0, y: 0}; z.a++; if (p.made) z.m++; z.x += s.coordinates.x; z.y += s.coordinates.y;
  }
  Object.assign(r, a);
  for (const [zn, z] of Object.entries(zones)) Z.push({team_id: id, side, zone: zn, fga: z.a, fgm: z.m, x: (z.x / z.a).toFixed(1), y: (z.y / z.a).toFixed(1)});
}), 4));
log('shots done');
// 4. opponent players
const P = {};
const prow = x => P[x.player.id] = P[x.player.id] || {player_id: x.player.id, name: x.player.name};
for (const x of await q(`${base} and offensiveteam eq oid(${OPP}) and (play eq 1) group offensiveplayer`)) {
  const r = prow(x); r.gp = x.gp; for (const k of NUM) r[k] = x[k] || 0;
}
for (const [k, rows] of await pool(Object.entries(PT).map(([k, ex]) => async () => [k, await q(`${base} and offensiveteam eq oid(${OPP}) and (${ex}) group offensiveplayer`)])))
  for (const x of rows) { const r = prow(x); r['poss_' + k] = x.possessions || 0; r['pts_' + k] = x.pointMade || 0; }
const byName = {}; for (const r of Object.values(P)) byName[r.name] = r;
const pr = n => { if (!byName[n]) { const hit = Object.values(P).find(r => r.name.split(' ').slice(-1)[0] === n.split(' ').slice(-1)[0]); byName[n] = hit || (P['x' + n] = {player_id: '', name: n}); } return byName[n]; };
const PK = ['fga', 'fgm', 'rim_a', 'rim_m', 'paint_a', 'paint_m', 'mid_a', 'mid_m', 'three_a', 'three_m', 'cs3_a', 'cs3_m', 'jump_tag', 'jump_open', 'drive_l', 'drive_r', 'drive_s', 'drive_fga_own'];
for (const r of Object.values(P)) for (const k of PK) r[k] = 0;
for (const s of SH.opp || []) {
  const p = parse(s), r = pr(p.shooter); for (const k of PK) r[k] = r[k] || 0;
  r.number = r.number || p.number; r.fga++; if (p.made) r.fgm++;
  r[p.zone + '_a']++; if (p.made) r[p.zone + '_m']++;
  if (p.cs && p.three) { r.cs3_a++; if (p.made) r.cs3_m++; }
  if (p.open || p.guarded) { r.jump_tag++; if (p.open) r.jump_open++; }
  const own = p.drives.find(d => d[0] === p.shooter); if (own) r.drive_fga_own++;
  for (const [who, dir] of p.drives) { const d = pr(who || p.shooter); for (const k of PK) d[k] = d[k] || 0; d[dir === 'Left' ? 'drive_l' : dir === 'Right' ? 'drive_r' : 'drive_s']++; }
}
// 5. reference-team defenders
const D = {};
const DPT = {all: 'play eq 1', ...PT};
for (const [k, rows] of await pool(Object.entries(DPT).map(([k, ex]) => async () => [k, await q(`${base} and defensiveteam eq oid(${REF}) and (${ex}) group defensiveplayer`)])))
  for (const x of rows) { const r = D[x.player.id] = D[x.player.id] || {player_id: x.player.id, name: x.player.name}; if (k === 'all') r.gp = x.gp; r['poss_' + k] = x.possessions || 0; r['pts_' + k] = x.pointMade || 0; r['fga_' + k] = x.shotAttempt || 0; r['to_' + k] = x.turnover || 0; }
// 6. files
const ptc = Object.keys(PT).flatMap(k => ['poss_' + k, 'pts_' + k, 'to_' + k]);
const tcols = ['team_id', 'abbr', 'name', 'side', 'gp', ...NUM, 'offreb', 'defreb', 'assist', 'steal', ...ptc, 'shots', 'rim_a', 'rim_m', 'paint_a', 'paint_m', 'mid_a', 'mid_m', 'three_a', 'three_m',
               'cs3_a', 'cs3_m', 'jump_tag', 'jump_open', 'open3_a', 'open3_m', 'drive_fga', 'drive_l', 'drive_r', 'sq_tot', 'sq_n'];
const pcols = ['player_id', 'name', 'number', 'gp', ...NUM, ...Object.keys(PT).flatMap(k => ['poss_' + k, 'pts_' + k]), ...PK];
const dcols = ['player_id', 'name', 'gp', ...Object.keys(DPT).flatMap(k => ['poss_' + k, 'pts_' + k, 'fga_' + k, 'to_' + k])];
const scols = ['gameId', 'gameDate', 'player', 'playerNumber', 'pointsAttempted', 'made', 'zoneName', 'shotDistance', 'x', 'y', 'shotQuality', 'play_type', 'description'];
const srow = s => ({...s, player: s.player && s.player.name, made: parse(s).made ? 1 : 0, x: s.coordinates.x, y: s.coordinates.y, play_type: parse(s).playType});
const dates = (SH.opp || []).map(s => s.gameDate).sort();
window.__kn.files = {
  'teams.csv': csv(tcols, Object.values(T).sort((a, b) => a.name.localeCompare(b.name) || a.side.localeCompare(b.side))),
  'zones.csv': csv(['team_id', 'side', 'zone', 'fga', 'fgm', 'x', 'y'], Z),
  'players.csv': csv(pcols, Object.values(P).filter(r => r.possessions || r.fga).sort((a, b) => (b.fga || 0) - (a.fga || 0))),
  'defenders.csv': csv(dcols, Object.values(D).sort((a, b) => (b.poss_all || 0) - (a.poss_all || 0))),
  'opp_shots.csv': csv(scols, (SH.opp || []).map(srow)),
  'ref_def_shots.csv': csv(scols, (SH.refdef || []).map(srow)),
};
window.__kn.meta = {pulled: new Date().toISOString(), last_game: dates[dates.length - 1], opp_fga: (SH.opp || []).length, teams: teams.length, config: CONFIG};
window.__kn.sizes = Object.fromEntries(Object.entries(window.__kn.files).map(([k, v]) => [k, v.length]));
window.__kn.done = true;
})().catch(e => { window.__kn.error = String(e && e.stack || e); window.__kn.done = true; });
