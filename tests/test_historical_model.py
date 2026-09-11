import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from historical_model import select_row


class HistoricalModelTests(unittest.TestCase):
    def test_rejects_training_dates_and_future_dates(self):
        for day in ['2024-12-31', '2026-01-01', '2025-02-30']:
            with self.assertRaises(ValueError):
                select_row([], 'A', day)

    def test_requires_exact_eligible_station_date(self):
        rows = [dict(station_id='A', target_date='2025-01-01')]
        self.assertEqual(select_row(rows, 'A', '2025-01-01'), rows[0])
        for station, day in [('B', '2025-01-01'), ('A', '2025-01-02')]:
            with self.assertRaises(ValueError):
                select_row(rows, station, day)
        with self.assertRaises(ValueError):
            select_row(rows*2, 'A', '2025-01-01')
