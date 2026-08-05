#!/usr/bin/env python3
"""Recompute per-LGA counts for EVERY NSW LGA (not just the top 12) so the LGA
panel can be normalised instead of ranking raw counts.

Also emits severity rates by urbanisation class and by road-feature type, which the
original extract did not compute.

Writes lga_extra.json. Deliberately does NOT touch bus_nsw.json, so published
figures in the rest of the report cannot drift. Reconciles its own totals
against bus_nsw.json and fails loudly if they disagree."""
import pandas as pd, json, sys, os

UP = '/mnt/user-data/uploads/'
COMPASS = UP + 'compass/'
CCA = UP + 'Car Crash Analysis/'
BASE = os.path.dirname(os.path.abspath(__file__)) + '/bus_nsw.json'
import os
OUT = os.path.dirname(os.path.abspath(__file__)) + '/lga_extra.json'
ENG = 'calamine'

cols = ['Crash ID', 'Year of crash', 'LGA', 'Urbanisation', 'Type of location',
        'No. killed', 'No. seriously injured']

print('reading 2020-24 crash...', flush=True)
new = pd.read_excel(COMPASS + 'nsw_road_crash_data_2020-2024_crash.xlsx', usecols=cols, engine=ENG)
print('reading 2016-20 crash...', flush=True)
old = pd.read_excel(COMPASS + 'nsw_road_crash_data_2016-2020.xlsx', usecols=cols, engine=ENG)
old = old[(old['Year of crash'] >= 2016) & (old['Year of crash'] < 2020)]
print('reading traffic units...', flush=True)
tu = pd.concat([
    pd.read_excel(CCA + 'nsw_road_crash_data_2016-2020_traffic_unit.xlsx',
                  usecols=['Crash ID', 'Traffic unit ID', 'TU type group'], engine=ENG),
    pd.read_excel(CCA + 'nsw_road_crash_data_2020-2024_traffic_unit.xlsx',
                  usecols=['Crash ID', 'Traffic unit ID', 'TU type group'], engine=ENG)])

d = pd.concat([old, new]).drop_duplicates('Crash ID')
d['severe'] = ((d['No. killed'] > 0) | (d['No. seriously injured'] > 0)).astype(int)
d['LGA'] = d['LGA'].fillna('Unknown').astype(str).str.strip()

bus_ids = set(tu[(tu['TU type group'] == 'Bus') & (tu['Crash ID'].isin(set(d['Crash ID'])))]['Crash ID'])
bus = d[d['Crash ID'].isin(bus_ids)].copy()

# ---- reconcile against the published extract before doing anything else ----
base = json.load(open(BASE))
errs = []
if len(d) != base['all_n']:
    errs.append(f"all crashes {len(d)} != published {base['all_n']}")
if len(bus) != base['n']:
    errs.append(f"bus crashes {len(bus)} != published {base['n']}")
for k, v in base['lga'].items():
    got = int((bus['LGA'] == k).sum())
    if got != v:
        errs.append(f"LGA {k}: {got} != published {v}")
if errs:
    print('RECONCILIATION FAILED:', *errs, sep='\n  ')
    sys.exit(1)
print(f'reconciled OK: {len(d)} all crashes, {len(bus)} bus-involved', flush=True)

bus_by = bus.groupby('LGA').agg(bus_n=('Crash ID', 'size'), bus_sev=('severe', 'sum'))
all_by = d.groupby('LGA').agg(all_n=('Crash ID', 'size'))
m = bus_by.join(all_by, how='left').reset_index()
m['share'] = (1000 * m['bus_n'] / m['all_n']).round(1)   # bus crashes per 1,000 crashes
m = m[m['LGA'] != 'Unknown']

state_rate = round(1000 * len(bus) / len(d), 1)

MIN_N = 25   # below this the rate is too unstable to rank on
rank = m[m['bus_n'] >= MIN_N].sort_values('share', ascending=False)

# severity rate by urbanisation class and by road feature, bus-involved crashes only
def sev_rate(col, order=None, min_n=40):
    g = bus.groupby(bus[col].fillna('Unknown').astype(str))['severe'].agg(['count', 'sum'])
    g = g[(g['count'] >= min_n) & (g.index != 'Unknown')]
    g['pct'] = (100 * g['sum'] / g['count']).round(1)
    g = g.sort_values('pct', ascending=False)
    return [dict(label=k, n=int(r['count']), sev=int(r['sum']), pct=float(r['pct']))
            for k, r in g.iterrows()]

URB_SHORT = {'Sydney metro. area': 'Sydney metro', 'Newcastle met. area': 'Newcastle metro',
             'Wollongong met. area': 'Wollongong metro', 'Country urban': 'Country urban',
             'Country non-urban': 'Country non-urban'}
urb_sev = sev_rate('Urbanisation')
for r in urb_sev:
    r['label'] = URB_SHORT.get(r['label'], r['label'])
loc_sev = sev_rate('Type of location')

out = dict(
    state_rate=state_rate,
    urb_sev=urb_sev,
    loc_sev=loc_sev,
    bus_sev_pct=round(100 * bus['severe'].mean(), 1),
    min_n=MIN_N,
    n_lga_total=int(len(m)),
    n_lga_ranked=int(len(rank)),
    # normalised ranking, highest bus share of local crashes first
    rank=[dict(lga=r.LGA, bus=int(r.bus_n), all=int(r.all_n), share=float(r.share),
               sev=int(r.bus_sev)) for r in rank.head(15).itertuples()],
    # raw-count leaders, kept so the two views can sit side by side
    count=[dict(lga=r.LGA, bus=int(r.bus_n), all=int(r.all_n), share=float(r.share))
           for r in m.sort_values('bus_n', ascending=False).head(12).itertuples()],
)
json.dump(out, open(OUT, 'w'), indent=1)
print('written', OUT)
print(json.dumps(out, indent=1)[:2600])
