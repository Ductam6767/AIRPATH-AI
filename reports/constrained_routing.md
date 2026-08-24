# AIRPATH-AI Milestone 5 — constrained multi-route research experiment

## Scope

This is an **offline research optimization experiment**. It does not build a
web application and must not be described as a medical or health recommendation.
User control is an absolute additional-time allowance in minutes.

## A. OD scenarios

10 deterministic OD scenarios were generated with seed
42 by uniform rejection sampling inside the validated stations 2–6
polygon, retaining straight-line separations of 2–6 km.

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

## B. Candidate diversity

Each scenario/mode retains the true fastest route, then creates OSM-valid
alternatives by repeatedly penalizing already-used directed edges during
shortest-path search. Routes are capped at 15 additional minutes and 119 total
minutes to stay within the frozen hourly forecast horizon.

| scenario_id   | mode      |   candidate_count |   mean_pairwise_edge_jaccard |   maximum_pairwise_edge_jaccard |   minimum_pairwise_edge_jaccard |
|:--------------|:----------|------------------:|-----------------------------:|--------------------------------:|--------------------------------:|
| od_01         | motorbike |                 8 |                       0.0103 |                          0.0769 |                          0      |
| od_01         | walking   |                 8 |                       0.1596 |                          0.9565 |                          0.0025 |
| od_02         | motorbike |                 8 |                       0.025  |                          0.0997 |                          0.0053 |
| od_02         | walking   |                 8 |                       0.0601 |                          0.6564 |                          0.0061 |
| od_03         | motorbike |                 8 |                       0.0099 |                          0.0475 |                          0      |
| od_03         | walking   |                 8 |                       0.0335 |                          0.144  |                          0      |
| od_04         | motorbike |                 8 |                       0.0113 |                          0.0415 |                          0.0043 |
| od_04         | walking   |                 8 |                       0.258  |                          0.9795 |                          0.0068 |
| od_05         | motorbike |                 8 |                       0.0115 |                          0.0519 |                          0      |
| od_05         | walking   |                 8 |                       0.359  |                          0.9841 |                          0.005  |
| od_06         | motorbike |                 8 |                       0.014  |                          0.1942 |                          0      |
| od_06         | walking   |                 8 |                       0.2196 |                          0.9733 |                          0      |
| od_07         | motorbike |                 8 |                       0.0235 |                          0.2542 |                          0      |
| od_07         | walking   |                 8 |                       0.146  |                          0.9672 |                          0      |
| od_08         | motorbike |                 8 |                       0.0044 |                          0.0485 |                          0      |
| od_08         | walking   |                 8 |                       0.1105 |                          0.9885 |                          0      |
| od_09         | motorbike |                 8 |                       0.0219 |                          0.1364 |                          0      |
| od_09         | walking   |                 8 |                       0.1447 |                          0.9608 |                          0      |
| od_10         | motorbike |                 8 |                       0.0122 |                          0.0861 |                          0.0022 |
| od_10         | walking   |                 8 |                       0.1933 |                          0.9695 |                          0.0024 |

Edge Jaccard 1 means identical edge sets; lower values indicate more distinct
alternatives. This heuristic improves diversity but does not guarantee
behaviorally distinct routes.

## C. Feasible-route availability by user tolerance

`T_max = T_fastest + delta_time_allowed_minutes`, with
`delta ∈ {0,1,2,3,5,10}`.

|   delta_time_allowed_minutes |   scenario_mode_cases |   no_alternative_beyond_fastest |   only_one_feasible_route |   exactly_two_feasible_routes |   at_least_three_feasible_routes |   at_least_three_feasible_alternatives |
|-----------------------------:|----------------------:|--------------------------------:|--------------------------:|------------------------------:|---------------------------------:|---------------------------------------:|
|                            0 |                    20 |                              20 |                        20 |                             0 |                                0 |                                      0 |
|                            1 |                    20 |                               0 |                         0 |                             7 |                               13 |                                      5 |
|                            2 |                    20 |                               0 |                         0 |                             2 |                               18 |                                      9 |
|                            3 |                    20 |                               0 |                         0 |                             0 |                               20 |                                     16 |
|                            5 |                    20 |                               0 |                         0 |                             0 |                               20 |                                     19 |
|                           10 |                    20 |                               0 |                         0 |                             0 |                               20 |                                     20 |

Zero minutes is intentionally strict and often leaves only the fastest route.
No tolerance is altered to manufacture alternatives.

## D. Top-3 multi-route output

The output always retains the fastest route as a reference and adds up to three
distinct feasible alternatives sorted by predicted exposure. A representative
subset is shown; complete web-ready rows are in `shortlist.csv`.

| scenario_id   | mode      |   delta_time_allowed_minutes |   epsilon_internal |   maximum_feasible_time_minutes | route_id    |   rank | route_type          |   travel_time_minutes |   additional_time_vs_fastest_minutes |   distance_m |   predicted_exposure_index |   predicted_exposure_reduction_vs_fastest |   oracle_exposure_index |   oracle_exposure_reduction_vs_fastest |   segment_count |   edge_jaccard_with_fastest |   edge_difference_fraction_from_fastest |   available_feasible_alternatives |   requested_alternative_count | fewer_than_requested_alternatives   |
|:--------------|:----------|-----------------------------:|-------------------:|--------------------------------:|:------------|-------:|:--------------------|----------------------:|-------------------------------------:|-------------:|---------------------------:|------------------------------------------:|------------------------:|---------------------------------------:|----------------:|----------------------------:|----------------------------------------:|----------------------------------:|------------------------------:|:------------------------------------|
| od_01         | motorbike |                            0 |             0      |                          8.2303 | motorbike-1 |      0 | fastest             |                8.2303 |                               0      |      3429.29 |                    213.668 |                                    0      |                 263.291 |                                 0      |             119 |                      1      |                                  0      |                                 0 |                             3 | True                                |
| od_01         | motorbike |                            3 |             0.3645 |                         11.2303 | motorbike-1 |      0 | fastest             |                8.2303 |                               0      |      3429.29 |                    213.668 |                                    0      |                 263.291 |                                 0      |             119 |                      1      |                                  0      |                                 2 |                             3 | True                                |
| od_01         | motorbike |                            3 |             0.3645 |                         11.2303 | motorbike-2 |      1 | AIRPATH alternative |                8.9293 |                               0.699  |      3720.55 |                    233.611 |                                  -19.9424 |                 289.102 |                               -25.811  |             139 |                      0.0118 |                                  0.9882 |                                 2 |                             3 | True                                |
| od_01         | motorbike |                            3 |             0.3645 |                         11.2303 | motorbike-3 |      2 | AIRPATH alternative |               10.4832 |                               2.2529 |      4368.01 |                    269.75  |                                  -56.081  |                 330.716 |                               -67.4251 |             203 |                      0.0769 |                                  0.9231 |                                 2 |                             3 | True                                |
| od_01         | motorbike |                           10 |             1.215  |                         18.2303 | motorbike-1 |      0 | fastest             |                8.2303 |                               0      |      3429.29 |                    213.668 |                                    0      |                 263.291 |                                 0      |             119 |                      1      |                                  0      |                                 6 |                             3 | False                               |
| od_01         | motorbike |                           10 |             1.215  |                         18.2303 | motorbike-2 |      1 | AIRPATH alternative |                8.9293 |                               0.699  |      3720.55 |                    233.611 |                                  -19.9424 |                 289.102 |                               -25.811  |             139 |                      0.0118 |                                  0.9882 |                                 6 |                             3 | False                               |
| od_01         | motorbike |                           10 |             1.215  |                         18.2303 | motorbike-3 |      2 | AIRPATH alternative |               10.4832 |                               2.2529 |      4368.01 |                    269.75  |                                  -56.081  |                 330.716 |                               -67.4251 |             203 |                      0.0769 |                                  0.9231 |                                 6 |                             3 | False                               |
| od_01         | motorbike |                           10 |             1.215  |                         18.2303 | motorbike-5 |      3 | AIRPATH alternative |               11.7199 |                               3.4896 |      4883.28 |                    300.263 |                                  -86.5941 |                 366.846 |                              -103.555  |             218 |                      0.012  |                                  0.988  |                                 6 |                             3 | False                               |
| od_01         | walking   |                            0 |             0      |                         40.006  | walking-1   |      0 | fastest             |               40.006  |                               0      |      3333.83 |                   1038.35  |                                    0      |                1280.4   |                                 0      |             111 |                      1      |                                  0      |                                 0 |                             3 | True                                |
| od_01         | walking   |                            3 |             0.075  |                         43.006  | walking-1   |      0 | fastest             |               40.006  |                               0      |      3333.83 |                   1038.35  |                                    0      |                1280.4   |                                 0      |             111 |                      1      |                                  0      |                                 3 |                             3 | False                               |
| od_01         | walking   |                            3 |             0.075  |                         43.006  | walking-7   |      1 | AIRPATH alternative |               40.0185 |                               0.0126 |      3334.88 |                   1038.67  |                                   -0.3244 |                1280.8   |                                -0.3993 |             111 |                      0.9474 |                                  0.0526 |                                 3 |                             3 | False                               |
| od_01         | walking   |                            3 |             0.075  |                         43.006  | walking-8   |      2 | AIRPATH alternative |               40.0464 |                               0.0404 |      3337.2  |                   1039.39  |                                   -1.043  |                1281.66  |                                -1.2584 |             114 |                      0.9565 |                                  0.0435 |                                 3 |                             3 | False                               |
| od_01         | walking   |                            3 |             0.075  |                         43.006  | walking-2   |      3 | AIRPATH alternative |               41.5539 |                               1.5479 |      3462.82 |                   1082.1   |                                  -43.7536 |                1338.08  |                               -57.6757 |             105 |                      0.0141 |                                  0.9859 |                                 3 |                             3 | False                               |
| od_01         | walking   |                           10 |             0.25   |                         50.006  | walking-1   |      0 | fastest             |               40.006  |                               0      |      3333.83 |                   1038.35  |                                    0      |                1280.4   |                                 0      |             111 |                      1      |                                  0      |                                 5 |                             3 | False                               |
| od_01         | walking   |                           10 |             0.25   |                         50.006  | walking-7   |      1 | AIRPATH alternative |               40.0185 |                               0.0126 |      3334.88 |                   1038.67  |                                   -0.3244 |                1280.8   |                                -0.3993 |             111 |                      0.9474 |                                  0.0526 |                                 5 |                             3 | False                               |
| od_01         | walking   |                           10 |             0.25   |                         50.006  | walking-8   |      2 | AIRPATH alternative |               40.0464 |                               0.0404 |      3337.2  |                   1039.39  |                                   -1.043  |                1281.66  |                                -1.2584 |             114 |                      0.9565 |                                  0.0435 |                                 5 |                             3 | False                               |
| od_01         | walking   |                           10 |             0.25   |                         50.006  | walking-2   |      3 | AIRPATH alternative |               41.5539 |                               1.5479 |      3462.82 |                   1082.1   |                                  -43.7536 |                1338.08  |                               -57.6757 |             105 |                      0.0141 |                                  0.9859 |                                 5 |                             3 | False                               |
| od_02         | motorbike |                            0 |             0      |                          9.6748 | motorbike-1 |      0 | fastest             |                9.6748 |                               0      |      4031.17 |                    259.827 |                                    0      |                 380.062 |                                 0      |             136 |                      1      |                                  0      |                                 0 |                             3 | True                                |
| od_02         | motorbike |                            3 |             0.3101 |                         12.6748 | motorbike-1 |      0 | fastest             |                9.6748 |                               0      |      4031.17 |                    259.827 |                                    0      |                 380.062 |                                 0      |             136 |                      1      |                                  0      |                                 5 |                             3 | False                               |
| od_02         | motorbike |                            3 |             0.3101 |                         12.6748 | motorbike-2 |      1 | AIRPATH alternative |               10.0312 |                               0.3564 |      4179.67 |                    265.985 |                                   -6.1585 |                 380.332 |                                -0.2693 |             132 |                      0.0308 |                                  0.9692 |                                 5 |                             3 | False                               |
| od_02         | motorbike |                            3 |             0.3101 |                         12.6748 | motorbike-3 |      2 | AIRPATH alternative |               10.0948 |                               0.42   |      4206.18 |                    270.116 |                                  -10.289  |                 392.623 |                               -12.5614 |             116 |                      0.05   |                                  0.95   |                                 5 |                             3 | False                               |
| od_02         | motorbike |                            3 |             0.3101 |                         12.6748 | motorbike-4 |      3 | AIRPATH alternative |               11.1908 |                               1.516  |      4662.85 |                    297.089 |                                  -37.2622 |                 427.511 |                               -47.449  |             153 |                      0.0105 |                                  0.9895 |                                 5 |                             3 | False                               |
| od_02         | motorbike |                           10 |             1.0336 |                         19.6748 | motorbike-1 |      0 | fastest             |                9.6748 |                               0      |      4031.17 |                    259.827 |                                    0      |                 380.062 |                                 0      |             136 |                      1      |                                  0      |                                 7 |                             3 | False                               |
| od_02         | motorbike |                           10 |             1.0336 |                         19.6748 | motorbike-2 |      1 | AIRPATH alternative |               10.0312 |                               0.3564 |      4179.67 |                    265.985 |                                   -6.1585 |                 380.332 |                                -0.2693 |             132 |                      0.0308 |                                  0.9692 |                                 7 |                             3 | False                               |

The internal predicted-optimal route is recorded separately and is not the only
route exposed to the future user interface.

## E–G. Predicted/oracle exposure and decision regret

Predicted-optimal selections by tolerance:

| mode      |   delta_time_allowed_minutes |   mean_selected_additional_minutes |   mean_predicted_exposure_reduction |   mean_oracle_exposure_reduction |   oracle_optimal_agreement_rate |
|:----------|-----------------------------:|-----------------------------------:|------------------------------------:|---------------------------------:|--------------------------------:|
| motorbike |                            0 |                                  0 |                                   0 |                                0 |                               1 |
| motorbike |                            1 |                                  0 |                                   0 |                                0 |                               1 |
| motorbike |                            2 |                                  0 |                                   0 |                                0 |                               1 |
| motorbike |                            3 |                                  0 |                                   0 |                                0 |                               1 |
| motorbike |                            5 |                                  0 |                                   0 |                                0 |                               1 |
| motorbike |                           10 |                                  0 |                                   0 |                                0 |                               1 |
| walking   |                            0 |                                  0 |                                   0 |                                0 |                               1 |
| walking   |                            1 |                                  0 |                                   0 |                                0 |                               1 |
| walking   |                            2 |                                  0 |                                   0 |                                0 |                               1 |
| walking   |                            3 |                                  0 |                                   0 |                                0 |                               1 |
| walking   |                            5 |                                  0 |                                   0 |                                0 |                               1 |
| walking   |                           10 |                                  0 |                                   0 |                                0 |                               1 |

Decision regret:

| delta_time_allowed_minutes   |   decisions |   mean_regret |   median_regret |   maximum_regret |   zero_regret_percentage |   oracle_optimal_agreement_percentage |
|:-----------------------------|------------:|--------------:|----------------:|-----------------:|-------------------------:|--------------------------------------:|
| ALL                          |         120 |             0 |               0 |                0 |                      100 |                                   100 |
| 0.0                          |          20 |             0 |               0 |                0 |                      100 |                                   100 |
| 1.0                          |          20 |             0 |               0 |                0 |                      100 |                                   100 |
| 2.0                          |          20 |             0 |               0 |                0 |                      100 |                                   100 |
| 3.0                          |          20 |             0 |               0 |                0 |                      100 |                                   100 |
| 5.0                          |          20 |             0 |               0 |                0 |                      100 |                                   100 |
| 10.0                         |          20 |             0 |               0 |                0 |                      100 |                                   100 |

Regret is
`(oracle exposure of predicted-optimal - oracle feasible minimum) / oracle feasible minimum`.
The delta=0 case is structurally trivial when only the fastest route is feasible,
so nontrivial readiness criteria use tolerances above zero.

## H. Expanded ranking quality

| scenario_id   | mode      |   route_count |   spearman_rank_correlation |   kendall_tau_a | top_1_agreement   |   top_2_overlap_count |   top_2_overlap_fraction |
|:--------------|:----------|--------------:|----------------------------:|----------------:|:------------------|----------------------:|-------------------------:|
| od_01         | motorbike |             8 |                      1      |          1      | True              |                     2 |                      1   |
| od_01         | walking   |             8 |                      1      |          1      | True              |                     2 |                      1   |
| od_02         | motorbike |             8 |                      1      |          1      | True              |                     2 |                      1   |
| od_02         | walking   |             8 |                      0.9762 |          0.9286 | True              |                     1 |                      0.5 |
| od_03         | motorbike |             8 |                      0.9762 |          0.9286 | True              |                     2 |                      1   |
| od_03         | walking   |             8 |                      0.9762 |          0.9286 | True              |                     2 |                      1   |
| od_04         | motorbike |             8 |                      1      |          1      | True              |                     2 |                      1   |
| od_04         | walking   |             8 |                      0.9762 |          0.9286 | True              |                     2 |                      1   |
| od_05         | motorbike |             8 |                      1      |          1      | True              |                     2 |                      1   |
| od_05         | walking   |             8 |                      0.9762 |          0.9286 | True              |                     2 |                      1   |
| od_06         | motorbike |             8 |                      1      |          1      | True              |                     2 |                      1   |
| od_06         | walking   |             8 |                      1      |          1      | True              |                     2 |                      1   |
| od_07         | motorbike |             8 |                      1      |          1      | True              |                     2 |                      1   |
| od_07         | walking   |             8 |                      1      |          1      | True              |                     2 |                      1   |
| od_08         | motorbike |             8 |                      0.9762 |          0.9286 | True              |                     2 |                      1   |
| od_08         | walking   |             8 |                      0.9762 |          0.9286 | True              |                     2 |                      1   |
| od_09         | motorbike |             8 |                      1      |          1      | True              |                     2 |                      1   |
| od_09         | walking   |             8 |                      1      |          1      | True              |                     2 |                      1   |
| od_10         | motorbike |             8 |                      0.9762 |          0.9286 | True              |                     2 |                      1   |
| od_10         | walking   |             8 |                      0.9762 |          0.9286 | True              |                     2 |                      1   |

Milestone 4 mean Spearman was 0.875 over four scenario/mode cases. This expanded
experiment reports 20 cases; top-1 agreement remains an evaluation statistic,
not a recommendation.

## I–K. Mode and tolerance trade-offs

Walking accumulates a larger PM×minutes index because baseline travel time is
longer. Tables and `time_exposure_tradeoff.png` show additional minutes,
predicted reduction, and oracle reduction rather than hiding the trade-off.

The primary parameter is always absolute minutes. Epsilon may be derived as
`delta / fastest_time` internally but is not required from users.

## Feasibility failures

|   delta_time_allowed_minutes |   scenario_mode_cases |   no_alternative_beyond_fastest |   only_one_feasible_route |   exactly_two_feasible_routes |   at_least_three_feasible_routes |   at_least_three_feasible_alternatives |
|-----------------------------:|----------------------:|--------------------------------:|--------------------------:|------------------------------:|---------------------------------:|---------------------------------------:|
|                            0 |                    20 |                              20 |                        20 |                             0 |                                0 |                                      0 |
|                            1 |                    20 |                               0 |                         0 |                             7 |                               13 |                                      5 |
|                            2 |                    20 |                               0 |                         0 |                             2 |                               18 |                                      9 |
|                            3 |                    20 |                               0 |                         0 |                             0 |                               20 |                                     16 |
|                            5 |                    20 |                               0 |                         0 |                             0 |                               20 |                                     19 |
|                           10 |                    20 |                               0 |                         0 |                             0 |                               20 |                                     20 |

Rows explicitly distinguish no alternative, exactly two feasible routes, and
three-or-more feasible choices for future UI handling.

## Scientific limitations

1. Exposure is a time-weighted PM2.5 proxy, not inhaled dose.
2. Target-time PM2.5 remains hourly; minute-level accuracy is unvalidated.
3. Oracle exposure is IDW-derived and not measured on roads.
4. Speeds omit traffic, signals, turns, and delay.
5. The pilot is geographically bounded.
6. Fixed/community/reference data limitations remain.
7. Alternatives are algorithmic OSM paths and can still overlap.
8. Forecast exposure magnitude error observed in Milestone 4 remains.
9. Lower predicted exposure is not a guaranteed health benefit.

Use “lower estimated PM2.5 exposure”, “lower predicted exposure”, and
“exposure-aware route”; do not claim medical protection.

## L. Prototype integration decision

### A. READY FOR PROTOTYPE INTEGRATION

All strict decision-quality and shortlist-availability gates pass.

```json
{
  "nontrivial_mean_decision_regret": 0.0,
  "nontrivial_maximum_decision_regret": 0.0,
  "nontrivial_oracle_optimal_agreement_rate": 1.0,
  "expanded_mean_spearman": 0.9892857142857142,
  "five_minute_three_alternative_availability_rate": 0.95,
  "strict_mean_regret_le_0_02": true,
  "strict_max_regret_le_0_10": true,
  "strict_oracle_agreement_ge_0_90": true,
  "strict_mean_spearman_ge_0_80": true,
  "strict_three_alternative_rate_ge_0_80": true,
  "restricted_mean_regret_le_0_05": true,
  "restricted_max_regret_le_0_20": true,
  "restricted_oracle_agreement_ge_0_70": true,
  "restricted_mean_spearman_ge_0_60": true,
  "restricted_three_alternative_rate_ge_0_50": true
}
```

An A/B result permits only future prototype integration that shows the fastest
route and multiple transparent alternatives. It does not authorize a
single-route recommendation or production deployment.
