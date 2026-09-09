# Broward Air Quality ML

A local research project developing next-day PM2.5 prediction for six air-monitoring stations in Broward County, Florida.

## Current milestone

Collected and audited 390 Florida DEP monthly reports through December 2025: 11,533 reported daily PM2.5 values across 11,874 station-days. Missing observations remain null. No forecasting model has been trained yet.

EPA method verification and weather enrichment are complete: the modeling dataset now uses 11,553 method-checked EPA observations and eight ERA5 weather variables. The original DEP values remain a comparison source. See [data methods and limitations](DATA_METHODS.md), including corrected instrument data and retrospective weather availability.

## Reproduce the data audit

Requires Python 3.10+; the collector and tests use only the standard library.

```powershell
python scripts/collect_dep_pm25.py
python scripts/enrich_broward_data.py
python -m unittest discover -s tests -v
```

The collector downloads source HTML, records retrieval timestamps and SHA256 hashes, validates station/month identity and daily rows, and caches successful downloads. Repeated runs reuse the cache. Outputs are local and excluded from Git:

- `data/broward_dep/daily_pm25.jsonl`: reported daily means in micrograms per cubic meter, with source URLs and missing-value status.
- `data/broward_dep/monthly_audit.json`: source provenance and monthly completeness.
- `data/broward_dep/annual_coverage.json` and `missing_runs.json`: calculated coverage and gaps.
- `data/broward_dep/source_html/`: source pages and retrieval metadata.

See [the coverage audit](BROWARD_COVERAGE_AUDIT.md) and [source research](BROWARD_DATA_SOURCES.md).

## Forecasting plan

Verify monitor methods, attach weather data with explicit time alignment, then compare a persistence baseline with regression models using chronological evaluation. The first target is a measured pollutant concentration at a station, not a synthetic health score.

Coverage is the presence of a reported number, not proof of regulatory validity or hourly completeness. PM2.5 method history, weather provenance, and data availability at forecast time must be documented before claiming operational forecast accuracy.

This project grew out of my computer science coursework. Original course implementations and materials remain separate, ignored local references; this repository starts with the new public-data workflow.
