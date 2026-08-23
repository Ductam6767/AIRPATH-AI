# AIRPATH-AI P0-3 — downstream freeze and final robustness

## Status

**Development / exploratory research-engine freeze.** This report does not claim
untouched final-test performance and does not authorize a web application.

## A. Forecasting model frozen

Frozen learned forecaster: **`C_xgboost_current_pm`**

Persistence remains a strong baseline and retains lower MAE in the P0-1 fairness
experiment, while `C_xgboost_current_pm` provides the fairer learned comparison and
better RMSE/R². The old unfair XGBoost V1 is **not** used for any new downstream
result in this freeze.

## B. Refreshed downstream exposure results

Pipeline:

`C_xgboost_current_pm` → hourly target-time mapping → IDW p=1 → segment PM2.5 →
route exposure → constrained multi-route selection

Reuses the validated spatial model, OSM network, ETA engine, exposure definition,
and optimizer. Scenario set is the P0-2B reproducible panel
(30 OD × walking/motorbike × supported departure times).

Routes in refreshed table: **2400**

| forecaster           | mode      | departure_time      |   routes |   mean_airpath_exposure |   mean_oracle_exposure |   mean_static_exposure |   mean_abs_pct_airpath_vs_static |
|:---------------------|:----------|:--------------------|---------:|------------------------:|-----------------------:|-----------------------:|---------------------------------:|
| C_xgboost_current_pm | motorbike | 2022-02-27T06:00:00 |      240 |                 375.159 |                447.046 |                388.822 |                           3.5956 |
| C_xgboost_current_pm | motorbike | 2022-02-27T08:00:00 |      240 |                 402.137 |                276.638 |                392.174 |                           3.9013 |
| C_xgboost_current_pm | motorbike | 2022-02-27T12:00:00 |      240 |                 228.144 |                161.679 |                194.721 |                          17.2068 |
| C_xgboost_current_pm | motorbike | 2022-02-27T17:00:00 |      240 |                 209.443 |                230.182 |                199.766 |                           4.7195 |
| C_xgboost_current_pm | motorbike | 2022-02-27T20:00:00 |      240 |                 211.854 |                215.641 |                213.192 |                           0.8368 |
| C_xgboost_current_pm | walking   | 2022-02-27T06:00:00 |      240 |                1467.63  |               1738.06  |               1525.51  |                           4.0002 |
| C_xgboost_current_pm | walking   | 2022-02-27T08:00:00 |      240 |                1570.42  |               1079.58  |               1537.37  |                           3.8361 |
| C_xgboost_current_pm | walking   | 2022-02-27T12:00:00 |      240 |                 890.789 |                632.716 |                763.083 |                          16.9205 |
| C_xgboost_current_pm | walking   | 2022-02-27T17:00:00 |      240 |                 820.419 |                898.527 |                783.024 |                           4.6994 |
| C_xgboost_current_pm | walking   | 2022-02-27T20:00:00 |      240 |                 827.373 |                844.647 |                835.396 |                           1.0781 |

## C. Refreshed constrained-routing results

Constrained decisions evaluated: **1800**
(scenario × mode × departure × tolerance × perturbation, with baseline focus below).

Absolute budgets remain `δ ∈ {0,1,2,3,5,10}` minutes. The output retains the
fastest route and up to three lower-predicted-exposure feasible alternatives.

## D–F. Robustness under ±5/10/20% PM perturbation

Perturbation scales: 0.8, 0.9, 0.95, 1.0, 1.05, 1.1, 1.2.

These are controlled prediction-error sensitivity experiments, **not** calibrated
uncertainty intervals. Only predicted/AIRPATH PM exposures are scaled; oracle
values are never perturbed.

Because the same global factor multiplies every candidate route exposure, predicted
route **ordering is mathematically invariant** under this perturbation family.
Observed top-1/top-3 stability is therefore expected to be perfect; the useful
content is confirmation of that invariance plus oracle quality on the unperturbed
baseline.

|   perturbation_scale |   cases |   top1_agreement_rate |   mean_top3_overlap_fraction |   mean_abs_travel_time_difference_minutes |   mean_abs_predicted_exposure_difference |   mean_decision_regret_difference |
|---------------------:|--------:|----------------------:|-----------------------------:|------------------------------------------:|-----------------------------------------:|----------------------------------:|
|                 0.8  |    1800 |                     1 |                            1 |                                         0 |                                 123.056  |                                 0 |
|                 0.9  |    1800 |                     1 |                            1 |                                         0 |                                  61.5281 |                                 0 |
|                 0.95 |    1800 |                     1 |                            1 |                                         0 |                                  30.7641 |                                 0 |
|                 1    |    1800 |                     1 |                            1 |                                         0 |                                   0      |                                 0 |
|                 1.05 |    1800 |                     1 |                            1 |                                         0 |                                  30.7641 |                                 0 |
|                 1.1  |    1800 |                     1 |                            1 |                                         0 |                                  61.5281 |                                 0 |
|                 1.2  |    1800 |                     1 |                            1 |                                         0 |                                 123.056  |                                 0 |

## G–H. Model-based oracle comparison (unperturbed baseline)

Oracle exposure is IDW-derived from monitors and is **not** road-measured ground
truth. Agreement/regret below are versus this **model-based oracle**.

| summary_level   |   cases |   oracle_optimal_agreement_rate |   mean_decision_regret |   median_decision_regret |   max_decision_regret |   zero_regret_rate |   mode |   delta_time_allowed_minutes |   departure_time |
|:----------------|--------:|--------------------------------:|-----------------------:|-------------------------:|----------------------:|-------------------:|-------:|-----------------------------:|-----------------:|
| all             |    1800 |                          0.9811 |                 0.0001 |                        0 |                0.0186 |             0.9811 |    nan |                          nan |              nan |

By mode:

| summary_level   |   cases |   oracle_optimal_agreement_rate |   mean_decision_regret |   median_decision_regret |   max_decision_regret |   zero_regret_rate | mode      |   delta_time_allowed_minutes |   departure_time |
|:----------------|--------:|--------------------------------:|-----------------------:|-------------------------:|----------------------:|-------------------:|:----------|-----------------------------:|-----------------:|
| mode            |     900 |                          0.9889 |                 0.0001 |                        0 |                0.0186 |             0.9889 | motorbike |                          nan |              nan |
| mode            |     900 |                          0.9733 |                 0.0001 |                        0 |                0.0186 |             0.9733 | walking   |                          nan |              nan |

## I. Static vs arrival-time conclusion

MIXED/WEAK evidence that hourly forecast-bucket-aware exposure changes route decisions relative to a static departure-time snapshot (P0-2A/P0-2B).

Do not claim a large Gap 1 route-selection benefit from hourly forecast buckets.

## J. Walking vs motorbike

Mode-specific oracle and stability summaries are saved under
`data/processed/final_robustness/`. Walking accumulates larger PM×minutes indexes
because travel durations are longer; selection stability under global multiplicative
bias remains complete for both modes.

## K. Final research-engine readiness

### A. READY TO FREEZE

Frozen Model C downstream decisions are stable under global multiplicative prediction bias and pass strict model-based oracle gates.

```json
{
  "frozen_forecaster": "C_xgboost_current_pm",
  "gap1_conclusion": "MIXED/WEAK evidence that hourly forecast-bucket-aware exposure changes route decisions relative to a static departure-time snapshot (P0-2A/P0-2B).",
  "baseline_top1_agreement": 1.0,
  "min_perturbed_top1_agreement": 1.0,
  "min_perturbed_top3_overlap": 1.0,
  "oracle_optimal_agreement_rate": 0.9811111111111112,
  "mean_decision_regret": 0.00013246836669939265,
  "max_decision_regret": 0.01863276459363978,
  "global_multiplicative_perturbation_is_rank_invariant": true,
  "strict_top1_ge_0_95": true,
  "strict_top3_ge_0_90": true,
  "strict_oracle_agreement_ge_0_85": true,
  "strict_mean_regret_le_0_02": true,
  "strict_max_regret_le_0_10": true,
  "restricted_top1_ge_0_90": true,
  "restricted_top3_ge_0_80": true,
  "restricted_oracle_agreement_ge_0_70": true,
  "restricted_mean_regret_le_0_05": true,
  "restricted_max_regret_le_0_20": true
}
```

Remaining issues / restrictions:

- Hourly HealthyAir resolution; no minute-level validation.
- Six-station spatial support; road PM2.5 is model-estimated.
- Oracle exposure is IDW-derived, not road-measured.
- Constant-speed ETA without traffic/signal/turn delay.
- Pilot-area only; Gap 1 hourly arrival-time benefit remains MIXED/WEAK.

## L. Exact remaining limitations before prototype/web

1. HealthyAir is hourly; no minute-level validation.
2. Spatial network has only six stations.
3. Road-level PM2.5 is model-estimated.
4. Oracle is IDW-derived, not road-measured.
5. Constant-speed ETA; no traffic/signal/turn-delay model.
6. Pilot-area only.
7. Community/fine-resolution external data not yet validated.
8. Exposure is a time-weighted PM2.5 proxy, not inhaled dose.
9. Gap 1 hourly arrival-time benefit remains MIXED/WEAK.
10. No web application is authorized by this freeze.
