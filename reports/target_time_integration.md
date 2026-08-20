# AIRPATH-AI Milestone 3C — target-time PM2.5 integration

## A. End-to-end integration status

Milestone 3C connects the frozen station forecaster, Milestone 3A IDW p=1
estimator, and Milestone 3B ordered segment ETAs. It produces auditable
`PM2.5(segment midpoint, mapped target hour)` records for one walking and one
motorbike route inside the validated stations 2–6 pilot polygon.

It does **not** calculate exposure, optimize or recommend routes, apply a travel
time constraint, retrain forecasting, or add air-quality data.

## B. Target-time mapping rule

Current HealthyAir/model resolution is hourly. The adapter uses:

- exact hourly ETA → same hour (`exact_hour`);
- non-hourly ETA → **ceiling to the next exact hour**
  (`ceiling_to_next_hour_no_interpolation`).

Thus 17:03 maps explicitly to 18:00. This conservative time rule never maps a
traveler passage to an earlier forecast, performs no interpolation, and records
the offset. It estimates the supported hourly target, not PM2.5 at 17:03.

## C. Supported forecast horizons

Only frozen XGBoost horizons **t+1h, t+2h, and t+3h** are accepted. Mapped
targets at t+0h, before the origin, or beyond t+3h return
`UnsupportedTargetTimeError`; no extrapolation is attempted.

The reproducible example uses forecasting/departure origin
**2022-02-28 06:00:00** in the existing validation period. All route
midpoints map to t+1h. This is an integration demonstration, not new model
selection or an untouched final evaluation.

## D–E. Oracle and deployment results

| pipeline_mode   | travel_mode   | route_id    |   segments |   mapped_target_hours |   pm25_min |   pm25_mean |   pm25_max |   supported_reliability_segments |   moderate_reliability_segments |   weak_spatial_support_segments |
|:----------------|:--------------|:------------|-----------:|----------------------:|-----------:|------------:|-----------:|---------------------------------:|--------------------------------:|--------------------------------:|
| oracle          | walking       | walking-1   |        121 |                     1 |    15.67   |     27.6665 |    33.258  |                              113 |                               8 |                               0 |
| oracle          | motorbike     | motorbike-1 |        133 |                     1 |    15.67   |     26.9543 |    33.258  |                              130 |                               3 |                               0 |
| deployment      | walking       | walking-1   |        121 |                     1 |    15.6732 |     21.7576 |    25.1026 |                              113 |                               8 |                               0 |
| deployment      | motorbike     | motorbike-1 |        133 |                     1 |    15.6732 |     21.3898 |    25.1026 |                              130 |                               3 |                               0 |

Station values at mapped target 2022-02-28 07:00:00:

|   station_id |   oracle_observed_pm25 |   deployment_forecast_pm25 |
|-------------:|-----------------------:|---------------------------:|
|            1 |                25.0833 |                    22.3056 |
|            2 |                50.3767 |                    21.5211 |
|            3 |                52.3233 |                    34.6705 |
|            4 |                35.202  |                    31.0247 |
|            5 |                13.7833 |                    14.7133 |
|            6 |                33.305  |                    25.2283 |

- **Oracle mode** reads actual station observations at the mapped hour solely to
  isolate the spatial pathway.
- **Deployment mode** accepts only an exact `StationLagBundle` containing
  station t-1h/t-2h/t-3h values and timestamps strictly before the forecasting
  origin. It calls the frozen forecaster and has no future-observation argument.

The two pathways are separate and their station-value provenance is attached to
every segment.

## F. Route-segment PM2.5 example

Small ordered excerpts (first three and final segment per route/pathway):

| station_value_source   | mode      | route_id    |   segment_index | requested_target_time         | supported_target_time   |   forecast_horizon_hours |   predicted_pm25 |   nearest_station_distance_km |   effective_station_count | reliability_status   |
|:-----------------------|:----------|:------------|----------------:|:------------------------------|:------------------------|-------------------------:|-----------------:|------------------------------:|--------------------------:|:---------------------|
| oracle_observed        | walking   | walking-1   |               1 | 2022-02-28T06:01:01.276915927 | 2022-02-28T07:00:00     |                        1 |          33.258  |                        0.0761 |                    1.1311 | supported            |
| oracle_observed        | walking   | walking-1   |               2 | 2022-02-28T06:02:28.376424359 | 2022-02-28T07:00:00     |                        1 |          33.1961 |                        0.1475 |                    1.2609 | supported            |
| oracle_observed        | walking   | walking-1   |               3 | 2022-02-28T06:03:26.392246959 | 2022-02-28T07:00:00     |                        1 |          33.1463 |                        0.1875 |                    1.3366 | supported            |
| oracle_observed        | walking   | walking-1   |             121 | 2022-02-28T06:46:13.918312141 | 2022-02-28T07:00:00     |                        1 |          15.67   |                        0.1039 |                    1.1715 | supported            |
| oracle_observed        | motorbike | motorbike-1 |               1 | 2022-02-28T06:00:12.255383185 | 2022-02-28T07:00:00     |                        1 |          33.258  |                        0.0761 |                    1.1311 | supported            |
| oracle_observed        | motorbike | motorbike-1 |               2 | 2022-02-28T06:00:29.675284872 | 2022-02-28T07:00:00     |                        1 |          33.1961 |                        0.1475 |                    1.2609 | supported            |
| oracle_observed        | motorbike | motorbike-1 |               3 | 2022-02-28T06:00:41.278449392 | 2022-02-28T07:00:00     |                        1 |          33.1463 |                        0.1875 |                    1.3366 | supported            |
| oracle_observed        | motorbike | motorbike-1 |             133 | 2022-02-28T06:09:12.899526607 | 2022-02-28T07:00:00     |                        1 |          15.67   |                        0.1039 |                    1.1715 | supported            |
| deployment_forecast    | walking   | walking-1   |               1 | 2022-02-28T06:01:01.276915927 | 2022-02-28T07:00:00     |                        1 |          25.1026 |                        0.0761 |                    1.1311 | supported            |
| deployment_forecast    | walking   | walking-1   |               2 | 2022-02-28T06:02:28.376424359 | 2022-02-28T07:00:00     |                        1 |          24.9892 |                        0.1475 |                    1.2609 | supported            |
| deployment_forecast    | walking   | walking-1   |               3 | 2022-02-28T06:03:26.392246959 | 2022-02-28T07:00:00     |                        1 |          24.9221 |                        0.1875 |                    1.3366 | supported            |
| deployment_forecast    | walking   | walking-1   |             121 | 2022-02-28T06:46:13.918312141 | 2022-02-28T07:00:00     |                        1 |          15.6732 |                        0.1039 |                    1.1715 | supported            |
| deployment_forecast    | motorbike | motorbike-1 |               1 | 2022-02-28T06:00:12.255383185 | 2022-02-28T07:00:00     |                        1 |          25.1026 |                        0.0761 |                    1.1311 | supported            |
| deployment_forecast    | motorbike | motorbike-1 |               2 | 2022-02-28T06:00:29.675284872 | 2022-02-28T07:00:00     |                        1 |          24.9892 |                        0.1475 |                    1.2609 | supported            |
| deployment_forecast    | motorbike | motorbike-1 |               3 | 2022-02-28T06:00:41.278449392 | 2022-02-28T07:00:00     |                        1 |          24.9221 |                        0.1875 |                    1.3366 | supported            |
| deployment_forecast    | motorbike | motorbike-1 |             133 | 2022-02-28T06:09:12.899526607 | 2022-02-28T07:00:00     |                        1 |          15.6732 |                        0.1039 |                    1.1715 | supported            |

Complete records are saved under `data/processed/target_time/`. Each includes
segment geometry/duration, requested and supported target times, mapping rule,
horizon, all station values used, IDW result, and reliability proxies.

## G. Reliability flags

The propagated geometry proxies are nearest and second-nearest station distance,
contributing station count, maximum IDW weight, weight concentration, and
effective station count.

Qualitative flags are deterministic heuristics:

- `supported`: either nearest station ≤1 km, or nearest ≤5 km plus
  second-nearest ≤8 km, at least five contributors, maximum weight ≤0.5, and
  effective count ≥3;
- `moderate reliability`: nearest ≤10 km, at least four contributors, effective
  count ≥2;
- otherwise `weak spatial support`.

These are **not calibrated confidence intervals**.

## H. Unsupported cases

- mapped horizon outside 1–3 hours;
- target at/before forecast origin;
- mismatched timezones or non-hourly forecasting origin;
- missing/non-finite exact station lags;
- lag timestamps not exactly origin minus 1/2/3 hours;
- missing oracle observations;
- station-value target different from the segment's mapped target;
- non-contiguous segment ordering.

## I. Core hourly-resolution limitation

Current HealthyAir data are hourly. Therefore this prototype establishes
`PM2.5(location, target_time)` **only at the supported hourly forecast
resolution**. Second-level route ETAs determine an explicit hourly target; they
do not establish minute-level PM2.5 predictive accuracy or ground truth.

The adapter boundary is resolution-aware, so future validated higher-frequency
observations and models can replace the hourly mapping without changing the
route/segment or spatial interfaces.

## J. Recommended next milestone

Next, validate temporal grouping and compounded forecast-plus-spatial error, then
implement a transparent route-exposure aggregation baseline **without route
optimization**. Route recommendation and travel-time-constraint optimization
should remain later milestones.
