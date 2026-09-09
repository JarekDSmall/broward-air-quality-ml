# Broward PM2.5 source inventory

Reviewed September 8, 2026. Project direction: next-day mean PM2.5 prediction at Broward monitoring stations, subject to a historical data coverage audit. The existing school-data pipeline has not yet been adapted.

**Update:** The monthly audit has been extended through December 2025 for all six stations. See [BROWARD_COVERAGE_AUDIT.md](BROWARD_COVERAGE_AUDIT.md) for calculated results. Collection starts in January 2019 for Coconut Creek, Fort Lauderdale Near Road, and Daniela Banu; April 2019 for Pompano Highlands; August 2021 for Vista View; and September 2025 for Pompano, following the user's supplied ranges. The initial page-navigation observations below are historical research notes, not the measured coverage results.

## Candidate stations

| AQS site ID | Station | Findings from supplied DEP page |
| --- | --- | --- |
| 12-011-0033 | [Vista View Park](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/SiteDetail/120110033/2025) | PM2.5 start listed as August 1, 2021; PM2.5 year links cover 2021–2025. |
| 12-011-0034 | [Daniela Banu (NCore)](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/SiteDetail/120110034/2025) | PM2.5 year links cover 2011–2025; also lists ozone, PM10, SO2, and CO. |
| 12-011-0035 | [Fort Lauderdale Near Road](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/SiteDetail/120110035/2025) | PM2.5 year links cover 2011–2025; also lists NO2 and CO monitoring. |
| 12-011-0037 | [Pompano](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/SiteDetail/120110037/2026) | Supplied link uses 2026. Detail page could not be retrieved; history unverified. |
| 12-011-2003 | [Pompano Highlands Fire House](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/SiteDetail/120112003/2025) | Detail page could not be retrieved; history unverified. |
| 12-011-5005 | [Coconut Creek](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/SiteDetail/120115005/2025) | Actual monthly PM2.5 readings verified for 2019: 336 of 365 days. December 2018 page had no PM2.5 table. Earlier year links are not evidence of observations. |

Station names and PM2.5 inclusion are listed in the [DEP Broward directory](https://floridadep.gov/air/air-monitoring/content/broward-county-air-monitoring).

## Interpretation

Year-navigation links do not establish actual measurement completeness. Several detail pages list the same January 1, 1984 monitoring start date across pollutants; treat those dates as unverified metadata until checked against monitor records and observations. Do not infer a continuous PM2.5 history from them. The 2026 URL alone does not establish Pompano's opening date.

The web search tool failed to retrieve monthly reports, but subsequent browser inspection and direct HTTP downloads succeeded. Daily observations are now saved locally in `data/broward_dep/daily_pm25.jsonl`, with cached source pages and retrieval metadata. Instrument methods, underlying hourly completeness, and quality flags remain unverified. No observations have been used for training.

## Coconut Creek monthly verification

The user identified the monthly URL pattern. All 12 report pages were read in the browser on September 8, 2026. Values are labeled daily average PM2.5 in micrograms per cubic meter; an asterisk means unavailable.

| Month (source report) | Numeric readings / calendar days | Unavailable dates |
| --- | --- | --- |
| [January](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/Monthly/120115005/01/2019/*) | 31 / 31 | None |
| [February](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/Monthly/120115005/02/2019/*) | 28 / 28 | None |
| [March](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/Monthly/120115005/03/2019/*) | 31 / 31 | None |
| [April](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/Monthly/120115005/04/2019/*) | 30 / 30 | None |
| [May](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/Monthly/120115005/05/2019/*) | 31 / 31 | None |
| [June](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/Monthly/120115005/06/2019/*) | 30 / 30 | None |
| [July](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/Monthly/120115005/07/2019/*) | 31 / 31 | None |
| [August](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/Monthly/120115005/08/2019/*) | 29 / 31 | August 30–31 |
| [September](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/Monthly/120115005/09/2019/*) | 24 / 30 | September 1–6 |
| [October](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/Monthly/120115005/10/2019/*) | 30 / 31 | October 9 |
| [November](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/Monthly/120115005/11/2019/*) | 10 / 30 | November 3–22 |
| [December](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/Monthly/120115005/12/2019/*) | 31 / 31 | None |

Total: 336 numeric daily averages out of 365 days (92.1%); 29 unavailable days. Longest unavailable run: November 3–22, 20 days. These counts measure presence on the report, not regulatory validity or underlying hourly completeness.

The [December 2018 report](https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/Monthly/120115005/12/2018/*) had no PM2.5 table. This supports starting the current audit in January 2019, but does not prove no earlier measurements exist elsewhere or establish the instrument's commissioning date.

## Next data audit

Use [EPA AirData downloads](https://aqs.epa.gov/aqsweb/airdata/download_files.html) to obtain monitor metadata and daily PM2.5 records. Initially investigate 2015–2025, filtering to Florida state code 12, Broward county code 011, and these six site numbers. Keep identifiers as strings so leading zeros are preserved.

For each station and year, calculate first/last observation dates, valid days, missing days, sampling frequency, and longest gap. Check parameter codes, units, instrument methods, and co-located monitor identifiers before combining records; avoid counting multiple summaries of the same observation as separate training examples.

Daniela Banu is a provisional first candidate because the page offers a longer PM2.5 year range and multiple pollutants. Confirm this choice using actual coverage. Vista View cannot support the full proposed 2015–2025 interval based on its listed PM2.5 start.

Forecasts should initially be station-specific, with chronological evaluation and a persistence baseline. Weather and pollution predictors must be available at the forecast issue time; future observed weather must not enter training features for a purported next-day forecast.
