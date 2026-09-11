import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from check_demo import validate_history


class DemoDataTests(unittest.TestCase):
    def fixture(self):
        return dict(stations={'A': 'Example'}, rows=[dict(station='A', date='2025-01-01',
                    observed=0, predicted=1.5, persistence=2)])

    def test_valid_zero_retained(self):
        self.assertEqual(validate_history(self.fixture()), {'A': 1})

    def test_duplicate_rejected(self):
        history = self.fixture()
        history['rows'] *= 2
        with self.assertRaises(ValueError):
            validate_history(history)

    def test_invalid_data_rejected(self):
        for field, value in [('date', '2024-12-31'), ('station', 'B'),
                             ('predicted', float('nan')), ('observed', True), ('persistence', None)]:
            with self.subTest(field=field):
                history = self.fixture()
                history['rows'][0][field] = value
                with self.assertRaises(ValueError):
                    validate_history(history)
