# AIRPATH-AI

AIRPATH-AI is a research project investigating whether future PM2.5 forecasts
can improve route-level exposure estimation and later support route selection
under an explicit travel-time constraint.

## Current milestone

Milestone 1 covers **data audit and conservative preprocessing only**. It does
not implement forecasting, spatial interpolation, route optimization, or a web
application. Station observations are not direct road-level PM2.5 measurements.

## Dataset

The expected input is the original hourly HealthyAir station dataset:

`data/raw/Air Quality Ho Chi Minh City.csv`

The audit verifies the file's actual columns, types, timestamps, station
coverage, missingness, duplicates, temporal gaps, PM2.5 quality indicators, and
pairwise-complete correlations. It does not infer station coordinates, fill
large gaps, delete outliers, or drop observations because secondary pollutants
are missing.

The source CSV is not committed to this repository. At the time this milestone
was prepared, it was also not available in the supplied working tree, so no
dataset-derived findings or processed observations have been fabricated.

## Reproduce the audit

Use Python 3 with `pandas`, `numpy`, `matplotlib`, `seaborn`, and `tabulate`
installed. From the repository root:

```bash
mkdir -p data/raw
# Copy the unmodified source file to:
# data/raw/Air Quality Ho Chi Minh City.csv
python3 -m src.data_validation
```

The command fails clearly if the input is absent or if required columns differ
from the documented schema. On success it writes:

- `data/processed/airquality_hcmc_clean.csv`
- `reports/data_audit.md`
- audit tables under `reports/tables/`
- research figures under `reports/figures/`

The equivalent interactive workflow is in
`notebooks/01_data_audit.ipynb`.

Run the automated checks with:

```bash
python3 -m pytest
```

## Current limitations and leakage safeguards

- Initial forecast horizons should be t+1, t+2, and t+3 hours; hourly data must
  not be presented as sub-hourly ground truth.
- Suspicious PM2.5 values receive transparent flags and remain in the data.
- Any later lag feature must use only information available at prediction time.
- Future PM2.5 must not enter model features.
- Fitted preprocessing must use training observations only.
- Train, validation, and test partitions must remain chronological.
- Correlation does not establish causality.
- Forecasting performance has not been evaluated.
