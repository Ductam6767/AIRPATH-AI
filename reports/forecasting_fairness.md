# AIRPATH-AI P0 — forecasting fairness refinement

## Status label

**Development / exploratory comparison only.**

The chronological test partition was already exposed by the historical XGBoost
V1 experiment. This refinement therefore:

- fits Models B and C on the **train** partition only;
- evaluates all three models on the **validation** partition only;
- does **not** retune on test;
- does **not** claim a new untouched final holdout evaluation;
- does **not** overwrite historical V1 metrics, predictions, or reports.

Zero PM2.5 and IQR-flagged observations are retained. No external, spatial, or
routing features are added.

## Protocol

| item | choice |
|:-----|:-------|
| Model A | Persistence: `ŷ(t+h) = PM2.5(t)` |
| Model B | Historical XGBoost V1 features: PM2.5(t-1/2/3), hour, day_of_week, month, categorical station |
| Model C | Current-PM-aware XGBoost: PM2.5(t) + PM2.5(t-1/2/3) + hour + day_of_week + month + categorical station |
| Hyperparameters | Frozen V1 validation-selected settings shared by B and C (controlled ablation) |
| Fit split | `train` |
| Evaluation split | `validation` |
| Horizons | t+1h, t+2h, t+3h |
| Metrics | MAE, RMSE, R² |

Chronological boundaries (unchanged from Milestone 1):

| split      | start               | end                 |   unique_timestamps |
|:-----------|:--------------------|:--------------------|--------------------:|
| train      | 2021-02-23 21:00:00 | 2022-01-31 02:00:00 |                7316 |
| validation | 2022-01-31 03:00:00 | 2022-04-08 00:00:00 |                1568 |
| test       | 2022-04-08 01:00:00 | 2022-06-21 17:00:00 |                1568 |

Development sample counts used here:

| split | rows |
|:------|-----:|
| train (fit) | 102001 |
| validation (evaluate) | 25744 |
| test (not used in this experiment) | 23655 |

Declared hyperparameter candidate grid size remains 4;
this experiment does not re-search that grid for Model C.

## 1. Model A metrics (persistence)

| model         | split      | evaluation_label                   | Station_No   | horizon_hours   |     n |    mae |    rmse |     r2 |
|:--------------|:-----------|:-----------------------------------|:-------------|:----------------|------:|-------:|--------:|-------:|
| A_persistence | validation | development_validation_exploratory | ALL          | ALL             | 25744 | 4.4866 |  9.2182 | 0.399  |
| A_persistence | validation | development_validation_exploratory | ALL          | 1               |  8603 | 3.0381 |  7.0253 | 0.6518 |
| A_persistence | validation | development_validation_exploratory | ALL          | 2               |  8580 | 4.6392 |  9.4533 | 0.3675 |
| A_persistence | validation | development_validation_exploratory | ALL          | 3               |  8561 | 5.7893 | 10.7874 | 0.1756 |

## 2. Model B metrics (XGBoost V1, no current PM2.5)

| model                   | split      | evaluation_label                   | Station_No   | horizon_hours   |     n |    mae |   rmse |     r2 |
|:------------------------|:-----------|:-----------------------------------|:-------------|:----------------|------:|-------:|-------:|-------:|
| B_xgboost_v1_no_current | validation | development_validation_exploratory | ALL          | ALL             | 25744 | 5.5771 | 8.9357 | 0.4353 |
| B_xgboost_v1_no_current | validation | development_validation_exploratory | ALL          | 1               |  8603 | 4.6986 | 8.0883 | 0.5384 |
| B_xgboost_v1_no_current | validation | development_validation_exploratory | ALL          | 2               |  8580 | 5.6768 | 9.0076 | 0.4257 |
| B_xgboost_v1_no_current | validation | development_validation_exploratory | ALL          | 3               |  8561 | 6.3599 | 9.6461 | 0.3408 |

## 3. Model C metrics (current-PM-aware XGBoost)

| model                | split      | evaluation_label                   | Station_No   | horizon_hours   |     n |    mae |   rmse |     r2 |
|:---------------------|:-----------|:-----------------------------------|:-------------|:----------------|------:|-------:|-------:|-------:|
| C_xgboost_current_pm | validation | development_validation_exploratory | ALL          | ALL             | 25744 | 4.5998 | 8.04   | 0.5428 |
| C_xgboost_current_pm | validation | development_validation_exploratory | ALL          | 1               |  8603 | 3.2098 | 6.5219 | 0.6999 |
| C_xgboost_current_pm | validation | development_validation_exploratory | ALL          | 2               |  8580 | 4.7328 | 8.1191 | 0.5334 |
| C_xgboost_current_pm | validation | development_validation_exploratory | ALL          | 3               |  8561 | 5.8632 | 9.2506 | 0.3937 |

## 4. Improvement / degradation by horizon

Versus persistence (negative MAE/RMSE delta means better than persistence):

| model                   |   horizon_hours |    n |    mae |   rmse |     r2 |   persistence_mae |   persistence_rmse |   persistence_r2 |   mae_delta_vs_persistence |   mae_percent_vs_persistence |   rmse_delta_vs_persistence |   r2_delta_vs_persistence | beats_persistence_mae   |
|:------------------------|----------------:|-----:|-------:|-------:|-------:|------------------:|-------------------:|-----------------:|---------------------------:|-----------------------------:|----------------------------:|--------------------------:|:------------------------|
| B_xgboost_v1_no_current |               1 | 8603 | 4.6986 | 8.0883 | 0.5384 |            3.0381 |             7.0253 |           0.6518 |                     1.6605 |                      54.6572 |                      1.063  |                   -0.1133 | False                   |
| B_xgboost_v1_no_current |               2 | 8580 | 5.6768 | 9.0076 | 0.4257 |            4.6392 |             9.4533 |           0.3675 |                     1.0377 |                      22.3671 |                     -0.4457 |                    0.0582 | False                   |
| B_xgboost_v1_no_current |               3 | 8561 | 6.3599 | 9.6461 | 0.3408 |            5.7893 |            10.7874 |           0.1756 |                     0.5705 |                       9.8551 |                     -1.1413 |                    0.1652 | False                   |
| C_xgboost_current_pm    |               1 | 8603 | 3.2098 | 6.5219 | 0.6999 |            3.0381 |             7.0253 |           0.6518 |                     0.1717 |                       5.6532 |                     -0.5033 |                    0.0481 | False                   |
| C_xgboost_current_pm    |               2 | 8580 | 4.7328 | 8.1191 | 0.5334 |            4.6392 |             9.4533 |           0.3675 |                     0.0936 |                       2.0185 |                     -1.3342 |                    0.1659 | False                   |
| C_xgboost_current_pm    |               3 | 8561 | 5.8632 | 9.2506 | 0.3937 |            5.7893 |            10.7874 |           0.1756 |                     0.0739 |                       1.2765 |                     -1.5368 |                    0.2182 | False                   |

Effect of adding PM2.5(t) (Model C minus Model B; negative MAE/RMSE means C improved):

|   horizon_hours |    n |    mae |   rmse |     r2 |   v1_mae |   v1_rmse |   v1_r2 |   mae_delta_vs_v1 |   mae_percent_vs_v1 |   rmse_delta_vs_v1 |   r2_delta_vs_v1 |
|----------------:|-----:|-------:|-------:|-------:|---------:|----------:|--------:|------------------:|--------------------:|-------------------:|-----------------:|
|               1 | 8603 | 3.2098 | 6.5219 | 0.6999 |   4.6986 |    8.0883 |  0.5384 |           -1.4888 |            -31.6856 |            -1.5663 |           0.1615 |
|               2 | 8580 | 4.7328 | 8.1191 | 0.5334 |   5.6768 |    9.0076 |  0.4257 |           -0.944  |            -16.6291 |            -0.8885 |           0.1077 |
|               3 | 8561 | 5.8632 | 9.2506 | 0.3937 |   6.3599 |    9.6461 |  0.3408 |           -0.4966 |             -7.809  |            -0.3955 |           0.053  |

## 5. Does current PM2.5 materially change the conclusion?

**Yes.**

Current PM2.5 materially repairs the unfair V1 comparison: Model C nearly matches persistence on development-validation MAE (2.52% gap), wins RMSE on 3/3 horizons, and remains far stronger than Model B. Freeze C as the fair learned forecaster for downstream experiments, while documenting that persistence still wins MAE at +1h.

Criteria snapshot:

```json
{
  "evaluation_split": "validation",
  "evaluation_status": "development_exploratory_not_untouched_final",
  "persistence_mae_t_plus_1h": 3.038068292731256,
  "xgboost_v1_mae_t_plus_1h": 4.698592482790346,
  "xgboost_current_mae_t_plus_1h": 3.2098168815765993,
  "mean_mae_reduction_c_vs_b": 0.976475663140382,
  "horizons_b_beats_persistence_mae": 0,
  "horizons_c_beats_persistence_mae": 0,
  "pooled_mae_winner": "A_persistence",
  "pooled_rmse_winner": "C_xgboost_current_pm",
  "c_vs_a_pooled_mae_gap_percent": 2.5225950700816524,
  "c_rmse_horizons_better_than_persistence": 3,
  "hyperparameters": "frozen_v1_validation_selected_shared_by_b_and_c",
  "test_partition_used_for_tuning": false,
  "zeros_or_iqr_removed": false
}
```

## 6. Does persistence still win at +1h?

**Yes.**

At t+1h on development validation, persistence MAE is compared directly against
Model C. A “win” means lower or equal MAE for persistence.

## 7. Recommended forecasting model to freeze for downstream experiments

### `C_xgboost_current_pm`

Current PM2.5 materially repairs the unfair V1 comparison: Model C nearly matches persistence on development-validation MAE (2.52% gap), wins RMSE on 3/3 horizons, and remains far stronger than Model B. Freeze C as the fair learned forecaster for downstream experiments, while documenting that persistence still wins MAE at +1h.

This recommendation is limited to the fair development comparison above. It does
not authorize overwriting frozen downstream deployment artifacts in this P0
change set, and it is not a new untouched final-test claim.

## Scientific limitations

1. Validation was already used for historical V1 hyperparameter selection.
2. The chronological test partition is previously exposed and unused here.
3. Shared frozen hyperparameters favor interpretability of the PM2.5(t) ablation
   over exhaustive re-tuning of Model C.
4. Persistence and Model C both observe PM2.5(t); Model B does not — that was
   the fairness defect motivating this experiment.
5. Metrics remain station-level hourly forecasts, not road-segment exposure.
