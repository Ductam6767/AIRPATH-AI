# AIRPATH-AI Milestone 3D — end-to-end forecast + spatial validation

## Protocol

This development-only experiment uses persisted **XGBoost V1 validation
predictions generated from training-period fits**. It does not retrain a model,
select on the exposed forecasting test period, or alter any temporal split.
Complete six-station forecast cases are evaluated with leave-one-station-out
(LOSO) spatial validation. IDW p=1 and its five contributing stations are
identical in oracle and forecast+spatial modes.

Pooled rows count forecast cases; because one target can be reached from
different origins/horizons, pooled `n` is not the number of unique hours. Both
are reported in saved tables.

## A–C. Oracle spatial, forecast-only, and forecast+spatial metrics

### Pooled

| pipeline         |     n |   unique_target_timestamps |    mae |   rmse |     r2 |
|:-----------------|------:|---------------------------:|-------:|-------:|-------:|
| forecast_only    | 20664 |                       1183 | 5.4622 | 7.9257 | 0.4731 |
| oracle_spatial   | 20664 |                       1183 | 5.4416 | 8.0392 | 0.4579 |
| forecast_spatial | 20664 |                       1183 | 6.9116 | 9.5043 | 0.2423 |

### Per horizon

| pipeline         |   horizon_hours |    n |    mae |   rmse |     r2 |
|:-----------------|----------------:|-----:|-------:|-------:|-------:|
| forecast_only    |               1 | 6930 | 4.5721 | 6.9377 | 0.5934 |
| forecast_only    |               2 | 6882 | 5.5677 | 8.032  | 0.4629 |
| forecast_only    |               3 | 6852 | 6.2565 | 8.7158 | 0.3625 |
| oracle_spatial   |               1 | 6930 | 5.4233 | 7.9225 | 0.4697 |
| oracle_spatial   |               2 | 6882 | 5.4457 | 8.0767 | 0.4569 |
| oracle_spatial   |               3 | 6852 | 5.4559 | 8.1181 | 0.4469 |
| forecast_spatial |               1 | 6930 | 6.3787 | 8.9192 | 0.3279 |
| forecast_spatial |               2 | 6882 | 6.9482 | 9.5702 | 0.2375 |
| forecast_spatial |               3 | 6852 | 7.4137 | 9.9986 | 0.161  |

### Per held-out station

| pipeline         |   held_out_station |    n |    mae |    rmse |      r2 |
|:-----------------|-------------------:|-----:|-------:|--------:|--------:|
| forecast_only    |                  1 | 3444 | 6.0289 |  7.8985 |  0.2841 |
| forecast_only    |                  2 | 3444 | 4.5301 |  6.4895 |  0.4512 |
| forecast_only    |                  3 | 3444 | 7.7935 | 11.1183 |  0.3235 |
| forecast_only    |                  4 | 3444 | 6.1632 |  9.3556 |  0.4696 |
| forecast_only    |                  5 | 3444 | 4.1094 |  5.2123 |  0.3318 |
| forecast_only    |                  6 | 3444 | 4.1482 |  5.8383 |  0.5067 |
| oracle_spatial   |                  1 | 3444 | 5.3565 |  7.5739 |  0.3417 |
| oracle_spatial   |                  2 | 3444 | 2.62   |  4.1121 |  0.7796 |
| oracle_spatial   |                  3 | 3444 | 5.1102 |  8.8703 |  0.5694 |
| oracle_spatial   |                  4 | 3444 | 8.8275 | 11.4961 |  0.1991 |
| oracle_spatial   |                  5 | 3444 | 8.3526 |  9.5807 | -1.2577 |
| oracle_spatial   |                  6 | 3444 | 2.3827 |  3.2961 |  0.8428 |
| forecast_spatial |                  1 | 3444 | 7.0689 |  9.0672 |  0.0565 |
| forecast_spatial |                  2 | 3444 | 4.7139 |  6.4797 |  0.4528 |
| forecast_spatial |                  3 | 3444 | 7.5641 | 11.1835 |  0.3156 |
| forecast_spatial |                  4 | 3444 | 8.4624 | 12.3541 |  0.0751 |
| forecast_spatial |                  5 | 3444 | 9.5741 | 10.3528 | -1.6362 |
| forecast_spatial |                  6 | 3444 | 4.0861 |  5.737  |  0.5237 |

Full station×horizon results are saved in `heldout_metrics.csv`.

## D. Error decomposition

| horizon_hours   |   forecast_only_mae |   oracle_spatial_mae |   forecast_spatial_mae |   combined_minus_oracle_mae |   combined_minus_forecast_only_mae |   forecast_only_rmse |   oracle_spatial_rmse |   forecast_spatial_rmse |   combined_minus_oracle_rmse |   combined_minus_forecast_only_rmse |   forecast_only_r2 |   oracle_spatial_r2 |   forecast_spatial_r2 |   combined_minus_oracle_r2 |   combined_minus_forecast_only_r2 |
|:----------------|--------------------:|---------------------:|-----------------------:|----------------------------:|-----------------------------------:|---------------------:|----------------------:|------------------------:|-----------------------------:|------------------------------------:|-------------------:|--------------------:|----------------------:|---------------------------:|----------------------------------:|
| ALL             |              5.4622 |               5.4416 |                 6.9116 |                      1.47   |                             1.4494 |               7.9257 |                8.0392 |                  9.5043 |                       1.4651 |                              1.5786 |             0.4731 |              0.4579 |                0.2423 |                    -0.2156 |                           -0.2308 |
| 1               |              4.5721 |               5.4233 |                 6.3787 |                      0.9554 |                             1.8066 |               6.9377 |                7.9225 |                  8.9192 |                       0.9967 |                              1.9814 |             0.5934 |              0.4697 |                0.3279 |                    -0.1418 |                           -0.2655 |
| 2               |              5.5677 |               5.4457 |                 6.9482 |                      1.5025 |                             1.3805 |               8.032  |                8.0767 |                  9.5702 |                       1.4934 |                              1.5382 |             0.4629 |              0.4569 |                0.2375 |                    -0.2194 |                           -0.2254 |
| 3               |              6.2565 |               5.4559 |                 7.4137 |                      1.9578 |                             1.1573 |               8.7158 |                8.1181 |                  9.9986 |                       1.8805 |                              1.2828 |             0.3625 |              0.4469 |                0.161  |                    -0.2859 |                           -0.2015 |

`combined_minus_oracle` describes the error change when station forecasts
replace simultaneous observations before the same IDW operation.
`combined_minus_forecast_only` describes the difference between predicting the
held-out station directly and transferring the other five forecasts spatially.
These differences are not additive variance components and do not establish
causality; forecast and spatial errors can reinforce or partially cancel.

## E. Route-segment end-to-end check

Two reproducible station-6-to-station-5 routes (walking and motorbike) depart at
2022-02-28 06:00:00, using saved validation forecasts from origin
2022-02-28 05:00:00. The table shows selected segments under the current
ceiling rule:

| mode      | route_id    |   segment_index | eta                           | mapping_method                        | mapped_target_time   |   oracle_spatial_pm25 |   forecast_spatial_pm25 |   absolute_error |   nearest_station_distance_km |   effective_station_count | reliability_status   |
|:----------|:------------|----------------:|:------------------------------|:--------------------------------------|:---------------------|----------------------:|------------------------:|-----------------:|------------------------------:|--------------------------:|:---------------------|
| motorbike | motorbike-1 |               1 | 2022-02-28 06:00:12.255383185 | ceiling_to_next_hour_no_interpolation | 2022-02-28 07:00:00  |               33.258  |                 26.6846 |           6.5735 |                        0.0761 |                    1.1311 | supported            |
| motorbike | motorbike-1 |               2 | 2022-02-28 06:00:29.675284872 | ceiling_to_next_hour_no_interpolation | 2022-02-28 07:00:00  |               33.1961 |                 26.565  |           6.6312 |                        0.1475 |                    1.2609 | supported            |
| motorbike | motorbike-1 |               3 | 2022-02-28 06:00:41.278449392 | ceiling_to_next_hour_no_interpolation | 2022-02-28 07:00:00  |               33.1463 |                 26.4961 |           6.6501 |                        0.1875 |                    1.3366 | supported            |
| walking   | walking-1   |               1 | 2022-02-28 06:01:01.276915927 | ceiling_to_next_hour_no_interpolation | 2022-02-28 07:00:00  |               33.258  |                 26.6846 |           6.5735 |                        0.0761 |                    1.1311 | supported            |
| walking   | walking-1   |               2 | 2022-02-28 06:02:28.376424359 | ceiling_to_next_hour_no_interpolation | 2022-02-28 07:00:00  |               33.1961 |                 26.565  |           6.6312 |                        0.1475 |                    1.2609 | supported            |
| walking   | walking-1   |               3 | 2022-02-28 06:03:26.392246959 | ceiling_to_next_hour_no_interpolation | 2022-02-28 07:00:00  |               33.1463 |                 26.4961 |           6.6501 |                        0.1875 |                    1.3366 | supported            |
| motorbike | motorbike-1 |             133 | 2022-02-28 06:09:12.899526607 | ceiling_to_next_hour_no_interpolation | 2022-02-28 07:00:00  |               15.67   |                 17.3318 |           1.6618 |                        0.1039 |                    1.1715 | supported            |
| walking   | walking-1   |             121 | 2022-02-28 06:46:13.918312141 | ceiling_to_next_hour_no_interpolation | 2022-02-28 07:00:00  |               15.67   |                 17.3318 |           1.6618 |                        0.1039 |                    1.1715 | supported            |

The reference is hourly oracle IDW at the road midpoint using all six observed
station values. It is the best internal reference available but **is not an
observed road concentration**. Segment error is forecast+IDW minus oracle IDW;
no exposure is aggregated.

## F. Target-time mapping sensitivity

No method interpolates:

- `ceiling`: next hour;
- `floor`: containing hour;
- `nearest`: closest hour, with exact hh:30 ties going forward.

| mode      | mapping_rule   |   segments |   mapped_target_hours |   mae_vs_oracle_spatial |   rmse_vs_oracle_spatial |   max_absolute_error |
|:----------|:---------------|-----------:|----------------------:|------------------------:|-------------------------:|---------------------:|
| motorbike | ceiling        |        133 |                     1 |                  4.0345 |                   4.5226 |               6.6797 |
| motorbike | floor          |        133 |                     1 |                  1.4621 |                   1.5299 |               2.6976 |
| motorbike | nearest        |        133 |                     1 |                  1.4621 |                   1.5299 |               2.6976 |
| walking   | ceiling        |        121 |                     1 |                  4.3736 |                   4.7557 |               6.6797 |
| walking   | floor          |        121 |                     1 |                  1.3951 |                   1.4594 |               2.6976 |
| walking   | nearest        |        121 |                     2 |                  1.5282 |                   1.7199 |               3.6079 |

For this development example, mean segment MAE across modes is
**1.429** for floor, **1.495** for nearest, and
**4.204 µg/m³** for ceiling. The lowest-error rule is therefore
**floor**.

The most defensible rule for retrospective validation of the current hourly
product is **floor to the containing hour**, conditional on treating `HH:00` as
the label of that hourly bin. It also has the lowest development error here and
does not interpolate. This does **not** silently change Milestone 3C: when the
forecast origin equals departure, floor may map early segments to unsupported
t+0h. A prospective deployment adopting floor must issue forecasts at least one
hour before departure and still enforce the frozen 1–3h horizon. Ceiling remains
an explicit fallback when that operational condition is not met. No rule is
validated at the exact minute because no sub-hourly road reference exists.

## G. Reliability/error relationship

| analysis                  | error_measure                          | proxy                              |   n |   spearman_rank_correlation |
|:--------------------------|:---------------------------------------|:-----------------------------------|----:|----------------------------:|
| heldout_station_aggregate | combined_mae                           | nearest_station_distance_km        |   6 |                     -0.2319 |
| heldout_station_aggregate | combined_mae                           | second_nearest_station_distance_km |   6 |                     -0.3189 |
| heldout_station_aggregate | combined_mae                           | maximum_idw_weight                 |   6 |                      0.3714 |
| heldout_station_aggregate | combined_mae                           | effective_station_count            |   6 |                     -0.0286 |
| route_segments_ceiling    | absolute_forecast_minus_oracle_spatial | nearest_station_distance_km        | 254 |                      0.2369 |
| route_segments_ceiling    | absolute_forecast_minus_oracle_spatial | second_nearest_station_distance_km | 254 |                     -0.2165 |
| route_segments_ceiling    | absolute_forecast_minus_oracle_spatial | maximum_idw_weight                 | 254 |                     -0.2457 |
| route_segments_ceiling    | absolute_forecast_minus_oracle_spatial | effective_station_count            | 254 |                      0.2517 |

Ceiling-rule route errors by qualitative status:

| mode      | reliability_status   |   segments |   mae_vs_oracle_spatial |   rmse_vs_oracle_spatial |
|:----------|:---------------------|-----------:|------------------------:|-------------------------:|
| motorbike | moderate reliability |          3 |                  4.2112 |                   4.4101 |
| motorbike | supported            |        130 |                  4.0304 |                   4.5252 |
| walking   | moderate reliability |          8 |                  3.5701 |                   3.6926 |
| walking   | supported            |        113 |                  4.4305 |                   4.8221 |

Correlations are descriptive Spearman rank associations. Held-out geometry has
only six independent station locations; segment rows share stations, routes,
and forecast errors. These proxies are not calibrated intervals, and observed
associations must not be generalized as uncertainty calibration.

## H. Limitations

1. Validation is development-only; no untouched final end-to-end test remains.
2. Frozen validation predictions are from training-period fits, while the
   serialized deployment forecaster was later refit on train+validation.
3. Six stations provide sparse, heterogeneous spatial support.
4. Complete-case evaluation favors hours with all station values and forecasts.
5. Route “truth” is an oracle IDW pseudo-reference, not road measurement.
6. Constant-speed ETA and heavy overlap between candidate routes remain.
7. Forecast and spatial error differences are descriptive, not causal.
8. No exposure, dose, route ranking, or optimization is computed.

## I. Readiness decision

### B. READY WITH RESTRICTIONS

Combined error meets pooled usability criteria and generalizes positively at at least four stations, but not every strict criterion.

Proceed only to an offline, pilot-area exposure-aggregation experiment with reliability flags and station-level diagnostics. Do not use it for route recommendation: station 5 has negative combined R² and no road-level ground truth exists.

Decision criteria and observed pass/fail values:

```json
{
  "combined_mae_relative_to_worse_component": 1.2653444956096038,
  "combined_mae_degradation_le_50_percent": true,
  "pooled_r2_positive": true,
  "at_least_four_of_six_station_r2_positive": true,
  "positive_station_r2_count": 5,
  "ready_strict_mae_degradation_le_10_percent": false,
  "ready_strict_r2_no_worse_than_component_floor": false,
  "ready_strict_all_station_r2_nonnegative": false
}
```

The decision uses relative degradation from the worse standalone component,
pooled combined R², and the number of stations with positive combined R².
The restricted gate allows at most 50% MAE degradation and requires positive
pooled R² plus positive R² at four of six stations. The strict gate allows at
most 10% degradation, no pooled R² loss below the weaker standalone component,
and non-negative R² at every station. These are transparent prototype
progression gates, not clinical or regulatory air-quality thresholds.

## J. Future sub-hourly validation requirements

Current HealthyAir validation is hourly. The system can construct
`PM2.5(location, target_time)` only at supported hourly targets. These results
do **not** validate PM2.5 at minute-level arrival times.

Validating `PM2.5(X, exact arrival time)` requires independent, quality-controlled
sub-hourly observations with documented station/location metadata, timestamps,
continuity, calibration, and coverage overlapping the road pilot. The same
resolution-aware adapter can accept that future source without fabricating
intermediate observations.
