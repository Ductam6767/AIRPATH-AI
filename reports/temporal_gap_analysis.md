# AIRPATH-AI P0-2B — temporal robustness of Gap 1

## Status

**Development / exploratory only.** This experiment does not claim untouched
final-test performance. It reuses the P0-2A OD scenarios and the selected
forecaster `C_xgboost_current_pm`. P0-2A artifacts are not modified.

AIRPATH exposure remains:

**hourly forecast-bucket-aware arrival-time exposure**

No sub-hourly interpolation is performed.

## Departure-time support

Preferred clock times: 06:00, 08:00, 12:00, 17:00, 20:00.

Analysis date: **2022-02-27**.

P0-2A used `2022-02-28 06:00`. On that calendar day, `08:00` and `12:00` cannot
support complete +1/+2/+3h Model C / observed station tables (station 4 gaps).
`2022-02-27` retains all five preferred clock times with intact horizons, so the
temporal comparison uses that day rather than mixing incomplete Feb-28 hours.

| preferred_clock_time   | analysis_date   | departure_time      | forecasting_origin   | supported   | exclusion_reason   |
|:-----------------------|:----------------|:--------------------|:---------------------|:------------|:-------------------|
| 06:00                  | 2022-02-27      | 2022-02-27T06:00:00 | 2022-02-27T05:00:00  | True        |                    |
| 08:00                  | 2022-02-27      | 2022-02-27T08:00:00 | 2022-02-27T07:00:00  | True        |                    |
| 12:00                  | 2022-02-27      | 2022-02-27T12:00:00 | 2022-02-27T11:00:00  | True        |                    |
| 17:00                  | 2022-02-27      | 2022-02-27T17:00:00 | 2022-02-27T16:00:00  | True        |                    |
| 20:00                  | 2022-02-27      | 2022-02-27T20:00:00 | 2022-02-27T19:00:00  | True        |                    |

Forecasting origin remains one hour before each departure, matching P0-2A.

## A. Case count

- OD scenarios: **30**
- Modes: walking, motorbike
- Supported departure times: **5**
- OD × mode × departure-time cases: **300**
- Nontrivial budget rows (δ > 0): **1500**

## B. Ranking correlations

Mean Spearman by departure time:

| clock_time   |   mean_spearman |   mean_kendall |   mean_material_rank_change_pct |
|:-------------|----------------:|---------------:|--------------------------------:|
| 06:00        |          0.9925 |         0.981  |                          6.25   |
| 08:00        |          0.998  |         0.994  |                          2.0833 |
| 12:00        |          0.9988 |         0.9964 |                          1.25   |
| 17:00        |          0.9984 |         0.9952 |                          1.6667 |
| 20:00        |          0.9988 |         0.9964 |                          1.25   |

Pooled mean Spearman: **0.9973**

## C. Route-selection differences

| clock_time   |   nontrivial_selection_difference_rate |   mean_oracle_pct_improvement_when_differ |   positive_oracle_gain_rate_when_differ |
|:-------------|---------------------------------------:|------------------------------------------:|----------------------------------------:|
| 06:00        |                                 0.05   |                                    0.0257 |                                  0.3333 |
| 08:00        |                                 0.0167 |                                    0.0076 |                                  1      |
| 12:00        |                                 0      |                                  nan      |                                nan      |
| 17:00        |                                 0      |                                  nan      |                                nan      |
| 20:00        |                                 0      |                                  nan      |                                nan      |

Edge cases by tolerance (pooled over departure times):

|   delta_time_allowed_minutes |   scenario_mode_cases |   same_route_selected |   different_routes_selected |   only_one_feasible_route |   no_alternative_beyond_fastest |   percentage_selections_differ |
|-----------------------------:|----------------------:|----------------------:|----------------------------:|--------------------------:|--------------------------------:|-------------------------------:|
|                            0 |                   300 |                   300 |                           0 |                       300 |                             300 |                         0      |
|                            1 |                   300 |                   296 |                           4 |                        30 |                              30 |                         1.3333 |
|                            2 |                   300 |                   296 |                           4 |                        10 |                              10 |                         1.3333 |
|                            3 |                   300 |                   296 |                           4 |                         0 |                               0 |                         1.3333 |
|                            5 |                   300 |                   296 |                           4 |                         0 |                               0 |                         1.3333 |
|                           10 |                   300 |                   296 |                           4 |                         0 |                               0 |                         1.3333 |

## D. Oracle improvement

Oracle exposure remains IDW-derived from monitors and is **not** road-measured
ground truth. Values above are mean percent improvement of AIRPATH-selected
routes over static-selected routes **when selections differ**.

## E. Departure-time sensitivity

Strongest clock times: **06:00, 08:00**

Weakest clock times: **20:00, 17:00**

| departure_time      | clock_time   |   scenario_mode_cases |   mean_abs_pct_exposure_diff |   mean_spearman |   mean_kendall |   mean_material_rank_change_pct |   nontrivial_selection_difference_rate |   mean_oracle_pct_improvement_when_differ |   positive_oracle_gain_rate_when_differ |
|:--------------------|:-------------|----------------------:|-----------------------------:|----------------:|---------------:|--------------------------------:|---------------------------------------:|------------------------------------------:|----------------------------------------:|
| 2022-02-27T06:00:00 | 06:00        |                    60 |                       3.7979 |          0.9925 |         0.981  |                          6.25   |                                 0.05   |                                    0.0257 |                                  0.3333 |
| 2022-02-27T08:00:00 | 08:00        |                    60 |                       3.8687 |          0.998  |         0.994  |                          2.0833 |                                 0.0167 |                                    0.0076 |                                  1      |
| 2022-02-27T12:00:00 | 12:00        |                    60 |                      17.0637 |          0.9988 |         0.9964 |                          1.25   |                                 0      |                                  nan      |                                nan      |
| 2022-02-27T17:00:00 | 17:00        |                    60 |                       4.7094 |          0.9984 |         0.9952 |                          1.6667 |                                 0      |                                  nan      |                                nan      |
| 2022-02-27T20:00:00 | 20:00        |                    60 |                       0.9575 |          0.9988 |         0.9964 |                          1.25   |                                 0      |                                  nan      |                                nan      |

## F. Tolerance sensitivity

| departure_time      | mode      |   delta_time_allowed_minutes |   cases |   percentage_selections_differ |   mean_static_predicted_reduction_vs_fastest |   mean_airpath_predicted_reduction_vs_fastest |   mean_oracle_reduction_static_selected_vs_fastest |   mean_oracle_reduction_airpath_selected_vs_fastest |   differing_cases |   mean_oracle_percent_improvement_when_differ |
|:--------------------|:----------|-----------------------------:|--------:|-------------------------------:|---------------------------------------------:|----------------------------------------------:|---------------------------------------------------:|----------------------------------------------------:|------------------:|----------------------------------------------:|
| 2022-02-27T06:00:00 | motorbike |                            0 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T06:00:00 | motorbike |                            1 |      30 |                         3.3333 |                                       0.3419 |                                        0.0747 |                                             0.1593 |                                              0.2057 |                 1 |                                        0.4965 |
| 2022-02-27T06:00:00 | motorbike |                            2 |      30 |                         3.3333 |                                       0.3419 |                                        0.0747 |                                             0.1593 |                                              0.2057 |                 1 |                                        0.4965 |
| 2022-02-27T06:00:00 | motorbike |                            3 |      30 |                         3.3333 |                                       0.3419 |                                        0.0747 |                                             0.1593 |                                              0.2057 |                 1 |                                        0.4965 |
| 2022-02-27T06:00:00 | motorbike |                            5 |      30 |                         3.3333 |                                       0.3419 |                                        0.0747 |                                             0.1593 |                                              0.2057 |                 1 |                                        0.4965 |
| 2022-02-27T06:00:00 | motorbike |                           10 |      30 |                         3.3333 |                                       0.3419 |                                        0.0747 |                                             0.1593 |                                              0.2057 |                 1 |                                        0.4965 |
| 2022-02-27T06:00:00 | walking   |                            0 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T06:00:00 | walking   |                            1 |      30 |                         6.6667 |                                       0.1682 |                                        0      |                                             0.1672 |                                              0      |                 2 |                                       -0.2097 |
| 2022-02-27T06:00:00 | walking   |                            2 |      30 |                         6.6667 |                                       1.1069 |                                        0.0271 |                                             0.6639 |                                              0.4967 |                 2 |                                       -0.2097 |
| 2022-02-27T06:00:00 | walking   |                            3 |      30 |                         6.6667 |                                       1.1069 |                                        0.0271 |                                             0.6639 |                                              0.4967 |                 2 |                                       -0.2097 |
| 2022-02-27T06:00:00 | walking   |                            5 |      30 |                         6.6667 |                                       1.1069 |                                        0.0271 |                                             0.6639 |                                              0.4967 |                 2 |                                       -0.2097 |
| 2022-02-27T06:00:00 | walking   |                           10 |      30 |                         6.6667 |                                       1.1069 |                                        0.0271 |                                             0.6639 |                                              0.4967 |                 2 |                                       -0.2097 |
| 2022-02-27T08:00:00 | motorbike |                            0 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T08:00:00 | motorbike |                            1 |      30 |                         0      |                                       0.4115 |                                        0.1156 |                                            -0.1196 |                                             -0.1196 |                 0 |                                      nan      |
| 2022-02-27T08:00:00 | motorbike |                            2 |      30 |                         0      |                                       0.4115 |                                        0.1156 |                                            -0.1196 |                                             -0.1196 |                 0 |                                      nan      |
| 2022-02-27T08:00:00 | motorbike |                            3 |      30 |                         0      |                                       0.4115 |                                        0.1156 |                                            -0.1196 |                                             -0.1196 |                 0 |                                      nan      |
| 2022-02-27T08:00:00 | motorbike |                            5 |      30 |                         0      |                                       0.4115 |                                        0.1156 |                                            -0.1196 |                                             -0.1196 |                 0 |                                      nan      |
| 2022-02-27T08:00:00 | motorbike |                           10 |      30 |                         0      |                                       0.4115 |                                        0.1156 |                                            -0.1196 |                                             -0.1196 |                 0 |                                      nan      |
| 2022-02-27T08:00:00 | walking   |                            0 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T08:00:00 | walking   |                            1 |      30 |                         3.3333 |                                       0.0032 |                                        0      |                                            -0.003  |                                              0      |                 1 |                                        0.0076 |
| 2022-02-27T08:00:00 | walking   |                            2 |      30 |                         3.3333 |                                       1.3114 |                                        0.1867 |                                            -0.6074 |                                             -0.6044 |                 1 |                                        0.0076 |
| 2022-02-27T08:00:00 | walking   |                            3 |      30 |                         3.3333 |                                       1.3114 |                                        0.1867 |                                            -0.6074 |                                             -0.6044 |                 1 |                                        0.0076 |
| 2022-02-27T08:00:00 | walking   |                            5 |      30 |                         3.3333 |                                       1.3114 |                                        0.1867 |                                            -0.6074 |                                             -0.6044 |                 1 |                                        0.0076 |
| 2022-02-27T08:00:00 | walking   |                           10 |      30 |                         3.3333 |                                       1.3114 |                                        0.1867 |                                            -0.6074 |                                             -0.6044 |                 1 |                                        0.0076 |
| 2022-02-27T12:00:00 | motorbike |                            0 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T12:00:00 | motorbike |                            1 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T12:00:00 | motorbike |                            2 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T12:00:00 | motorbike |                            3 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T12:00:00 | motorbike |                            5 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T12:00:00 | motorbike |                           10 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T12:00:00 | walking   |                            0 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T12:00:00 | walking   |                            1 |      30 |                         0      |                                       0.1101 |                                        0.0146 |                                            -0.1046 |                                             -0.1046 |                 0 |                                      nan      |
| 2022-02-27T12:00:00 | walking   |                            2 |      30 |                         0      |                                       0.1101 |                                        0.0146 |                                            -0.1046 |                                             -0.1046 |                 0 |                                      nan      |
| 2022-02-27T12:00:00 | walking   |                            3 |      30 |                         0      |                                       0.1101 |                                        0.0146 |                                            -0.1046 |                                             -0.1046 |                 0 |                                      nan      |
| 2022-02-27T12:00:00 | walking   |                            5 |      30 |                         0      |                                       0.1101 |                                        0.0146 |                                            -0.1046 |                                             -0.1046 |                 0 |                                      nan      |
| 2022-02-27T12:00:00 | walking   |                           10 |      30 |                         0      |                                       0.1101 |                                        0.0146 |                                            -0.1046 |                                             -0.1046 |                 0 |                                      nan      |
| 2022-02-27T17:00:00 | motorbike |                            0 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T17:00:00 | motorbike |                            1 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T17:00:00 | motorbike |                            2 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T17:00:00 | motorbike |                            3 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T17:00:00 | motorbike |                            5 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T17:00:00 | motorbike |                           10 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T17:00:00 | walking   |                            0 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T17:00:00 | walking   |                            1 |      30 |                         0      |                                       0.1276 |                                        0.1637 |                                             0.1356 |                                              0.1356 |                 0 |                                      nan      |
| 2022-02-27T17:00:00 | walking   |                            2 |      30 |                         0      |                                       0.1276 |                                        0.1637 |                                             0.1356 |                                              0.1356 |                 0 |                                      nan      |
| 2022-02-27T17:00:00 | walking   |                            3 |      30 |                         0      |                                       0.1276 |                                        0.1637 |                                             0.1356 |                                              0.1356 |                 0 |                                      nan      |
| 2022-02-27T17:00:00 | walking   |                            5 |      30 |                         0      |                                       0.1276 |                                        0.1637 |                                             0.1356 |                                              0.1356 |                 0 |                                      nan      |
| 2022-02-27T17:00:00 | walking   |                           10 |      30 |                         0      |                                       0.1276 |                                        0.1637 |                                             0.1356 |                                              0.1356 |                 0 |                                      nan      |
| 2022-02-27T20:00:00 | motorbike |                            0 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T20:00:00 | motorbike |                            1 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T20:00:00 | motorbike |                            2 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T20:00:00 | motorbike |                            3 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T20:00:00 | motorbike |                            5 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T20:00:00 | motorbike |                           10 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T20:00:00 | walking   |                            0 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| 2022-02-27T20:00:00 | walking   |                            1 |      30 |                         0      |                                       0.1198 |                                        0.102  |                                             0.272  |                                              0.272  |                 0 |                                      nan      |
| 2022-02-27T20:00:00 | walking   |                            2 |      30 |                         0      |                                       0.1198 |                                        0.102  |                                             0.272  |                                              0.272  |                 0 |                                      nan      |
| 2022-02-27T20:00:00 | walking   |                            3 |      30 |                         0      |                                       0.1198 |                                        0.102  |                                             0.272  |                                              0.272  |                 0 |                                      nan      |
| 2022-02-27T20:00:00 | walking   |                            5 |      30 |                         0      |                                       0.1198 |                                        0.102  |                                             0.272  |                                              0.272  |                 0 |                                      nan      |
| 2022-02-27T20:00:00 | walking   |                           10 |      30 |                         0      |                                       0.1198 |                                        0.102  |                                             0.272  |                                              0.272  |                 0 |                                      nan      |

## G. Updated Gap 1 conclusion

### B. MIXED EVIDENCE

Across supported departure times on 2022-02-27, nontrivial selection differences average 1.3% (range 0.0–5.0%). Strongest clock times: 06:00, 08:00; weakest: 20:00, 17:00. Mean oracle gain when selections differ is 0.02%. The pooled Gap 1 conclusion remains aligned with MIXED/weak evidence from P0-2A.

Gap 1 conclusion changed vs single-time P0-2A: **False**

```json
{
  "evaluation_status": "development_exploratory_not_untouched_final",
  "forecaster": "C_xgboost_current_pm",
  "nontrivial_selection_difference_rate": 0.013333333333333334,
  "mean_oracle_percent_improvement_when_differ": 0.021162238573929182,
  "positive_oracle_gain_rate_when_differ": 0.5,
  "mean_spearman_static_vs_airpath": 0.9973015873015871,
  "mean_percentage_routes_with_material_rank_change": 2.5,
  "five_minute_selection_difference_percentage": 1.3333333333333335,
  "strong_differ_rate_ge_0_25": false,
  "strong_oracle_gain_ge_1_0": false,
  "strong_positive_gain_rate_ge_0_60": false,
  "mixed_differ_rate_ge_0_10": false,
  "mixed_rank_change_ge_10": false,
  "analysis_date": "2022-02-27",
  "overall_nontrivial_selection_difference_rate": 0.013333333333333334,
  "overall_mean_oracle_pct_improvement_when_differ": 0.021162238573929182,
  "overall_mean_spearman": 0.9973015873015871,
  "max_departure_differ_rate": 0.05,
  "min_departure_differ_rate": 0.0,
  "p0_2a_reference_differ_rate": 0.0633,
  "gap1_conclusion_changed_vs_p0_2a": false,
  "strongest_departure_times": [
    "06:00",
    "08:00"
  ],
  "weakest_departure_times": [
    "20:00",
    "17:00"
  ]
}
```

## H. Implications for the final paper

1. A single morning departure is not sufficient to claim Gap 1 benefit.
2. Temporal replication across clock times is required before product claims.
3. If signals remain weak across times of day, AIRPATH should emphasize
   transparency of alternatives rather than asserting large arrival-time gains.
4. Hourly buckets remain a binding scientific limitation.

## Limitations

1. Hourly forecasting buckets only.
2. Constant-speed ETA omits traffic and signals.
3. No road-level PM2.5 measurements.
4. Oracle exposure is IDW-derived.
5. Pilot-area OSM / station support remains bounded.
6. Calendar day shifted from P0-2A to obtain complete preferred clock coverage.
7. Development/exploratory protocol; previously exposed test partition unused.
