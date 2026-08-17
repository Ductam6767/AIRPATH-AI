# AIRPATH-AI data audit

Audit status: **not executed — source dataset unavailable**.

The repository supplied for this milestone did not contain
`Air Quality Ho Chi Minh City.csv`. The sections below intentionally contain no
fabricated values. Run `python -m src.data_validation` after placing the
unmodified file at `data/raw/Air Quality Ho Chi Minh City.csv`; this report will
then be replaced with the observed results.

## 1. Dataset dimensions

Not available without the source file.

## 2. Temporal coverage

Not available without the source file.

## 3. Station coverage

Not available without the source file.

## 4. Missingness

Not available without the source file.

## 5. PM2.5 statistics

Not available without the source file.

## 6. Temporal gaps

Not available without the source file.

## 7. Outlier flags

Not available without the source file. The implemented audit flags global and
station-level IQR observations, negatives, and zeros without removing them.

## 8. Recommended train/validation/test split

Exact boundaries cannot be recommended before observing temporal and station
coverage. The implemented candidate split preserves equal timestamps and uses
approximately the earliest 70% of unique timestamps for training, the following
15% for validation, and the latest 15% for testing. Boundaries must be reviewed
after the actual audit.

## 9. Recommended forecast horizons

The initial scientific targets are t+1 hour, t+2 hours, and t+3 hours. No
sub-hourly observations are created.

## 10. Known limitations

- Dataset-specific quality and coverage are currently unknown.
- Station observations are not direct road-level PM2.5 measurements.
- No station coordinates are inferred.
- Flags are screening indicators, not evidence that a measurement is invalid.
- Correlations do not establish causality.
- Later feature engineering must prevent future-target and preprocessing
  leakage and retain chronological evaluation.
