#!/usr/bin/env python3
"""Build preview.png - the 1200x630 Open Graph card used for link previews.

Composed offline rather than screenshotting the live page, because the map basemap
needs network access and a sparse basemap-less screenshot looks broken. The crash
points themselves are drawn from bus_nsw.json, so the card is real data.

Run after build_bus_report.py:  python3 build_preview.py
Needs playwright (`pip install playwright`) with a chromium build available.
"""
import json, base64, os

HERE = os.path.dirname(os.path.abspath(__file__)) + '/'
OUT = os.path.abspath(HERE + '../preview.png')
CARD = '/tmp/preview_card.html'
LOGO = os.environ.get('HADRON_LOGO', '/root/.claude/skills/hadron-slides/assets/hadron_logo.png')

d = json.load(open(HERE + 'bus_nsw.json'))
logo64 = base64.b64encode(open(LOGO, 'rb').read()).decode()
fmt = lambda n: f'{n:,}'

# ---- point cloud, drawn as inline SVG on an equirectangular projection ----
# Clipped to the Sydney basin, where 72% of the crashes are: the all-NSW extent is
# mostly empty space at this size and the dense pattern is what reads as a map.
W, H = 660, 630
LAT0, LAT1 = -34.20, -33.55      # south, north
LON0, LON1 = 150.62, 151.35      # west, east
PAD = 26

pts = [p for p in d['pts'] if LAT0 <= p[0] <= LAT1 and LON0 <= p[1] <= LON1]
# draw least severe first so fatal sits on top
pts.sort(key=lambda p: p[2])

def project(lat, lon):
    x = PAD + (lon - LON0) / (LON1 - LON0) * (W - 2 * PAD)
    y = PAD + (LAT1 - lat) / (LAT1 - LAT0) * (H - 2 * PAD)
    return round(x, 1), round(y, 1)

STYLE = [('#9FC3EC', 2.6, .60), ('#1E3A5C', 3.2, .80), ('#F6A75D', 4.6, .95)]
circles = []
for lat, lon, sev in pts:
    x, y = project(lat, lon)
    col, r, op = STYLE[sev]
    circles.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}" fill-opacity="{op}"/>')
svg = f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">{"".join(circles)}</svg>'

html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1200px;height:630px;overflow:hidden;background:#fff;
font-family:Arial,Helvetica,sans-serif;color:#3A3A3A;display:flex}}
.left{{width:540px;padding:52px 40px 40px 56px;display:flex;flex-direction:column}}
.kicker{{font-size:13px;font-weight:bold;letter-spacing:.16em;text-transform:uppercase;color:#5999DF}}
h1{{font-family:"Aptos Display","Segoe UI",Arial,sans-serif;font-size:46px;line-height:1.1;
margin-top:16px;color:#1E3A5C;font-weight:700}}
.years{{font-size:19px;color:#6E6E6E;margin-top:14px}}
.stats{{display:grid;grid-template-columns:1fr 1fr;gap:22px 26px;margin-top:auto;margin-bottom:26px}}
.v{{font-family:"Aptos Display","Segoe UI",Arial,sans-serif;font-size:36px;font-weight:700;color:#1E3A5C;
line-height:1}}
.l{{font-size:13px;color:#6E6E6E;margin-top:5px;line-height:1.3}}
.stat{{border-top:3px solid #5999DF;padding-top:11px}}
.foot{{display:flex;align-items:center;justify-content:space-between}}
.foot img{{width:132px}}
.foot span{{font-size:12px;color:#9AA4AF}}
.right{{width:660px;position:relative;background:#F7FAFD;border-left:1px solid #DDE3EA}}
.tag{{position:absolute;left:26px;bottom:22px;font-size:12px;color:#9AA4AF}}
</style></head><body>
<div class="left">
  <div class="kicker">Hadron Group · Transport Safety Analytics</div>
  <h1>Bus-involved crashes in NSW</h1>
  <div class="years">2016–2024 · Transport for NSW open crash data</div>
  <div class="stats">
    <div class="stat"><div class="v">{fmt(d['n'])}</div><div class="l">bus-involved crashes</div></div>
    <div class="stat"><div class="v">{d['killed']}</div><div class="l">people killed</div></div>
    <div class="stat"><div class="v">{d['serious']}</div><div class="l">people seriously injured</div></div>
    <div class="stat"><div class="v">{d['sev_pct']}%</div><div class="l">fatal or serious</div></div>
  </div>
  <div class="foot"><img src="data:image/png;base64,{logo64}"><span>hadrongroup.github.io</span></div>
</div>
<div class="right">{svg}<div class="tag">Sydney basin · {fmt(len(pts))} of {fmt(d['n'])} crashes</div></div>
</body></html>"""

open(CARD, 'w').write(html)

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1200, 'height': 630})
    pg.goto('file://' + CARD)
    pg.wait_for_timeout(900)
    pg.screenshot(path=OUT)
    b.close()
print('written', OUT, os.path.getsize(OUT) // 1024, 'KB ·', len(pts), 'points drawn')
