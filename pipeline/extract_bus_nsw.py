#!/usr/bin/env python3
"""Extract NSW-wide bus-involved crashes 2016-2024 -> bus_nsw.json
Bus involvement via traffic-unit tables ('TU type group' == 'Bus')."""
import pandas as pd, json, math, sys

COMPASS = '/sessions/serene-ecstatic-einstein/mnt/compass/'
CCA = '/sessions/serene-ecstatic-einstein/mnt/Car Crash Analysis/'
OUT = '/sessions/serene-ecstatic-einstein/mnt/outputs/bus_nsw.json'

cols = ['Crash ID','Year of crash','Day of week of crash','Two-hour intervals',
        'Degree of crash','Street of crash','Town','LGA','Urbanisation',
        'Latitude','Longitude','Speed limit','RUM - description','First impact type',
        'School zone location','Type of location','No. of traffic units involved',
        'No. killed','No. seriously injured','No. moderately injured','No. minor-other injured']

ENG = 'calamine'
print('reading new crash...', flush=True)
new = pd.read_excel(COMPASS+'nsw_road_crash_data_2020-2024_crash.xlsx', usecols=cols, engine=ENG)
print('reading old crash...', flush=True)
old = pd.read_excel(COMPASS+'nsw_road_crash_data_2016-2020.xlsx',
                    usecols=[c if c != 'Two-hour intervals' else 'Time of crash - Two-hour intervals' for c in cols],
                    engine=ENG)
old = old.rename(columns={'Time of crash - Two-hour intervals': 'Two-hour intervals'})
old = old[(old['Year of crash'] >= 2016) & (old['Year of crash'] < 2020)]
print('reading TU tables...', flush=True)
tu = pd.concat([pd.read_excel(CCA+'nsw_road_crash_data_2016-2020_traffic_unit.xlsx', engine=ENG),
                pd.read_excel(CCA+'nsw_road_crash_data_2020-2024_traffic_unit.xlsx', engine=ENG)])

d = pd.concat([old, new]).drop_duplicates('Crash ID')
d['severe'] = ((d['No. killed'] > 0) | (d['No. seriously injured'] > 0)).astype(int)
d['fatal'] = (d['No. killed'] > 0).astype(int)
print('all NSW crashes 2016-24:', len(d), flush=True)

bus_units = tu[(tu['TU type group'] == 'Bus') & (tu['Crash ID'].isin(set(d['Crash ID'])))] \
              .drop_duplicates(['Crash ID', 'Traffic unit ID'])
bus = d[d['Crash ID'].isin(set(bus_units['Crash ID']))].copy()
print('bus-involved:', len(bus), flush=True)

# what buses hit: other TU types in the same crashes
other_units = tu[(tu['Crash ID'].isin(set(bus['Crash ID']))) & (tu['TU type group'] != 'Bus')] \
                .drop_duplicates(['Crash ID', 'Traffic unit ID'])

YEARS = [str(y) for y in range(2016, 2025)]
def dist(s, topn=10):
    vc = s.fillna('Unknown').astype(str).value_counts()
    return {k: int(v) for k, v in vc.head(topn).items()}

def sev_by(cat):
    g = bus.groupby(bus[cat].fillna('Unknown').astype(str))['severe'].agg(['count','sum'])
    g = g[g['count'] >= 30].sort_values('count', ascending=False)
    return {k: [int(r['count']), int(r['sum'])] for k, r in g.iterrows()}

# region split: metro conurbations vs rest
urb = dist(bus['Urbanisation'], 20)
urb_all = dist(d['Urbanisation'], 20)

# hourly + dow ordered
DOW = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
dow = {k: int((bus['Day of week of crash'] == k).sum()) for k in DOW}
hrs_order = sorted(bus['Two-hour intervals'].dropna().unique().tolist())
hrs = {h: int((bus['Two-hour intervals'] == h).sum()) for h in hrs_order}

# black-spot clustering: greedy 40 m discs, min 3 crashes
pts_df = bus.dropna(subset=['Latitude','Longitude'])
P = pts_df[['Latitude','Longitude','severe','fatal']].values.tolist()
meta = pts_df[['Street of crash','Town','LGA','RUM - description']].fillna('').values.tolist()
R = 0.040  # km
used = [False]*len(P)
import collections
cells = collections.defaultdict(list)
def cell(la, lo): return (round(la, 3), round(lo, 3))
for i,(la,lo,s,f) in enumerate(P): cells[cell(la,lo)].append(i)
def near(i):
    la,lo = P[i][0], P[i][1]
    out=[]
    for dla in (-0.001,0,0.001):
        for dlo in (-0.001,0,0.001):
            for j in cells.get((round(la+dla,3),round(lo+dlo,3)),[]):
                if used[j]: continue
                dy=(P[j][0]-la)*111.32; dx=(P[j][1]-lo)*111.32*math.cos(math.radians(la))
                if dy*dy+dx*dx <= R*R: out.append(j)
    return out
order = sorted(range(len(P)), key=lambda i: -len(near(i)))
clusters=[]
for i in order:
    if used[i]: continue
    nb = near(i)
    if len(nb) < 3: continue
    for j in nb: used[j]=True
    st = collections.Counter(meta[j][0] for j in nb).most_common(1)[0][0]
    tw = collections.Counter(meta[j][1] for j in nb).most_common(1)[0][0]
    lg = collections.Counter(meta[j][2] for j in nb).most_common(1)[0][0]
    rum = collections.Counter(meta[j][3] for j in nb if meta[j][3]).most_common(2)
    clusters.append(dict(n=len(nb), sev=int(sum(P[j][2] for j in nb)), fat=int(sum(P[j][3] for j in nb)),
                         lat=round(sum(P[j][0] for j in nb)/len(nb),5), lon=round(sum(P[j][1] for j in nb)/len(nb),5),
                         street=st, town=tw, lga=lg, rum=[f'{k} ({v})' for k,v in rum]))
clusters.sort(key=lambda c: (-c['n'], -c['sev']))
clusters = clusters[:15]

out = dict(
    n=len(bus), n_coords=len(pts_df),
    severe=int(bus.severe.sum()), fatal_crashes=int(bus.fatal.sum()),
    killed=int(bus['No. killed'].sum()), serious=int(bus['No. seriously injured'].sum()),
    moderate=int(bus['No. moderately injured'].sum()), minor=int(bus['No. minor-other injured'].sum()),
    sev_pct=round(bus.severe.mean()*100, 1),
    all_n=len(d), all_sev_pct=round(d.severe.mean()*100, 1),
    nunits=len(bus_units),
    years={y: int((bus['Year of crash'] == int(y)).sum()) for y in YEARS},
    sev_years={y: int(bus[bus['Year of crash'] == int(y)]['severe'].sum()) for y in YEARS},
    all_years={y: int((d['Year of crash'] == int(y)).sum()) for y in YEARS},
    degree=dist(bus['Degree of crash'], 6),
    rum=dist(bus['RUM - description'], 12),
    rum_sev=sev_by('RUM - description'),
    speed=dist(bus['Speed limit'], 8), speed_sev=sev_by('Speed limit'),
    lga=dist(bus['LGA'], 12),
    urb=urb, urb_all=urb_all,
    dow=dow, hrs=hrs,
    school=dist(bus['School zone location'], 5),
    loc_type=dist(bus['Type of location'], 5),
    manoeuvre=dist(bus_units['Manoeuvre'], 10),
    role=dist(bus_units['TU role in first impact'], 4),
    other_tu=dist(other_units['TU type group'], 10),
    clusters=clusters,
    pts=[[round(la,5), round(lo,5), 2 if f else (1 if s else 0)] for la,lo,s,f in P],
)
json.dump(out, open(OUT, 'w'))
print('written', OUT, flush=True)
print(json.dumps({k: v for k, v in out.items() if k not in ('pts','clusters')}, indent=1)[:2000])
