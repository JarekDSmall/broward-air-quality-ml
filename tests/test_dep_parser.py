"""Offline checks for report identity, missing values, and malformed DEP rows."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("collector", Path(__file__).resolve().parents[1] / "scripts" / "collect_dep_pm25.py")
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


def fixture():
    cells = "".join(f"<tr><td>FEB-{d}</td><td>{'*' if d == 3 else d / 10}</td>" for d in range(1, 30))
    return ('<h3>Readings for February 2020</h3><h5>AQS # L011-5005</h5>'
            '<table><h4>PM 2.5 Data</h4>Micrograms Per Cubic Meter' + cells +
            '<td>* = Value Not Available</td></table>'
            '<table><h4>PM 10 Data</h4><td>FEB-1</td><td>999</td></table>')


class ParserTests(unittest.TestCase):
    def test_leap_day_missing_marker_and_pm10_isolation(self):
        values = collector.parse_report(fixture(), "120115005", 2020, 2)
        self.assertEqual(len(values), 29)
        self.assertEqual(values[1], "0.1")
        self.assertEqual(values[3], "*")
        self.assertEqual(values[29], "2.9")

    def test_wrong_station_or_period_rejected(self):
        for station, year, month in [("120110033", 2020, 2), ("120115005", 2021, 2), ("120115005", 2020, 3)]:
            with self.assertRaises(ValueError):
                collector.parse_report(fixture(), station, year, month)

    def test_duplicate_or_missing_dates_rejected(self):
        for doc in [fixture().replace("FEB-29", "FEB-28"), fixture().replace("<tr><td>FEB-29</td><td>2.9</td>", "")]:
            with self.assertRaises(ValueError):
                collector.parse_report(doc, "120115005", 2020, 2)

    def test_unexpected_value_rejected(self):
        with self.assertRaises(ValueError):
            collector.parse_report(fixture().replace("<td>0.1</td>", "<td>unknown</td>"), "120115005", 2020, 2)

    def test_absent_table_distinct_from_numeric_zero(self):
        doc = '<h3>Readings for February 2020</h3><h5>AQS # L011-5005</h5>This site did not monitor PM2.5 during February, 2020.'
        self.assertIsNone(collector.parse_report(doc, "120115005", 2020, 2))
        self.assertEqual(collector.parse_report(fixture().replace("<td>0.1</td>", "<td>0</td>"), "120115005", 2020, 2)[1], "0")


if __name__ == "__main__":
    unittest.main()
