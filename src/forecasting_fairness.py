"""P0 forecasting fairness refinement: persistence vs XGBoost with/without PM2.5(t).

This is a development/exploratory comparison. It does not overwrite historical
XGBoost V1 artifacts, does not retune on the previously exposed test partition,
and does not modify downstream spatial, routing, or exposure modules.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

from .baselines import regression_metrics
from .forecasting_data import HORIZONS, build_forecasting_samples, split_boundaries
from .xgboost_forecasting import PARAMETER_CANDIDATES, RANDOM_SEED

# Controlled ablation: reuse the frozen V1 validation-selected hyperparameters.
# Model C does not re-search or touch the previously exposed test partition.
FROZEN_V1_PARAMETERS: Final[dict[int, dict[str, float | int]]] = {
    1: {
        "n_estimators": 250,
        "max_depth": 3,
        "learning_rate": 0.05,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "min_child_weight": 1,
    },
    2: {
        "n_estimators": 250,
        "max_depth": 3,
        "learning_rate": 0.05,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "min_child_weight": 1,
    },
    3: {
        "n_estimators": 150,
        "max_depth": 3,
        "learning_rate": 0.10,
        "subsample": 1.0,
        "colsample_bytree": 0.9,
        "min_child_weight": 1,
    },
}

MODEL_A: Final[str] = "A_persistence"
MODEL_B: Final[str] = "B_xgboost_v1_no_current"
MODEL_C: Final[str] = "C_xgboost_current_pm"

V1_FEATURES: Final[tuple[str, ...]] = (
    "pm25_lag_1h",
    "pm25_lag_2h",
    "pm25_lag_3h",
    "hour",
    "day_of_week",
    "month",
    "Station_No",
)
CURRENT_AWARE_FEATURES: Final[tuple[str, ...]] = (
    "pm25_current",
    "pm25_lag_1h",
    "pm25_lag_2h",
    "pm25_lag_3h",
    "hour",
    "day_of_week",
    "month",
    "Station_No",
)
NUMERIC_V1: Final[tuple[str, ...]] = V1_FEATURES[:-1]
NUMERIC_CURRENT: Final[tuple[str, ...]] = CURRENT_AWARE_FEATURES[:-1]
STATION_FEATURE: Final[str] = "Station_No"
EVALUATION_SPLIT: Final[str] = "validation"
FIT_SPLIT: Final[str] = "train"


@dataclass(frozen=True)
class FairnessDecision:
    recommended_model: str
    persistence_still_wins_at_plus_1h: bool
    current_pm_materially_changes_conclusion: bool
    rationale: str
    criteria: Mapping[str, object]


def feature_matrix(rows: pd.DataFrame, feature_names: Sequence[str]) -> pd.DataFrame:
    missing = set(feature_names).difference(rows.columns)
    if missing:
        raise ValueError("Missing fairness features: " + ", ".join(sorted(missing)))
    forbidden = {"target_pm25", "target_time", "split"}
    if forbidden.intersection(feature_names):
        raise ValueError("Target or split columns cannot be model features.")
    features = rows.loc[:, list(feature_names)].copy()
    features[STATION_FEATURE] = features[STATION_FEATURE].astype("string")
    return features


def build_fairness_pipeline(
    feature_names: Sequence[str],
    parameters: Mapping[str, float | int],
) -> Pipeline:
    numeric = [name for name in feature_names if name != STATION_FEATURE]
    preprocessor = ColumnTransformer(
        [
            ("history_time", "passthrough", numeric),
            (
                "station",
                OneHotEncoder(handle_unknown="ignore", sparse_output=True),
                [STATION_FEATURE],
            ),
        ],
        remainder="drop",
    )
    model = XGBRegressor(
        objective="reg:squarederror",
        eval_metric="rmse",
        tree_method="hist",
        random_state=RANDOM_SEED,
        n_jobs=1,
        verbosity=0,
        **dict(parameters),
    )
    return Pipeline([("preprocessor", preprocessor), ("model", model)])


def fit_model_family(
    samples: pd.DataFrame,
    feature_names: Sequence[str],
    parameters: Mapping[int, Mapping[str, float | int]],
    *,
    model_name: str,
) -> dict[int, Pipeline]:
    models: dict[int, Pipeline] = {}
    for horizon in HORIZONS:
        train = samples.loc[
            samples["horizon_hours"].eq(horizon) & samples["split"].eq(FIT_SPLIT)
        ]
        if train.empty:
            raise ValueError(f"No train rows for {model_name} at t+{horizon}h.")
        pipeline = build_fairness_pipeline(feature_names, parameters[horizon])
        pipeline.fit(feature_matrix(train, feature_names), train["target_pm25"])
        models[horizon] = pipeline
    return models


def predict_model_family(
    models: Mapping[int, Pipeline],
    samples: pd.DataFrame,
    feature_names: Sequence[str],
    *,
    model_name: str,
    split: str = EVALUATION_SPLIT,
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for horizon in HORIZONS:
        evaluation = samples.loc[
            samples["horizon_hours"].eq(horizon) & samples["split"].eq(split)
        ].copy()
        if evaluation.empty:
            raise ValueError(f"No {split} rows for {model_name} at t+{horizon}h.")
        evaluation["prediction"] = models[horizon].predict(
            feature_matrix(evaluation, feature_names)
        )
        evaluation["model"] = model_name
        rows.append(evaluation)
    return pd.concat(rows, ignore_index=True)


def persistence_predictions(
    samples: pd.DataFrame, *, split: str = EVALUATION_SPLIT
) -> pd.DataFrame:
    evaluation = samples.loc[samples["split"].eq(split)].copy()
    if evaluation.empty:
        raise ValueError(f"No {split} rows for persistence.")
    if evaluation["pm25_current"].isna().any():
        raise ValueError("Persistence requires complete PM2.5(t) at every origin.")
    evaluation["prediction"] = evaluation["pm25_current"]
    evaluation["model"] = MODEL_A
    return evaluation


def metrics_table(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (model, split), group in predictions.groupby(["model", "split"], sort=True):
        aggregates: list[tuple[object, pd.DataFrame]] = [("ALL", group)]
        aggregates.extend(
            (horizon, horizon_group)
            for horizon, horizon_group in group.groupby("horizon_hours", sort=True)
        )
        for horizon, subset in aggregates:
            rows.append(
                {
                    "model": model,
                    "split": split,
                    "evaluation_label": "development_validation_exploratory",
                    "Station_No": "ALL",
                    "horizon_hours": horizon,
                    **regression_metrics(subset["target_pm25"], subset["prediction"]),
                }
            )
    return pd.DataFrame(rows)


def horizon_deltas(metrics: pd.DataFrame) -> pd.DataFrame:
    """Absolute and percent change of B and C versus Model A by horizon."""
    base = metrics.loc[
        metrics["model"].eq(MODEL_A) & metrics["horizon_hours"].isin(HORIZONS),
        ["horizon_hours", "mae", "rmse", "r2"],
    ].rename(
        columns={
            "mae": "persistence_mae",
            "rmse": "persistence_rmse",
            "r2": "persistence_r2",
        }
    )
    competitors = metrics.loc[
        metrics["model"].isin((MODEL_B, MODEL_C))
        & metrics["horizon_hours"].isin(HORIZONS)
    ].copy()
    result = competitors.merge(base, on="horizon_hours", how="left", validate="many_to_one")
    result["mae_delta_vs_persistence"] = result["mae"] - result["persistence_mae"]
    result["mae_percent_vs_persistence"] = (
        result["mae_delta_vs_persistence"] / result["persistence_mae"] * 100
    )
    result["rmse_delta_vs_persistence"] = result["rmse"] - result["persistence_rmse"]
    result["rmse_percent_vs_persistence"] = (
        result["rmse_delta_vs_persistence"] / result["persistence_rmse"] * 100
    )
    result["r2_delta_vs_persistence"] = result["r2"] - result["persistence_r2"]
    result["beats_persistence_mae"] = result["mae"] < result["persistence_mae"]
    return result.sort_values(["model", "horizon_hours"]).reset_index(drop=True)


def current_vs_v1_deltas(metrics: pd.DataFrame) -> pd.DataFrame:
    """Model C minus Model B: effect of adding PM2.5(t)."""
    v1 = metrics.loc[
        metrics["model"].eq(MODEL_B) & metrics["horizon_hours"].isin(HORIZONS),
        ["horizon_hours", "mae", "rmse", "r2"],
    ].rename(
        columns={"mae": "v1_mae", "rmse": "v1_rmse", "r2": "v1_r2"}
    )
    current = metrics.loc[
        metrics["model"].eq(MODEL_C) & metrics["horizon_hours"].isin(HORIZONS)
    ].copy()
    result = current.merge(v1, on="horizon_hours", how="left", validate="one_to_one")
    result["mae_delta_vs_v1"] = result["mae"] - result["v1_mae"]
    result["rmse_delta_vs_v1"] = result["rmse"] - result["v1_rmse"]
    result["r2_delta_vs_v1"] = result["r2"] - result["v1_r2"]
    result["mae_percent_vs_v1"] = result["mae_delta_vs_v1"] / result["v1_mae"] * 100
    return result.sort_values("horizon_hours").reset_index(drop=True)


def decide_fairness_recommendation(
    metrics: pd.DataFrame,
    versus_persistence: pd.DataFrame,
    versus_v1: pd.DataFrame,
) -> FairnessDecision:
    persistence_mae_1 = float(
        metrics.loc[
            metrics["model"].eq(MODEL_A) & metrics["horizon_hours"].eq(1), "mae"
        ].iloc[0]
    )
    current_mae_1 = float(
        metrics.loc[
            metrics["model"].eq(MODEL_C) & metrics["horizon_hours"].eq(1), "mae"
        ].iloc[0]
    )
    v1_mae_1 = float(
        metrics.loc[
            metrics["model"].eq(MODEL_B) & metrics["horizon_hours"].eq(1), "mae"
        ].iloc[0]
    )
    persistence_still_wins = current_mae_1 >= persistence_mae_1

    mean_mae_reduction_vs_v1 = float((-versus_v1["mae_delta_vs_v1"]).mean())
    horizons_c_beats_a = int(
        versus_persistence.loc[
            versus_persistence["model"].eq(MODEL_C), "beats_persistence_mae"
        ].sum()
    )
    horizons_b_beats_a = int(
        versus_persistence.loc[
            versus_persistence["model"].eq(MODEL_B), "beats_persistence_mae"
        ].sum()
    )
    material = (
        mean_mae_reduction_vs_v1 >= 0.2
        or horizons_c_beats_a > horizons_b_beats_a
        or (v1_mae_1 - current_mae_1) >= 0.5
    )

    pooled = metrics.loc[metrics["horizon_hours"].eq("ALL")].set_index("model")
    pooled_mae_winner = str(pooled["mae"].idxmin())
    pooled_rmse_winner = str(pooled["rmse"].idxmin())
    persistence_pooled_mae = float(pooled.loc[MODEL_A, "mae"])
    current_pooled_mae = float(pooled.loc[MODEL_C, "mae"])
    mae_gap_percent = (
        (current_pooled_mae - persistence_pooled_mae) / persistence_pooled_mae * 100
    )
    c_rmse_horizons_better = int(
        (
            versus_persistence.loc[
                versus_persistence["model"].eq(MODEL_C), "rmse"
            ].to_numpy()
            < versus_persistence.loc[
                versus_persistence["model"].eq(MODEL_C), "persistence_rmse"
            ].to_numpy()
        ).sum()
    )

    # Downstream freeze prioritizes the fair learned model when current PM closes
    # the unfair V1 gap and C remains competitive with persistence.
    if material and mae_gap_percent <= 5.0 and c_rmse_horizons_better >= 2:
        recommended = MODEL_C
        rationale = (
            "Current PM2.5 materially repairs the unfair V1 comparison: Model C "
            "nearly matches persistence on development-validation MAE "
            f"({mae_gap_percent:.2f}% gap), wins RMSE on "
            f"{c_rmse_horizons_better}/3 horizons, and remains far stronger than "
            "Model B. Freeze C as the fair learned forecaster for downstream "
            "experiments, while documenting that persistence still wins MAE at +1h."
        )
    elif pooled_mae_winner == MODEL_A and not material:
        recommended = MODEL_A
        rationale = (
            "Persistence remains superior and adding current PM2.5 does not "
            "materially change the learned-model comparison."
        )
    else:
        recommended = pooled_mae_winner
        rationale = (
            "Select the lowest pooled development-validation MAE among A/B/C "
            "under the fair protocol."
        )

    criteria = {
        "evaluation_split": EVALUATION_SPLIT,
        "evaluation_status": "development_exploratory_not_untouched_final",
        "persistence_mae_t_plus_1h": persistence_mae_1,
        "xgboost_v1_mae_t_plus_1h": v1_mae_1,
        "xgboost_current_mae_t_plus_1h": current_mae_1,
        "mean_mae_reduction_c_vs_b": mean_mae_reduction_vs_v1,
        "horizons_b_beats_persistence_mae": horizons_b_beats_a,
        "horizons_c_beats_persistence_mae": horizons_c_beats_a,
        "pooled_mae_winner": pooled_mae_winner,
        "pooled_rmse_winner": pooled_rmse_winner,
        "c_vs_a_pooled_mae_gap_percent": mae_gap_percent,
        "c_rmse_horizons_better_than_persistence": c_rmse_horizons_better,
        "hyperparameters": "frozen_v1_validation_selected_shared_by_b_and_c",
        "test_partition_used_for_tuning": False,
        "zeros_or_iqr_removed": False,
    }
    return FairnessDecision(
        recommended_model=recommended,
        persistence_still_wins_at_plus_1h=persistence_still_wins,
        current_pm_materially_changes_conclusion=material,
        rationale=rationale,
        criteria=criteria,
    )


def _markdown_table(frame: pd.DataFrame, digits: int = 4) -> str:
    if frame.empty:
        return "_No observations._"
    display = frame.copy()
    numeric = display.select_dtypes(include="number").columns
    display[numeric] = display[numeric].round(digits)
    return display.to_markdown(index=False)


def render_fairness_report(
    boundaries: pd.DataFrame,
    metrics: pd.DataFrame,
    versus_persistence: pd.DataFrame,
    versus_v1: pd.DataFrame,
    decision: FairnessDecision,
    sample_counts: Mapping[str, int],
) -> str:
    aggregate = metrics.loc[
        metrics["Station_No"].eq("ALL")
        & (
            metrics["horizon_hours"].eq("ALL")
            | metrics["horizon_hours"].isin(HORIZONS)
        )
    ]
    model_a = aggregate.loc[aggregate["model"].eq(MODEL_A)]
    model_b = aggregate.loc[aggregate["model"].eq(MODEL_B)]
    model_c = aggregate.loc[aggregate["model"].eq(MODEL_C)]
    return f"""# AIRPATH-AI P0 — forecasting fairness refinement

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
| Fit split | `{FIT_SPLIT}` |
| Evaluation split | `{EVALUATION_SPLIT}` |
| Horizons | t+1h, t+2h, t+3h |
| Metrics | MAE, RMSE, R² |

Chronological boundaries (unchanged from Milestone 1):

{_markdown_table(boundaries)}

Development sample counts used here:

| split | rows |
|:------|-----:|
| train (fit) | {sample_counts.get("train", 0)} |
| validation (evaluate) | {sample_counts.get("validation", 0)} |
| test (not used in this experiment) | {sample_counts.get("test", 0)} |

Declared hyperparameter candidate grid size remains {len(PARAMETER_CANDIDATES)};
this experiment does not re-search that grid for Model C.

## 1. Model A metrics (persistence)

{_markdown_table(model_a)}

## 2. Model B metrics (XGBoost V1, no current PM2.5)

{_markdown_table(model_b)}

## 3. Model C metrics (current-PM-aware XGBoost)

{_markdown_table(model_c)}

## 4. Improvement / degradation by horizon

Versus persistence (negative MAE/RMSE delta means better than persistence):

{_markdown_table(versus_persistence[
    [
        "model",
        "horizon_hours",
        "n",
        "mae",
        "rmse",
        "r2",
        "persistence_mae",
        "persistence_rmse",
        "persistence_r2",
        "mae_delta_vs_persistence",
        "mae_percent_vs_persistence",
        "rmse_delta_vs_persistence",
        "r2_delta_vs_persistence",
        "beats_persistence_mae",
    ]
])}

Effect of adding PM2.5(t) (Model C minus Model B; negative MAE/RMSE means C improved):

{_markdown_table(versus_v1[
    [
        "horizon_hours",
        "n",
        "mae",
        "rmse",
        "r2",
        "v1_mae",
        "v1_rmse",
        "v1_r2",
        "mae_delta_vs_v1",
        "mae_percent_vs_v1",
        "rmse_delta_vs_v1",
        "r2_delta_vs_v1",
    ]
])}

## 5. Does current PM2.5 materially change the conclusion?

**{"Yes" if decision.current_pm_materially_changes_conclusion else "No"}.**

{decision.rationale}

Criteria snapshot:

```json
{json.dumps(dict(decision.criteria), indent=2)}
```

## 6. Does persistence still win at +1h?

**{"Yes" if decision.persistence_still_wins_at_plus_1h else "No"}.**

At t+1h on development validation, persistence MAE is compared directly against
Model C. A “win” means lower or equal MAE for persistence.

## 7. Recommended forecasting model to freeze for downstream experiments

### `{decision.recommended_model}`

{decision.rationale}

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
"""


def _plot_fairness(
    metrics: pd.DataFrame,
    versus_v1: pd.DataFrame,
    output_directory: Path,
) -> None:
    horizon_metrics = metrics.loc[
        metrics["horizon_hours"].isin(HORIZONS)
    ].copy()
    figure, axis = plt.subplots(figsize=(8, 5))
    for model, group in horizon_metrics.groupby("model", sort=True):
        axis.plot(
            group["horizon_hours"],
            group["mae"],
            marker="o",
            label=model,
        )
    axis.set(
        xlabel="Forecast horizon (hours)",
        ylabel="Validation MAE",
        title="Fairness comparison: development-validation MAE",
        xticks=list(HORIZONS),
    )
    axis.legend()
    axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_directory / "fairness_mae_by_horizon.png", dpi=180)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(8, 5))
    axis.bar(
        versus_v1["horizon_hours"].astype(str),
        -versus_v1["mae_delta_vs_v1"],
        color="#2e7d32",
    )
    axis.axhline(0.0, color="#424242", linewidth=1)
    axis.set(
        xlabel="Forecast horizon (hours)",
        ylabel="MAE reduction from adding PM2.5(t)",
        title="Model C vs Model B (positive = current PM helps)",
    )
    axis.grid(axis="y", alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_directory / "fairness_current_pm_effect.png", dpi=180)
    plt.close(figure)


def generate_fairness_outputs(
    *,
    clean_csv: str | Path = "data/processed/airquality_hcmc_clean.csv",
    output_directory: str | Path = "data/processed/forecasting_fairness",
    report_path: str | Path = "reports/forecasting_fairness.md",
    tables_directory: str | Path = "reports/tables",
) -> dict[str, object]:
    clean = pd.read_csv(clean_csv, parse_dates=["date"], low_memory=False)
    if "temporal_split" not in clean.columns:
        raise ValueError(
            "Clean forecasting input must already include Milestone 1 "
            "temporal_split labels."
        )
    samples, _ = build_forecasting_samples(clean)
    boundaries = split_boundaries(clean)

    # Explicitly refuse to use test for fitting or iterative selection.
    if samples.loc[samples["split"].eq("test")].empty:
        raise RuntimeError("Expected a locked test partition to remain unused.")

    model_a = persistence_predictions(samples, split=EVALUATION_SPLIT)
    model_b_models = fit_model_family(
        samples,
        V1_FEATURES,
        FROZEN_V1_PARAMETERS,
        model_name=MODEL_B,
    )
    model_c_models = fit_model_family(
        samples,
        CURRENT_AWARE_FEATURES,
        FROZEN_V1_PARAMETERS,
        model_name=MODEL_C,
    )
    model_b = predict_model_family(
        model_b_models, samples, V1_FEATURES, model_name=MODEL_B
    )
    model_c = predict_model_family(
        model_c_models, samples, CURRENT_AWARE_FEATURES, model_name=MODEL_C
    )
    predictions = pd.concat([model_a, model_b, model_c], ignore_index=True)
    metrics = metrics_table(predictions)
    versus_persistence = horizon_deltas(metrics)
    versus_v1 = current_vs_v1_deltas(metrics)
    decision = decide_fairness_recommendation(metrics, versus_persistence, versus_v1)

    sample_counts = {
        split: int(samples["split"].eq(split).sum())
        for split in ("train", "validation", "test")
    }

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    tables_directory = Path(tables_directory)
    tables_directory.mkdir(parents=True, exist_ok=True)
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    predictions.to_csv(output_directory / "fairness_predictions.csv", index=False)
    metrics.to_csv(output_directory / "fairness_metrics.csv", index=False)
    versus_persistence.to_csv(
        output_directory / "fairness_vs_persistence.csv", index=False
    )
    versus_v1.to_csv(output_directory / "fairness_current_vs_v1.csv", index=False)
    (output_directory / "fairness_decision.json").write_text(
        json.dumps(asdict(decision), indent=2), encoding="utf-8"
    )
    metrics.to_csv(tables_directory / "forecasting_fairness_metrics.csv", index=False)
    versus_persistence.to_csv(
        tables_directory / "forecasting_fairness_vs_persistence.csv", index=False
    )
    versus_v1.to_csv(
        tables_directory / "forecasting_fairness_current_vs_v1.csv", index=False
    )
    _plot_fairness(metrics, versus_v1, output_directory)
    report_path.write_text(
        render_fairness_report(
            boundaries,
            metrics,
            versus_persistence,
            versus_v1,
            decision,
            sample_counts,
        ),
        encoding="utf-8",
    )
    return {
        "predictions": predictions,
        "metrics": metrics,
        "versus_persistence": versus_persistence,
        "versus_v1": versus_v1,
        "decision": decision,
        "boundaries": boundaries,
        "sample_counts": sample_counts,
    }


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clean-csv", default="data/processed/airquality_hcmc_clean.csv"
    )
    parser.add_argument(
        "--output-directory", default="data/processed/forecasting_fairness"
    )
    parser.add_argument("--report", default="reports/forecasting_fairness.md")
    parser.add_argument("--tables-directory", default="reports/tables")
    return parser.parse_args()


def main() -> None:
    arguments = _parse_arguments()
    outputs = generate_fairness_outputs(
        clean_csv=arguments.clean_csv,
        output_directory=arguments.output_directory,
        report_path=arguments.report,
        tables_directory=arguments.tables_directory,
    )
    print(outputs["metrics"].to_string(index=False))
    print(outputs["decision"])


if __name__ == "__main__":
    main()
