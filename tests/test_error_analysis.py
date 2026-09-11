import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from analyze_errors import annual_fold, group_scores, high_threshold, saved_predictions, season


def row(day, value, station='A'):
    return dict(target_date=day, target_pm25=value, station_id=station)


class ErrorAnalysisTests(unittest.TestCase):
    def test_fold_excludes_future_and_unseen_stations(self):
        rows = [row('2020-12-31', 1), row('2021-01-01', 2),
                row('2021-06-01', 3, 'B'), row('2022-01-01', 999)]
        train, test, unseen = annual_fold(rows, 2021)
        self.assertEqual([r['target_pm25'] for r in train], [1])
        self.assertEqual([r['target_pm25'] for r in test], [2])
        self.assertEqual([r['station_id'] for r in unseen], ['B'])
        self.assertEqual(high_threshold(train), 1)

    def test_groups_keep_matching_predictions(self):
        rows = [row('2025-01-01', 2), row('2025-06-01', 10), row('2025-12-01', 4)]
        result = group_scores(rows, [1, 15, 2], lambda r: season(r['target_date']))
        self.assertEqual(result['DJF']['n'], 2)
        self.assertEqual(result['DJF']['mae'], 1.5)
        self.assertEqual(result['DJF']['bias'], -1.5)
        self.assertEqual(result['JJA']['mae'], 5)

    def test_saved_predictions_align_by_key_and_reject_stale_targets(self):
        rows = [row('2025-01-01', 1), row('2025-01-02', 2)]
        records = [dict(station_id='A', target_date=r['target_date'], observed=r['target_pm25'],
                        predicted=r['target_pm25']+1, model='m') for r in reversed(rows)]
        self.assertEqual(saved_predictions(rows, records, 'm').tolist(), [2, 3])
        with self.assertRaises(ValueError):
            saved_predictions(rows, records+records[:1], 'm')
        with self.assertRaises(ValueError):
            saved_predictions(rows, records[:1], 'm')
        records[0]['observed'] = 999
        with self.assertRaises(ValueError):
            saved_predictions(rows, records, 'm')


if __name__ == '__main__':
    unittest.main()
