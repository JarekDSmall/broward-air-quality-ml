# Broward Air Quality ML

A local research project developing next-day PM2.5 prediction for six air-monitoring stations in Broward County, Florida.

## Current milestone

Collected and audited 390 Florida DEP monthly reports through December 2025: 11,533 reported daily PM2.5 values across 11,874 station-days. Missing observations remain null.

EPA method verification and weather enrichment are complete: the modeling dataset now uses 11,553 method-checked EPA observations and eight ERA5 weather variables. The original DEP values remain a comparison source. See [data methods and limitations](DATA_METHODS.md), including corrected instrument data and retrospective weather availability.

Built 11,483 next-day examples and compared persistence, a seven-day mean, ridge regression and gradient boosting. Training uses 2019–2023, validation uses 2024 and testing uses 2025. The validation-selected boosting model reduced established-station test MAE from 1.466 to 1.433 µg/m³ (about 2.3%). Pollution-only ridge achieved 1.410; adding weather did not consistently help on the test year. See [full results and station-level comparisons](BASELINE_RESULTS.md). These are retrospective results, not operational forecasts.

## Reproduce the data audit

To explore the included historical demo immediately, open `demo/dist/index.html` in a browser. Python and the raw research data are not needed for this path. For a local web address, run `python -m http.server 8765 --bind 127.0.0.1 --directory demo/dist` and open http://127.0.0.1:8765.

For full reproduction, use a virtual environment from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux, activate with `source .venv/bin/activate`. Collection and enrichment download external data; subsequent runs reuse successful cached source downloads. Numerical package versions are pinned to the tested environment.

Collection and enrichment use Python's standard library. Modeling and its tests require the pinned packages below; the complete workflow was verified with Python 3.14.4.

```powershell
python -m pip install -r requirements.txt
python scripts/collect_dep_pm25.py
python scripts/enrich_broward_data.py
python scripts/build_training_data.py
python scripts/compare_baselines.py
python scripts/analyze_errors.py
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

Completed [error analysis and expanding-year evaluation](ERROR_ANALYSIS.md): all three regression candidates beat persistence in each of 2021–2024, but performance varies by station and season. The validation-selected model underpredicts the 113 high-concentration station-days in 2025 by 3.947 µg/m³ on average. This is a relative concentration group, not a health category. Full diagnostics and earlier-fold predictions are generated under `reports/error_analysis/`.

The original validation-selected model is now packaged with a historical replay command and a local demo. See the [model card and commands](MODEL_CARD.md). Run `python scripts/historical_model.py package`, then `python scripts/export_demo.py`, and open `demo/dist/index.html`. The demo includes station/month filters, observed/model/persistence curves, average errors, daily values, and limitations. Its static historical data is included for immediate exploration; large raw archives and trained artifacts remain local.

Any choices informed by the 2025 results must treat that year as examined data and reserve a new holdout for final confirmation. Public portfolio integration is the next delivery step.

## Repository checks and architecture

[Repository checks](.github/workflows/checks.yml) run on pushes and pull requests using Windows and Linux with Python 3.14. They install dependencies, run the offline tests, validate the committed demo's historical rows and local assets, and check JavaScript syntax. They do not access ignored source archives or retrain the model. The first hosted run must be confirmed after pushing the workflow.

Run the same checks locally with:

```powershell
python -m unittest discover -s tests -v
python scripts/check_demo.py
node --check demo/dist/app.js
node --check demo/dist/data.js
```

Node.js 24 is used for JavaScript syntax checks; it is not needed to browse the demo. The [architecture diagram](ARCHITECTURE.md) describes each pipeline stage and what is tracked versus generated. The [model card](MODEL_CARD.md) includes packaging and replay commands.

Coverage is the presence of a reported number, not proof of regulatory validity or hourly completeness. PM2.5 method history, weather provenance, and data availability at forecast time must be documented before claiming operational forecast accuracy.

This project grew out of my computer science coursework. Original course implementations and materials remain separate, ignored local references; this repository starts with the new public-data workflow.
