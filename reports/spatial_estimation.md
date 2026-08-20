# AIRPATH-AI Milestone 3A — spatial PM2.5 estimation foundation

## Scope and scientific protocol

This milestone estimates **PM2.5(X, T)** from station-level PM2.5 values supplied
for an exact target time. It does not implement routing, ETA, exposure, web
features, external observations, additional pollutants, or new forecasting models.

The primary experiment is **leave-one-station-out (LOSO)** spatial cross-validation:
each HealthyAir station is held out in turn and estimated from the other five at
timestamps where all six PM2.5 observations exist. No rows are randomly split.

Only the pre-existing **train + validation development period** is used. The
previously exposed forecasting test period (2022-04-08 01:00 onward) is not used
for spatial model comparison or temporal robustness. Consequently these are
development results, not a new untouched final test claim.

## A. Verified station coordinates and source

Coordinates and station types are from Rakholia et al., *Outdoor air quality data
for spatiotemporal analysis and air quality modelling in Ho Chi Minh City,
Vietnam: A part of HealthyAir Project*, Data in Brief 46 (2023) 108774,
[doi:10.1016/j.dib.2022.108774](https://doi.org/10.1016/j.dib.2022.108774),
Table 1. The accompanying dataset is archived as
[Mendeley Data doi:10.17632/pk6tzrjks8.1](https://doi.org/10.17632/pk6tzrjks8.1)
under CC BY 4.0.

**Coordinate-label caveat:** the paper's rendered Table 1 labels the 10.x column
“longitude” and the 106.x column “latitude.” Those headers are geographically
transposed: HCMC is near 10.8°N, 106.7°E. Values below retain the paper's exact
numbers but assign the physically valid WGS84 order (`latitude=10.x`,
`longitude=106.x`). This is a documented source correction, not geocoding.

|   station_id |   latitude |   longitude | station_type                                       | location                                                         |
|-------------:|-----------:|------------:|:---------------------------------------------------|:-----------------------------------------------------------------|
|            1 |    10.8699 |     106.796 | Urban background: Industry + Traffic + Residential | Vietnam National University, Linh Trung ward, Thu Duc city, HCMC |
|            2 |    10.741  |     106.617 | Traffic                                            | 20 Nguyen Trong Tri street, An Lac ward, Binh Tan district, HCMC |
|            3 |    10.8162 |     106.62  | Industry                                           | Tan Binh industrial zone, Tay Thanh ward, Tan Phu district, HCMC |
|            4 |    10.8158 |     106.717 | Residential                                        | 49 Thanh Da street, Ward 27, Binh Thanh district, HCMC           |
|            5 |    10.7764 |     106.688 | Traffic                                            | 268 Nguyen Dinh Chieu street, Ward 6, District 3, HCMC           |
|            6 |    10.7805 |     106.659 | Traffic + Residential                              | MM18 Truong Son street, Ward 14, District 10, HCMC               |

The station map is `reports/figures/spatial_station_map.png`; no external basemap
or geographic dataset is used.

## B. Spatial coverage and geometry limitations

Pairwise separation ranges from **3.13 km** (stations 5–6) to
**24.24 km** (stations 1–2). The six-station convex hull covers
approximately **96.1 km²**. Stations 2–6 form a denser
central/western support polygon of approximately **54.9 km²**;
station 1 is a relatively isolated north-eastern point.

|   station_a |   station_b |   distance_km |
|------------:|------------:|--------------:|
|           1 |           2 |        24.236 |
|           1 |           3 |        20.086 |
|           1 |           4 |        10.481 |
|           1 |           5 |        15.746 |
|           1 |           6 |        17.928 |
|           2 |           3 |         8.374 |
|           2 |           4 |        13.76  |
|           2 |           5 |         8.666 |
|           2 |           6 |         6.377 |
|           3 |           4 |        10.596 |
|           3 |           5 |         8.592 |
|           3 |           6 |         5.829 |
|           4 |           5 |         5.453 |
|           4 |           6 |         7.454 |
|           5 |           6 |         3.13  |

Nearest-neighbour support by station:

|   station_id |   nearest_other_station_km |
|-------------:|---------------------------:|
|            1 |                     10.481 |
|            2 |                      6.377 |
|            3 |                      5.829 |
|            4 |                      5.453 |
|            5 |                      3.13  |
|            6 |                      3.13  |

The geometry samples traffic, residential, industrial, and mixed contexts, but
six points are not sufficient for city-wide road-scale interpolation. The
network has no replicated local neighbourhoods, substantial edge/extrapolation
regions, a 24 km longest baseline, and no covariates for roads, land use,
elevation, meteorology, or local emission sources. IDW encodes smoothness by
distance only; it cannot represent barriers or near-road gradients.

## C–E. LOSO baseline results

Pooled development-period results:

| model   |     n |   unique_timestamps |    mae |    rmse |     r2 |
|:--------|------:|--------------------:|-------:|--------:|-------:|
| nearest | 25368 |                4228 | 8.7038 | 15.4612 | 0.0227 |
| idw_p1  | 25368 |                4228 | 7.0606 | 12.7208 | 0.3384 |
| idw_p2  | 25368 |                4228 | 7.1737 | 12.8978 | 0.3199 |

`nearest` is the nearest-station baseline. `idw_p1` and `idw_p2` use
`w_i = 1 / d_i^p`, with exact zero-distance queries returning the coincident
station value safely. The two IDW powers were declared in advance; there was no
large hyperparameter search.

## F. Held-out station performance

| model   |   held_out_station |    n |   unique_timestamps |     mae |    rmse |      r2 |
|:--------|-------------------:|-----:|--------------------:|--------:|--------:|--------:|
| nearest |                  1 | 4228 |                4228 | 10.2615 | 19.6869 | -2.1011 |
| nearest |                  2 | 4228 |                4228 |  3.8116 |  6.9639 |  0.6928 |
| nearest |                  3 | 4228 |                4228 |  8.443  | 15.9339 |  0.403  |
| nearest |                  4 | 4228 |                4228 | 15.184  | 23.5043 | -0.3123 |
| nearest |                  5 | 4228 |                4228 |  7.2612 |  9.7949 | -0.3353 |
| nearest |                  6 | 4228 |                4228 |  7.2612 |  9.7949 |  0.211  |
| idw_p1  |                  1 | 4228 |                4228 |  6.7714 | 10.404  |  0.1339 |
| idw_p1  |                  2 | 4228 |                4228 |  4.1121 |  6.9934 |  0.6902 |
| idw_p1  |                  3 | 4228 |                4228 |  8.505  | 15.8297 |  0.4108 |
| idw_p1  |                  4 | 4228 |                4228 |  9.7258 | 18.9891 |  0.1435 |
| idw_p1  |                  5 | 4228 |                4228 |  9.9564 | 13.0395 | -1.3664 |
| idw_p1  |                  6 | 4228 |                4228 |  3.2932 |  5.7063 |  0.7322 |
| idw_p2  |                  1 | 4228 |                4228 |  7.0174 | 11.537  | -0.065  |
| idw_p2  |                  2 | 4228 |                4228 |  3.9081 |  6.731  |  0.713  |
| idw_p2  |                  3 | 4228 |                4228 |  8.4998 | 15.8674 |  0.408  |
| idw_p2  |                  4 | 4228 |                4228 | 10.7112 | 19.7497 |  0.0735 |
| idw_p2  |                  5 | 4228 |                4228 |  9.3289 | 12.0937 | -1.0356 |
| idw_p2  |                  6 | 4228 |                4228 |  3.5766 |  5.6243 |  0.7399 |

LOSO is genuine spatial generalisation: the held-out station never contributes
to its estimate. Negative R² values mean the interpolator performs worse than
predicting that held-out sample set's mean; they are retained rather than hidden.

## G. Temporal robustness

The common complete-case development timestamps were divided chronologically
into equal early, middle, and late thirds. These periods are diagnostics only
and do not tune the methods.

| period   | period_start        | period_end          | model   |    n |   unique_timestamps |     mae |    rmse |      r2 |
|:---------|:--------------------|:--------------------|:--------|-----:|--------------------:|--------:|--------:|--------:|
| early    | 2021-02-24 16:00:00 | 2021-11-16 22:00:00 | idw_p1  | 8460 |                1410 |  6.0253 | 13.9523 |  0.1405 |
| early    | 2021-02-24 16:00:00 | 2021-11-16 22:00:00 | idw_p2  | 8460 |                1410 |  5.9324 | 14.1799 |  0.1122 |
| early    | 2021-02-24 16:00:00 | 2021-11-16 22:00:00 | nearest | 8460 |                1410 |  6.7532 | 17.3633 | -0.3312 |
| middle   | 2021-11-16 23:00:00 | 2022-01-23 05:00:00 | idw_p1  | 8454 |                1409 |  9.1572 | 14.2207 |  0.322  |
| middle   | 2021-11-16 23:00:00 | 2022-01-23 05:00:00 | idw_p2  | 8454 |                1409 |  9.3227 | 14.3072 |  0.3138 |
| middle   | 2021-11-16 23:00:00 | 2022-01-23 05:00:00 | nearest | 8454 |                1409 | 11.5114 | 16.6775 |  0.0675 |
| late     | 2022-01-23 06:00:00 | 2022-04-07 17:00:00 | idw_p1  | 8454 |                1409 |  6.0001 |  9.4094 |  0.4382 |
| late     | 2022-01-23 06:00:00 | 2022-04-07 17:00:00 | idw_p2  | 8454 |                1409 |  6.2667 |  9.6579 |  0.4082 |
| late     | 2022-01-23 06:00:00 | 2022-04-07 17:00:00 | nearest | 8454 |                1409 |  7.848  | 11.7253 |  0.1277 |

Late-versus-early MAE change:

| model   |   early |   middle |   late |   late_vs_early_mae_change_pct |
|:--------|--------:|---------:|-------:|-------------------------------:|
| idw_p1  |   6.025 |    9.157 |  6     |                         -0.417 |
| idw_p2  |   5.932 |    9.323 |  6.267 |                          5.635 |
| nearest |   6.753 |   11.511 |  7.848 |                         16.213 |

Material changes across periods indicate temporal non-stationarity and changing
pollution regimes. Stable geometry does not imply stable error: source mixtures
and station-specific biases can change over time.

## H. Reliability / uncertainty proxies

These are **not calibrated prediction intervals**:

- nearest-station distance;
- distance to the second-nearest station;
- number of stations with positive interpolation weight;
- maximum normalised IDW weight;
- weight concentration `Σw²` (higher means reliance on fewer stations);
- effective station count `1/Σw²`.

Held-out-location diagnostics:

| model   |   held_out_station |   nearest_distance_km |   second_nearest_distance_km |   contributing_stations |   maximum_weight |   weight_concentration |   effective_station_count |
|:--------|-------------------:|----------------------:|-----------------------------:|------------------------:|-----------------:|-----------------------:|--------------------------:|
| idw_p1  |                  1 |               10.4806 |                      15.7458 |                       5 |           0.3121 |                 0.2185 |                    4.5758 |
| idw_p1  |                  2 |                6.3773 |                       8.3742 |                       5 |           0.3102 |                 0.2314 |                    4.321  |
| idw_p1  |                  3 |                5.8293 |                       8.3742 |                       5 |           0.311  |                 0.2256 |                    4.4326 |
| idw_p1  |                  4 |                5.4532 |                       7.4541 |                       5 |           0.3162 |                 0.2227 |                    4.4902 |
| idw_p1  |                  5 |                3.1304 |                       5.4532 |                       5 |           0.4003 |                 0.2615 |                    3.8242 |
| idw_p1  |                  6 |                3.1304 |                       5.8293 |                       5 |           0.3813 |                 0.2525 |                    3.9611 |
| idw_p2  |                  1 |               10.4806 |                      15.7458 |                       5 |           0.4456 |                 0.2824 |                    3.5409 |
| idw_p2  |                  2 |                6.3773 |                       8.3742 |                       5 |           0.4157 |                 0.2904 |                    3.4433 |
| idw_p2  |                  3 |                5.8293 |                       8.3742 |                       5 |           0.4289 |                 0.2842 |                    3.5183 |
| idw_p2  |                  4 |                5.4532 |                       7.4541 |                       5 |           0.4489 |                 0.2931 |                    3.4123 |
| idw_p2  |                  5 |                3.1304 |                       5.4532 |                       5 |           0.6126 |                 0.4297 |                    2.3273 |
| idw_p2  |                  6 |                3.1304 |                       5.8293 |                       5 |           0.576  |                 0.3892 |                    2.5692 |
| nearest |                  1 |               10.4806 |                      15.7458 |                       1 |           1      |                 1      |                    1      |
| nearest |                  2 |                6.3773 |                       8.3742 |                       1 |           1      |                 1      |                    1      |
| nearest |                  3 |                5.8293 |                       8.3742 |                       1 |           1      |                 1      |                    1      |
| nearest |                  4 |                5.4532 |                       7.4541 |                       1 |           1      |                 1      |                    1      |
| nearest |                  5 |                3.1304 |                       5.4532 |                       1 |           1      |                 1      |                    1      |
| nearest |                  6 |                3.1304 |                       5.8293 |                       1 |           1      |                 1      |                    1      |

`reports/figures/spatial_prediction_example.png` shows an example IDW surface,
nearest-distance proxy, and weight-concentration proxy. Reliability should
decrease outside the station convex hull and where nearest distances are high.

## I. Recommended initial study area

AIRPATH should **not initially claim coverage for all HCMC**. The defensible
pilot is the station-supported central/western polygon bounded by stations
**2, 3, 4, 5, and 6** (Binh Tan–Tan Phu–Binh Thanh, including the central
District 3/District 10 interior). This choice follows monitoring geometry and
is not an automatic District 5 selection.

Restrict initial road integration to locations inside that convex hull, report
nearest-distance and weight-concentration proxies, and flag edge locations.
Station 1/Thu Duc can support a separate local demonstration but the 10–24 km
gaps between it and the rest of the network do not justify filling all eastern
HCMC by smooth interpolation.

## J. Exact forecasting-to-spatial interface

```python
estimate_pm25(
    latitude: float,
    longitude: float,
    target_time: timestamp,
    station_values: Mapping[station_id, pm25_at_target_time],
    method="idw",
    power=2,
) -> float
```

The spatial module has no forecasting-model dependency. `station_values` is the
boundary:

- **Mode A — spatial oracle:** `estimate_oracle_pm25(..., observed_station_values)`
  accepts actual station observations at T solely to evaluate interpolation.
- **Mode B — deployment:** `estimate_deployment_pm25(..., forecasted_station_values)`
  accepts station forecasts generated using information available before T.
  It has no dataset argument and cannot read future observed PM2.5.

Both wrappers call the same spatial algorithm.

### Exact target-time demonstration

At the representative existing hourly timestamp **2021-12-19 13:00**,
the supplied oracle values are `S1=8.97, S2=12.92, S3=11.10, S4=12.90, S5=6.17, S6=11.38` µg/m³. At
X=(10.778419, 106.673634), IDW p=2 produces
**9.03 µg/m³**. The architecture accepts an exact
T, but this experiment has hourly support only. It does not fabricate or claim
17:08/17:12 observations or minute-level accuracy.

## K. Readiness for road-network integration

**Proceed only to a bounded pilot integration, not city-wide production.**
The interface is suitable for passing target-time station forecasts into a
future road-segment layer, and LOSO provides an honest spatial baseline.
Road integration must retain reliability flags and must describe outputs as
spatial estimates, never direct road-level measurements.

## L. Known limitations

1. Only six stations; five contributors in each LOSO fold.
2. Coordinates are static and the paper's coordinate headers require the
   documented latitude/longitude correction above.
3. Complete-case LOSO can overrepresent periods with better network uptime.
4. Oracle metrics isolate spatial error and understate end-to-end deployment
   error, which will also contain station forecast error.
5. The forecasting test set was previously exposed during the forecasting
   milestones and was deliberately not reused here; no untouched final spatial
   test is claimed.
6. IDW/nearest use distance only and cannot resolve road-scale or source-specific
   gradients.
7. Reliability indicators are geometry proxies, not probabilistic uncertainty.
8. Predictions outside the convex hull are extrapolations and should not be
   presented as supported city-wide estimates.

## Reproducibility outputs

- `reports/tables/spatial_station_geometry.csv`
- `reports/tables/spatial_pairwise_distances.csv`
- `reports/tables/spatial_cv_metrics.csv`
- `reports/tables/spatial_heldout_results.csv`
- `reports/tables/spatial_temporal_robustness.csv`
- `reports/tables/spatial_reliability_diagnostics.csv`
- `reports/figures/spatial_station_map.png`
- `reports/figures/spatial_prediction_example.png`

No raw HealthyAir observations or forecasting split assignments were modified.
