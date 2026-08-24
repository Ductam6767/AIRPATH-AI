# AIRPATH-AI Milestone 4 — route exposure aggregation validation

## Scope

This is an **offline exposure-aggregation experiment only**. It does not
optimize, recommend, or constrain routes and does not alter forecasting or
spatial models.

## A. Exposure definition

For ordered route segments:

`E(route) = Σ PM2.5_i × duration_i_minutes`

The result is a **time-weighted PM2.5 exposure proxy/index** in
**(µg/m³)·min**. It is not inhaled dose: breathing rate, uptake, activity,
and personal microenvironment are absent.

## B–C. Oracle and predicted exposure results

Two OD scenarios inside the validated pilot use the existing K=5 candidates for
walking and motorbike. Oracle uses observed station values; predicted uses only
persisted frozen V1 station forecasts. Both apply identical ceiling target-time
mapping and IDW p=1.

| scenario_id   | mode      | route_id    |   total_distance_m |   total_travel_time_minutes |   segment_count |   oracle_exposure_index |   predicted_exposure_index |   exposure_difference |   absolute_exposure_error |   percentage_difference |   absolute_percentage_error |   mean_nearest_station_distance_km |   max_nearest_station_distance_km |   mean_effective_station_count |   moderate_or_weak_segment_fraction |
|:--------------|:----------|:------------|-------------------:|----------------------------:|----------------:|------------------------:|---------------------------:|----------------------:|--------------------------:|------------------------:|----------------------------:|-----------------------------------:|----------------------------------:|-------------------------------:|------------------------------------:|
| s6_to_s5      | walking   | walking-1   |            3882.4  |                     46.5888 |             121 |                1283.48  |                   1090.55  |             -192.932  |                  192.932  |                -15.0319 |                     15.0319 |                             0.9555 |                            1.603  |                         2.8075 |                              0.0661 |
| s6_to_s5      | walking   | walking-2   |            3882.72 |                     46.5926 |             120 |                1283.57  |                   1090.63  |             -192.939  |                  192.939  |                -15.0314 |                     15.0314 |                             0.9541 |                            1.603  |                         2.8044 |                              0.0667 |
| s6_to_s5      | walking   | walking-3   |            3883.7  |                     46.6044 |             120 |                1283.91  |                   1090.91  |             -192.997  |                  192.997  |                -15.032  |                     15.032  |                             0.9529 |                            1.603  |                         2.8027 |                              0.0667 |
| s6_to_s5      | walking   | walking-4   |            3884.02 |                     46.6082 |             119 |                1284     |                   1091     |             -193.004  |                  193.004  |                -15.0315 |                     15.0315 |                             0.9514 |                            1.603  |                         2.7995 |                              0.0672 |
| s6_to_s5      | walking   | walking-5   |            3884.21 |                     46.6105 |             121 |                1286.75  |                   1092.48  |             -194.268  |                  194.268  |                -15.0976 |                     15.0976 |                             0.9571 |                            1.603  |                         2.8105 |                              0.0661 |
| s6_to_s5      | motorbike | motorbike-1 |            3869.32 |                      9.2864 |             133 |                 254.413 |                    216.598 |              -37.8157 |                   37.8157 |                -14.8639 |                     14.8639 |                             0.8994 |                            1.603  |                         2.7021 |                              0.0226 |
| s6_to_s5      | motorbike | motorbike-2 |            3872.51 |                      9.294  |             130 |                 254.664 |                    216.801 |              -37.863  |                   37.863  |                -14.8678 |                     14.8678 |                             0.9148 |                            1.603  |                         2.7321 |                              0.0231 |
| s6_to_s5      | motorbike | motorbike-3 |            3877.15 |                      9.3052 |             129 |                 255.009 |                    217.074 |              -37.9348 |                   37.9348 |                -14.8758 |                     14.8758 |                             0.9008 |                            1.603  |                         2.7012 |                              0.0233 |
| s6_to_s5      | motorbike | motorbike-4 |            3880.34 |                      9.3128 |             126 |                 255.26  |                    217.278 |              -37.9821 |                   37.9821 |                -14.8798 |                     14.8798 |                             0.9166 |                            1.603  |                         2.7322 |                              0.0238 |
| s6_to_s5      | motorbike | motorbike-5 |            3883.7  |                      9.3209 |             120 |                 256.782 |                    218.183 |              -38.5994 |                   38.5994 |                -15.032  |                     15.032  |                             0.9529 |                            1.603  |                         2.8027 |                              0.0667 |
| s2_to_s6      | walking   | walking-1   |            6947.64 |                     83.3717 |             282 |                3064     |                   2127.59  |             -936.407  |                  936.407  |                -30.5616 |                     30.5616 |                             1.7242 |                            3.1827 |                         3.3879 |                              0.0851 |
| s2_to_s6      | walking   | walking-2   |            6948.35 |                     83.3802 |             282 |                3064.24  |                   2127.81  |             -936.424  |                  936.424  |                -30.5598 |                     30.5598 |                             1.7241 |                            3.1827 |                         3.3877 |                              0.0851 |
| s2_to_s6      | walking   | walking-3   |            6948.93 |                     83.3871 |             283 |                3064.6   |                   2127.99  |             -936.612  |                  936.612  |                -30.5623 |                     30.5623 |                             1.7291 |                            3.1827 |                         3.3922 |                              0.0848 |
| s2_to_s6      | walking   | walking-4   |            6949.64 |                     83.3957 |             283 |                3064.84  |                   2128.21  |             -936.629  |                  936.629  |                -30.5605 |                     30.5605 |                             1.729  |                            3.1827 |                         3.392  |                              0.0848 |
| s2_to_s6      | walking   | walking-5   |            6949.64 |                     83.3957 |             281 |                3064.87  |                   2128.2   |             -936.661  |                  936.661  |                -30.5612 |                     30.5612 |                             1.7212 |                            3.1827 |                         3.384  |                              0.0854 |
| s2_to_s6      | motorbike | motorbike-1 |            7373.17 |                     17.6956 |             276 |                 680.448 |                    451.721 |             -228.726  |                  228.726  |                -33.6141 |                     33.6141 |                             1.7931 |                            3.1827 |                         3.488  |                              0.1268 |
| s2_to_s6      | motorbike | motorbike-2 |            7374.37 |                     17.6985 |             275 |                 680.583 |                    451.789 |             -228.794  |                  228.794  |                -33.6173 |                     33.6173 |                             1.7946 |                            3.1827 |                         3.4903 |                              0.1236 |
| s2_to_s6      | motorbike | motorbike-3 |            7374.39 |                     17.6985 |             273 |                 680.54  |                    451.801 |             -228.739  |                  228.739  |                -33.6114 |                     33.6114 |                             1.8102 |                            3.1827 |                         3.5125 |                              0.1282 |
| s2_to_s6      | motorbike | motorbike-4 |            7374.46 |                     17.6987 |             277 |                 680.568 |                    451.801 |             -228.767  |                  228.767  |                -33.6142 |                     33.6142 |                             1.7979 |                            3.1827 |                         3.4919 |                              0.1264 |
| s2_to_s6      | motorbike | motorbike-5 |            7374.6  |                     17.699  |             276 |                 680.614 |                    451.803 |             -228.811  |                  228.811  |                -33.6183 |                     33.6183 |                             1.7926 |                            3.1827 |                         3.4873 |                              0.1268 |

Rank 1 is not called a recommendation; ranks are evaluation labels only.

## D. Exposure error

| mode      |   routes |   mae_exposure_index |   rmse_exposure_index |   mean_absolute_percentage_error |   max_absolute_percentage_error |
|:----------|---------:|---------------------:|----------------------:|---------------------------------:|--------------------------------:|
| motorbike |       10 |              133.403 |               163.984 |                          24.2595 |                         33.6183 |
| walking   |       10 |              564.887 |               676.187 |                          22.803  |                         30.5623 |

Errors compare predicted exposure with the internal oracle-IDW exposure index.
The oracle remains a spatial estimate, not route-level measurement.

## E–F. Route ranking correlation and top-route agreement

| scenario_id   | mode      |   route_count |   spearman_rank_correlation |   kendall_tau_a | oracle_top_1_route   | predicted_top_1_route   | top_1_agreement   |   top_2_overlap_count |   top_2_overlap_fraction |
|:--------------|:----------|--------------:|----------------------------:|----------------:|:---------------------|:------------------------|:------------------|----------------------:|-------------------------:|
| s2_to_s6      | motorbike |             5 |                         0.6 |             0.4 | motorbike-1          | motorbike-1             | True              |                     1 |                      0.5 |
| s2_to_s6      | walking   |             5 |                         0.9 |             0.8 | walking-1            | walking-1               | True              |                     2 |                      1   |
| s6_to_s5      | motorbike |             5 |                         1   |             1   | motorbike-1          | motorbike-1             | True              |                     2 |                      1   |
| s6_to_s5      | walking   |             5 |                         1   |             1   | walking-1            | walking-1               | True              |                     2 |                      1   |

Per-route rank shifts:

| scenario_id   | mode      | route_id    |   oracle_exposure_index |   predicted_exposure_index |   oracle_rank |   predicted_rank |   rank_shift |
|:--------------|:----------|:------------|------------------------:|---------------------------:|--------------:|-----------------:|-------------:|
| s2_to_s6      | motorbike | motorbike-1 |                 680.448 |                    451.721 |             1 |                1 |            0 |
| s2_to_s6      | motorbike | motorbike-2 |                 680.583 |                    451.789 |             4 |                2 |           -2 |
| s2_to_s6      | motorbike | motorbike-3 |                 680.54  |                    451.801 |             2 |                4 |            2 |
| s2_to_s6      | motorbike | motorbike-4 |                 680.568 |                    451.801 |             3 |                3 |            0 |
| s2_to_s6      | motorbike | motorbike-5 |                 680.614 |                    451.803 |             5 |                5 |            0 |
| s2_to_s6      | walking   | walking-1   |                3064     |                   2127.59  |             1 |                1 |            0 |
| s2_to_s6      | walking   | walking-2   |                3064.24  |                   2127.81  |             2 |                2 |            0 |
| s2_to_s6      | walking   | walking-3   |                3064.6   |                   2127.99  |             3 |                3 |            0 |
| s2_to_s6      | walking   | walking-4   |                3064.84  |                   2128.21  |             4 |                5 |            1 |
| s2_to_s6      | walking   | walking-5   |                3064.87  |                   2128.2   |             5 |                4 |           -1 |
| s6_to_s5      | motorbike | motorbike-1 |                 254.413 |                    216.598 |             1 |                1 |            0 |
| s6_to_s5      | motorbike | motorbike-2 |                 254.664 |                    216.801 |             2 |                2 |            0 |
| s6_to_s5      | motorbike | motorbike-3 |                 255.009 |                    217.074 |             3 |                3 |            0 |
| s6_to_s5      | motorbike | motorbike-4 |                 255.26  |                    217.278 |             4 |                4 |            0 |
| s6_to_s5      | motorbike | motorbike-5 |                 256.782 |                    218.183 |             5 |                5 |            0 |
| s6_to_s5      | walking   | walking-1   |                1283.48  |                   1090.55  |             1 |                1 |            0 |
| s6_to_s5      | walking   | walking-2   |                1283.57  |                   1090.63  |             2 |                2 |            0 |
| s6_to_s5      | walking   | walking-3   |                1283.91  |                   1090.91  |             3 |                3 |            0 |
| s6_to_s5      | walking   | walking-4   |                1284     |                   1091     |             4 |                4 |            0 |
| s6_to_s5      | walking   | walking-5   |                1286.75  |                   1092.48  |             5 |                5 |            0 |

Spearman and Kendall assess whether forecast+spatial error changes ordering.
Top-1 agreement and top-2 overlap are descriptive research outcomes, not route
selection.

## Segment contribution analysis

Representative largest segment fractions (one per scenario/mode/pathway):

| scenario_id   | mode      | route_id    | pipeline_mode      |   segment_index | eta                           | mapped_target_time   |   pm25_estimate |   segment_duration_minutes |   exposure_contribution |   contribution_fraction |
|:--------------|:----------|:------------|:-------------------|----------------:|:------------------------------|:---------------------|----------------:|---------------------------:|------------------------:|------------------------:|
| s2_to_s6      | motorbike | motorbike-1 | oracle_exposure    |              24 | 2022-02-28T06:01:37.625669963 | 2022-02-28T07:00:00  |         45.1931 |                     0.2895 |                 13.085  |                  0.0192 |
| s2_to_s6      | motorbike | motorbike-1 | predicted_exposure |             274 | 2022-02-28T06:17:17.587859760 | 2022-02-28T07:00:00  |         26.6327 |                     0.3682 |                  9.806  |                  0.0217 |
| s2_to_s6      | walking   | walking-1   | oracle_exposure    |             268 | 2022-02-28T07:14:38.887252461 | 2022-02-28T08:00:00  |         28.2381 |                     2.0818 |                 58.7874 |                  0.0192 |
| s2_to_s6      | walking   | walking-1   | predicted_exposure |             268 | 2022-02-28T07:14:38.887252461 | 2022-02-28T08:00:00  |         26.0583 |                     2.0818 |                 54.2494 |                  0.0255 |
| s6_to_s5      | motorbike | motorbike-1 | oracle_exposure    |               1 | 2022-02-28T06:00:12.255383185 | 2022-02-28T07:00:00  |         33.258  |                     0.4085 |                 13.5863 |                  0.0534 |
| s6_to_s5      | motorbike | motorbike-1 | predicted_exposure |               1 | 2022-02-28T06:00:12.255383185 | 2022-02-28T07:00:00  |         26.6846 |                     0.4085 |                 10.901  |                  0.0503 |
| s6_to_s5      | walking   | walking-1   | oracle_exposure    |               1 | 2022-02-28T06:01:01.276915927 | 2022-02-28T07:00:00  |         33.258  |                     2.0426 |                 67.9317 |                  0.0529 |
| s6_to_s5      | walking   | walking-1   | predicted_exposure |               1 | 2022-02-28T06:01:01.276915927 | 2022-02-28T07:00:00  |         26.6846 |                     2.0426 |                 54.505  |                  0.05   |

The complete top-five list for every candidate/pathway is saved in
`top_segment_contributions.csv`.

Contribution means `PM × minutes`; a large fraction may reflect duration,
concentration, or both. It does not establish a pollution cause.

## G. Walking versus motorbike

Walking has much longer duration and therefore a larger index under the same OD
and hourly PM2.5 field. This is expected from the definition and is not a claim
about inhaled dose or behavioral risk.

## H. Exposure error relationships

| mode      | proxy                             |   routes |   spearman_with_absolute_exposure_error |
|:----------|:----------------------------------|---------:|----------------------------------------:|
| motorbike | total_distance_m                  |       10 |                                  0.9636 |
| motorbike | total_travel_time_minutes         |       10 |                                  0.9636 |
| motorbike | mean_nearest_station_distance_km  |       10 |                                  0.8182 |
| motorbike | max_nearest_station_distance_km   |       10 |                                  0.8704 |
| motorbike | mean_effective_station_count      |       10 |                                  0.7939 |
| motorbike | moderate_or_weak_segment_fraction |       10 |                                  0.8328 |
| walking   | total_distance_m                  |       10 |                                  1      |
| walking   | total_travel_time_minutes         |       10 |                                  1      |
| walking   | mean_nearest_station_distance_km  |       10 |                                  0.7333 |
| walking   | max_nearest_station_distance_km   |       10 |                                  0.8704 |
| walking   | mean_effective_station_count      |       10 |                                  0.7333 |
| walking   | moderate_or_weak_segment_fraction |       10 |                                  0.7976 |

These are Spearman associations across only ten routes per mode. Candidate
routes overlap heavily, and the two OD scenarios differ strongly in distance.
Associations are therefore substantially confounded by scenario/route length;
they do not isolate spatial reliability effects. Reliability proxies are not
calibrated uncertainty.

## I. Hourly and scientific limitations

1. Segment ETA is specific, but PM2.5 is mapped to the next supported hour.
2. The experiment does not validate exact minute-level exposure.
3. Finer temporal validation requires genuine sub-hourly observations.
4. Oracle exposure uses IDW from fixed stations, not road measurements.
5. Only two OD scenarios and highly overlapping K-shortest candidates are used.
6. Constant walking/motorbike speeds omit real traffic and behavior.
7. Exposure index omits inhalation rate and cannot be interpreted as dose.
8. Validation predictions and examples are development-period only.
9. No route recommendation, optimization, or travel-time constraint is applied.

## J. Readiness for constrained optimization

### B. READY WITH RESTRICTIONS

Exposure ranking is sufficiently stable for further offline work, but one or more strict agreement/error gates fail.

Observed restrictions are material: predicted indices underestimate their
oracle counterparts by roughly 15–34%, one scenario/mode has Spearman 0.6 and
only 50% top-2 overlap, only two OD pairs are tested, and candidate routes
overlap heavily. Any subsequent constrained-optimization work must remain an
offline sensitivity experiment and must not produce user-facing recommendations.

```json
{
  "top_1_agreement_rate": 1.0,
  "mean_spearman_rank_correlation": 0.8749999999999999,
  "minimum_scenario_spearman": 0.6,
  "maximum_mode_mape_percent": 24.2594617350267,
  "strict_top_1_agreement_all": true,
  "strict_mean_spearman_ge_0_9": false,
  "strict_minimum_spearman_ge_0_8": false,
  "strict_maximum_mode_mape_le_10": false,
  "restricted_top_1_agreement_ge_half": true,
  "restricted_mean_spearman_ge_0_6": true,
  "restricted_no_negative_scenario_spearman": true,
  "restricted_maximum_mode_mape_le_25": true
}
```

Strict readiness requires perfect top-1 agreement, mean Spearman ≥0.9, every
scenario Spearman ≥0.8, and mode MAPE ≤10%. Restricted readiness requires at
least 50% top-1 agreement, mean Spearman ≥0.6, no negative scenario correlation,
and mode MAPE ≤25%. These are transparent prototype progression gates, not
health or regulatory thresholds.

Even an A/B result authorizes only a later **offline constrained-optimization
research experiment**. It does not authorize user-facing route recommendations.
