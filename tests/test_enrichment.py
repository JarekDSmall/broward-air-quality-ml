import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from enrich_broward_data import select_epa, weather_records, VARIABLES, EXPECTED_UNITS


def sample(**changes):
    row={'State Code':'12','County Code':'011','Site Num':'5005',
         'Date Local':'2020-02-29','Parameter Code':'88101','POC':'23',
         'Sample Duration':'1 HOUR','Pollutant Standard':'','Method Code':'736',
         'Method Name':'Corrected T640','Event Type':'None',
         'Units of Measure':'Micrograms/cubic meter (LC)',
         'Observation Count':'24','Observation Percent':'100',
         'Arithmetic Mean':'5.5','Date of Last Change':'2025-09-23'}
    row.update(changes)
    return row


class EPATests(unittest.TestCase):
    def test_excludes_uncorrected_and_block_summary(self):
        rows=[sample(), sample(**{'Method Code':'236','POC':'3'}),
              sample(**{'Sample Duration':'24-HR BLK AVG','Observation Count':'1'})]
        selected,excluded=select_epa(rows)
        self.assertEqual(len(selected),1)
        self.assertEqual(selected[0]['method_code'],'736')
        self.assertEqual(excluded['unapproved_or_uncorrected_method'],1)

    def test_hourly_completeness_threshold(self):
        self.assertEqual(len(select_epa([sample(**{'Observation Count':'18','Observation Percent':'75'})])[0]),1)
        self.assertEqual(select_epa([sample(**{'Observation Count':'17','Observation Percent':'70.8'})])[0],[])

    def test_keeps_events_included_but_not_excluded(self):
        self.assertEqual(len(select_epa([sample(**{'Event Type':'Included'})])[0]),1)
        self.assertEqual(select_epa([sample(**{'Event Type':'Excluded'})])[0],[])

    def test_duplicate_summaries_not_double_counted(self):
        self.assertEqual(len(select_epa([sample(),sample()])[0]),1)

    def test_ambiguous_same_rank_is_error(self):
        with self.assertRaises(ValueError):
            select_epa([sample(),sample(**{'Arithmetic Mean':'9'})])

    def test_aligned_method_priority(self):
        selected,_=select_epa([sample(),sample(**{'Method Code':'636','POC':'3','Arithmetic Mean':'5.6'})])
        self.assertEqual(selected[0]['method_code'],'636')


class WeatherTests(unittest.TestCase):
    def payload(self):
        return {'utc_offset_seconds':-18000,'daily_units':dict(EXPECTED_UNITS),
                'daily':{'time':['2020-02-28','2020-02-29','2020-03-01'],
                         **{v:[1,None,3] for v in VARIABLES}}}

    def test_leap_day_and_missing_weather_preserved(self):
        rows=weather_records(json.dumps(self.payload()),'120115005','2020-02-28','2020-03-01')
        self.assertEqual(rows[1]['date'],'2020-02-29')
        self.assertIsNone(rows[1]['temperature_2m_mean'])

    def test_dst_offset_rejected(self):
        obj=self.payload(); obj['utc_offset_seconds']=-14400
        with self.assertRaises(ValueError):
            weather_records(json.dumps(obj),'120115005','2020-02-28','2020-03-01')

    def test_wrong_units_or_dates_rejected(self):
        obj=self.payload(); obj['daily_units']['wind_speed_10m_mean']='km/h'
        with self.assertRaises(ValueError):
            weather_records(json.dumps(obj),'120115005','2020-02-28','2020-03-01')
        obj=self.payload(); obj['daily']['time'][1]='2020-02-28'
        with self.assertRaises(ValueError):
            weather_records(json.dumps(obj),'120115005','2020-02-28','2020-03-01')


if __name__=='__main__':
    unittest.main()
