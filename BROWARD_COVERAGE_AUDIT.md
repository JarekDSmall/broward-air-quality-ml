# Broward PM2.5 historical coverage audit

Retrieved 390 monthly reports; 0 errors. Sources are Florida DEP FLAQS monthly report tables.

Ranges follow the user-provided starting months and end in December 2025. Partial first years use only inspected months as the denominator. Start months are collection boundaries, not verified instrument commissioning dates.

| Station | Year | Readings / inspected days | Missing | Coverage |
| --- | --- | --- | --- | --- |
| Coconut Creek | 2019 | 336 / 365 | 29 | 92.1% |
| Coconut Creek | 2020 | 363 / 366 | 3 | 99.2% |
| Coconut Creek | 2021 | 359 / 365 | 6 | 98.4% |
| Coconut Creek | 2022 | 360 / 365 | 5 | 98.6% |
| Coconut Creek | 2023 | 341 / 365 | 24 | 93.4% |
| Coconut Creek | 2024 | 313 / 366 | 53 | 85.5% |
| Coconut Creek | 2025 | 357 / 365 | 8 | 97.8% |
| Pompano Highlands Fire House | 2019 | 258 / 275 | 17 | 93.8% |
| Pompano Highlands Fire House | 2020 | 362 / 366 | 4 | 98.9% |
| Pompano Highlands Fire House | 2021 | 361 / 365 | 4 | 98.9% |
| Pompano Highlands Fire House | 2022 | 360 / 365 | 5 | 98.6% |
| Pompano Highlands Fire House | 2023 | 363 / 365 | 2 | 99.5% |
| Pompano Highlands Fire House | 2024 | 364 / 366 | 2 | 99.5% |
| Pompano Highlands Fire House | 2025 | 365 / 365 | 0 | 100.0% |
| Fort Lauderdale Near Road | 2019 | 339 / 365 | 26 | 92.9% |
| Fort Lauderdale Near Road | 2020 | 361 / 366 | 5 | 98.6% |
| Fort Lauderdale Near Road | 2021 | 363 / 365 | 2 | 99.5% |
| Fort Lauderdale Near Road | 2022 | 359 / 365 | 6 | 98.4% |
| Fort Lauderdale Near Road | 2023 | 365 / 365 | 0 | 100.0% |
| Fort Lauderdale Near Road | 2024 | 355 / 366 | 11 | 97.0% |
| Fort Lauderdale Near Road | 2025 | 363 / 365 | 2 | 99.5% |
| Daniela Banu (NCore) | 2019 | 345 / 365 | 20 | 94.5% |
| Daniela Banu (NCore) | 2020 | 357 / 366 | 9 | 97.5% |
| Daniela Banu (NCore) | 2021 | 362 / 365 | 3 | 99.2% |
| Daniela Banu (NCore) | 2022 | 358 / 365 | 7 | 98.1% |
| Daniela Banu (NCore) | 2023 | 364 / 365 | 1 | 99.7% |
| Daniela Banu (NCore) | 2024 | 351 / 366 | 15 | 95.9% |
| Daniela Banu (NCore) | 2025 | 365 / 365 | 0 | 100.0% |
| Vista View Park | 2021 | 142 / 153 | 11 | 92.8% |
| Vista View Park | 2022 | 336 / 365 | 29 | 92.1% |
| Vista View Park | 2023 | 352 / 365 | 13 | 96.4% |
| Vista View Park | 2024 | 365 / 366 | 1 | 99.7% |
| Vista View Park | 2025 | 347 / 365 | 18 | 95.1% |
| Pompano | 2025 | 122 / 122 | 0 | 100.0% |

## Longest gaps by station

- Coconut Creek: 48 days, 2024-10-02 through 2024-11-18. [Source month](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/Monthly/120115005/10/2024/*)
- Pompano Highlands Fire House: 11 days, 2019-04-01 through 2019-04-11. [Source month](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/Monthly/120112003/04/2019/*)
- Fort Lauderdale Near Road: 11 days, 2019-08-30 through 2019-09-09. [Source month](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/Monthly/120110035/08/2019/*)
- Daniela Banu (NCore): 15 days, 2024-03-18 through 2024-04-01. [Source month](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/Monthly/120110034/03/2024/*)
- Vista View Park: 18 days, 2022-09-18 through 2022-10-05. [Source month](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/Monthly/120110033/09/2022/*)
- Pompano: no missing dates in the inspected reports.

## Files and interpretation

- `data/broward_dep/daily_pm25.jsonl`: one record per calendar day; null indicates missing, never zero-filled.
- `data/broward_dep/monthly_audit.json`: source links, retrieval timestamps, HTML SHA256 hashes and monthly coverage.
- `data/broward_dep/annual_coverage.json` and `missing_runs.json`: calculated summaries.
- `data/broward_dep/source_html/`: cached source HTML and retrieval metadata.

Reported numeric values are daily PM2.5 averages in micrograms per cubic meter. Presence of a value does not establish regulatory validity, hourly completeness, instrument comparability, or real-time availability. Causes of gaps have not been established. No values were imputed, no weather data were joined, and no model was trained.

Before modeling, verify monitor methods and quality metadata against EPA AQS, preserve calendar gaps when creating lags and next-day targets, and use chronological evaluation. Missing targets must not be invented. Long gaps warrant a second station for comparison.

Re-run `python scripts/collect_dep_pm25.py` to regenerate from cached HTML or retrieve missing months. Collection uses at most three concurrent requests, bounded retries, and fails visibly on malformed tables.
