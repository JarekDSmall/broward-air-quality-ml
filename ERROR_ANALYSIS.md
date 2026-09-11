# Error analysis and earlier-year validation

Fixed baseline settings were reused without tuning. Errors are in µg/m³; lower MAE is better.

## Expanding annual evaluation

Each fold trains on all earlier target dates and predicts the following year using preceding-day observations. Imputation/scaling fit within that fold. Stations with no earlier training history are excluded from these fold aggregates.

| Evaluation year | Training rows | Evaluation rows | Unseen rows excluded |
| --- | ---: | ---: | ---: |
| 2021 | 2720 | 1438 | 141 |
| 2022 | 4299 | 1760 | 0 |
| 2023 | 6059 | 1775 | 0 |
| 2024 | 7834 | 1739 | 0 |

| Candidate | 2021 MAE | 2022 MAE | 2023 MAE | 2024 MAE | Years beating persistence |
| --- | ---: | ---: | ---: | ---: | ---: |
| persistence | 1.768 | 1.837 | 2.046 | 1.762 | 0/4 |
| rolling_mean7 | 2.135 | 2.032 | 2.243 | 2.034 | 0/4 |
| ridge_air | 1.651 | 1.722 | 1.896 | 1.670 | 4/4 |
| ridge_weather | 1.635 | 1.738 | 1.854 | 1.651 | 4/4 |
| boosted_weather | 1.738 | 1.788 | 1.826 | 1.592 | 4/4 |

## 2025 diagnostic slices

These reuse saved first-run 2025 predictions; no models are refitted for the slices. Seasons use calendar quarters DJF/MAM/JJA/SON, not a local wet/dry season classification.

High-pollution observations are at or above the pooled training-period (2019–2024) 90th percentile: **11.012 µg/m³**. This is a descriptive relative threshold, not an AQI or health category. Grouping by the observed target is for analysis only.

### Station

| Group | Days | Persistence MAE | Air ridge MAE | Weather ridge MAE | Boosting MAE | Boosting bias |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Vista View Park | 344 | 1.248 | 1.278 | 1.274 | 1.277 | 0.436 |
| Daniela Banu (NCore) | 365 | 1.479 | 1.414 | 1.406 | 1.416 | 0.249 |
| Fort Lauderdale Near Road | 362 | 1.664 | 1.493 | 1.522 | 1.547 | 0.053 |
| Pompano (unseen; separate) | 121 | 0.978 | 1.014 | 0.921 | 0.969 | 0.310 |
| Pompano Highlands Fire House | 365 | 1.648 | 1.530 | 1.564 | 1.526 | 0.246 |
| Coconut Creek | 353 | 1.272 | 1.325 | 1.380 | 1.392 | 0.541 |

### Season

| Group | Days | Persistence MAE | Air ridge MAE | Weather ridge MAE | Boosting MAE | Boosting bias |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DJF | 447 | 1.483 | 1.369 | 1.324 | 1.360 | 0.234 |
| JJA | 438 | 2.193 | 2.023 | 2.214 | 2.220 | 0.354 |
| MAM | 455 | 1.469 | 1.334 | 1.402 | 1.376 | 0.161 |
| SON | 449 | 0.735 | 0.930 | 0.805 | 0.797 | 0.462 |

### Concentration

| Group | Days | Persistence MAE | Air ridge MAE | Weather ridge MAE | Boosting MAE | Boosting bias |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| high | 113 | 4.598 | 4.571 | 4.494 | 4.415 | -3.947 |
| other | 1676 | 1.254 | 1.197 | 1.225 | 1.232 | 0.588 |

## Largest daily errors for validation-selected boosting (2025)

Mean absolute error across available established stations on each date. These identify cases to inspect; they do not establish a pollution source or cause.

| Target date | Stations | MAE | Bias |
| --- | ---: | ---: | ---: |
| 2025-06-27 | 5 | 9.015 | -9.015 |
| 2025-07-24 | 5 | 8.340 | -8.340 |
| 2025-06-12 | 5 | 7.519 | -7.519 |
| 2025-08-20 | 5 | 7.421 | -6.316 |
| 2025-06-05 | 4 | 7.273 | -7.273 |
| 2025-01-01 | 5 | 6.364 | -6.364 |
| 2025-08-21 | 5 | 6.006 | -1.955 |
| 2025-07-05 | 5 | 5.867 | 5.867 |
| 2025-06-09 | 4 | 5.542 | 5.542 |
| 2025-03-01 | 5 | 5.488 | -5.488 |

## Findings

Air-only ridge beats persistence in 4/4 earlier years; weather ridge in 4/4; boosting in 4/4. The model ranking varies by year, so there is no consistent winner across all periods.

The validation-selected model has MAE 4.415 and bias -3.947 on 113 high-concentration station-days in 2025. This subgroup is substantially harder than ordinary days; low overall error should not be presented as reliable peak prediction.

For the first historical demo, retain the original validation-selected boosting model and show persistence alongside it. Keep air-only ridge as the simpler comparison. Investigate large-error dates before considering new features, and use a new untouched period for any subsequent final model comparison.

## Evaluation boundaries

- Earlier-year folds are retrospective development diagnostics, not newly untouched tests: those years contributed to the original model-development dataset. 2024 repeats the original validation period.
- Station availability changes across years (Vista View first appears in the seen-station evaluation in 2022). Year-to-year differences reflect both coverage and conditions.
- Station-days are correlated. No independence-based significance tests or confidence claims are made. Bias is prediction minus observation; negative values mean underprediction.
- Seasons/concentration groups exclude the new Pompano monitor; the station table includes its separate short evaluation.
- No candidate or parameter was changed after inspecting 2025. The original validation-selected candidate remains boosting; a new final evaluation needs data not used for these decisions.
- Reanalysis and revised pollutant histories retain the availability limitations documented in DATA_METHODS.md.

Training SHA256: `a0ca690b8476ac1059a35e30ccc1260c879f15f57bd7a1d02a4d4dcc8ac35702`. Full slice metrics (including RMSE/bias) and earlier-fold predictions are in `reports/error_analysis/`.
