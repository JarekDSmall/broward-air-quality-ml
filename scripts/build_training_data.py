"""Build calendar-aligned next-day examples; no fitting or future imputation."""
import hashlib
import json
import math
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEATHER = ['temperature_2m_mean', 'relative_humidity_2m_mean', 'precipitation_sum',
           'wind_speed_10m_mean', 'pressure_msl_mean', 'cloud_cover_mean',
           'shortwave_radiation_sum']
AIR_FEATURES = ['pm25_today', 'pm25_lag1', 'pm25_lag2', 'pm25_lag7',
                'pm25_mean7', 'pm25_count7', 'season_sin', 'season_cos']
FEATURES = AIR_FEATURES + WEATHER + ['wind_sin', 'wind_cos']


def split_for(target_date):
    if target_date <= '2023-12-31':
        return 'train'
    if target_date <= '2024-12-31':
        return 'validation'
    return 'test'


def build_examples(rows):
    index = {}
    for row in rows:
        key = (row['station_id'], row['date'])
        date.fromisoformat(row['date'])
        if key in index:
            raise ValueError(f'Duplicate station date: {key}')
        for field in ['pm25_ug_m3', *WEATHER, 'wind_direction_10m_dominant']:
            value = row.get(field)
            if value is not None and not math.isfinite(value):
                raise ValueError(f'Nonfinite {field}: {key}')
        index[key] = row
    examples, excluded = [], Counter()
    for (station, day), current in sorted(index.items()):
        today = date.fromisoformat(day)
        tomorrow = (today + timedelta(days=1)).isoformat()
        target = index.get((station, tomorrow), {}).get('pm25_ug_m3')
        if target is None:
            excluded['missing_next_calendar_day_target'] += 1
            continue
        if current['pm25_ug_m3'] is None:
            excluded['missing_today_for_persistence'] += 1
            continue
        def lag(n):
            return index.get((station, (today-timedelta(days=n)).isoformat()), {}).get('pm25_ug_m3')
        history = [lag(n) for n in range(7)]
        observed = [v for v in history if v is not None]
        angle = 2*math.pi*(today.timetuple().tm_yday-1)/365.25
        wind = current.get('wind_direction_10m_dominant')
        example = dict(station_id=station, feature_date=day, target_date=tomorrow,
                       split=split_for(tomorrow), target_pm25=target,
                       pm25_today=lag(0), pm25_lag1=lag(1), pm25_lag2=lag(2), pm25_lag7=lag(7),
                       pm25_mean7=sum(observed)/len(observed), pm25_count7=len(observed),
                       season_sin=math.sin(angle), season_cos=math.cos(angle),
                       **{v: current.get(v) for v in WEATHER},
                       wind_sin=None if wind is None else math.sin(math.radians(wind)),
                       wind_cos=None if wind is None else math.cos(math.radians(wind)))
        examples.append(example)
    return examples, dict(excluded)


def main():
    source = ROOT/'data/analysis/station_days.jsonl'
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    examples, excluded = build_examples(rows)
    out = ROOT/'data/training'
    out.mkdir(parents=True, exist_ok=True)
    (out/'next_day.jsonl').write_text(''.join(json.dumps(r, allow_nan=False)+'\n' for r in examples))
    manifest = dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    input_rows=len(rows), examples=len(examples), excluded=excluded,
                    features=FEATURES, split_counts=dict(Counter(r['split'] for r in examples)),
                    station_split_counts=dict(Counter(r['station_id']+'/'+r['split'] for r in examples)))
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == '__main__':
    main()
