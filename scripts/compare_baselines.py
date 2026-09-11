"""Fixed candidates; choose by 2024 MAE, refit through 2024, evaluate 2025."""
import hashlib
import json
import platform
from collections import Counter

import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from build_training_data import ROOT, FEATURES, AIR_FEATURES

NEW_STATION = '120110037'
CANDIDATES = ['persistence', 'rolling_mean7', 'ridge_air', 'ridge_weather', 'boosted_weather']


def model_for(name):
    if name.startswith('ridge'):
        return make_pipeline(SimpleImputer(strategy='median', add_indicator=True),
                             StandardScaler(), Ridge(alpha=10.0))
    if name == 'boosted_weather':
        return make_pipeline(SimpleImputer(strategy='median', add_indicator=True),
                             HistGradientBoostingRegressor(max_iter=150, max_leaf_nodes=15,
                                 learning_rate=0.05, l2_regularization=10.0,
                                 early_stopping=False, random_state=42))
    raise ValueError(name)


def matrix(rows, name):
    features = AIR_FEATURES if name == 'ridge_air' else FEATURES
    return np.array([[np.nan if r[f] is None else r[f] for f in features] for r in rows])


def predict(name, train, evaluation):
    if name in ['persistence', 'rolling_mean7']:
        key = 'pm25_today' if name == 'persistence' else 'pm25_mean7'
        return np.array([r[key] for r in evaluation])
    model = model_for(name)
    model.fit(matrix(train, name), [r['target_pm25'] for r in train])
    return model.predict(matrix(evaluation, name))


def metrics(rows, predictions):
    truth = np.array([r['target_pm25'] for r in rows])
    return dict(n=len(rows), mae=float(mean_absolute_error(truth, predictions)),
                rmse=float(np.sqrt(mean_squared_error(truth, predictions))),
                bias=float(np.mean(predictions-truth)))


def main():
    source = ROOT/'data/training/next_day.jsonl'
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    train = [r for r in rows if r['split'] == 'train']
    validation = [r for r in rows if r['split'] == 'validation']
    test = [r for r in rows if r['split'] == 'test']
    assert max(r['target_date'] for r in train) < min(r['target_date'] for r in validation)
    assert max(r['target_date'] for r in validation) < min(r['target_date'] for r in test)
    validation_scores = {name: metrics(validation, predict(name, train, validation)) for name in CANDIDATES}
    winner = min(CANDIDATES, key=lambda name: validation_scores[name]['mae'])
    print(f'2024 selection: {winner}', flush=True)
    result = dict(python=platform.python_version(), numpy=np.__version__, sklearn=sklearn.__version__,
                  training_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), seed=42,
                  split_counts=dict(Counter(r['split'] for r in rows)), selected=winner,
                  validation=validation_scores, test={}, station_test={})
    predictions = []
    for name in CANDIDATES:
        pred = predict(name, train+validation, test)
        established = np.array([r['station_id'] != NEW_STATION for r in test])
        result['test'][name] = metrics([r for r, keep in zip(test, established) if keep], pred[established])
        result['station_test'][name] = {}
        for station in sorted({r['station_id'] for r in test}):
            mask = np.array([r['station_id'] == station for r in test])
            result['station_test'][name][station] = metrics([r for r, keep in zip(test, mask) if keep], pred[mask])
        for row, value in zip(test, pred):
            predictions.append(dict(station_id=row['station_id'], target_date=row['target_date'],
                                    model=name, observed=row['target_pm25'], predicted=float(value)))
    out = ROOT/'reports/baselines'
    out.mkdir(parents=True, exist_ok=True)
    (out/'metrics.json').write_text(json.dumps(result, indent=2)+'\n')
    (out/'test_predictions.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in predictions))
    lines = ['# Next-day PM2.5 baseline comparison', '',
             'Retrospective experiment using corrected EPA PM2.5 and ERA5 weather. Errors are in µg/m³.', '',
             'Train: target dates through 2023. Validation: 2024. Test: 2025. All candidates use identical eligible rows.',
             f"Counts: {len(train):,} training, {len(validation):,} validation, {len(test):,} test (including the new Pompano station).", '',
             f'**Selected using validation MAE: {winner}.** All fixed candidates are then refitted through 2024.', '',
             '## Five established stations', '',
             '| Candidate | 2024 validation MAE | 2025 test MAE | 2025 test RMSE | Test bias |',
             '| --- | ---: | ---: | ---: | ---: |']
    for name in CANDIDATES:
        m = result['test'][name]
        lines.append(f"| {name} | {validation_scores[name]['mae']:.3f} | {m['mae']:.3f} | {m['rmse']:.3f} | {m['bias']:.3f} |")
    lines += ['', '## Selected candidate versus persistence by station (2025)', '',
              '| Station | Days | Persistence MAE | Selected MAE |', '| --- | ---: | ---: | ---: |']
    for station, m in result['station_test'][winner].items():
        baseline = result['station_test']['persistence'][station]
        label = station + (' (new Pompano; unseen station)' if station == NEW_STATION else '')
        lines.append(f"| {label} | {m['n']} | {baseline['mae']:.3f} | {m['mae']:.3f} |")
    lines += ['', '## Interpretation and limits', '',
              '- Persistence predicts tomorrow equals today; rolling_mean7 averages available observations from today through six days earlier.',
              '- Ridge uses alpha=10. Air features include current PM2.5, calendar lags 1/2/7, seven-day mean/count and annual sine/cosine. Weather adds day-t ERA5 variables and circular wind direction.',
              '- Gradient boosting uses 150 iterations, 15 leaves, learning rate 0.05, L2=10, seed=42, and no internal random validation split. No hyperparameter search was performed.',
              '- Median imputation and scaling fit only on each training period. Station IDs and method codes are not model features. Missing targets/current PM2.5 are excluded; missing older lags remain missing until training-only imputation.',
              '- Test evaluation is rolling one-day-ahead with each preceding day observed, not a recursive year-ahead forecast. The target date determines its split. No target-day weather is used.',
              '- Pompano starts September 2025 and is reported separately. Aggregate errors weight station-days equally; sites share weather and pollution events, so rows are not independent.',
              '- Revised EPA history and delayed ERA5 reanalysis cannot establish as-issued forecast accuracy. No statistical significance, operational readiness or health-risk claim is made.',
              '- This is the first fixed holdout comparison. Further tuning informed by these test results would require a new untouched holdout.', '',
              f"Environment: Python {result['python']}, NumPy {result['numpy']}, scikit-learn {result['sklearn']}.",
              f"Training file SHA256: `{result['training_sha256']}`.", '',
              'Detailed metrics and row-level test predictions are generated locally under `reports/baselines/`.']
    (ROOT/'BASELINE_RESULTS.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
