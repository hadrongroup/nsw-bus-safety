#!/usr/bin/env python3
"""Build the NSW bus-involved crash report (Hadron 2026 brand).

Inputs:  bus_nsw.json   (from extract_bus_nsw.py)
         lga_extra.json (from extract_lga.py - all-LGA counts for normalisation)
Output:  index.html     (for GitHub Pages)

2026-08-05 revision: prose rewritten plainer, indexed-trend chart removed, LGA chart
normalised by each LGA's own crash total, urbanisation chart replaced with road feature,
source line kept to the top and footer only, and an "Explore map" full-screen view added
(scroll-wheel zoom is enabled only there, so the inline map never hijacks page scroll).
"""
import json, base64, os

HERE = os.path.dirname(os.path.abspath(__file__)) + '/'
DATA = HERE
OUT = os.path.abspath(HERE + '../index.html')
# Hadron wordmark, embedded base64 into the page. Point this at the copy in the
# hadron-slides skill assets folder on whichever machine you are building from.
LOGO = os.environ.get('HADRON_LOGO', '/root/.claude/skills/hadron-slides/assets/hadron_logo.png')

d = json.load(open(DATA + 'bus_nsw.json'))
L = json.load(open(DATA + 'lga_extra.json'))
logo64 = base64.b64encode(open(LOGO, 'rb').read()).decode()

# ---- inline Chart.js + Leaflet so the page is a single self-contained file ----
# A relative <script src> breaks the moment someone saves just the .html on its own, and a
# CDN breaks on networks that block third-party script hosts. Inlining survives both. Only
# the basemap tiles still need internet.
VEND = os.path.abspath(HERE + '../vendor') + '/'
chart_js = open(VEND + 'chart.umd.js').read()
leaflet_js = open(VEND + 'leaflet.js').read()
leaflet_css = open(VEND + 'leaflet.css').read()
for img in sorted(os.listdir(VEND + 'images')):
    b64 = base64.b64encode(open(VEND + 'images/' + img, 'rb').read()).decode()
    leaflet_css = leaflet_css.replace('images/' + img, f'data:image/png;base64,{b64}')
for _name, _blob in (('chart.umd.js', chart_js), ('leaflet.js', leaflet_js)):
    if '</script' in _blob.lower():
        raise SystemExit(f'{_name} contains a closing script tag; cannot inline as-is')

YEARS = [str(y) for y in range(2016, 2025)]
fmt = lambda n: f'{n:,}'

# ---- derived narrative numbers ----
syd = d['urb'].get('Sydney metro. area', 0)
reg = d['urb'].get('Country urban', 0) + d['urb'].get('Country non-urban', 0)
syd_pct = round(100 * syd / d['n'])
reg_pct = round(100 * reg / d['n'])
all_syd_pct = round(100 * d['urb_all'].get('Sydney metro. area', 0) / d['all_n'])
y16, y21, y24 = d['years']['2016'], d['years']['2021'], d['years']['2024']
drop_pct = round(100 * (1 - y21 / y16))
reb_pct = round(100 * (y24 / y21 - 1))
all_reb = round(100 * (d['all_years']['2024'] / d['all_years']['2021'] - 1))
wk = sum(d['dow'][k] for k in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])
wk_pct = round(100 * wk / d['n'])
sch_pct = round(100 * d['school'].get('Yes', 0) / d['n'], 1)
ped_n = d['rum_sev']['Ped nearside'][0] + d['rum_sev']['Ped far side'][0]
ped_s = d['rum_sev']['Ped nearside'][1] + d['rum_sev']['Ped far side'][1]
ped_sev_pct = round(100 * ped_s / ped_n)
re_n, re_s = d['rum_sev']['Rear end']
re_pct = round(100 * re_s / re_n)
fell = d['rum'].get('Fell in/from vehicle', 0)
sev_pct_v, all_sev_v = d['sev_pct'], d['all_sev_pct']

# rum severity chart, sorted by % severe
rum_sev_sorted = sorted(((k, v[0], v[1]) for k, v in d['rum_sev'].items()), key=lambda t: -t[2] / t[1])
rs_labels = [k for k, n, s in rum_sev_sorted]
rs_pct = [round(100 * s / n, 1) for k, n, s in rum_sev_sorted]
rs_n = [n for k, n, s in rum_sev_sorted]
rs_colors = ['#F6A75D' if k.startswith('Ped') else '#1E3A5C' for k in rs_labels]

# normalised LGA panel
lga_rank = L['rank'][:12]
lga_lab = [r['lga'] for r in lga_rank]
lga_rate = [r['share'] for r in lga_rank]
lga_bus = [r['bus'] for r in lga_rank]
lga_all = [r['all'] for r in lga_rank]
top_lga, top_rate = lga_rank[0]['lga'], lga_rank[0]['share']
syd_lga = next((r for r in lga_rank if r['lga'] == 'Sydney'), None)

hrs_lab = list(d['hrs'].keys()); hrs_val = list(d['hrs'].values())
dow_lab = list(d['dow'].keys()); dow_val = list(d['dow'].values())
dow_col = ['#5999DF'] * 5 + ['#C9D2DC'] * 2

speed_lab = [k for k in ['40 km/h', '50 km/h', '60 km/h', '70 km/h', '80 km/h', '90 km/h', '100 km/h', '110 km/h']
             if k in d['speed_sev']]
speed_pct = [round(100 * d['speed_sev'][k][1] / d['speed_sev'][k][0], 1) for k in speed_lab]
speed_n = [d['speed_sev'][k][0] for k in speed_lab]

rumf = dict(list(d['rum'].items())[:10])
otu = d['other_tu']; man = dict(list(d['manoeuvre'].items())[:8])

CH = json.dumps(dict(
    years=YEARS, yr=[d['years'][y] for y in YEARS], sev=[d['sev_years'][y] for y in YEARS],
    lga_lab=lga_lab, lga_rate=lga_rate, lga_bus=lga_bus, lga_all=lga_all, state_rate=L['state_rate'],
    rumf_lab=list(rumf.keys()), rumf_val=list(rumf.values()),
    rs_labels=rs_labels, rs_pct=rs_pct, rs_n=rs_n, rs_colors=rs_colors,
    otu_lab=list(otu.keys()), otu_val=list(otu.values()),
    man_lab=list(man.keys()), man_val=list(man.values()),
    hrs_lab=hrs_lab, hrs_val=hrs_val, dow_lab=dow_lab, dow_val=dow_val, dow_col=dow_col,
    deg_lab=['Fatal', 'Serious injury', 'Other injury', 'Non-casualty (towaway)'],
    deg_val=[d['fatal_crashes'], d['severe'] - d['fatal_crashes'],
             d['degree'].get('Injury', 0) - (d['severe'] - d['fatal_crashes']),
             d['degree'].get('Non-casualty (towaway)', 0)],
    speed_lab=speed_lab, speed_pct=speed_pct, speed_n=speed_n,
    pts=d['pts'], clusters=d['clusters'],
))

DATASET_URL = 'https://opendata.transport.nsw.gov.au/data/dataset/nsw-crash-data'
# Absolute, because Open Graph crawlers do not resolve relative image paths.
SITE_URL = 'https://hadrongroup.github.io/nsw-bus-safety/'
OG_TITLE = 'Bus-involved crashes in NSW, 2016-2024'
OG_DESC = ('Spatial analysis of ' + fmt(d['n']) + ' police-reported bus-involved crashes across NSW, '
           'from Transport for NSW open crash data. Hadron Group.')


def callout(text):
    return f'<div class="callout">{text}</div>'


def section(kicker, title, body):
    return f'<section><div class="kicker">{kicker}</div><h2>{title}</h2><div class="rule"></div>{body}</section>'


cluster_rows = ''.join(
    f"<tr><td class='rk'>{i+1}</td><td>{c['street'].title()} · {c['town'].title()}</td><td>{c['lga']}</td>"
    f"<td class='num'>{c['n']}</td><td class='num'>{c['sev']}</td><td class='num'>{c['fat'] or ''}</td>"
    f"<td>{', '.join(c['rum'])}</td></tr>"
    for i, c in enumerate(d['clusters']))

html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bus-involved crashes in NSW 2016–2024 · Hadron Group</title>
<meta name="description" content="{OG_DESC}">
<link rel="canonical" href="{SITE_URL}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Hadron Group">
<meta property="og:url" content="{SITE_URL}">
<meta property="og:title" content="{OG_TITLE}">
<meta property="og:description" content="{OG_DESC}">
<meta property="og:image" content="{SITE_URL}preview.png">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Map of bus-involved crash locations across the Sydney basin, with headline counts.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{OG_TITLE}">
<meta name="twitter:description" content="{OG_DESC}">
<meta name="twitter:image" content="{SITE_URL}preview.png">
<script>{chart_js}</script>
<script>{leaflet_js}</script>
<style>{leaflet_css}</style>
<style>
:root{{--blue:#5999DF;--navy:#1E3A5C;--ink:#3A3A3A;--lblue:#9FC3EC;--grey:#C9D2DC;--grid:#DDE3EA;
--axis:#6E6E6E;--srcc:#9AA4AF;--fill:#DFE9F3;--ochre:#F6A75D}}
*{{box-sizing:border-box}}
html,body{{overflow-x:hidden}}
body{{margin:0;background:#fff;color:var(--ink);font:14px/1.55 Arial,Helvetica,sans-serif}}
.wrap{{max-width:1080px;margin:0 auto;padding:36px 28px 60px}}
h1,h2{{font-family:"Aptos Display","Segoe UI",Arial,sans-serif;color:var(--ink);font-weight:700;margin:0}}
h1{{font-size:34px;line-height:1.15;max-width:800px}}
h2{{font-size:22px;line-height:1.25;max-width:820px}}
.kicker{{font-size:11px;font-weight:bold;letter-spacing:.14em;text-transform:uppercase;color:var(--blue);margin-bottom:6px}}
.rule{{height:1px;background:var(--grid);margin:14px 0 20px}}
header{{position:relative;margin-bottom:8px}}
header img{{position:absolute;top:0;right:0;width:150px}}
.sub{{color:var(--axis);font-size:14px;margin-top:10px;max-width:760px}}
.sub a{{color:var(--blue);text-decoration:none;border-bottom:1px solid var(--lblue)}}
.sub a:hover{{color:var(--navy);border-bottom-color:var(--navy)}}
.tiles{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:26px 0 6px}}
.tile{{border:1px solid var(--grid);border-top:3px solid var(--blue);padding:12px 14px;border-radius:2px}}
.tile .v{{font-family:"Aptos Display","Segoe UI",Arial;font-size:26px;font-weight:700;color:var(--navy)}}
.tile .l{{font-size:11px;color:var(--axis);margin-top:2px;line-height:1.35}}
section{{margin-top:44px}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:26px}}
.cbox{{position:relative}}
.cbox h4{{font-size:11px;font-weight:bold;letter-spacing:.06em;text-transform:uppercase;color:var(--axis);margin:0 0 8px}}
.cbox .csub{{font-size:11px;color:var(--srcc);margin:-4px 0 8px}}
.ch{{position:relative;height:250px}}
.ch canvas{{max-height:100%}}
.ch.tall{{height:320px}}
.ch.xtall{{height:400px}}
.callout{{background:var(--fill);border-radius:2px;padding:15px 17px;margin:20px 0 4px;max-width:880px;
color:var(--navy);font-size:13.5px}}
/* The inline map sits in the text column; "Explore map" is the route to a big view.
   NB: never wrap #mapshell in an element with a CSS transform - a transform on an ancestor
   becomes the containing block for position:fixed, which collapses the full-screen panel. */
#mapshell{{display:flex;flex-direction:column;background:#fff}}
#mapshell.fs{{position:fixed;inset:0;z-index:9999;padding:14px 18px 12px;margin:0}}
#mapshell.fs #map{{flex:1 1 auto;height:auto;min-height:0;margin-top:0}}
#maptools{{display:flex;align-items:center;gap:14px;margin:6px 0 8px;flex-wrap:wrap}}
.btn{{font:bold 11px/1 Arial,Helvetica,sans-serif;letter-spacing:.09em;text-transform:uppercase;color:#fff;
background:var(--navy);border:0;border-radius:2px;padding:10px 15px;cursor:pointer}}
.btn:hover{{background:#2C5480}}
.btn:focus-visible{{outline:2px solid var(--blue);outline-offset:2px}}
.hint{{font-size:11px;color:var(--srcc)}}
#map{{height:620px;border:1px solid var(--grid);border-radius:2px;margin-top:0}}
.maplegend{{font-size:12px;color:var(--axis);margin:10px 0 0;display:flex;gap:22px;flex-wrap:wrap;align-items:center}}
.maplegend label{{cursor:pointer;display:flex;align-items:center;gap:6px}}
.dot{{display:inline-block;width:11px;height:11px;border-radius:50%}}
table{{border-collapse:collapse;width:100%;margin-top:18px;font-size:12.5px}}
th{{text-align:left;font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--axis);
border-bottom:2px solid var(--navy);padding:7px 8px}}
td{{border-bottom:1px solid var(--grid);padding:7px 8px;vertical-align:top}}
td.num,th.num{{text-align:right}} td.rk{{color:var(--blue);font-weight:bold}}
.note{{font-size:12px;color:var(--axis);max-width:880px}}
footer{{margin-top:56px;border-top:1px solid var(--grid);padding-top:14px;font-size:11px;color:var(--srcc)}}
footer a{{color:var(--blue);text-decoration:none;border-bottom:1px solid var(--grid)}}
footer a:hover{{color:var(--navy)}}
p{{max-width:880px}}
@media(max-width:900px){{.tiles{{grid-template-columns:repeat(3,1fr)}}.grid2{{grid-template-columns:1fr}}
h1{{font-size:26px}} #map{{height:min(64vh,480px)}}
#mapshell.fs{{padding:10px 12px 10px}}}}
</style></head><body><div class="wrap">

<header>
<img src="data:image/png;base64,{logo64}" alt="Hadron Group">
<div class="kicker">Hadron Group · Transport Safety Analytics · August 2026</div>
<h1>Bus-involved crashes in NSW, 2016–2024</h1>
<div class="sub">{fmt(d['n'])} police-reported crashes involving a bus, taken from the
<a href="{DATASET_URL}" target="_blank" rel="noopener">Transport for NSW open crash data</a>.</div>
<div class="rule"></div>
</header>

<div class="tiles">
<div class="tile"><div class="v">{fmt(d['n'])}</div><div class="l">bus-involved crashes 2016–24</div></div>
<div class="tile"><div class="v">{d['killed']}</div><div class="l">people killed</div></div>
<div class="tile"><div class="v">{d['serious']}</div><div class="l">people seriously injured</div></div>
<div class="tile"><div class="v">{d['sev_pct']}%</div><div class="l">of crashes fatal or serious – vs {d['all_sev_pct']}% for all NSW crashes</div></div>
<div class="tile"><div class="v">{syd_pct}%</div><div class="l">in Sydney metro – vs {all_syd_pct}% of all crashes</div></div>
</div>

{section('1 · Trend', 'Crashes by year', f'''
<div class="cbox"><h4>Bus-involved crashes and fatal or serious crashes by year</h4>
<div class="ch tall"><canvas id="c_trend"></canvas></div></div>
{callout(f'Bus-involved crashes fell {drop_pct}% between 2016 and 2021, then rose {reb_pct}% by 2024.')}
''')}

{section('2 · Where', 'Where the crashes are', f'''
<p>Each point is one crash, coloured by severity. Numbered markers are the tightest repeat locations, defined
as three or more crashes falling within 40 m of each other.</p>
<div id="mapshell">
<div id="maptools">
<button id="mapfs" class="btn" type="button">Explore map</button>
<span class="hint" id="maphint">Opens full screen, where the scroll wheel zooms. Esc closes it.</span>
</div>
<div id="map"></div>
<div class="maplegend">
<label><input type="checkbox" id="cb2" checked><span class="dot" style="background:#F6A75D"></span>Fatal ({d['fatal_crashes']})</label>
<label><input type="checkbox" id="cb1" checked><span class="dot" style="background:#1E3A5C"></span>Serious injury ({d['severe'] - d['fatal_crashes']})</label>
<label><input type="checkbox" id="cb0" checked><span class="dot" style="background:#9FC3EC"></span>Other ({d['n'] - d['severe']})</label>
</div>
</div>
<h4 style="font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--axis);margin:26px 0 0">Repeat locations (three or more crashes within 40 m)</h4>
<table><thead><tr><th>#</th><th>Street · town</th><th>LGA</th><th class="num">Crashes</th><th class="num">Severe</th><th class="num">Fatal</th><th>Dominant crash types</th></tr></thead>
<tbody>{cluster_rows}</tbody></table>
{callout('The repeat locations fall into two groups: cross-traffic conflicts at suburban intersections in Fairfield, Parramatta and The Hills, and pedestrian impacts on Sydney CBD streets.')}
''')}

{section('3 · Geography', 'Where bus crashes are concentrated', f'''
<div class="cbox"><h4>Bus involvement per 1,000 crashes, by LGA</h4>
<div class="csub">LGAs with at least {L['min_n']} bus-involved crashes ({L['n_lga_ranked']} of {L['n_lga_total']}) · dashed line = NSW average of {L['state_rate']}</div>
<div class="ch xtall"><canvas id="c_lga"></canvas></div></div>
{callout(f'{syd_pct}% of bus-involved crashes are in the Sydney metropolitan area against {all_syd_pct}% of all crashes, which mostly reflects where bus services run. Normalising by the number of crashes in each LGA changes the ranking: buses are involved in {top_rate} crashes per 1,000 in {top_lga} and {syd_lga["share"] if syd_lga else "-"} per 1,000 in the City of Sydney, against {L["state_rate"]} statewide. The denominator here is each LGA&rsquo;s own crash total.')}
''')}

{section('4 · Crash types', 'Crash types and their outcomes', f'''
<div class="grid2">
<div class="cbox"><h4>Most frequent crash types (RUM)</h4><div class="ch"><canvas id="c_rumf"></canvas></div></div>
<div class="cbox"><h4>% fatal or serious by crash type</h4>
<div class="csub">Crash types with at least 30 crashes</div>
<div class="ch xtall"><canvas id="c_rums"></canvas></div></div>
</div>
<div class="grid2" style="margin-top:22px">
<div class="cbox"><h4>What the bus collided with</h4><div class="ch"><canvas id="c_otu"></canvas></div></div>
<div class="cbox"><h4>Bus manoeuvre at time of crash</h4><div class="ch"><canvas id="c_man"></canvas></div></div>
</div>
{callout(f'Rear-end collisions are the most common crash type at {re_n} crashes, and {re_pct}% of them are fatal or serious. Pedestrian impacts run the other way: {ped_n} crashes, of which {ped_sev_pct}% are fatal or serious, making them the largest single source of severe outcomes. A further {fell} crashes were passengers falling in or from the bus, which is a vehicle and stop-design problem rather than a road one.')}
''')}

{section('5 · When', 'Crashes follow the timetable', f'''
<div class="grid2">
<div class="cbox"><h4>Crashes by time of day (two-hour intervals)</h4><div class="ch"><canvas id="c_hrs"></canvas></div></div>
<div class="cbox"><h4>Crashes by day of week</h4><div class="ch"><canvas id="c_dow"></canvas></div></div>
</div>
{callout(f'{wk_pct}% of crashes are on weekdays, peaking between 8 and 10 am and between 2 and 6 pm. {sch_pct}% are in an active school zone. This is the shape of exposure rather than risk: those are the hours with the most services running and the most people boarding. Any comparison between routes or between times of day needs service-kilometres in the denominator.')}
''')}

{section('6 · Severity', 'How severe these crashes are', f'''
<div class="grid2">
<div class="cbox"><h4>Crash severity</h4>
<div class="csub">Fatal and serious together = {sev_pct_v}% of bus-involved crashes</div>
<div class="ch"><canvas id="c_deg"></canvas></div></div>
<div class="cbox"><h4>% fatal or serious by speed zone</h4><div class="ch"><canvas id="c_spd"></canvas></div></div>
</div>
{callout(f'{sev_pct_v}% of bus-involved crashes are fatal or serious, against {all_sev_v}% for all NSW crashes. Severity rises with the speed zone, from 22% at 50 km/h to between 33% and 37% in the 80–110 km/h zones.')}
''')}

<footer>
Prepared by Hadron Group · August 2026 · Source: <a href="{DATASET_URL}">Transport for NSW road crash data</a>,
published on the <a href="https://opendata.transport.nsw.gov.au/">NSW Open Data portal</a> · Method: releases 2016–2020 and 2020–2024 merged and
deduplicated on Crash ID ({fmt(d['all_n'])} crashes); bus involvement flagged where any traffic unit in the crash has
TU type group = Bus ({fmt(d['nunits'])} bus units in {fmt(d['n'])} crashes). Severe = at least one person killed or
seriously injured. Crash data are police-reported, so minor incidents and on-board injuries without a collision
are likely to be under-represented. 'Bus' follows the Transport for NSW definition and includes all bus types.
Section 3 rates use each LGA's total crash count as the denominator; LGAs with fewer than {L['min_n']} bus-involved
crashes are excluded because the rate is unstable at low counts.
</footer>
</div>

<script>
const D = {CH};
Chart.defaults.font.family = 'Arial, Helvetica, sans-serif';
Chart.defaults.font.size = 11;
Chart.defaults.color = '#6E6E6E';
const GRID = {{color:'#DDE3EA'}}, NOGRID = {{display:false}};
const noleg = {{plugins:{{legend:{{display:false}}}}}};
function hbar(id, labels, vals, color, xtitle) {{
  new Chart(document.getElementById(id), {{type:'bar',
    data:{{labels:labels, datasets:[{{data:vals, backgroundColor:color, borderRadius:2, barPercentage:.75}}]}},
    options:{{indexAxis:'y', maintainAspectRatio:false, ...noleg,
      scales:{{x:{{beginAtZero:true, grid:GRID, title:xtitle?{{display:true,text:xtitle,font:{{size:10}}}}:undefined}},
              y:{{grid:NOGRID}}}}}}}});
}}
new Chart(document.getElementById('c_trend'), {{type:'bar',
  data:{{labels:D.years, datasets:[
    {{type:'bar', label:'Crashes', data:D.yr, backgroundColor:'#5999DF', borderRadius:2, order:2}},
    {{type:'line', label:'Fatal or serious', data:D.sev, borderColor:'#1E3A5C', backgroundColor:'#1E3A5C',
      pointRadius:3, borderWidth:2, yAxisID:'y2', order:1}}]}},
  options:{{maintainAspectRatio:false, plugins:{{legend:{{position:'bottom', labels:{{boxWidth:10, font:{{size:10}}}}}}}},
    scales:{{y:{{beginAtZero:true, grid:GRID, title:{{display:true,text:'crashes',font:{{size:10}}}}}},
            y2:{{beginAtZero:true, position:'right', grid:{{display:false}},
                 title:{{display:true,text:'fatal or serious',font:{{size:10}}}}}},
            x:{{grid:NOGRID}}}}}}}});
// LGA panel: normalised by the LGA's own crash total, with the state rate as a marker line
const stateLine = {{
  id:'stateLine',
  afterDatasetsDraw(c) {{
    const x = c.scales.x.getPixelForValue(D.state_rate), a = c.chartArea, g = c.ctx;
    g.save(); g.setLineDash([4,3]); g.strokeStyle='#F6A75D'; g.lineWidth=1.6;
    g.beginPath(); g.moveTo(x, a.top); g.lineTo(x, a.bottom); g.stroke(); g.restore();
  }}
}};
new Chart(document.getElementById('c_lga'), {{type:'bar',
  data:{{labels:D.lga_lab, datasets:[{{data:D.lga_rate, backgroundColor:'#1E3A5C', borderRadius:2, barPercentage:.8}}]}},
  options:{{indexAxis:'y', maintainAspectRatio:false,
    plugins:{{legend:{{display:false}}, tooltip:{{callbacks:{{label:(c)=>
      c.parsed.x+' per 1,000 · '+D.lga_bus[c.dataIndex]+' bus of '+D.lga_all[c.dataIndex].toLocaleString()+' crashes'}}}}}},
    scales:{{x:{{beginAtZero:true, grid:GRID, title:{{display:true,text:'bus-involved crashes per 1,000 crashes',font:{{size:10}}}}}},
            y:{{grid:NOGRID, ticks:{{autoSkip:false, font:{{size:10}}}}}}}}}},
  plugins:[stateLine]}});
hbar('c_rumf', D.rumf_lab, D.rumf_val, '#5999DF', 'crashes');
new Chart(document.getElementById('c_rums'), {{type:'bar',
  data:{{labels:D.rs_labels, datasets:[{{data:D.rs_pct, backgroundColor:D.rs_colors, borderRadius:2, barPercentage:.75}}]}},
  options:{{indexAxis:'y', maintainAspectRatio:false, ...noleg,
    plugins:{{legend:{{display:false}}, tooltip:{{callbacks:{{label:(c)=>c.parsed.x+'% severe · n='+D.rs_n[c.dataIndex]}}}}}},
    scales:{{x:{{beginAtZero:true, grid:GRID, title:{{display:true,text:'% fatal or serious',font:{{size:10}}}}}},
            y:{{grid:NOGRID, ticks:{{autoSkip:false, font:{{size:10}}}}}}}}}}}});
hbar('c_otu', D.otu_lab, D.otu_val, '#5999DF', 'crashes');
hbar('c_man', D.man_lab, D.man_val, '#9FC3EC', 'bus traffic units');
new Chart(document.getElementById('c_hrs'), {{type:'bar',
  data:{{labels:D.hrs_lab.map(h=>h.replace(' - ','–')), datasets:[{{data:D.hrs_val, backgroundColor:'#5999DF', borderRadius:2}}]}},
  options:{{maintainAspectRatio:false, ...noleg, scales:{{y:{{beginAtZero:true, grid:GRID}},
    x:{{grid:NOGRID, ticks:{{font:{{size:8.5}}, maxRotation:60, minRotation:60}}}}}}}}}});
new Chart(document.getElementById('c_dow'), {{type:'bar',
  data:{{labels:D.dow_lab.map(s=>s.slice(0,3)), datasets:[{{data:D.dow_val, backgroundColor:D.dow_col, borderRadius:2}}]}},
  options:{{maintainAspectRatio:false, ...noleg, scales:{{y:{{beginAtZero:true, grid:GRID}}, x:{{grid:NOGRID}}}}}}}});
new Chart(document.getElementById('c_deg'), {{type:'doughnut',
  data:{{labels:D.deg_lab, datasets:[{{data:D.deg_val,
    backgroundColor:['#F6A75D','#1E3A5C','#5999DF','#C9D2DC'], borderColor:'#fff', borderWidth:2}}]}},
  options:{{maintainAspectRatio:false, cutout:'62%',
    plugins:{{legend:{{position:'bottom', labels:{{boxWidth:10, font:{{size:10}}}}}}}}}}}});
new Chart(document.getElementById('c_spd'), {{type:'bar',
  data:{{labels:D.speed_lab, datasets:[{{data:D.speed_pct, backgroundColor:'#1E3A5C', borderRadius:2}}]}},
  options:{{maintainAspectRatio:false, ...noleg,
    plugins:{{legend:{{display:false}}, tooltip:{{callbacks:{{label:(c)=>c.parsed.y+'% severe · n='+D.speed_n[c.dataIndex]}}}}}},
    scales:{{y:{{beginAtZero:true, grid:GRID, title:{{display:true,text:'% fatal or serious',font:{{size:10}}}}}}, x:{{grid:NOGRID}}}}}}}});

// ---- map ----
const map = L.map('map', {{preferCanvas:true, scrollWheelZoom:false}});
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png',
  {{attribution:'© OpenStreetMap · © CARTO', maxZoom:19}}).addTo(map);
const STYLE = [
  {{color:'#9FC3EC', r:3, op:.55}},   // other
  {{color:'#1E3A5C', r:4, op:.75}},   // serious
  {{color:'#F6A75D', r:5.5, op:.95}}  // fatal
];
const SEVNAME = ['Other (minor/moderate injury or tow-away)','Serious injury crash','Fatal crash'];
const groups = [L.layerGroup(), L.layerGroup(), L.layerGroup()];
D.pts.forEach(p => {{
  const s = STYLE[p[2]];
  groups[p[2]].addLayer(L.circleMarker([p[0], p[1]],
    {{radius:s.r, color:s.color, weight:p[2]===2?1.5:0.8, fillColor:s.color, fillOpacity:s.op, opacity:.9}})
    .bindPopup(SEVNAME[p[2]]));
}});
groups[0].addTo(map); groups[1].addTo(map); groups[2].addTo(map);
D.clusters.forEach((c, i) => {{
  L.marker([c.lat, c.lon], {{icon: L.divIcon({{className:'', iconSize:[24,24], iconAnchor:[12,12],
    html:`<div style="width:24px;height:24px;border-radius:50%;background:#1E3A5C;color:#fff;font:bold 11px/24px Arial;text-align:center;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.35)">${{i+1}}</div>`}})}})
    .bindPopup(`<b>#${{i+1}} ${{c.street}} · ${{c.town}}</b><br>${{c.n}} crashes · ${{c.sev}} severe · ${{c.fat}} fatal<br>${{c.rum.join(', ')}}`)
    .addTo(map);
}});
map.fitBounds(L.latLngBounds(D.pts.map(p=>[p[0],p[1]])).pad(0.05));
[0,1,2].forEach(i => document.getElementById('cb'+i).addEventListener('change', e =>
  e.target.checked ? groups[i].addTo(map) : map.removeLayer(groups[i])));
window.addEventListener('resize', () => map.invalidateSize());

// ---- full-screen map. Scroll-wheel zoom is only enabled in full screen, so that
// scrolling the page over the inline map does not hijack the reader's scroll. ----
const shell = document.getElementById('mapshell');
const fsbtn = document.getElementById('mapfs');
const fshint = document.getElementById('maphint');
let prevOverflow = '';
function setFullscreen(on) {{
  if (on === shell.classList.contains('fs')) return;
  shell.classList.toggle('fs', on);
  if (on) {{ prevOverflow = document.body.style.overflow; document.body.style.overflow = 'hidden'; }}
  else {{ document.body.style.overflow = prevOverflow; }}
  fsbtn.textContent = on ? 'Close map' : 'Explore map';
  fshint.textContent = on ? 'Scroll to zoom · drag to pan · Esc to close'
                          : 'Opens full screen, where the scroll wheel zooms. Esc closes it.';
  if (on) map.scrollWheelZoom.enable(); else map.scrollWheelZoom.disable();
  // Leaflet needs to be told the container changed size, after the layout settles
  requestAnimationFrame(() => {{ map.invalidateSize(); setTimeout(() => map.invalidateSize(), 120); }});
  if (!on) fsbtn.focus();
}}
fsbtn.addEventListener('click', () => setFullscreen(!shell.classList.contains('fs')));
document.addEventListener('keydown', e => {{ if (e.key === 'Escape') setFullscreen(false); }});
</script>
</body></html>"""

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, 'w').write(html)
print('written', OUT, len(html) // 1024, 'KB')
