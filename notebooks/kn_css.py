"""CSS of the Key numbers tab: the stylesheet of the SkillCorner game-preparation page, scoped under .kn2 so it does not touch the
site around it (and the site's styles are reset inside it). Fonts from Google Fonts (Chakra Petch, Roboto) instead of embedded files."""

CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;600;700&family=Roboto:wght@400;500;700&display=swap');
.kn2 {
  --card: #FFFFFF; --text: #252525; --text-muted: #575757; --text-subtle: #878787;
  --accent: #00A82F; --accent-bright: #32FE6B; --gold: #FFA324;
  --font-heading: 'Chakra Petch', 'Segoe UI', sans-serif; --font-body: 'Roboto', Arial, Helvetica, sans-serif;
  --ink: #161817; --on-ink: #F2F4F1; --on-ink-muted: #A9B0AB;
  --paper: #F3F4F2; --line: #E3E5E2; --track: #E9EBE8;
  --good: #00852A; --good-bg: #E2F4E7; --bad: #CE1620; --bad-bg: #FCE6E7; --neutral: #8B918D;
  --s1: 4px; --s2: 8px; --s3: 12px; --s4: 16px; --s5: 24px; --s6: 40px;
  --t-xs: .72rem; --t-sm: .82rem; --t-md: .94rem; --t-lg: 1.14rem; --t-xl: 1.5rem; --t-2xl: 2.1rem; --t-3xl: 2.8rem;
  --r: 12px; --r-sm: 6px;
  background: var(--paper); color: var(--text); font: 400 var(--t-md)/1.45 var(--font-body); -webkit-font-smoothing: antialiased;
  padding: var(--s4); border-radius: var(--r); margin: var(--s4) 0;
}
.kn2 *, .kn2 *::before, .kn2 *::after { box-sizing: border-box; margin: 0; padding: 0; }
.kn2 .h2, .kn2 h3 { font-family: var(--font-heading); font-weight: 600; line-height: 1.15; text-wrap: balance; color: inherit; border: 0; }
.kn2 b, .kn2 .num { font-variant-numeric: tabular-nums; }
.kn2 p { margin: 0; }
.kn2 .eyebrow { font: 600 var(--t-xs)/1.2 var(--font-heading); text-transform: uppercase; letter-spacing: .09em; color: var(--text-subtle); }
.kn2 .hero .eyebrow { color: var(--accent-bright); }
.kn2 .av { flex: none; width: 52px; height: 52px; border-radius: 50%; overflow: hidden; background: var(--ink); color: var(--on-ink);
  display: grid; place-items: center; font: 600 1.05rem var(--font-heading); letter-spacing: .02em; }
.kn2 .av.sm { width: 30px; height: 30px; font-size: .7rem; }
.kn2 .no { font: 600 .82em var(--font-heading); color: var(--text-subtle); margin-right: .35em; font-variant-numeric: tabular-nums; }
.kn2 .chips { display: flex; gap: var(--s1); flex-wrap: wrap; }
.kn2 .chip { font: 600 .68rem/1 var(--font-heading); text-transform: uppercase; letter-spacing: .06em; padding: 5px 9px;
  border-radius: 4px; background: var(--ink); color: var(--on-ink); white-space: nowrap; }
.kn2 .lines { display: grid; gap: 6px; }
.kn2 .ln { display: grid; grid-template-columns: 20px 1fr; gap: var(--s2); align-items: start; font-size: var(--t-sm); line-height: 1.35; }
.kn2 .ln i { font: 700 .8rem/20px var(--font-heading); font-style: normal; width: 20px; height: 20px; border-radius: 50%; text-align: center; color: #fff; }
.kn2 .ln.g i { background: var(--good); } .kn2 .ln.r i { background: var(--bad); } .kn2 .ln.n i { background: var(--neutral); }
.kn2 .ln b { font-weight: 700; font-size: 1.08em; }
.kn2 .ln.g b { color: var(--good); } .kn2 .ln.r b { color: var(--bad); }
.kn2 .bar { display: block; height: 8px; border-radius: 4px; background: var(--track); overflow: hidden; min-width: 48px; }
.kn2 .bar i { display: block; height: 100%; border-radius: 4px; background: var(--neutral); min-width: 6px; }
.kn2 .bar.good i { background: var(--good); } .kn2 .bar.bad i { background: var(--bad); } .kn2 .bar.ink i { background: var(--ink); }
.kn2 .topbar { display: flex; justify-content: space-between; align-items: center; gap: var(--s4); flex-wrap: wrap; margin-bottom: var(--s4); }
.kn2 .scopes { display: flex; flex: none; background: var(--track); border-radius: 8px; padding: 3px; }
.kn2 .scopes button { font: 500 var(--t-sm) var(--font-body); padding: 0 14px; min-height: 40px; border: 0; border-radius: 6px;
  background: transparent; color: var(--text-muted); cursor: pointer; white-space: nowrap; }
.kn2 .scopes button[aria-pressed="true"] { background: var(--card); color: var(--ink); box-shadow: 0 1px 2px rgba(0,0,0,.12); }
.kn2 section.tab { display: none; }
.kn2 section.tab.on { display: grid; gap: var(--s6); }
.kn2 section.tab > * { min-width: 0; }
.kn2 .sec { display: grid; gap: var(--s4); }
.kn2 .sec > header { display: grid; gap: 2px; }
.kn2 .sec .h2 { font-size: var(--t-xl); }
.kn2 .note { color: var(--text-muted); font-size: var(--t-sm); max-width: 78ch; }
.kn2 .recent { background: var(--card); border-left: 4px solid var(--gold); border-radius: var(--r-sm); padding: 10px 14px; font-size: var(--t-sm); }
.kn2 .hero { background: var(--ink); color: var(--on-ink); border-radius: var(--r); padding: var(--s5);
  display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.5fr); gap: var(--s5); align-items: end; }
.kn2 .hero .h2 { font-size: var(--t-2xl); font-weight: 700; margin-top: 6px; }
.kn2 .hero .meta { color: var(--on-ink-muted); font-size: var(--t-sm); margin-top: 6px; }
.kn2 .hero .three { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--s5); }
.kn2 .hero .hs .l { font-size: var(--t-xs); color: var(--on-ink-muted); text-transform: uppercase; letter-spacing: .06em; min-height: 2.6em; }
.kn2 .hero .hs .v { font: 700 var(--t-3xl)/1 var(--font-heading); margin: 2px 0 10px; }
.kn2 .hero .bar { background: #3A3F3C; } .kn2 .hero .bar i { background: var(--accent-bright); }
.kn2 .hero .hs .rk { display: block; margin-top: 6px; font-size: var(--t-sm); color: var(--on-ink-muted); }
.kn2 .hero .hs .rk b { color: var(--on-ink); font-weight: 500; }
.kn2 .panel { background: var(--card); border-radius: var(--r); padding: var(--s4) var(--s5); min-width: 0; }
.kn2 .panel > h3 { font-size: var(--t-lg); margin-bottom: var(--s1); }
.kn2 .cols3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr)); gap: var(--s4); align-items: start; }
.kn2 .cols2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr)); gap: var(--s4); align-items: start; }
.kn2 .cols3 > *, .kn2 .cols2 > * { min-width: 0; }
.kn2 .cols3.even { align-items: stretch; }
.kn2 .stack-v { display: grid; gap: var(--s4); }
.kn2 .brief h3 { display: flex; align-items: center; gap: var(--s2); font-size: var(--t-lg); }
.kn2 .brief h3::before { content: ""; width: 10px; height: 10px; border-radius: 50%; background: var(--neutral); flex: none; }
.kn2 .brief.stop h3::before { background: var(--bad); } .kn2 .brief.allow h3::before { background: var(--good); }
.kn2 .brief .sub { font-size: var(--t-xs); color: var(--text-subtle); margin: 2px 0 var(--s2); }
.kn2 .it { padding: var(--s3) 0; border-top: 1px solid var(--line); display: grid; gap: var(--s2); }
.kn2 .it .h { display: flex; justify-content: space-between; align-items: baseline; gap: var(--s3); }
.kn2 .it .h span { font-weight: 500; }
.kn2 .it .h b { font: 700 var(--t-xl)/1 var(--font-heading); white-space: nowrap; }
.kn2 .rr { display: grid; grid-template-columns: 1fr 3.2em; gap: var(--s2); align-items: center; }
.kn2 .rr .rk { font: 600 var(--t-sm) var(--font-heading); text-align: right; color: var(--text-muted); }
.kn2 .duel { display: grid; grid-template-columns: minmax(4.5em, auto) 3.6em 1fr 3.2em; gap: 6px var(--s2); align-items: center; font-size: var(--t-sm); }
.kn2 .duel .who-l { color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kn2 .duel b { font: 700 var(--t-md) var(--font-heading); text-align: right; }
.kn2 .duel .rk { font: 600 var(--t-sm) var(--font-heading); text-align: right; color: var(--text-muted); }
.kn2 .it .t { font-weight: 500; }
.kn2 .panel > .it:first-child, .kn2 .panel > h3 + .it, .kn2 .panel > .sub + .it { border-top: 0; }
.kn2 .stop-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 2.4fr); gap: var(--s5); padding: var(--s4) 0; border-top: 1px solid var(--line); align-items: center; }
.kn2 .stop-row:first-of-type { border-top: 0; }
.kn2 .stop-row .a h3 { font-size: var(--t-md); font-weight: 600; }
.kn2 .stop-row .a .v { font: 700 var(--t-xl)/1.1 var(--font-heading); margin: 2px 0 6px; display: block; }
.kn2 .stop-row .a .rr { max-width: 220px; }
.kn2 .stop-row .d .eyebrow { margin-bottom: 6px; }
.kn2 .whos { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--s2); }
.kn2 .who { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: var(--s2); align-items: center; padding: 8px 10px; border-radius: 8px; background: var(--paper); }
.kn2 .who.good { background: var(--good-bg); } .kn2 .who.bad { background: var(--bad-bg); }
.kn2 .who .nm { font-size: var(--t-sm); font-weight: 500; line-height: 1.2; overflow-wrap: anywhere; }
.kn2 .who .nm small { display: block; font-weight: 400; color: var(--text-muted); font-size: var(--t-xs); }
.kn2 .who b { font: 700 var(--t-lg) var(--font-heading); }
.kn2 .who.good b { color: var(--good); } .kn2 .who.bad b { color: var(--bad); }
.kn2 .people { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 290px), 1fr)); gap: var(--s3); }
.kn2 .pc { background: var(--card); border-radius: var(--r); padding: var(--s4); display: grid; gap: var(--s3); align-content: start; min-width: 0; }
.kn2 .pc .id { display: flex; gap: var(--s3); align-items: center; min-width: 0; }
.kn2 .pc .id h3, .kn2 .pc > h3 { font-size: var(--t-lg); margin-bottom: 5px; }
.kn2 .pc .none { font-size: var(--t-xs); color: var(--text-subtle); }
.kn2 .big4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--s2); text-align: center; }
.kn2 .big4 b { display: block; font: 700 var(--t-lg) var(--font-heading); }
.kn2 .big4 span { font-size: var(--t-xs); color: var(--text-subtle); }
.kn2 .split { display: grid; gap: 3px; }
.kn2 .split .lab { display: flex; justify-content: space-between; font-size: var(--t-xs); color: var(--text-muted); }
.kn2 .seg { display: flex; gap: 2px; height: 10px; }
.kn2 .seg i { display: block; height: 100%; border-radius: 2px; min-width: 2px; }
.kn2 .c-rim, .kn2 .c-left { background: var(--ink); } .kn2 .c-mid, .kn2 .c-right { background: #B9BEBA; } .kn2 .c-three { background: var(--accent); }
.kn2 .scroll { overflow-x: auto; }
.kn2 table { width: 100%; border-collapse: collapse; font-size: var(--t-sm); margin: 0; border: 0; background: none; }
.kn2 th { font: 600 var(--t-xs) var(--font-heading); color: var(--text-subtle); text-align: right; padding: 6px 8px; text-transform: uppercase;
  letter-spacing: .05em; border: 0; border-bottom: 1px solid var(--line); vertical-align: bottom; background: none; }
.kn2 td { padding: 9px 8px; text-align: right; border: 0; border-bottom: 1px solid var(--line); font-variant-numeric: tabular-nums; white-space: nowrap; background: none; }
.kn2 th:first-child, .kn2 td:first-child { text-align: left; padding-left: 0; }
.kn2 th:last-child, .kn2 td:last-child { padding-right: 0; }
.kn2 tr:last-child td { border-bottom: 0; }
.kn2 td.p { font-weight: 500; font-size: var(--t-md); }
.kn2 td .of { color: var(--text-subtle); font-size: var(--t-xs); margin-left: 6px; }
.kn2 .val { display: inline-block; min-width: 3.1em; text-align: center; font-weight: 700; font-size: var(--t-md); padding: 2px 6px; border-radius: var(--r-sm); }
.kn2 .val.good { background: var(--good-bg); color: var(--good); } .kn2 .val.bad { background: var(--bad-bg); color: var(--bad); }
.kn2 .mt { display: inline-grid; grid-template-columns: minmax(70px, 150px) auto; gap: var(--s2); align-items: center; }
.kn2 .mbar { position: relative; display: block; height: 10px; background: var(--track); border-radius: 3px; }
.kn2 .mbar i { display: block; height: 100%; border-radius: 3px; background: var(--neutral); }
.kn2 .key { display: flex; gap: var(--s4); flex-wrap: wrap; font-size: var(--t-xs); color: var(--text-muted); margin-top: var(--s3); }
.kn2 .key i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }
.kn2 .k-hi { background: #F5C2C5; } .kn2 .k-lo { background: #BDE6C8; } .kn2 .k-mid { background: #E6E8E5; } .kn2 .k-low { background: #F4F5F3; border: 1px solid var(--line); }
.kn2 .cov { padding: var(--s3) 0; border-top: 1px solid var(--line); display: grid; gap: 6px; }
.kn2 .cov:first-of-type { border-top: 0; }
.kn2 .cov .h { display: flex; justify-content: space-between; align-items: baseline; gap: var(--s2); font-weight: 600; }
.kn2 .cov .h span { font-weight: 400; font-size: var(--t-xs); color: var(--text-subtle); }
.kn2 .cov .l { display: grid; grid-template-columns: minmax(6em, 12em) 1fr 3em 4.2em; gap: var(--s2); align-items: center; font-size: var(--t-sm); }
.kn2 .cov .l .who-l { color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kn2 .cov .l .s { text-align: right; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.kn2 .cov .bar { height: 10px; border-radius: 3px; } .kn2 .cov .bar i { border-radius: 3px; }
.kn2 svg.zones { width: 100%; height: auto; display: block; max-width: 460px; margin: var(--s2) auto 0; }
.kn2 svg.zones .z { stroke: var(--paper); stroke-width: 2; }
.kn2 svg.zones .arc { fill: none; stroke: var(--paper); stroke-width: 4; }
.kn2 svg.zones .z.bad { fill: #F5C2C5; } .kn2 svg.zones .z.good { fill: #BDE6C8; }
.kn2 svg.zones .z.mid { fill: #E6E8E5; } .kn2 svg.zones .z.low { fill: #F4F5F3; }
.kn2 svg.zones text { text-anchor: middle; font-family: var(--font-heading); fill: var(--ink); }
.kn2 svg.zones .fg { font-size: 17px; font-weight: 700; } .kn2 svg.zones .sh { font-size: 11.5px; fill: var(--text-muted); font-family: var(--font-body); }
.kn2 svg.zones .cap { font-size: 10.5px; fill: var(--text-subtle); font-family: var(--font-body); }
.kn2 .hand { display: inline-grid; grid-template-columns: 2.6em 110px 2.6em; gap: 6px; align-items: center; }
.kn2 details.fold { background: var(--card); border-radius: var(--r); border: 0; margin: 0; }
.kn2 details.fold > summary { cursor: pointer; list-style: none; font: 600 var(--t-lg) var(--font-heading); padding: var(--s4) var(--s5); min-height: 56px;
  display: flex; justify-content: space-between; align-items: center; gap: var(--s3); border-radius: var(--r); background: none; color: var(--text); }
.kn2 details.fold > summary::-webkit-details-marker { display: none; }
.kn2 details.fold > summary::after { content: "+"; font: 500 1.4rem/1 var(--font-heading); color: var(--text-subtle); }
.kn2 details.fold[open] > summary::after { content: "\2212"; }
.kn2 details.fold > .in { padding: 0 var(--s5) var(--s5); display: grid; gap: var(--s5); }
.kn2 details.fold .panel { background: var(--paper); }
.kn2 details.fold .who { background: var(--card); }
.kn2 .folds { display: grid; gap: var(--s2); }
.kn2 .readcare { padding-top: var(--s5); border-top: 1px solid var(--line); font-size: var(--t-sm); color: var(--text-muted); }
.kn2 .readcare .h2 { font-size: var(--t-lg); color: var(--text); margin-bottom: var(--s2); }
.kn2 .readcare li { margin: 0 0 5px 18px; max-width: 100ch; }
@media (max-width: 760px) {
  .kn2 { padding: var(--s2); }
  .kn2 .hero { grid-template-columns: 1fr; padding: var(--s4); } .kn2 .hero .h2 { font-size: var(--t-xl); }
  .kn2 .hero .three { gap: var(--s3); } .kn2 .hero .hs .v { font-size: var(--t-xl); } .kn2 .hero .hs .l { min-height: 4em; }
  .kn2 .panel { padding: var(--s4); } .kn2 details.fold > summary { padding: var(--s4); } .kn2 details.fold > .in { padding: 0 var(--s4) var(--s4); }
  .kn2 .stop-row { grid-template-columns: 1fr; gap: var(--s3); } .kn2 .whos { grid-template-columns: 1fr; }
  .kn2 .cov .l { grid-template-columns: minmax(5em, 7em) 1fr 2.6em 3.8em; }
}
@media print {
  .kn2 * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .kn2 .scopes { display: none; }
  .kn2 section.tab[data-scope="season"] { display: grid !important; }
  .kn2 section.tab[data-scope="last"] { display: none !important; }
  .kn2 details.fold > .in { display: grid !important; }
  .kn2 .pc, .kn2 .panel, .kn2 .stop-row { break-inside: avoid; }
}
"""

# switch between the two scopes; written without equality operators because the site turns "==text==" into highlights
JS = r"""
(function () {
  var root = document.currentScript ? document.currentScript.parentNode : document;
  function show(scope) {
    root.querySelectorAll('section.tab').forEach(function (s) { s.classList.toggle('on', s.getAttribute('data-scope').indexOf(scope) > -1); });
    root.querySelectorAll('.scopes button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-scope').indexOf(scope) > -1)); });
  }
  root.querySelectorAll('.scopes button').forEach(function (b) { b.addEventListener('click', function () { show(b.getAttribute('data-scope')); }); });
})();
"""
