# AIRPATH-AI forecasting baseline evaluation

## Scope and leakage controls

Milestone 2A constructs station-level targets at exact t+1h, t+2h, and t+3h
timestamps. It uses only current/past PM2.5 and deterministic calendar features.
No interpolation, secondary pollutants, temperature, humidity, spatial features,
random splitting, or learned forecasting model is used.

- `pm25_current` is PM2.5 observed at prediction origin t.
- `pm25_lag_1h`, `pm25_lag_2h`, and `pm25_lag_3h` are exact timestamp lookups.
- `hour`, `day_of_week`, and `month` describe the prediction origin.
- A sample requires complete exact t through t-3h history.
- A target requires a non-missing observation at the exact future timestamp.
- Origin and target must lie in the same chronological partition.
- Zero and IQR-flagged observations are retained.

## Chronological boundaries

| split      | start               | end                 |   unique_timestamps |
|:-----------|:--------------------|:--------------------|--------------------:|
| train      | 2021-02-23 21:00:00 | 2022-01-31 02:00:00 |                7316 |
| validation | 2022-01-31 03:00:00 | 2022-04-08 00:00:00 |                1568 |
| test       | 2022-04-08 01:00:00 | 2022-06-21 17:00:00 |                1568 |

Split boundaries are inherited from Milestone 1. Cross-boundary target candidates
are excluded so training labels cannot enter validation and validation labels
cannot enter test.

## Valid sample construction

|   Station_No |   horizon_hours |   complete_lag_origins |   exact_nonmissing_targets |   cross_partition_candidates |   valid_samples |
|-------------:|----------------:|-----------------------:|---------------------------:|-----------------------------:|----------------:|
|            1 |               1 |                   7723 |                       7834 |                            2 |            7666 |
|            2 |               1 |                   9161 |                       9289 |                            1 |            9099 |
|            3 |               1 |                   8123 |                       8316 |                            1 |            8028 |
|            4 |               1 |                   9655 |                       9847 |                            1 |            9560 |
|            5 |               1 |                   7266 |                       7372 |                            2 |            7213 |
|            6 |               1 |                   9270 |                       9416 |                            1 |            9201 |
|            1 |               2 |                   7723 |                       7791 |                            4 |            7623 |
|            2 |               2 |                   9161 |                       9230 |                            2 |            9042 |
|            3 |               2 |                   8123 |                       8251 |                            2 |            7964 |
|            4 |               2 |                   9655 |                       9791 |                            2 |            9505 |
|            5 |               2 |                   7266 |                       7336 |                            4 |            7177 |
|            6 |               2 |                   9270 |                       9358 |                            2 |            9146 |
|            1 |               3 |                   7723 |                       7753 |                            6 |            7584 |
|            2 |               3 |                   9161 |                       9175 |                            3 |            8990 |
|            3 |               3 |                   8123 |                       8190 |                            3 |            7906 |
|            4 |               3 |                   9655 |                       9745 |                            3 |            9460 |
|            5 |               3 |                   7266 |                       7304 |                            6 |            7145 |
|            6 |               3 |                   9270 |                       9304 |                            3 |            9091 |

`valid_samples` is the common comparison set used by both baselines and any later
model: exact target, complete exact lag history, and no split-boundary crossing.

## Baselines

**Persistence:** predicts PM2.5(t) for every horizon.

**Historical time baseline:** predicts the training-only station-specific mean
for the target timestamp's hour-of-day and day-of-week. An unseen combination
falls back to that station's training mean, then the global training mean.
Fallback predictions used across all partitions/horizons: **0**.

## Overall and per-horizon metrics

| model           | split      | Station_No   | horizon_hours   |     n |    mae |    rmse |      r2 |
|:----------------|:-----------|:-------------|:----------------|------:|-------:|--------:|--------:|
| persistence     | validation | ALL          | ALL             | 25744 | 4.4866 |  9.2182 |  0.3990 |
| persistence     | validation | ALL          | 1               |  8603 | 3.0381 |  7.0253 |  0.6518 |
| persistence     | validation | ALL          | 2               |  8580 | 4.6392 |  9.4533 |  0.3675 |
| persistence     | validation | ALL          | 3               |  8561 | 5.7893 | 10.7874 |  0.1756 |
| persistence     | test       | ALL          | ALL             | 23655 | 4.3162 |  8.7469 |  0.4172 |
| persistence     | test       | ALL          | 1               |  7929 | 2.9996 |  7.1405 |  0.6134 |
| persistence     | test       | ALL          | 2               |  7883 | 4.4941 |  8.8765 |  0.3991 |
| persistence     | test       | ALL          | 3               |  7843 | 5.4684 | 10.0006 |  0.2354 |
| historical_time | validation | ALL          | ALL             | 25744 | 8.2669 | 11.2472 |  0.1053 |
| historical_time | validation | ALL          | 1               |  8603 | 8.2712 | 11.2583 |  0.1058 |
| historical_time | validation | ALL          | 2               |  8580 | 8.2652 | 11.2433 |  0.1052 |
| historical_time | validation | ALL          | 3               |  8561 | 8.2642 | 11.2400 |  0.1050 |
| historical_time | test       | ALL          | ALL             | 23655 | 8.6403 | 11.4557 |  0.0003 |
| historical_time | test       | ALL          | 1               |  7929 | 8.6546 | 11.4607 |  0.0040 |
| historical_time | test       | ALL          | 2               |  7883 | 8.6361 | 11.4529 | -0.0004 |
| historical_time | test       | ALL          | 3               |  7843 | 8.6299 | 11.4534 | -0.0029 |

Metrics marked `split=validation` support model development; `split=test` is the
held-out baseline result. Aggregation pools prediction rows, so stations with
more valid samples contribute more observations.

## Test metrics by station

| model           | split   |   Station_No | horizon_hours   |    n |     mae |    rmse |      r2 |
|:----------------|:--------|-------------:|:----------------|-----:|--------:|--------:|--------:|
| persistence     | test    |            1 | ALL             | 4600 |  4.6658 |  7.8477 |  0.5861 |
| persistence     | test    |            2 | ALL             | 4206 |  3.6330 |  5.8158 |  0.3888 |
| persistence     | test    |            3 | ALL             | 2896 |  4.9509 |  7.5621 |  0.2153 |
| persistence     | test    |            4 | ALL             | 4174 |  5.9723 |  9.5603 |  0.4493 |
| persistence     | test    |            5 | ALL             | 3492 |  2.3902 |  3.9996 |  0.8333 |
| persistence     | test    |            6 | ALL             | 4287 |  4.1389 | 13.4996 | -0.3765 |
| historical_time | test    |            1 | ALL             | 4600 | 10.4665 | 13.0092 | -0.1373 |
| historical_time | test    |            2 | ALL             | 4206 |  6.2077 |  7.7777 | -0.0931 |
| historical_time | test    |            3 | ALL             | 2896 | 11.0521 | 12.6595 | -1.1990 |
| historical_time | test    |            4 | ALL             | 4174 |  9.3551 | 12.3884 |  0.0753 |
| historical_time | test    |            5 | ALL             | 3492 |  8.4289 | 10.4307 | -0.1341 |
| historical_time | test    |            6 | ALL             | 4287 |  6.9142 | 11.6989 | -0.0338 |

## Test metrics by station and horizon

| model           | split   |   Station_No |   horizon_hours |    n |     mae |    rmse |      r2 |
|:----------------|:--------|-------------:|----------------:|-----:|--------:|--------:|--------:|
| persistence     | test    |            1 |               1 | 1540 |  3.1516 |  5.3767 |  0.8055 |
| persistence     | test    |            1 |               2 | 1533 |  4.8169 |  7.9984 |  0.5704 |
| persistence     | test    |            1 |               3 | 1527 |  6.0412 |  9.5992 |  0.3810 |
| persistence     | test    |            2 |               1 | 1407 |  2.5085 |  3.9772 |  0.7156 |
| persistence     | test    |            2 |               2 | 1402 |  3.7939 |  5.9032 |  0.3707 |
| persistence     | test    |            2 |               3 | 1397 |  4.6042 |  7.1364 |  0.0743 |
| persistence     | test    |            3 |               1 |  974 |  3.5683 |  5.5566 |  0.5828 |
| persistence     | test    |            3 |               2 |  965 |  5.1640 |  7.7451 |  0.1728 |
| persistence     | test    |            3 |               3 |  957 |  6.1433 |  9.0077 | -0.1256 |
| persistence     | test    |            4 |               1 | 1404 |  4.1900 |  6.7799 |  0.7255 |
| persistence     | test    |            4 |               2 | 1390 |  6.2348 |  9.7999 |  0.4199 |
| persistence     | test    |            4 |               3 | 1380 |  7.5210 | 11.5304 |  0.1935 |
| persistence     | test    |            5 |               1 | 1169 |  1.4984 |  2.4872 |  0.9354 |
| persistence     | test    |            5 |               2 | 1164 |  2.4985 |  4.0444 |  0.8295 |
| persistence     | test    |            5 |               3 | 1159 |  3.1809 |  5.0527 |  0.7342 |
| persistence     | test    |            6 |               1 | 1435 |  2.9900 | 12.8148 | -0.2446 |
| persistence     | test    |            6 |               2 | 1429 |  4.3147 | 13.5862 | -0.3943 |
| persistence     | test    |            6 |               3 | 1423 |  5.1209 | 14.0732 | -0.4908 |
| historical_time | test    |            1 |               1 | 1540 | 10.4641 | 13.0016 | -0.1371 |
| historical_time | test    |            1 |               2 | 1533 | 10.4702 | 13.0119 | -0.1370 |
| historical_time | test    |            1 |               3 | 1527 | 10.4651 | 13.0142 | -0.1378 |
| historical_time | test    |            2 |               1 | 1407 |  6.2257 |  7.7992 | -0.0936 |
| historical_time | test    |            2 |               2 | 1402 |  6.2087 |  7.7801 | -0.0931 |
| historical_time | test    |            2 |               3 | 1397 |  6.1886 |  7.7535 | -0.0927 |
| historical_time | test    |            3 |               1 |  974 | 11.0131 | 12.6105 | -1.1488 |
| historical_time | test    |            3 |               2 |  965 | 11.0423 | 12.6542 | -1.2082 |
| historical_time | test    |            3 |               3 |  957 | 11.1018 | 12.7146 | -1.2426 |
| historical_time | test    |            4 |               1 | 1404 |  9.4346 | 12.4516 |  0.0741 |
| historical_time | test    |            4 |               2 | 1390 |  9.3375 | 12.3754 |  0.0749 |
| historical_time | test    |            4 |               3 | 1380 |  9.2920 | 12.3370 |  0.0768 |
| historical_time | test    |            5 |               1 | 1169 |  8.4266 | 10.4244 | -0.1342 |
| historical_time | test    |            5 |               2 | 1164 |  8.4268 | 10.4295 | -0.1336 |
| historical_time | test    |            5 |               3 | 1159 |  8.4333 | 10.4383 | -0.1345 |
| historical_time | test    |            6 |               1 | 1435 |  6.9160 | 11.6856 | -0.0349 |
| historical_time | test    |            6 |               2 | 1429 |  6.9133 | 11.6986 | -0.0338 |
| historical_time | test    |            6 |               3 | 1423 |  6.9131 | 11.7127 | -0.0327 |

R² can be negative when a baseline is worse than predicting the evaluation-set
mean. It is undefined if the observed target is constant.

## Retained target-quality flags

| split      |   horizon_hours |   samples |   zero_targets |
|:-----------|----------------:|----------:|---------------:|
| test       |               1 |      7929 |            205 |
| test       |               2 |      7883 |            205 |
| test       |               3 |      7843 |            205 |
| train      |               1 |     34235 |              2 |
| train      |               2 |     33994 |              2 |
| train      |               3 |     33772 |              2 |
| validation |               1 |      8603 |              0 |
| validation |               2 |      8580 |              0 |
| validation |               3 |      8561 |              0 |

No zero or IQR-flagged source observation was removed. IQR flags remain in the
saved sample data for later sensitivity analysis; they are not model features.

## Methodological limitations

- Baselines use no meteorological or secondary-pollutant predictors.
- Missing timestamps reduce samples non-uniformly by station and horizon.
- Historical means are descriptive seasonal averages and do not establish
  causal relationships.
- Hyperparameter tuning and model selection are outside this milestone.
- Test metrics should not guide repeated model-development decisions.
