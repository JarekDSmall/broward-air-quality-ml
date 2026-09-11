"""Export verified 2025 model replay to the local static demo."""
import json

import numpy as np

from build_training_data import ROOT
from collect_dep_pm25 import STATIONS
from compare_baselines import matrix
from historical_model import load_bundle, training_rows


def main():
    rows, source_hash = training_rows()
    bundle = load_bundle()
    if bundle['metadata']['training_sha256'] != source_hash:
        raise ValueError('Model/data mismatch; rebuild the package')
    test = [r for r in rows if r['split'] == 'test']
    values = bundle['model'].predict(matrix(test, 'boosted_weather'))
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite model outputs')
    payload = dict(stations={k: v[0] for k, v in STATIONS.items()}, rows=[
        dict(station=r['station_id'], date=r['target_date'], observed=r['target_pm25'],
             predicted=float(value), persistence=r['pm25_today']) for r, value in zip(test, values)])
    out = ROOT/'demo/dist/data.js'
    out.write_text('window.HISTORY = '+json.dumps(payload, allow_nan=False)+';\n', encoding='utf-8')
    print(f'Exported {len(test)} verified historical rows to {out}')


if __name__ == '__main__':
    main()
