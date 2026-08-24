# AIRPATH-AI data audit

## 1. Dataset dimensions

- Rows: 52548
- Columns: 10
- Observed columns: date, Station_No, TSP, PM2.5, O3, CO, NO2, SO2, Temperature, Humidity
- Missing expected columns: None
- Unexpected columns: None
- Source data types: {'date': 'str', 'Station_No': 'int64', 'TSP': 'float64', 'PM2.5': 'float64', 'O3': 'float64', 'CO': 'float64', 'NO2': 'float64', 'SO2': 'float64', 'Temperature': 'float64', 'Humidity': 'float64'}
- Additional complete duplicate rows beyond the first copy: 0
- Rows belonging to complete-duplicate groups (all copies counted): 0
- Additional duplicate `(Station_No, date)` rows beyond the first: 0
- Rows in duplicate `(Station_No, date)` groups (all copies counted): 0
- Invalid timestamp values: 0

Parse failures were converted to missing values only after being counted:

_Not available._

## 2. Temporal coverage

- Earliest timestamp: 2021-02-23 21:00:00
- Latest timestamp: 2022-06-21 17:00:00
- Unique observed timestamps: 10452
- Modal positive interval between unique timestamps: 0 days 01:00:00
- Overall gaps greater than one hour in the union of station timestamps: 47

## 3. Station coverage

|   Station_No |   observations |   valid_timestamps | start               | end                 |   duplicate_timestamp_rows | modal_positive_interval   | largest_gap      |   gaps_gt_1h |
|-------------:|---------------:|-------------------:|:--------------------|:--------------------|---------------------------:|:--------------------------|:-----------------|-------------:|
|            1 |           7892 |               7892 | 2021-02-23 21:00:00 | 2022-06-21 17:00:00 |                          0 | 0 days 01:00:00           | 82 days 16:00:00 |           57 |
|            2 |           9357 |               9357 | 2021-02-23 21:00:00 | 2022-06-21 17:00:00 |                          0 | 0 days 01:00:00           | 10 days 01:00:00 |           67 |
|            3 |           8418 |               8418 | 2021-02-23 21:00:00 | 2022-06-21 17:00:00 |                          0 | 0 days 01:00:00           | 27 days 00:00:00 |          101 |
|            4 |           9951 |               9951 | 2021-02-23 21:00:00 | 2022-06-21 17:00:00 |                          0 | 0 days 01:00:00           | 7 days 06:00:00  |          103 |
|            5 |           7431 |               7431 | 2021-02-23 21:00:00 | 2022-06-21 17:00:00 |                          0 | 0 days 01:00:00           | 76 days 01:00:00 |           58 |
|            6 |           9499 |               9499 | 2021-02-24 16:00:00 | 2022-06-21 17:00:00 |                          0 | 0 days 01:00:00           | 8 days 17:00:00  |           82 |

## 4. Missingness

Variable-level missingness:

| variable    |   missing_count |   missing_percent |
|:------------|----------------:|------------------:|
| date        |               0 |          0        |
| Station_No  |               0 |          0        |
| TSP         |              60 |          0.114181 |
| PM2.5       |               0 |          0        |
| O3          |           10610 |         20.1911   |
| CO          |            9065 |         17.2509   |
| NO2         |            5666 |         10.7825   |
| SO2         |           11006 |         20.9447   |
| Temperature |            4437 |          8.44371  |
| Humidity    |            4432 |          8.43419  |

Station-by-variable missingness is saved in `reports/tables/missingness_by_station.csv`.
Rows are retained when secondary pollutants are missing.

|   Station_No |   date_missing_count |   date_missing_percent |   Station_No_missing_count |   Station_No_missing_percent |   TSP_missing_count |   TSP_missing_percent |   PM2.5_missing_count |   PM2.5_missing_percent |   O3_missing_count |   O3_missing_percent |   CO_missing_count |   CO_missing_percent |   NO2_missing_count |   NO2_missing_percent |   SO2_missing_count |   SO2_missing_percent |   Temperature_missing_count |   Temperature_missing_percent |   Humidity_missing_count |   Humidity_missing_percent |
|-------------:|---------------------:|-----------------------:|---------------------------:|-----------------------------:|--------------------:|----------------------:|----------------------:|------------------------:|-------------------:|---------------------:|-------------------:|---------------------:|--------------------:|----------------------:|--------------------:|----------------------:|----------------------------:|------------------------------:|-------------------------:|---------------------------:|
|            1 |                    0 |                      0 |                          0 |                            0 |                  60 |              0.760264 |                     0 |                       0 |               5665 |           71.7816    |                 65 |            0.823619  |                5665 |            71.7816    |                5709 |            72.3391    |                           0 |                        0      |                        0 |                      0     |
|            2 |                    0 |                      0 |                          0 |                            0 |                   0 |              0        |                     0 |                       0 |                  0 |            0         |               8999 |           96.174     |                   0 |             0         |                   9 |             0.0961847 |                           0 |                        0      |                        0 |                      0     |
|            3 |                    0 |                      0 |                          0 |                            0 |                   0 |              0        |                     0 |                       0 |                  1 |            0.0118793 |                  1 |            0.0118793 |                   0 |             0         |                  28 |             0.332621  |                           0 |                        0      |                        0 |                      0     |
|            4 |                    0 |                      0 |                          0 |                            0 |                   0 |              0        |                     0 |                       0 |                 36 |            0.361773  |                  0 |            0         |                   0 |             0         |                  12 |             0.120591  |                           0 |                        0      |                        0 |                      0     |
|            5 |                    0 |                      0 |                          0 |                            0 |                   0 |              0        |                     0 |                       0 |               4908 |           66.0476    |                  0 |            0         |                   1 |             0.0134571 |                4945 |            66.5456    |                        4437 |                       59.7093 |                     4432 |                     59.642 |
|            6 |                    0 |                      0 |                          0 |                            0 |                   0 |              0        |                     0 |                       0 |                  0 |            0         |                  0 |            0         |                   0 |             0         |                 303 |             3.18981   |                           0 |                        0      |                        0 |                      0     |

## 5. PM2.5 statistics

| station   |   observations |   non_missing |   missing |   negative |   zero |     min |       q1 |   median |      q3 |     max |    mean |      std |   global_iqr_flags |   station_iqr_flags |
|:----------|---------------:|--------------:|----------:|-----------:|-------:|--------:|---------:|---------:|--------:|--------:|--------:|---------:|-------------------:|--------------------:|
| GLOBAL    |          52548 |         52548 |         0 |          0 |    207 | 0       | 12.52    |  17.475  | 25.6367 | 403.688 | 21.126  | 14.2297  |               2766 |                2784 |
| 1         |           7892 |          7892 |         0 |          0 |      2 | 0       | 13.1667  |  18.5442 | 26.4192 | 301.428 | 20.8208 | 11.8604  |                282 |                 249 |
| 2         |           9357 |          9357 |         0 |          0 |      0 | 4.75833 | 12.2817  |  16.0914 | 22.25   |  95.97  | 19.1751 | 10.6421  |                310 |                 629 |
| 3         |           8418 |          8418 |         0 |          0 |      0 | 0.995   | 12.4287  |  18.3625 | 29.0879 | 207.812 | 23.5455 | 17.6567  |                830 |                 517 |
| 4         |           9951 |          9951 |         0 |          0 |      0 | 6.94167 | 16.2858  |  22.5333 | 31.7675 | 403.688 | 26.5163 | 16.8849  |                917 |                 476 |
| 5         |           7431 |          7431 |         0 |          0 |    205 | 0       |  9.56667 |  13.0633 | 18.7367 | 290.433 | 15.1337 |  9.26201 |                 47 |                 322 |
| 6         |           9499 |          9499 |         0 |          0 |      0 | 5.53333 | 12.5558  |  16.7583 | 23.23   | 310.4   | 20.1983 | 13.4661  |                380 |                 591 |

Standard deviation uses the sample definition (`ddof=1`). Quartiles use pandas'
default linear quantile method. Values are reported as observed, including zero,
negative, and extreme values.

Pairwise-complete Pearson correlations (descriptive only):

| variable    |   paired_observations |   pearson_correlation |
|:------------|----------------------:|----------------------:|
| TSP         |                 52488 |              0.661845 |
| O3          |                 41938 |              0.108628 |
| CO          |                 43483 |              0.297432 |
| NO2         |                 46882 |             -0.125261 |
| SO2         |                 41542 |              0.165897 |
| Temperature |                 48111 |             -0.165926 |
| Humidity    |                 48116 |             -0.16293  |

## 6. Temporal gaps

The 20 largest gaps greater than one hour are shown below. The complete table is
saved in `reports/tables/temporal_gaps.csv`. Gaps are documented, not filled.

|   Station_No | gap_start           | gap_end             | gap              |   gap_hours |
|-------------:|:--------------------|:--------------------|:-----------------|------------:|
|            1 | 2021-07-15 19:00:00 | 2021-10-06 11:00:00 | 82 days 16:00:00 |        1984 |
|            5 | 2021-07-27 14:00:00 | 2021-10-11 15:00:00 | 76 days 01:00:00 |        1825 |
|            3 | 2021-07-30 19:00:00 | 2021-08-26 19:00:00 | 27 days 00:00:00 |         648 |
|            5 | 2021-05-21 14:00:00 | 2021-06-12 04:00:00 | 21 days 14:00:00 |         518 |
|            5 | 2022-05-07 16:00:00 | 2022-05-24 09:00:00 | 16 days 17:00:00 |         401 |
|            5 | 2021-10-16 18:00:00 | 2021-11-01 10:00:00 | 15 days 16:00:00 |         376 |
|            1 | 2021-06-17 15:00:00 | 2021-07-01 16:00:00 | 14 days 01:00:00 |         337 |
|            3 | 2022-03-05 09:00:00 | 2022-03-15 10:00:00 | 10 days 01:00:00 |         241 |
|            2 | 2022-03-04 14:00:00 | 2022-03-14 15:00:00 | 10 days 01:00:00 |         241 |
|            2 | 2021-03-17 18:00:00 | 2021-03-26 16:00:00 | 8 days 22:00:00  |         214 |
|            6 | 2021-02-24 17:00:00 | 2021-03-05 10:00:00 | 8 days 17:00:00  |         209 |
|            2 | 2022-04-07 17:00:00 | 2022-04-15 16:00:00 | 7 days 23:00:00  |         191 |
|            3 | 2021-03-16 17:00:00 | 2021-03-24 15:00:00 | 7 days 22:00:00  |         190 |
|            3 | 2022-04-07 17:00:00 | 2022-04-15 11:00:00 | 7 days 18:00:00  |         186 |
|            4 | 2021-03-26 18:00:00 | 2021-04-03 00:00:00 | 7 days 06:00:00  |         174 |
|            3 | 2022-06-10 22:00:00 | 2022-06-18 02:00:00 | 7 days 04:00:00  |         172 |
|            6 | 2022-04-07 17:00:00 | 2022-04-14 15:00:00 | 6 days 22:00:00  |         166 |
|            3 | 2021-04-02 19:00:00 | 2021-04-09 16:00:00 | 6 days 21:00:00  |         165 |
|            3 | 2021-09-30 05:00:00 | 2021-10-07 02:00:00 | 6 days 21:00:00  |         165 |
|            2 | 2021-09-30 05:00:00 | 2021-10-07 01:00:00 | 6 days 20:00:00  |         164 |

## 7. Outlier flags

`pm25_iqr_flag` applies the Q1 - 1.5 IQR / Q3 + 1.5 IQR rule globally;
`pm25_station_iqr_flag` applies it within each station. `pm25_negative_flag` and
`pm25_zero_flag` are separate. These are screening flags, not proof of
measurement error; no flagged observation was removed. Flagged rows are saved
in `reports/tables/pm25_flagged_observations.csv`.

## 8. Recommended train/validation/test split

| partition   |   rows |   unique_timestamps | start               | end                 |
|:------------|-------:|--------------------:|:--------------------|:--------------------|
| train       |  35601 |                7316 | 2021-02-23 21:00:00 | 2022-01-31 02:00:00 |
| validation  |   8740 |                1568 | 2022-01-31 03:00:00 | 2022-04-08 00:00:00 |
| test        |   8207 |                1568 | 2022-04-08 01:00:00 | 2022-06-21 17:00:00 |

The boundaries approximate 70%/15%/15% of unique observed timestamps while
keeping equal timestamps in one partition. They should be reviewed against
station coverage before modeling. All preprocessing parameters must be fit on
training data only; random time-series splitting is inappropriate.

## 9. Recommended forecast horizons

Initial targets: **t+1 hour, t+2 hours, and t+3 hours**. The source observations
are hourly; no finer-resolution ground truth is created.

## 10. Known limitations

- Station observations do not directly measure road-level PM2.5.
- No station coordinates are inferred or invented.
- IQR flags identify unusual values but do not establish that values are invalid.
- Pairwise correlations use available pairs and differing sample sizes; they do
  not imply causality.
- Large temporal gaps remain unfilled.
- Before feature engineering, lag features must contain only information
  available at prediction time. Future PM2.5 must never enter predictors, and
  validation/test data must not influence fitted preprocessing parameters.
