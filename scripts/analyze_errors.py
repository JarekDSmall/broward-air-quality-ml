"""Expanding-year diagnostics using unchanged candidates; no new model tuning."""
import hashlib
import json
import platform
from collections import defaultdict

import numpy as np
import sklearn

from build_training_data import ROOT
from collect_dep_pm25 import STATIONS
from compare_baselines import CANDIDATES, metrics, predict


def annual_fold(rows, year):
    train = [r for r in rows if r['target_date'] < f'{year}-01-01']
    seen = {r['station_id'] for r in train}
    evaluation = [r for r in rows if r['target_date'].startswith(str(year))]
    test = [r for r in evaluation if r['station_id'] in seen]
    unseen = [r for r in evaluation if r['station_id'] not in seen]
    if not train or not test:
        raise ValueError(f'Empty fold: {year}')
    if max(r['target_date'] for r in train) >= min(r['target_date'] for r in test):
        raise ValueError('Temporal overlap')
    return train, test, unseen


def season(day):
    month = int(day[5:7])
    return {12: 'DJF', 1: 'DJF', 2: 'DJF', 3: 'MAM', 4: 'MAM', 5: 'MAM',
            6: 'JJA', 7: 'JJA', 8: 'JJA', 9: 'SON', 10: 'SON', 11: 'SON'}[month]


def high_threshold(train):
    return float(np.quantile([r['target_pm25'] for r in train], .9))


def group_scores(rows, predictions, key):
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        groups[key(row)].append(i)
    return {name: metrics([rows[i] for i in indices], np.asarray(predictions)[indices])
            for name, indices in sorted(groups.items())}


def saved_predictions(rows, records, model):
    selected = [r for r in records if r['model'] == model]
    index = {(r['station_id'], r['target_date']): r for r in selected}
    if len(index) != len(selected):
        raise ValueError('Duplicate saved prediction')
    expected = {(r['station_id'], r['target_date']) for r in rows}
    if set(index) != expected:
        raise ValueError('Saved predictions do not match test rows')
    values = []
    for row in rows:
        old = index[(row['station_id'], row['target_date'])]
        if old['observed'] != row['target_pm25'] or not np.isfinite(old['predicted']):
            raise ValueError('Invalid saved prediction/target')
        values.append(old['predicted'])
    return np.array(values)


def main():
    source = ROOT/'data/training/next_day.jsonl'
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    previous = json.loads((ROOT/'reports/baselines/metrics.json').read_text())
    if source_hash != previous['training_sha256']:
        raise ValueError('Training data changed since baseline evaluation; reproduce baselines first')
    result = dict(training_sha256=source_hash,
                  environment=dict(python=platform.python_version(), numpy=np.__version__, sklearn=sklearn.__version__),
                  original_baseline_environment={k: previous[k] for k in ['python', 'numpy', 'sklearn']},
                  folds={}, diagnostics={})
    fold_predictions = []
    for year in [2021, 2022, 2023, 2024]:
        train, test, unseen = annual_fold(rows, year)
        fold = dict(train_rows=len(train), evaluation_rows=len(test), unseen_rows=len(unseen),
                    train_end=max(r['target_date'] for r in train), scores={})
        for model in CANDIDATES:
            values = predict(model, train, test)
            fold['scores'][model] = metrics(test, values)
            for row, value in zip(test, values):
                fold_predictions.append(dict(year=year, model=model, station_id=row['station_id'],
                    target_date=row['target_date'], observed=row['target_pm25'], predicted=float(value)))
        result['folds'][str(year)] = fold
        print(f"{year}: {len(train):,} train / {len(test):,} evaluation / {len(unseen)} unseen excluded", flush=True)
    train, test, unseen = annual_fold(rows, 2025)
    all_test = [r for r in rows if r['target_date'].startswith('2025')]
    cutoff = high_threshold(train)
    result['high_pm25_threshold'] = cutoff
    records = [json.loads(line) for line in (ROOT/'reports/baselines/test_predictions.jsonl').read_text().splitlines()]
    seen_mask = np.array([r['station_id'] in {x['station_id'] for x in test} for r in all_test])
    for model in CANDIDATES:
        all_values = saved_predictions(all_test, records, model)
        values = all_values[seen_mask]
        result['diagnostics'][model] = dict(
            station=group_scores(all_test, all_values, lambda r: r['station_id']),
            season=group_scores(test, values, lambda r: season(r['target_date'])),
            concentration=group_scores(test, values, lambda r: 'high' if r['target_pm25'] >= cutoff else 'other'))
    # Rank dates, not individual monitors, so a shared regional event is one entry.
    selected = previous['selected']
    selected_values = saved_predictions(all_test, records, selected)[seen_mask]
    date_errors = group_scores(test, selected_values, lambda r: r['target_date'])
    result['largest_error_dates'] = sorted(date_errors.items(), key=lambda item: item[1]['mae'], reverse=True)[:10]
    out = ROOT/'reports/error_analysis'
    out.mkdir(parents=True, exist_ok=True)
    (out/'metrics.json').write_text(json.dumps(result, indent=2)+'\n')
    (out/'fold_predictions.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in fold_predictions))
    lines = ['# Error analysis and earlier-year validation', '',
             'Fixed baseline settings were reused without tuning. Errors are in µg/m³; lower MAE is better.', '',
             '## Expanding annual evaluation', '',
             'Each fold trains on all earlier target dates and predicts the following year using preceding-day observations. Imputation/scaling fit within that fold. Stations with no earlier training history are excluded from these fold aggregates.', '',
             '| Evaluation year | Training rows | Evaluation rows | Unseen rows excluded |', '| --- | ---: | ---: | ---: |']
    for year, fold in result['folds'].items():
        lines.append(f"| {year} | {fold['train_rows']} | {fold['evaluation_rows']} | {fold['unseen_rows']} |")
    lines += ['', '| Candidate | 2021 MAE | 2022 MAE | 2023 MAE | 2024 MAE | Years beating persistence |',
              '| --- | ---: | ---: | ---: | ---: | ---: |']
    for model in CANDIDATES:
        scores = [fold['scores'][model]['mae'] for fold in result['folds'].values()]
        wins = sum(fold['scores'][model]['mae'] < fold['scores']['persistence']['mae'] for fold in result['folds'].values())
        lines.append('| '+model+' | '+' | '.join(f'{v:.3f}' for v in scores)+f' | {wins}/4 |')
    lines += ['', '## 2025 diagnostic slices', '',
              'These reuse saved first-run 2025 predictions; no models are refitted for the slices. Seasons use calendar quarters DJF/MAM/JJA/SON, not a local wet/dry season classification.', '',
              f'High-pollution observations are at or above the pooled training-period (2019–2024) 90th percentile: **{cutoff:.3f} µg/m³**. This is a descriptive relative threshold, not an AQI or health category. Grouping by the observed target is for analysis only.', '']
    for dimension in ['station', 'season', 'concentration']:
        lines += [f'### {dimension.title()}', '', '| Group | Days | Persistence MAE | Air ridge MAE | Weather ridge MAE | Boosting MAE | Boosting bias |',
                  '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
        for group, base in result['diagnostics']['persistence'][dimension].items():
            label = STATIONS[group][0] if dimension == 'station' else group
            if dimension == 'station' and group == '120110037':
                label += ' (unseen; separate)'
            values = [result['diagnostics'][m][dimension][group]['mae'] for m in ['persistence', 'ridge_air', 'ridge_weather', 'boosted_weather']]
            bias = result['diagnostics']['boosted_weather'][dimension][group]['bias']
            lines.append(f"| {label} | {base['n']} | "+' | '.join(f'{v:.3f}' for v in values)+f' | {bias:.3f} |')
        lines.append('')
    lines += ['## Largest daily errors for validation-selected boosting (2025)', '',
              'Mean absolute error across available established stations on each date. These identify cases to inspect; they do not establish a pollution source or cause.', '',
              '| Target date | Stations | MAE | Bias |', '| --- | ---: | ---: | ---: |']
    for day, score in result['largest_error_dates']:
        lines.append(f"| {day} | {score['n']} | {score['mae']:.3f} | {score['bias']:.3f} |")
    wins = {model: sum(fold['scores'][model]['mae'] < fold['scores']['persistence']['mae']
                      for fold in result['folds'].values()) for model in CANDIDATES}
    high = result['diagnostics'][selected]['concentration']['high']
    lines += ['', '## Findings', '',
              f"Air-only ridge beats persistence in {wins['ridge_air']}/4 earlier years; weather ridge in {wins['ridge_weather']}/4; boosting in {wins['boosted_weather']}/4. The model ranking varies by year, so there is no consistent winner across all periods.", '',
              f"The validation-selected model has MAE {high['mae']:.3f} and bias {high['bias']:.3f} on {high['n']} high-concentration station-days in 2025. This subgroup is substantially harder than ordinary days; low overall error should not be presented as reliable peak prediction.", '',
              'For the first historical demo, retain the original validation-selected boosting model and show persistence alongside it. Keep air-only ridge as the simpler comparison. Investigate large-error dates before considering new features, and use a new untouched period for any subsequent final model comparison.', '',
              '## Evaluation boundaries', '',
              '- Earlier-year folds are retrospective development diagnostics, not newly untouched tests: those years contributed to the original model-development dataset. 2024 repeats the original validation period.',
              '- Station availability changes across years (Vista View first appears in the seen-station evaluation in 2022). Year-to-year differences reflect both coverage and conditions.',
              '- Station-days are correlated. No independence-based significance tests or confidence claims are made. Bias is prediction minus observation; negative values mean underprediction.',
              '- Seasons/concentration groups exclude the new Pompano monitor; the station table includes its separate short evaluation.',
              '- No candidate or parameter was changed after inspecting 2025. The original validation-selected candidate remains boosting; a new final evaluation needs data not used for these decisions.',
              '- Reanalysis and revised pollutant histories retain the availability limitations documented in DATA_METHODS.md.', '',
              f'Training SHA256: `{source_hash}`. Full slice metrics (including RMSE/bias) and earlier-fold predictions are in `reports/error_analysis/`.', '']
    (ROOT/'ERROR_ANALYSIS.md').write_text('\n'.join(lines), encoding='utf-8')
    print('Saved ERROR_ANALYSIS.md and reports/error_analysis/', flush=True)


if __name__ == '__main__':
    main()
