# Data methods and weather milestone

Completed September 9, 2026. This is a retrospective research dataset, not an operational forecast service.

## Sources and selection

The original Florida DEP monthly tables remain preserved locally as reference data. We downloaded EPA site/monitor metadata and annual daily PM2.5 files for 2019–2025 from [EPA AirData](https://aqs.epa.gov/aqsweb/airdata/download_files.html). Source bytes, timestamps (or verification times for previously downloaded files), and SHA256 hashes are retained under `data/epa/`.

The method check matters: EPA's [T640/T640X advisory](https://aqs.epa.gov/aqsweb/airdata/Data_Advisory_PM25_88101_Pregen_Files.pdf) recommends network-aligned or corrected methods 636, 638, 736, and 738 rather than original methods 236 and 238. We also retain method 183, used earlier at two sites. The monitor listing's last method is not treated as the method for its entire history; each selected daily record carries its own method code.

Selection rules:

- Parameter 88101 and continuous-monitor POCs 3 or 23, within the requested station/date windows.
- Use daily summaries of `1 HOUR` samples with an empty pollutant-standard field. Their arithmetic mean is the daily mean, not an individual hourly observation. Do not confuse them with `24-HR BLK AVG` rows, where observation count is one daily block.
- Require at least 18 hourly observations and 75% observation coverage. This is a research completeness rule, not a claim that every selected day is regulator-certified.
- Retain events-included or no-event summaries; do not substitute event-excluded regulatory variants.
- Exclude original T640/T640X methods 236/238. Prefer 636/638 over corrected 736/738 when both occur on the same date. Preserve method 183 for its earlier period.
- Never average different instruments, methods, or regulatory summaries. Conflicting records at the same selection priority raise an error. Gravimetric POCs 1/2 are not substituted into the continuous series.

See [EPA field definitions](https://aqs.epa.gov/aqsweb/airdata/FileFormats.html) for daily summaries, method codes, event types, and local standard time. Individual hourly qualifier codes and annual certification status were not exhaustively audited; method/completeness selection does not establish unrestricted operational fitness.

## Results

| Station | Selected EPA days | DEP comparison days | Differences greater than 0.11 µg/m³ |
| --- | ---: | ---: | ---: |
| Coconut Creek | 2,429 | 2,429 | 1,683 |
| Pompano Highlands | 2,433 | 2,433 | 1,610 |
| Fort Lauderdale Near Road | 2,520 | 2,505 | 1,265 |
| Daniela Banu NCore | 2,507 | 2,502 | 1,454 |
| Vista View Park | 1,542 | 1,542 | 736 |
| Pompano | 122 | 122 | 0 |

Total: 11,553 selected EPA observations on an 11,874-row station/day calendar; 321 dates have no selected target. Twenty EPA observations occur on dates missing in the DEP tables. Of 11,533 overlapping numeric dates, 6,748 differ beyond the comparison tolerance. The tolerance of 0.11 accommodates the one-decimal display precision in DEP tables; it is not an instrument accuracy threshold. Do not combine uncorrected and corrected series as interchangeable training labels.

## Weather

[Weather data by Open-Meteo.com](https://open-meteo.com/), using the [ERA5 historical API](https://open-meteo.com/en/docs/historical-weather-api). ERA5 is gridded reanalysis, not a weather sensor at each air monitor. The model is fixed to ERA5 rather than the API's changing best-match blend. Its approximate 25 km grid can be shared by nearby sites; site-level requests are not independent local measurements.

Eight daily variables were downloaded: mean temperature, relative humidity, wind speed, sea-level pressure and cloud cover; precipitation sum; dominant wind direction; and solar-radiation sum. Values retain API units and are checked before use. There are 11,916 station/weather days including seven lead-in days per station, with zero missing weather values.

Weather uses fixed UTC−5 (`Etc/GMT+5`) to match the EPA local-standard day, rather than daylight-saving civil time. The returned UTC offset and complete date sequence are validated. EPA station coordinates are used for requests. Pompano Highlands is tagged NAD83; its coordinates are rounded to 0.01 degree for an explicitly approximate weather-grid lookup, not presented as a surveyed WGS84 transformation. Requested and returned grid coordinates are saved in `data/weather/grid_metadata.json`.

Open-Meteo API data are offered under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); see its [attribution guidance](https://open-meteo.com/en/licence). This project transforms the responses into station/date records and joins them with EPA observations. Credit Open-Meteo and Copernicus/ECMWF when displaying or redistributing the derived weather data. API service access terms are separate from the data licence and should be reviewed before deploying a public service.

## Forecasting boundary

`station_days.jsonl` is an aligned historical analysis table, not a ready-made supervised training matrix. Weather on a target date must not be used to predict that same date. Future feature construction must explicitly pair features through day t with an observed target on calendar day t+1, preserving gaps.

ERA5 is revised retrospective information and has publication latency (the API documents about five days). Even weather from day t may not have been available at a day-t issue time. An initial model can therefore evaluate a retrospective association/forecasting experiment, but cannot claim an as-issued operational backtest. For that claim, replace inputs with timestamped observations or archived forecasts available at issuance and audit pollutant reporting latency too.

## Reproduce

```powershell
python scripts/collect_dep_pm25.py
python scripts/enrich_broward_data.py
python -m unittest discover -s tests -v
```

The collection and enrichment scripts use Python's standard library. Modeling dependencies are listed in `requirements.txt`. Large source archives and generated data are ignored by Git. Relevant outputs:

- `data/epa/sites.json`, `monitors_pm25.json`: site coordinates and monitor metadata.
- `data/epa/daily_broward_raw.jsonl`: 37,682 EPA summary rows before selection.
- `data/epa/daily_pm25_selected.jsonl`: selected observations and method provenance.
- `data/epa/dep_comparison.jsonl`: comparison with original DEP readings.
- `data/weather/daily_weather.jsonl`: weather with date, station, units documented in grid metadata.
- `data/analysis/station_days.jsonl`: complete station calendar, selected EPA PM2.5, DEP reference, and weather.
- `data/analysis/enrichment_summary.json`: counts and method distributions.

The subsequent training milestone is documented in [baseline results](BASELINE_RESULTS.md). Its calendar-aligned builder and comparison can be run with `python scripts/build_training_data.py` and `python scripts/compare_baselines.py` after installing `requirements.txt`.
