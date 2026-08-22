# AIRPATH-AI P0-2A — static vs arrival-time exposure

## Status

**Development / exploratory only.** This experiment does not claim untouched
final-test performance. It uses the selected development forecaster
`C_xgboost_current_pm` and does not modify historical XGBoost V1 artifacts.

AIRPATH exposure here is explicitly labeled:

**hourly forecast-bucket-aware arrival-time exposure**

Hourly target buckets are used. No sub-hourly interpolation is performed. This
does **not** establish minute-level PM2.5 accuracy.

## Definitions

### Method A — static / current pollution exposure

At departure time `T0 = 2022-02-28 06:00:00`:

1. read the observed HealthyAir PM2.5 state at `T0`;
2. estimate spatial PM2.5 with existing IDW p=1;
3. assign that **same departure-time snapshot** to every route segment;
4. compute `E_static(R) = Σ_i PM_static(X_i, T0) × duration_i`.

ETA is recorded but does not change the pollution field.

### Method B — AIRPATH arrival-time exposure

Forecasting origin `2022-02-28 05:00:00` with `C_xgboost_current_pm`:

segment `i` → `ETA_i` → supported hourly bucket → station forecasts → IDW p=1
→ `PM2.5(X_i, ETA_bucket)` →
`E_AIRPATH(R) = Σ_i PM_AIRPATH_i × duration_i`.

Oracle exposure remains the existing ETA-bucket observed-station IDW pathway.
Oracle values are IDW-derived and are **not** road-measured ground truth.

## A. OD scenarios

30 deterministic OD scenarios (seed `42`) inside the
validated stations 2–6 polygon with straight-line distance 2–6 km.

| scenario_id   |   origin_latitude |   origin_longitude |   destination_latitude |   destination_longitude |   straight_line_distance_km |   generation_seed | generation_method                                                                   |
|:--------------|------------------:|-------------------:|-----------------------:|------------------------:|----------------------------:|------------------:|:------------------------------------------------------------------------------------|
| od_01         |           10.7992 |            106.661 |                10.8056 |                 106.687 |                      2.9189 |                42 | seeded uniform rejection inside stations 2–6 polygon; straight-line distance 2–6 km |
| od_02         |           10.7995 |            106.637 |                10.7761 |                 106.621 |                      3.087  |                42 | seeded uniform rejection inside stations 2–6 polygon; straight-line distance 2–6 km |
| od_03         |           10.7655 |            106.654 |                10.7763 |                 106.636 |                      2.319  |                42 | seeded uniform rejection inside stations 2–6 polygon; straight-line distance 2–6 km |
| od_04         |           10.7923 |            106.631 |                10.756  |                 106.618 |                      4.2902 |                42 | seeded uniform rejection inside stations 2–6 polygon; straight-line distance 2–6 km |
| od_05         |           10.7755 |            106.674 |                10.7515 |                 106.629 |                      5.6474 |                42 | seeded uniform rejection inside stations 2–6 polygon; straight-line distance 2–6 km |
| od_06         |           10.7887 |            106.673 |                10.783  |                 106.648 |                      2.8068 |                42 | seeded uniform rejection inside stations 2–6 polygon; straight-line distance 2–6 km |
| od_07         |           10.791  |            106.658 |                10.8022 |                 106.634 |                      2.9065 |                42 | seeded uniform rejection inside stations 2–6 polygon; straight-line distance 2–6 km |
| od_08         |           10.7996 |            106.689 |                10.7748 |                 106.644 |                      5.5968 |                42 | seeded uniform rejection inside stations 2–6 polygon; straight-line distance 2–6 km |
| od_09         |           10.798  |            106.689 |                10.7735 |                 106.68  |                      2.9117 |                42 | seeded uniform rejection inside stations 2–6 polygon; straight-line distance 2–6 km |
| od_10         |           10.7847 |            106.652 |                10.7854 |                 106.619 |                      3.5512 |                42 | seeded uniform rejection inside stations 2–6 polygon; straight-line distance 2–6 km |
| od_11         |           10.8131 |            106.665 |                10.7999 |                 106.625 |                      4.6178 |                42 | seeded uniform rejection inside stations 2–6 polygon; straight-line distance 2–6 km |
| od_12         |           10.7776 |            106.666 |                10.8115 |                 106.674 |                      3.8776 |                42 | seeded uniform rejection inside stations 2–6 polygon; straight-line distance 2–6 km |

## B–D. Exposure comparison

Pooled mean static exposure: **871.3000** (µg/m³)·min

Pooled mean AIRPATH exposure: **874.7673** (µg/m³)·min

Mean absolute difference |AIRPATH − static|: **30.9878**

Mean percentage difference: **0.7169%**

Per mode:

| mode      |   n_routes |   mean_static_exposure |   mean_airpath_exposure |   mean_pct_diff |
|:----------|-----------:|-----------------------:|------------------------:|----------------:|
| motorbike |        240 |                354.156 |                 355.016 |          0.6516 |
| walking   |        240 |               1388.44  |                1394.52  |          0.7821 |

## E. Ranking correlations

| scenario_id   | mode      |   route_count |   spearman_static_vs_airpath |   kendall_tau_a_static_vs_airpath | top_1_agreement   |   routes_with_material_rank_change |   percentage_routes_with_material_rank_change |
|:--------------|:----------|--------------:|-----------------------------:|----------------------------------:|:------------------|-----------------------------------:|----------------------------------------------:|
| od_01         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_01         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_02         | motorbike |             8 |                       0.9762 |                            0.9286 | False             |                                  2 |                                          25   |
| od_02         | walking   |             8 |                       0.9286 |                            0.8571 | False             |                                  3 |                                          37.5 |
| od_03         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_03         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_04         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_04         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_05         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_05         | walking   |             8 |                       0.9762 |                            0.9286 | True              |                                  2 |                                          25   |
| od_06         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_06         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_07         | motorbike |             8 |                       0.9762 |                            0.9286 | True              |                                  2 |                                          25   |
| od_07         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_08         | motorbike |             8 |                       0.9762 |                            0.9286 | True              |                                  2 |                                          25   |
| od_08         | walking   |             8 |                       0.9762 |                            0.9286 | True              |                                  2 |                                          25   |
| od_09         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_09         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_10         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_10         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_11         | motorbike |             8 |                       0.9762 |                            0.9286 | True              |                                  2 |                                          25   |
| od_11         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_12         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_12         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_13         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_13         | walking   |             8 |                       0.9762 |                            0.9286 | True              |                                  2 |                                          25   |
| od_14         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_14         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_15         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_15         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_16         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_16         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_17         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_17         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_18         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_18         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_19         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_19         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_20         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_20         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_21         | motorbike |             8 |                       0.9524 |                            0.8571 | False             |                                  4 |                                          50   |
| od_21         | walking   |             8 |                       0.9524 |                            0.8571 | True              |                                  4 |                                          50   |
| od_22         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_22         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_23         | motorbike |             8 |                       0.9762 |                            0.9286 | True              |                                  2 |                                          25   |
| od_23         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_24         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_24         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_25         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_25         | walking   |             8 |                       0.9524 |                            0.8571 | True              |                                  4 |                                          50   |
| od_26         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_26         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_27         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_27         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_28         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_28         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_29         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_29         | walking   |             8 |                       0.9524 |                            0.8571 | False             |                                  4 |                                          50   |
| od_30         | motorbike |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |
| od_30         | walking   |             8 |                       1      |                            1      | True              |                                  0 |                                           0   |

Mean Spearman: **0.9925**

Mean share of routes with material rank change (|Δrank| ≥ 1):
**7.29%**

## F. Route-selection differences

Nontrivial budgets (δ > 0): **6.33%** of OD/mode/budget cases
select different routes.

|   delta_time_allowed_minutes |   scenario_mode_cases |   same_route_selected |   different_routes_selected |   only_one_feasible_route |   no_alternative_beyond_fastest |   percentage_selections_differ |
|-----------------------------:|----------------------:|----------------------:|----------------------------:|--------------------------:|--------------------------------:|-------------------------------:|
|                            0 |                    60 |                    60 |                           0 |                        60 |                              60 |                         0      |
|                            1 |                    60 |                    57 |                           3 |                         6 |                               6 |                         5      |
|                            2 |                    60 |                    56 |                           4 |                         2 |                               2 |                         6.6667 |
|                            3 |                    60 |                    56 |                           4 |                         0 |                               0 |                         6.6667 |
|                            5 |                    60 |                    56 |                           4 |                         0 |                               0 |                         6.6667 |
|                           10 |                    60 |                    56 |                           4 |                         0 |                               0 |                         6.6667 |

## G. Oracle exposure improvement when selections differ

Mean oracle % improvement of AIRPATH-selected over static-selected routes when
they differ (δ > 0): **0.1077%**

Positive values favor AIRPATH selection under the IDW-derived oracle.

## H–I. Walking vs motorbike and time-budget sensitivity

| mode      |   delta_time_allowed_minutes |   cases |   percentage_selections_differ |   mean_static_predicted_reduction_vs_fastest |   mean_airpath_predicted_reduction_vs_fastest |   mean_oracle_reduction_static_selected_vs_fastest |   mean_oracle_reduction_airpath_selected_vs_fastest |   differing_cases |   mean_oracle_percent_improvement_when_differ |
|:----------|-----------------------------:|--------:|-------------------------------:|---------------------------------------------:|----------------------------------------------:|---------------------------------------------------:|----------------------------------------------------:|------------------:|----------------------------------------------:|
| motorbike |                            0 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| motorbike |                            1 |      30 |                         6.6667 |                                       0.2523 |                                        0.0303 |                                             0.048  |                                              0.0845 |                 2 |                                        0.1765 |
| motorbike |                            2 |      30 |                         6.6667 |                                       0.2523 |                                        0.0303 |                                             0.048  |                                              0.0845 |                 2 |                                        0.1765 |
| motorbike |                            3 |      30 |                         6.6667 |                                       0.2523 |                                        0.0303 |                                             0.048  |                                              0.0845 |                 2 |                                        0.1765 |
| motorbike |                            5 |      30 |                         6.6667 |                                       0.2523 |                                        0.0303 |                                             0.048  |                                              0.0845 |                 2 |                                        0.1765 |
| motorbike |                           10 |      30 |                         6.6667 |                                       0.2523 |                                        0.0303 |                                             0.048  |                                              0.0845 |                 2 |                                        0.1765 |
| walking   |                            0 |      30 |                         0      |                                       0      |                                        0      |                                             0      |                                              0      |                 0 |                                      nan      |
| walking   |                            1 |      30 |                         3.3333 |                                       0.3716 |                                        0.2426 |                                             1.0108 |                                              1.0106 |                 1 |                                       -0.0004 |
| walking   |                            2 |      30 |                         6.6667 |                                       1.0698 |                                        0.2426 |                                             0.9659 |                                              1.0106 |                 2 |                                        0.0352 |
| walking   |                            3 |      30 |                         6.6667 |                                       1.0698 |                                        0.2426 |                                             0.9659 |                                              1.0106 |                 2 |                                        0.0352 |
| walking   |                            5 |      30 |                         6.6667 |                                       1.0698 |                                        0.2426 |                                             0.9659 |                                              1.0106 |                 2 |                                        0.0352 |
| walking   |                           10 |      30 |                         6.6667 |                                       1.0698 |                                        0.2426 |                                             0.9659 |                                              1.0106 |                 2 |                                        0.0352 |

## J. Scientific interpretation

This experiment tests whether **future hourly pollution buckets** change
route-exposure estimates and constrained route selection relative to a
**static departure snapshot**, using the same candidate routes.

It does **not** claim minute-level PM2.5 prediction, medical benefit, or
road-measured truth.

## K. Limitations

1. Hourly forecast buckets only; no sub-hourly interpolation.
2. Development/exploratory protocol; previously exposed test partition unused.
3. Oracle exposure is IDW-derived from monitors, not roadside measurements.
4. Constant-speed ETA omits traffic, signals, and turn delay.
5. Pilot-area OSM graph and spatial support remain bounded.
6. Model C hyperparameters were frozen from the fairness ablation.
7. Exposure remains a PM×minutes proxy, not inhaled dose.

## Final decision

### B. MIXED EVIDENCE

Static and AIRPATH frameworks sometimes reorder or reselect routes, but oracle gains when selections differ are weak, inconsistent, or limited.

```json
{
  "evaluation_status": "development_exploratory_not_untouched_final",
  "forecaster": "C_xgboost_current_pm",
  "nontrivial_selection_difference_rate": 0.06333333333333334,
  "mean_oracle_percent_improvement_when_differ": 0.1076873292175646,
  "positive_oracle_gain_rate_when_differ": 0.7368421052631579,
  "mean_spearman_static_vs_airpath": 0.9924603174603174,
  "mean_percentage_routes_with_material_rank_change": 7.291666666666667,
  "five_minute_selection_difference_percentage": 6.666666666666667,
  "strong_differ_rate_ge_0_25": false,
  "strong_oracle_gain_ge_1_0": false,
  "strong_positive_gain_rate_ge_0_60": true,
  "mixed_differ_rate_ge_0_10": false,
  "mixed_rank_change_ge_10": false
}
```
