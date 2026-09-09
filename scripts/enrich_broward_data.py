"""Fetch method-tagged EPA PM2.5 records and ERA5 weather for a retrospective study.

Python standard library only. Run after collect_dep_pm25.py. Raw downloads and
derived records remain under ignored data/. No model fitting occurs here.
"""
import calendar
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
import csv
import hashlib
import io
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from collect_dep_pm25 import ROOT, STATIONS

EPA = ROOT / 'data/epa'
WEATHER = ROOT / 'data/weather'
OUT = ROOT / 'data/analysis'
AIRDATA = 'https://aqs.epa.gov/aqsweb/airdata/'
VARIABLES = ['temperature_2m_mean', 'relative_humidity_2m_mean', 'precipitation_sum',
             'wind_speed_10m_mean', 'wind_direction_10m_dominant', 'pressure_msl_mean',
             'cloud_cover_mean', 'shortwave_radiation_sum']
ALLOWED_METHODS = {'183', '636', '638', '736', '738'}
EXPECTED_UNITS = {'temperature_2m_mean':'°C', 'relative_humidity_2m_mean':'%',
                  'precipitation_sum':'mm', 'wind_speed_10m_mean':'m/s',
                  'wind_direction_10m_dominant':'°', 'pressure_msl_mean':'hPa',
                  'cloud_cover_mean':'%', 'shortwave_radiation_sum':'MJ/m²'}


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding='utf-8')


def jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as f:
        for row in rows:
            f.write(json.dumps(row, separators=(',', ':'))+'\n')


def download(url, path):
    """Cache exact response bytes and validate them on subsequent runs."""
    meta_path = path.with_suffix(path.suffix+'.source.json')
    if path.exists():
        payload = path.read_bytes()
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            if meta['url'] != url or meta['sha256'] != hashlib.sha256(payload).hexdigest():
                raise ValueError(f'Cache identity/checksum mismatch: {path}')
        else:
            # Existing files were retrieved in the initial source inspection;
            # record verification time rather than invent a retrieval timestamp.
            meta = dict(url=url, verified_at_utc=datetime.now(timezone.utc).isoformat(),
                        sha256=hashlib.sha256(payload).hexdigest())
            dump(meta_path, meta)
        return payload
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={'User-Agent':'BrowardCapstoneDataAudit/1.0'})
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = response.read()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            dump(meta_path, dict(url=url, retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                                 sha256=hashlib.sha256(payload).hexdigest()))
            return payload
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 3:
                raise
            delay = 60 if exc.code == 429 else 3*(attempt+1)
            print(f'Server {exc.code}; retrying in {delay}s', flush=True)
            time.sleep(delay)


def zip_rows(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [n for n in archive.namelist() if n.endswith('.csv')]
        if len(names) != 1:
            raise ValueError('Expected one CSV in EPA archive')
        with io.TextIOWrapper(archive.open(names[0]), encoding='utf-8-sig') as stream:
            yield from csv.DictReader(stream)


def site_id(row):
    return row['State Code']+row['County Code']+row.get('Site Num', row.get('Site Number', ''))


def in_range(row):
    site = site_id(row)
    if site not in STATIONS:
        return False
    _, y, m = STATIONS[site]
    return f'{y}-{m:02d}-01' <= row['Date Local'] <= '2025-12-31'


def select_epa(rows):
    """Choose one continuous-monitor daily mean; never average POCs/standards.

    Daily aggregate of 1-hour samples, blank standard, events included, >=18 samples.
    Network-aligned methods take priority over retroactively corrected duplicates.
    Gravimetric POCs and original T640 methods are deliberately not substituted.
    """
    candidates = defaultdict(list)
    excluded = Counter()
    for r in rows:
        if not in_range(r):
            continue
        if r['Parameter Code'] != '88101' or r['POC'] not in {'3','23'}:
            excluded['parameter_or_poc'] += 1
            continue
        if r['Sample Duration'] != '1 HOUR' or r['Pollutant Standard'] != '':
            excluded['alternate_summary'] += 1
            continue
        if r['Method Code'] not in ALLOWED_METHODS:
            excluded['unapproved_or_uncorrected_method'] += 1
            continue
        if r['Event Type'] not in {'None','Included'}:
            excluded['event_excluded_summary'] += 1
            continue
        if r['Units of Measure'] != 'Micrograms/cubic meter (LC)':
            raise ValueError('Unexpected EPA units')
        if int(r['Observation Count']) < 18 or float(r['Observation Percent']) < 75:
            excluded['incomplete_day'] += 1
            continue
        candidates[(site_id(r),r['Date Local'])].append(r)
    selected=[]
    priority={'636':0,'638':0,'736':1,'738':1,'183':2}
    for (site,day), items in sorted(candidates.items()):
        rank=min(priority[r['Method Code']] for r in items)
        best=[r for r in items if priority[r['Method Code']]==rank]
        signatures={(r['POC'],r['Method Code'],r['Arithmetic Mean'],r['Observation Count']) for r in best}
        if len(signatures)!=1:
            raise ValueError(f'Ambiguous EPA records: {site} {day}')
        r=best[0]
        selected.append(dict(station_id=site,date=day,pm25_ug_m3=float(r['Arithmetic Mean']),
                             method_code=r['Method Code'],method_name=r['Method Name'],poc=r['POC'],
                             observation_count=int(r['Observation Count']),event_type=r['Event Type'],
                             source_url=AIRDATA+f'daily_88101_{day[:4]}.zip',
                             date_of_last_change=r['Date of Last Change']))
    return selected,dict(excluded)


def weather_records(payload, station, start, end):
    obj=json.loads(payload)
    if obj.get('utc_offset_seconds') != -18000:
        raise ValueError('Weather must use fixed UTC-5 local standard time')
    daily=obj['daily']
    expected=[]
    cursor=date.fromisoformat(start)
    while cursor<=date.fromisoformat(end):
        expected.append(cursor.isoformat())
        cursor+=timedelta(days=1)
    if daily['time']!=expected:
        raise ValueError('Weather dates incomplete, duplicated, or out of order')
    for v in VARIABLES:
        if len(daily[v])!=len(expected) or obj['daily_units'][v]!=EXPECTED_UNITS[v]:
            raise ValueError(f'Weather shape/units mismatch: {v}')
    return [dict(station_id=station,date=d,weather_model='era5',
                 weather_time_zone='Etc/GMT+5',**{v:daily[v][i] for v in VARIABLES})
            for i,d in enumerate(expected)]


def main():
    sites=[r for r in zip_rows(download(AIRDATA+'aqs_sites.zip',EPA/'aqs_sites.zip')) if site_id(r) in STATIONS]
    monitors=[r for r in zip_rows(download(AIRDATA+'aqs_monitors.zip',EPA/'aqs_monitors.zip'))
              if site_id(r) in STATIONS and r['Parameter Code']=='88101']
    if {site_id(r) for r in sites}!=set(STATIONS):
        raise ValueError('Missing site coordinates')
    dump(EPA/'sites.json',sites)
    dump(EPA/'monitors_pm25.json',monitors)
    raw=[]
    for year in range(2019,2026):
        name=f'daily_88101_{year}.zip'
        rows=[r for r in zip_rows(download(AIRDATA+name,EPA/name)) if site_id(r) in STATIONS]
        raw.extend(rows)
        print(f'EPA {year}: {len(rows)} raw summary rows',flush=True)
    jsonl(EPA/'daily_broward_raw.jsonl',raw)
    selected,exclusions=select_epa(raw)
    jsonl(EPA/'daily_pm25_selected.jsonl',selected)
    dep=[json.loads(x) for x in (ROOT/'data/broward_dep/daily_pm25.jsonl').read_text().splitlines()]
    dep_index={(r['station_id'],r['date']):r for r in dep}
    comparison=[]
    for r in selected:
        original=dep_index.get((r['station_id'],r['date']),{}).get('pm25_ug_m3')
        comparison.append(dict(station_id=r['station_id'],date=r['date'],method_code=r['method_code'],
                               epa_pm25=r['pm25_ug_m3'],dep_pm25=original,
                               difference=None if original is None else r['pm25_ug_m3']-original))
    jsonl(EPA/'dep_comparison.jsonl',comparison)
    all_weather=[]
    weather_meta=[]
    for site in sites:
        station=site_id(site)
        _,y,m=STATIONS[station]
        start=(date(y,m,1)-timedelta(days=7)).isoformat()
        if site['Datum'] not in {'WGS84','NAD83'} or float(site['GMT Offset'])!=-5:
            raise ValueError('Unexpected coordinate/time reference')
        # NAD83 coordinates are used only as a coarse ERA5 grid lookup, rounded
        # to 0.01 degree; this is not a surveyed WGS84 datum transformation.
        lat=site['Latitude'] if site['Datum']=='WGS84' else str(round(float(site['Latitude']),2))
        lon=site['Longitude'] if site['Datum']=='WGS84' else str(round(float(site['Longitude']),2))
        params=dict(latitude=lat,longitude=lon,start_date=start,
                    end_date='2025-12-31',models='era5',timezone='Etc/GMT+5',
                    daily=','.join(VARIABLES),wind_speed_unit='ms',temperature_unit='celsius',precipitation_unit='mm')
        url='https://archive-api.open-meteo.com/v1/archive?'+urllib.parse.urlencode(params)
        payload=download(url,WEATHER/f'{station}_era5.json')
        records=weather_records(payload,station,start,'2025-12-31')
        obj=json.loads(payload)
        weather_meta.append(dict(station_id=station,requested_latitude=lat,requested_longitude=lon,
                                 source_datum=site['Datum'],coordinate_lookup='exact WGS84' if site['Datum']=='WGS84' else 'approximate grid lookup rounded to 0.01 degree; not datum transformed',
                                 grid_latitude=obj['latitude'],grid_longitude=obj['longitude'],
                                 elevation=obj['elevation'],units=obj['daily_units'],source_url=url))
        all_weather.extend(records)
        print(f'Weather {station}: {len(records)} days',flush=True)
    jsonl(WEATHER/'daily_weather.jsonl',all_weather)
    dump(WEATHER/'grid_metadata.json',weather_meta)
    wx={(r['station_id'],r['date']):r for r in all_weather}
    epa={(r['station_id'],r['date']):r for r in selected}
    joined=[]
    for d in dep:
        key=(d['station_id'],d['date'])
        r=epa.get(key)
        joined.append(dict(station_id=d['station_id'],date=d['date'],
                           pm25_ug_m3=r['pm25_ug_m3'] if r else None,
                           method_code=r['method_code'] if r else None,
                           observation_count=r['observation_count'] if r else None,
                           dep_pm25_reference=d['pm25_ug_m3'],
                           **{k:v for k,v in wx[key].items() if k not in {'station_id','date'}}))
    jsonl(OUT/'station_days.jsonl',joined)
    summary=dict(epa_rows=len(raw),selected_days=len(selected),joined_calendar_days=len(joined),
                 weather_days=len(all_weather),missing_weather_values=sum(r[v] is None for r in all_weather for v in VARIABLES),
                 excluded_rows=exclusions,stations=[])
    for station,(name,_,_) in STATIONS.items():
        sr=[r for r in selected if r['station_id']==station]
        comp=[r for r in comparison if r['station_id']==station and r['difference'] is not None]
        summary['stations'].append(dict(station_id=station,name=name,selected_days=len(sr),
            methods=dict(Counter(r['method_code'] for r in sr)),compared_days=len(comp),
            materially_different_days=sum(abs(r['difference'])>0.11 for r in comp)))
    dump(OUT/'enrichment_summary.json',summary)
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    main()
