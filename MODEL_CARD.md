# Historical Broward PM2.5 model

## Intended use

Educational portfolio exploration of next-day PM2.5 at six Broward County monitors during 2025. The packaged gradient boosting pipeline was selected by 2024 validation MAE, then trained on 9,573 examples with target dates through December 31, 2024. It is not a live forecasting or health-advice system.

## Inputs and output

Seventeen numerical inputs describe PM2.5 through day t, exact calendar lags, seven-day history, annual seasonality and day-t ERA5 weather. Output is predicted PM2.5 in µg/m³ for t+1. Station identity is not a feature. Missing historical inputs use training-period median imputation. The replay command supports only eligible dates in 2025 and displays the later observed target separately; the observation is not supplied to the estimator.

## Evaluation

Across 1,789 test station-days at five established sites, MAE is 1.433 versus persistence's 1.466 µg/m³. Pompano's 121 station-days are evaluated separately. On 113 relatively high-concentration station-days, model MAE is 4.415 and bias is −3.947 µg/m³. Persistence wins at some stations and seasons. See [baseline results](BASELINE_RESULTS.md) and [error analysis](ERROR_ANALYSIS.md).

The package command reloads the saved artifact and checks all 1,910 predictions against the original evaluation to numerical tolerance. The artifact manifest records the input hash, model hash, feature order, library versions and training cutoff. Data changes require rebuilding; comparisons fail if the original predictions no longer match.

## Limitations

EPA history includes instrument corrections, and ERA5 is delayed/revised gridded reanalysis. Historical inputs are not evidence of real-time availability. Sites share regional conditions; station-days are correlated. Results do not establish reliable peak prediction, statistical significance or generalization outside the study area. The 2025 period has now been examined; further model selection needs a new untouched evaluation period.

## Local reproduction

After the data and baseline workflow in README.md:

```powershell
python scripts/historical_model.py package
python scripts/historical_model.py predict --station 120115005 --date 2025-06-27
python scripts/export_demo.py
python -m http.server 8765 --bind 127.0.0.1 --directory demo/dist
```

Open http://127.0.0.1:8765. The static demo also works by opening `demo/dist/index.html` directly. It runs no live model or external API calls; its data file contains verified historical results. The model artifact stays ignored under `models/`; recreate it locally. Load only the locally generated joblib artifact, because pickle-based files can execute code.

## Sources

US EPA AirData PM2.5; Open-Meteo / Copernicus ECMWF ERA5 weather, with CC BY 4.0 attribution retained in the demo. Source selection, transformations and availability are detailed in [data methods](DATA_METHODS.md).
