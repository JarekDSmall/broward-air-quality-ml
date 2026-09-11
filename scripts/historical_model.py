"""Package the validation-selected model and replay eligible 2025 dates."""
import argparse
import hashlib
import json
import platform
from datetime import date

import joblib
import numpy as np
import sklearn

from build_training_data import ROOT, FEATURES
from collect_dep_pm25 import STATIONS
from compare_baselines import matrix, model_for

ARTIFACT = ROOT/'models/historical_boosting.joblib'


def training_rows():
    source = ROOT/'data/training/next_day.jsonl'
    return ([json.loads(line) for line in source.read_text().splitlines()],
            hashlib.sha256(source.read_bytes()).hexdigest())


def package():
    rows, source_hash = training_rows()
    scores = json.loads((ROOT/'reports/baselines/metrics.json').read_text())
    if scores['training_sha256'] != source_hash or scores['selected'] != 'boosted_weather':
        raise ValueError('Source or validation selection differs from the documented experiment')
    train = [r for r in rows if r['target_date'] < '2025-01-01']
    test = [r for r in rows if '2025-01-01' <= r['target_date'] <= '2025-12-31']
    model = model_for('boosted_weather')
    model.fit(matrix(train, 'boosted_weather'), [r['target_pm25'] for r in train])
    metadata = dict(model='boosted_weather', training_sha256=source_hash,
                    train_end=max(r['target_date'] for r in train), training_rows=len(train),
                    features=FEATURES, sklearn=sklearn.__version__, numpy=np.__version__,
                    python=platform.python_version(), use='Historical 2025 replay only; not a live forecast')
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(dict(model=model, metadata=metadata), ARTIFACT)
    restored = load_bundle()
    predictions = restored['model'].predict(matrix(test, 'boosted_weather'))
    saved = [json.loads(line) for line in (ROOT/'reports/baselines/test_predictions.jsonl').read_text().splitlines()]
    from analyze_errors import saved_predictions
    expected = saved_predictions(test, saved, 'boosted_weather')
    np.testing.assert_allclose(predictions, expected, rtol=1e-10, atol=1e-10)
    metadata['artifact_sha256'] = hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()
    metadata['verified_predictions'] = len(test)
    (ARTIFACT.parent/'historical_boosting.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps(metadata, indent=2))


def load_bundle():
    # Load only the locally generated artifact. Joblib/pickle must not load untrusted files.
    bundle = joblib.load(ARTIFACT)
    if bundle['metadata']['sklearn'] != sklearn.__version__ or bundle['metadata']['features'] != FEATURES:
        raise ValueError('Artifact environment/schema mismatch; rebuild with package')
    return bundle


def select_row(rows, station, target):
    date.fromisoformat(target)
    if not '2025-01-01' <= target <= '2025-12-31':
        raise ValueError('This model replays 2025 only; earlier dates overlap training')
    matches = [r for r in rows if r['station_id'] == station and r['target_date'] == target]
    if len(matches) != 1:
        raise ValueError('No eligible example for this station/date (missing current reading or target)')
    return matches[0]


def replay(station, target):
    rows, source_hash = training_rows()
    row = select_row(rows, station, target)
    bundle = load_bundle()
    if bundle['metadata']['training_sha256'] != source_hash:
        raise ValueError('Data changed; rebuild the historical package')
    value = float(bundle['model'].predict(matrix([row], 'boosted_weather'))[0])
    return dict(station_id=station, station=STATIONS[station][0], target_date=target,
                features_through=row['feature_date'], predicted_pm25=value,
                persistence_pm25=row['pm25_today'], observed_pm25=row['target_pm25'],
                units='µg/m³', use=bundle['metadata']['use'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('package')
    command = sub.add_parser('predict')
    command.add_argument('--station', choices=STATIONS, required=True)
    command.add_argument('--date', required=True, help='Target date in 2025 (YYYY-MM-DD)')
    args = parser.parse_args()
    try:
        if args.command == 'package':
            package()
        else:
            print(json.dumps(replay(args.station, args.date), indent=2, ensure_ascii=False))
    except (ValueError, FileNotFoundError) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
