// Synergy team leaderboards (offense and defense, overall and by play type) for data/synergy/leaderboards_<date>/.
// Same mechanics as webapp_pull.js: run in the browser console / Claude's browser pane on any page of
// https://apps.synergysports.com/basketball while logged in; the app's bearer token is read from localStorage.
// Paste the whole file, then read `window.__lb` (one CSV string per file) and save each one:
//   leaderboard_<competition>_<side>.csv   e.g. leaderboard_eurocup_defense.csv
// Long format, one row per team x play type ("All" = every possession, as the "PPP" sheet of the Synergy export).
// Columns follow the leaderboard page of the app: counts (poss, pts, fga, fgm, ...) are PER GAME like the app's
// "per game" view; poss_total is the raw count; pct_time = share of the team's possessions; rank is by PPP rounded
// to 3 decimals, ascending for defense (lower PPP = better) and descending for offense, ties share the rank, teams with
// fewer than 10 possessions of a play type are kept but not ranked (the app drops them). SSM = rounded PPS - rounded SSQ, as the app.
// Ids (2026-27) and play ids: see the header of webapp_pull.js.
const CONFIG = {
  S: '69bba845d0611197290c7acc',
  COMPS: {
    eurocup: '54457dce300969b132fcfb3f:COMP:560100ac8dc7a24394b95656',
    seriea:  '54457dce300969b132fcfb3f:COMP:560106aa8dc7a233b47b74bb',
  },
  SIDES: ['offense', 'defense'],
  LEAGUE: '54457dce300969b132fcfb3f',   // "International": gives the teams' full names
};
(async () => {
const {S, COMPS, SIDES} = CONFIG;
const tok = () => JSON.parse(localStorage.getItem('oidc.user:https://auth.synergysportstech.com:client.basketball.teamsite')).access_token;
const post = async (u, b) => (await fetch(u, {method: 'POST', headers: {Authorization: 'Bearer ' + tok(), 'Content-Type': 'application/json'}, body: JSON.stringify(b)})).json();
const q = async (expr) => { const r = await post('https://basketball.synergysportstech.com/api/possessionreports', {expressions: [expr], includePartiallyLoggedGames: false, includePlayByPlayStats: false}); return Array.isArray(r) ? r : (r.result || []); };
const PT = [['All','play eq 1'],['Spot Up','play eq 400'],['P&R Ball Handler','play eq 1 and play eq 136'],['Transition','play eq 418'],['P&R Roll Man','play eq 235'],['Cut','play eq 3'],['Offensive Rebounds (Put Backs)','play eq 415'],['Isolation','play eq 50'],['Post-Up','play eq 1 and play eq 259'],['Handoffs','play eq 11'],['Off Screen','play eq 85'],['Miscellaneous Plays','play eq 1 and play eq 452']];
const f1 = x => Math.round(x * 10) / 10, f2 = x => Math.round(x * 100) / 100, f3 = x => Math.round(x * 1000) / 1000;
const csv = (cols, rows) => [cols.join(','), ...rows.map(r => cols.map(c => { let v = r[c]; v = (v === undefined || v === null) ? '' : String(v); return /[,"]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }).join(','))].join('\n');
// per-game counts + the app's rate columns (same formulas as met() in webapp_pull.js)
const met = (s, gp) => { const poss = s.possessions || 0, fga = s.shotAttempt || 0, fgm = s.shotMade || 0, m3 = s.shot3Made || 0, fta = s.ftAttempt || 0, pts = s.pointMade || 0, a2 = s.shot2Attempt || 0, m2 = s.shot2Made || 0, a3 = s.shot3Attempt || 0; const pg = x => f2(x / gp); return {poss_total: poss, poss: pg(poss), pts: pg(pts), ppp: poss ? f3(pts / poss) : '', fga: pg(fga), fgm: pg(fgm), fg_miss: pg(fga - fgm), fg_pct: fga ? f1(100 * fgm / fga) : '', efg_pct: fga ? f1(100 * (fgm + 0.5 * m3) / fga) : '', ssq: s.shotQualityAttempt ? f2(s.shotQualityTotal / s.shotQualityAttempt) : '', pps: fga ? f2((2 * (fgm - m3) + 3 * m3) / fga) : '', ssm: (fga && s.shotQualityAttempt) ? f2(f2((2 * (fgm - m3) + 3 * m3) / fga) - f2(s.shotQualityTotal / s.shotQualityAttempt)) : '', to_pct: poss ? f1(100 * (s.turnover || 0) / poss) : '', ft_pct: poss ? f1(100 * (s.ftTimes || 0) / poss) : '', fta_per_fga: fga ? f2(fta / fga) : '', sf_pct: poss ? f1(100 * (s.shotFoul || 0) / poss) : '', score_pct: poss ? f1(100 * (s.score || 0) / poss) : '', fg2a: pg(a2), fg2m: pg(m2), fg2_miss: pg(a2 - m2), fg2_pct: a2 ? f1(100 * m2 / a2) : '', fg3a: pg(a3), fg3m: pg(m3), fg3_miss: pg(a3 - m3), fg3_pct: a3 ? f1(100 * m3 / a3) : '', fg3a_per_fga: fga ? f2(a3 / fga) : ''}; };
const MIN_POSS = 10;   // the app's leaderboard lists only teams with at least 10 possessions of the play type; here they are kept with an empty rank
const cols = ['play_type','rank','team','name','gp','poss','pct_time','pts','ppp','fga','fgm','fg_miss','fg_pct','efg_pct','ssq','pps','ssm','to_pct','ft_pct','fta_per_fga','sf_pct','score_pct','fg2a','fg2m','fg2_miss','fg2_pct','fg3a','fg3m','fg3_miss','fg3_pct','fg3a_per_fga','poss_total'];
const out = {};
const FULL = {}; { const tw = await (await fetch(`https://basketball.synergysportstech.com/api/leagues/${CONFIG.LEAGUE}/teamswithstats?seasonId=${S}`, {headers: {Authorization: 'Bearer ' + tok()}})).json(); for (const t of (Array.isArray(tw) ? tw : (tw.result || []))) FULL[t.id] = t.fullName || t.name; }
for (const [comp, C] of Object.entries(COMPS)) for (const side of SIDES) {
  const grp = side === 'offense' ? 'offensiveteam' : 'defensiveteam';
  const rows = [];
  let all = {};
  for (const [name, ex] of PT) {
    const teams = await q(`season eq oid(${S}) and competitiondefinitionkey eq compkey(${C}) and (${ex}) group ${grp}`);
    if (name === 'All') for (const t of teams) all[t.team.id] = t;
    const r = teams.map(t => { const a = all[t.team.id] || {}; const gp = a.gp || t.gp; return {play_type: name, team: t.team.abbr, name: FULL[t.team.id] || t.team.name, gp, pct_time: a.possessions ? f1(100 * (t.possessions || 0) / a.possessions) : '', ...met(t, gp)}; }).filter(x => x.poss_total > 0);
    const key = x => Number(x.ppp);
    r.sort((a, b) => side === 'defense' ? key(a) - key(b) : key(b) - key(a));
    const ranked = r.filter(x => x.poss_total >= MIN_POSS);
    for (const x of r) x.rank = x.poss_total >= MIN_POSS ? 1 + ranked.filter(y => side === 'defense' ? key(y) < key(x) : key(y) > key(x)).length : '';
    rows.push(...r);
  }
  out[`leaderboard_${comp}_${side}`] = csv(cols, rows);
}
window.__lb = out;
console.log(Object.fromEntries(Object.entries(out).map(([k, v]) => [k, v.split('\n').length - 1 + ' rows'])));
})();
