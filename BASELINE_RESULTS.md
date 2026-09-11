# Next-day PM2.5 baseline comparison

Retrospective experiment using corrected EPA PM2.5 and ERA5 weather. Errors are in µg/m³.

Train: target dates through 2023. Validation: 2024. Test: 2025. All candidates use identical eligible rows.
Counts: 7,834 training, 1,739 validation, 1,910 test (including the new Pompano station).

**Selected using validation MAE: boosted_weather.** All fixed candidates are then refitted through 2024.

## Five established stations

| Candidate | 2024 validation MAE | 2025 test MAE | 2025 test RMSE | Test bias |
| --- | ---: | ---: | ---: | ---: |
| persistence | 1.762 | 1.466 | 2.234 | -0.003 |
| rolling_mean7 | 2.034 | 1.650 | 2.363 | -0.023 |
| ridge_air | 1.670 | 1.410 | 1.994 | 0.213 |
| ridge_weather | 1.651 | 1.431 | 2.013 | 0.264 |
| boosted_weather | 1.592 | 1.433 | 2.050 | 0.302 |

## Selected candidate versus persistence by station (2025)

| Station | Days | Persistence MAE | Selected MAE |
| --- | ---: | ---: | ---: |
| 120110033 | 344 | 1.248 | 1.277 |
| 120110034 | 365 | 1.479 | 1.416 |
| 120110035 | 362 | 1.664 | 1.547 |
| 120110037 (new Pompano; unseen station) | 121 | 0.978 | 0.969 |
| 120112003 | 365 | 1.648 | 1.526 |
| 120115005 | 353 | 1.272 | 1.392 |

## Interpretation and limits

- Persistence predicts tomorrow equals today; rolling_mean7 averages available observations from today through six days earlier.
- Ridge uses alpha=10. Air features include current PM2.5, calendar lags 1/2/7, seven-day mean/count and annual sine/cosine. Weather adds day-t ERA5 variables and circular wind direction.
- Gradient boosting uses 150 iterations, 15 leaves, learning rate 0.05, L2=10, seed=42, and no internal random validation split. No hyperparameter search was performed.
- Median imputation and scaling fit only on each training period. Station IDs and method codes are not model features. Missing targets/current PM2.5 are excluded; missing older lags remain missing until training-only imputation.
- Test evaluation is rolling one-day-ahead with each preceding day observed, not a recursive year-ahead forecast. The target date determines its split. No target-day weather is used.
- Pompano starts September 2025 and is reported separately. Aggregate errors weight station-days equally; sites share weather and pollution events, so rows are not independent.
- Revised EPA history and delayed ERA5 reanalysis cannot establish as-issued forecast accuracy. No statistical significance, operational readiness or health-risk claim is made.
- This is the first fixed holdout comparison. Further tuning informed by these test results would require a new untouched holdout.

Environment: Python 3.14.4, NumPy 2.5.1, scikit-learn 1.9.0.
Training file SHA256: `a0ca690b8476ac1059a35e30ccc1260c879f15f57bd7a1d02a4d4dcc8ac35702`.

Detailed metrics and row-level test predictions are generated locally under `reports/baselines/`.
