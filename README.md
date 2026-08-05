# NSW bus-involved crashes, 2016–2024

Spatial analysis of police-reported crashes involving a bus in New South Wales, built by
[Hadron Group](https://hadrongroup.com.au) from Transport for NSW open crash data.

**Live page:** https://hadrongroup.github.io/nsw-bus-safety/

## What it shows

2,092 bus-involved crashes over nine years: the trend, a statewide map with repeat-location
clusters, geographic concentration, crash types and their severity, time-of-day and
day-of-week patterns, and severity by speed zone.

Buses are identified from the **traffic-unit** tables rather than the headline crash record.
A bus that was one vehicle in a multi-vehicle crash is often not the vehicle type recorded
against the crash, so a filter on the crash table alone under-counts them.

## Source data

Transport for NSW road crash data, published on the
[NSW Open Data portal](https://opendata.transport.nsw.gov.au/):

- `nsw_road_crash_data_2016-2020.xlsx` and `nsw_road_crash_data_2020-2024_crash.xlsx` – crash records
- `nsw_road_crash_data_2016-2020_traffic_unit.xlsx` and `nsw_road_crash_data_2020-2024_traffic_unit.xlsx` – traffic units

The two releases overlap in 2020, so they are merged and deduplicated on Crash ID, giving
183,448 NSW crashes for 2016–2024.

## Things to know before quoting a number

- **'Bus' is one vehicle type.** The Transport for NSW definition covers route services,
  school buses, charter vehicles and long-distance coaches, and the public release has no
  operator or service-type field. These figures cannot be read as contracted public transport
  services alone. Narrowing them would mean matching crash locations and times against the
  bus timetable, or working from operator-reported incident data.
- **Counts follow exposure.** Sydney leads because that is where most bus-kilometres are run.
  Section 3 normalises by each LGA's own crash total, which is a partial correction.
  Service-kilometres by route and segment would be better.
- **Coordinate precision varies.** The 40 m repeat-location clusters are a starting point for
  site investigation, not a finding on their own.
- **Crash data are police-reported.** Minor incidents, and on-board injuries with no
  collision, are likely to be under-represented.
- **Severe** means at least one person killed or seriously injured.

## Rebuilding the page

`pipeline/` holds the extraction and build scripts.

```bash
pip install pandas python-calamine
python3 pipeline/extract_bus_nsw.py    # crash + traffic-unit xlsx -> bus_nsw.json
python3 pipeline/extract_lga.py        # per-LGA counts for every NSW LGA -> lga_extra.json
python3 pipeline/build_bus_report.py   # json -> index.html
```

The source spreadsheets are not in this repo (they are large and are published by Transport
for NSW). Set the input paths at the top of each extract script to wherever you have them.
`extract_lga.py` reconciles its own totals against `bus_nsw.json` and exits non-zero if they
disagree, so a mismatched input set fails loudly rather than quietly changing a published
figure.

Chart.js and Leaflet are vendored in `vendor/` rather than loaded from a CDN, so the page
works on networks that block third-party script hosts. The basemap tiles still come from
CARTO, so the map needs internet access even though the charts do not.

## Publishing

GitHub Pages serves this repo from `main` / root. Push to `main` and the live page updates
within a minute or two. Any `.html` file in the repo is reachable at
`https://hadrongroup.github.io/nsw-bus-safety/<filename>`; `index.html` is the base URL.
