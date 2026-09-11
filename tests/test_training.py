import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from build_training_data import build_examples, split_for
from compare_baselines import model_for, predict


def row(day, pm, station='A', weather=20):
    return dict(station_id=station, date=day, pm25_ug_m3=pm, temperature_2m_mean=weather)


class TrainingTests(unittest.TestCase):
    def test_calendar_gap_is_not_compressed(self):
        examples, _ = build_examples([row('2023-01-01', 1), row('2023-01-03', 3), row('2023-01-04', 4)])
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0]['feature_date'], '2023-01-03')
        self.assertIsNone(examples[0]['pm25_lag1'])
        self.assertEqual(examples[0]['pm25_lag2'], 1)

    def test_target_and_future_weather_do_not_enter_features(self):
        a = [row('2023-01-01', 2), row('2023-01-02', 3, weather=999)]
        b = [a[0], row('2023-01-02', 500, weather=-999)]
        first = build_examples(a)[0][0]
        second = build_examples(b)[0][0]
        self.assertEqual(first.pop('target_pm25'), 3)
        self.assertEqual(second.pop('target_pm25'), 500)
        self.assertEqual(first, second)

    def test_station_isolation_and_seven_day_window(self):
        start = date(2023, 1, 1)
        rows = [row((start+timedelta(days=i)).isoformat(), i) for i in range(9)]
        rows += [row('2023-01-08', 999, station='B')]
        ex = build_examples(rows)[0][-1]
        self.assertEqual(ex['pm25_lag7'], 0)
        self.assertEqual(ex['pm25_mean7'], 4)
        self.assertEqual(ex['pm25_count7'], 7)

    def test_target_date_controls_split_and_leap_day(self):
        ex = build_examples([row('2023-12-31', 1), row('2024-01-01', 2)])[0][0]
        self.assertEqual(ex['split'], 'validation')
        self.assertEqual(split_for('2025-01-01'), 'test')
        ex = build_examples([row('2024-02-28', 1), row('2024-02-29', 2)])[0][0]
        self.assertEqual(ex['target_date'], '2024-02-29')

    def test_missing_current_or_target_excluded_zero_preserved(self):
        examples, excluded = build_examples([row('2023-01-01', None), row('2023-01-02', 0), row('2023-01-03', 2)])
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0]['pm25_today'], 0)
        self.assertEqual(excluded['missing_today_for_persistence'], 1)

    def test_duplicate_and_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            build_examples([row('2023-01-01', 1)]*2)
        with self.assertRaises(ValueError):
            build_examples([row('2023-01-01', float('nan'))])

    def test_preprocessing_does_not_refit_on_evaluation(self):
        model = model_for('ridge_air')
        model.fit([[1, 2], [3, 4], [5, None]], [1, 2, 3])
        before = model.named_steps['simpleimputer'].statistics_.copy()
        model.predict([[999, None]])
        self.assertEqual(before.tolist(), [3, 3])
        self.assertEqual(model.named_steps['simpleimputer'].statistics_.tolist(), before.tolist())

    def test_persistence_uses_only_today(self):
        self.assertEqual(predict('persistence', [], [{'pm25_today': 2, 'target_pm25': 999}]).tolist(), [2])


if __name__ == '__main__':
    unittest.main()
