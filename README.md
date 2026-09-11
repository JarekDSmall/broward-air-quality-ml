# Broward Air Quality ML

A local research project developing next-day PM2.5 prediction for six air-monitoring stations in Broward County, Florida.

## Current milestone

Collected and audited 390 Florida DEP monthly reports through December 2025: 11,533 reported daily PM2.5 values across 11,874 station-days. Missing observations remain null.

EPA method verification and weather enrichment are complete: the modeling dataset now uses 11,553 method-checked EPA observations and eight ERA5 weather variables. The original DEP values remain a comparison source. See [data methods and limitations](DATA_METHODS.md), including corrected instrument data and retrospective weather availability.

Built 11,483 next-day examples and compared persistence, a seven-day mean, ridge regression and gradient boosting. Training uses 2019–2023, validation uses 2024 and testing uses 2025. The validation-selected boosting model reduced established-station test MAE from 1.466 to 1.433 µg/m³ (about 2.3%). Pollution-only ridge achieved 1.410; adding weather did not consistently help on the test year. See [full results and station-level comparisons](BASELINE_RESULTS.md). These are retrospective results, not operational forecasts.

## Reproduce the data audit

Collection and enrichment use Python's standard library. Modeling and its tests require the pinned packages below; the complete workflow was verified with Python 3.14.4.

```powershell
python -m pip install -r requirements.txt
python scripts/collect_dep_pm25.py
python scripts/enrich_broward_data.py
python scripts/build_training_data.py
python scripts/compare_baselines.py
python -m unittest discover -s tests -v
```

The collector downloads source HTML, records retrieval timestamps and SHA256 hashes, validates station/month identity and daily rows, and caches successful downloads. Repeated runs reuse the cache. Outputs are local and excluded from Git:

- `data/broward_dep/daily_pm25.jsonl`: reported daily means in micrograms per cubic meter, with source URLs and missing-value status.
- `data/broward_dep/monthly_audit.json`: source provenance and monthly completeness.
- `data/broward_dep/annual_coverage.json` and `missing_runs.json`: calculated coverage and gaps.
- `data/broward_dep/source_html/`: source pages and retrieval metadata.

See [the coverage audit](BROWARD_COVERAGE_AUDIT.md) and [source research](BROWARD_DATA_SOURCES.md).

## Training and evaluation

Training rows pair features through day t with measured PM2.5 on calendar day t+1. Missing current readings or targets are excluded for fair persistence comparisons; older missing lags are imputed using training data only. The new Pompano station is evaluated separately because it has no pre-2025 training history. Local outputs include `data/training/next_day.jsonl`, its source-hash/count manifest, and `reports/baselines/` metrics and per-day predictions. Scripts print their results and regenerate the tracked results report.

The next analysis is to examine seasonal and pollution-event errors and assess stability across earlier chronological folds. Any choices informed by the 2025 results must treat that year as examined data and reserve a new holdout for final confirmation.

Coverage is the presence of a reported number, not proof of regulatory validity or hourly completeness. PM2.5 method history, weather provenance, and data availability at forecast time must be documented before claiming operational forecast accuracy.

This project grew out of my computer science coursework. Original course implementations and materials remain separate, ignored local references; this repository starts with the new public-data workflow.
