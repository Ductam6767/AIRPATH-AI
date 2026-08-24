"""Leakage-safe pooled XGBoost forecasting and hourly target-time interface."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Mapping

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import DMatrix, XGBRegressor

from .baselines import evaluate_baselines, regression_metrics
from .data_loading import load_air_quality_csv
from .data_validation import audit_dataset
from .forecasting_data import HORIZONS, build_forecasting_samples, split_boundaries

RANDOM_SEED: Final[int] = 42
BASE_FEATURES: Final[tuple[str, ...]] = (
    "pm25_lag_1h",
    "pm25_lag_2h",
    "pm25_lag_3h",
    "hour",
    "day_of_week",
    "month",
)
WEATHER_FEATURES: Final[tuple[str, ...]] = ("Temperature", "Humidity")
STATION_FEATURE: Final[str] = "Station_No"

# Small, declared search; no test observations participate.
PARAMETER_CANDIDATES: Final[tuple[dict[str, float | int], ...]] = (
    {
        "n_estimators": 150,
        "max_depth": 3,
        "learning_rate": 0.10,
        "subsample": 1.0,
        "colsample_bytree": 0.9,
        "min_child_weight": 1,
    },
    {
        "n_estimators": 250,
        "max_depth": 3,
        "learning_rate": 0.05,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "min_child_weight": 1,
    },
    {
        "n_estimators": 200,
        "max_depth": 4,
        "learning_rate": 0.05,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "min_child_weight": 1,
    },
    {
        "n_estimators": 250,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
    },
)


def attach_origin_weather(samples: pd.DataFrame, clean: pd.DataFrame) -> pd.DataFrame:
    """Attach weather observed at the prediction origin by exact station/time."""
    weather = clean[
        ["Station_No", "date", "Temperature", "Humidity"]
    ].rename(columns={"date": "origin_time"})
    if weather.duplicated(["Station_No", "origin_time"]).any():
        raise ValueError("Weather lookup has duplicate station-origin timestamps.")
    result = samples.merge(
        weather,
        on=["Station_No", "origin_time"],
        how="left",
        validate="many_to_one",
        sort=False,
    )
    if len(result) != len(samples):
        raise AssertionError("Weather attachment changed forecasting sample count.")
    return result


def feature_columns(version: str) -> tuple[str, ...]:
    if version == "v1":
        return (*BASE_FEATURES, STATION_FEATURE)
    if version == "v2":
        return (*BASE_FEATURES, *WEATHER_FEATURES, STATION_FEATURE)
    raise ValueError("Model version must be 'v1' or 'v2'.")


def feature_frame(rows: pd.DataFrame, version: str) -> pd.DataFrame:
    """Select only declared predictors and make station explicitly categorical."""
    columns = feature_columns(version)
    missing = set(columns).difference(rows.columns)
    if missing:
        raise ValueError("Missing model features: " + ", ".join(sorted(missing)))
    features = rows.loc[:, columns].copy()
    features[STATION_FEATURE] = features[STATION_FEATURE].astype("string")
    return features


def build_pipeline(
    version: str,
    parameters: Mapping[str, float | int],
) -> Pipeline:
    transformers: list[tuple[str, object, list[str]]] = [
        ("history_time", "passthrough", list(BASE_FEATURES)),
    ]
    if version == "v2":
        transformers.append(
            (
                "weather",
                SimpleImputer(strategy="median", add_indicator=True),
                list(WEATHER_FEATURES),
            )
        )
    transformers.append(
        (
            "station",
            OneHotEncoder(handle_unknown="ignore", sparse_output=True),
            [STATION_FEATURE],
        )
    )
    preprocessor = ColumnTransformer(transformers, remainder="drop")
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


def select_v1_hyperparameters(
    samples: pd.DataFrame,
) -> tuple[dict[int, dict[str, float | int]], pd.DataFrame]:
    """Select each horizon's V1 configuration using train/validation only."""
    selected: dict[int, dict[str, float | int]] = {}
    search_rows: list[dict[str, object]] = []
    for horizon in HORIZONS:
        horizon_rows = samples.loc[samples["horizon_hours"].eq(horizon)]
        train = horizon_rows.loc[horizon_rows["split"].eq("train")]
        validation = horizon_rows.loc[horizon_rows["split"].eq("validation")]
        if train.empty or validation.empty:
            raise ValueError(f"Insufficient train/validation data for t+{horizon}h.")

        best_key: tuple[float, int] | None = None
        best_parameters: dict[str, float | int] | None = None
        for candidate_id, parameters in enumerate(PARAMETER_CANDIDATES, start=1):
            pipeline = build_pipeline("v1", parameters)
            pipeline.fit(
                feature_frame(train, "v1"), train["target_pm25"]
            )
            predicted = pd.Series(
                pipeline.predict(feature_frame(validation, "v1")),
                index=validation.index,
            )
            scores = regression_metrics(validation["target_pm25"], predicted)
            search_rows.append(
                {
                    "horizon_hours": horizon,
                    "candidate_id": candidate_id,
                    **parameters,
                    **{f"validation_{key}": value for key, value in scores.items()},
                }
            )
            key = (float(scores["mae"]), candidate_id)
            if best_key is None or key < best_key:
                best_key = key
                best_parameters = dict(parameters)
        if best_parameters is None:
            raise AssertionError("Hyperparameter search produced no configuration.")
        selected[horizon] = best_parameters
    return selected, pd.DataFrame(search_rows)


def fit_horizon_models(
    samples: pd.DataFrame,
    version: str,
    parameters: Mapping[int, Mapping[str, float | int]],
    fit_splits: tuple[str, ...],
) -> dict[int, Pipeline]:
    models: dict[int, Pipeline] = {}
    for horizon in HORIZONS:
        fit_rows = samples.loc[
            samples["horizon_hours"].eq(horizon)
            & samples["split"].isin(fit_splits)
        ]
        if fit_rows.empty:
            raise ValueError(f"No fitting observations for t+{horizon}h.")
        pipeline = build_pipeline(version, parameters[horizon])
        pipeline.fit(
            feature_frame(fit_rows, version), fit_rows["target_pm25"]
        )
        models[horizon] = pipeline
    return models


def predict_horizon_models(
    models: Mapping[int, Pipeline],
    samples: pd.DataFrame,
    version: str,
    split: str,
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for horizon in HORIZONS:
        evaluation = samples.loc[
            samples["horizon_hours"].eq(horizon)
            & samples["split"].eq(split)
        ].copy()
        evaluation["prediction"] = models[horizon].predict(
            feature_frame(evaluation, version)
        )
        evaluation["model"] = f"xgboost_{version}"
        rows.append(evaluation)
    return pd.concat(rows, ignore_index=True)


def _metrics_for_prediction_rows(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (model, split), model_split in predictions.groupby(
        ["model", "split"], sort=True
    ):
        groups: list[tuple[object, object, pd.DataFrame]] = [
            ("ALL", "ALL", model_split)
        ]
        groups.extend(
            ("ALL", horizon, group)
            for horizon, group in model_split.groupby("horizon_hours", sort=True)
        )
        groups.extend(
            (station, "ALL", group)
            for station, group in model_split.groupby("Station_No", sort=True)
        )
        groups.extend(
            (station, horizon, group)
            for (station, horizon), group in model_split.groupby(
                ["Station_No", "horizon_hours"], sort=True
            )
        )
        for station, horizon, group in groups:
            rows.append(
                {
                    "model": model,
                    "split": split,
                    "Station_No": station,
                    "horizon_hours": horizon,
                    **regression_metrics(
                        group["target_pm25"], group["prediction"]
                    ),
                }
            )
    return pd.DataFrame(rows)


def _baseline_prediction_rows(
    samples: pd.DataFrame, clean: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    baseline_predictions, baseline_metrics = evaluate_baselines(samples, clean)
    rows = []
    for model, column in (
        ("persistence", "persistence_prediction"),
        ("historical_time", "historical_time_prediction"),
    ):
        subset = baseline_predictions.loc[
            baseline_predictions["split"].isin(("validation", "test"))
        ].copy()
        subset["model"] = model
        subset["prediction"] = subset[column]
        rows.append(subset)
    return pd.concat(rows, ignore_index=True), baseline_metrics


def improvement_over_persistence(metrics: pd.DataFrame) -> pd.DataFrame:
    persistence = metrics.loc[
        metrics["model"].eq("persistence"),
        [
            "split",
            "Station_No",
            "horizon_hours",
            "mae",
            "rmse",
            "r2",
        ],
    ].rename(
        columns={
            "mae": "persistence_mae",
            "rmse": "persistence_rmse",
            "r2": "persistence_r2",
        }
    )
    models = metrics.loc[metrics["model"].str.startswith("xgboost_")].copy()
    result = models.merge(
        persistence,
        on=["split", "Station_No", "horizon_hours"],
        how="left",
        validate="many_to_one",
    )
    result["mae_absolute_improvement"] = (
        result["persistence_mae"] - result["mae"]
    )
    result["mae_percent_improvement"] = (
        result["mae_absolute_improvement"] / result["persistence_mae"] * 100
    )
    result["rmse_absolute_improvement"] = (
        result["persistence_rmse"] - result["rmse"]
    )
    result["rmse_percent_improvement"] = (
        result["rmse_absolute_improvement"] / result["persistence_rmse"] * 100
    )
    result["r2_absolute_improvement"] = result["r2"] - result["persistence_r2"]
    return result


def weather_imputation_summary(
    models: Mapping[int, Pipeline],
    samples: pd.DataFrame,
    fit_splits: tuple[str, ...],
    fit_stage: str,
) -> pd.DataFrame:
    rows = []
    for horizon, pipeline in models.items():
        imputer = pipeline.named_steps["preprocessor"].named_transformers_[
            "weather"
        ]
        fit_rows = samples.loc[
            samples["horizon_hours"].eq(horizon)
            & samples["split"].isin(fit_splits)
        ]
        rows.append(
            {
                "fit_stage": fit_stage,
                "horizon_hours": horizon,
                "fit_rows": len(fit_rows),
                "temperature_missing": int(fit_rows["Temperature"].isna().sum()),
                "humidity_missing": int(fit_rows["Humidity"].isna().sum()),
                "temperature_training_median": float(imputer.statistics_[0]),
                "humidity_training_median": float(imputer.statistics_[1]),
            }
        )
    return pd.DataFrame(rows)


def feature_importance(
    models: Mapping[int, Pipeline], version: str
) -> pd.DataFrame:
    rows = []
    for horizon, pipeline in models.items():
        preprocessor = pipeline.named_steps["preprocessor"]
        names = preprocessor.get_feature_names_out()
        importances = pipeline.named_steps["model"].feature_importances_
        for name, importance in zip(names, importances, strict=True):
            rows.append(
                {
                    "model": f"xgboost_{version}",
                    "horizon_hours": horizon,
                    "feature": str(name),
                    "importance": float(importance),
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["horizon_hours", "importance"], ascending=[True, False]
    )


def tree_shap_importance(
    models: Mapping[int, Pipeline],
    samples: pd.DataFrame,
    version: str,
    max_rows_per_horizon: int = 500,
) -> pd.DataFrame:
    """Compute deterministic mean absolute XGBoost TreeSHAP contributions."""
    rows = []
    for horizon, pipeline in models.items():
        test = samples.loc[
            samples["horizon_hours"].eq(horizon) & samples["split"].eq("test")
        ]
        if len(test) > max_rows_per_horizon:
            test = test.sample(max_rows_per_horizon, random_state=RANDOM_SEED)
        preprocessor = pipeline.named_steps["preprocessor"]
        transformed = preprocessor.transform(feature_frame(test, version))
        model = pipeline.named_steps["model"]
        contributions = model.get_booster().predict(
            DMatrix(transformed), pred_contribs=True
        )
        names = preprocessor.get_feature_names_out()
        mean_absolute = np.abs(contributions[:, :-1]).mean(axis=0)
        for name, value in zip(names, mean_absolute, strict=True):
            rows.append(
                {
                    "model": f"xgboost_{version}",
                    "horizon_hours": horizon,
                    "feature": str(name),
                    "mean_absolute_shap": float(value),
                    "shap_sample_rows": len(test),
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["horizon_hours", "mean_absolute_shap"], ascending=[True, False]
    )


@dataclass
class HourlyStationForecaster:
    """Hourly monitored-station forecaster; spatial estimation is external."""

    models: dict[int, Pipeline]
    version: str
    station_ids: tuple[str, ...]

    def save(self, path: str | Path) -> None:
        """Serialize portable state without pickling this wrapper's module name."""
        joblib.dump(
            {
                "models": self.models,
                "version": self.version,
                "station_ids": self.station_ids,
            },
            path,
        )

    @classmethod
    def load(cls, path: str | Path) -> "HourlyStationForecaster":
        state = joblib.load(path)
        return cls(
            models=state["models"],
            version=state["version"],
            station_ids=tuple(state["station_ids"]),
        )

    def predict_pm25(
        self,
        station_or_location: str | int,
        target_time: pd.Timestamp | str,
        *,
        prediction_time: pd.Timestamp | str,
        pm25_lags: Mapping[int, float],
        temperature: float | None = None,
        humidity: float | None = None,
    ) -> float:
        """Predict station PM2.5 at an exact supported hourly target time.

        Geographic road locations are intentionally unsupported until a separate
        spatial-estimation layer maps locations to defensible concentration
        estimates.
        """
        station = str(station_or_location)
        if station not in self.station_ids:
            raise ValueError(
                "Unknown monitored station. Geographic-location prediction "
                "requires a future spatial estimation layer."
            )
        origin = pd.Timestamp(prediction_time)
        target = pd.Timestamp(target_time)
        for label, timestamp in (("prediction_time", origin), ("target_time", target)):
            if (
                timestamp.minute != 0
                or timestamp.second != 0
                or timestamp.microsecond != 0
                or timestamp.nanosecond != 0
            ):
                raise ValueError(f"{label} must be an exact hourly timestamp.")
        delta_hours = (target - origin) / pd.Timedelta(hours=1)
        if delta_hours not in self.models:
            raise ValueError("Supported target horizons are exactly 1, 2, or 3 hours.")
        missing_lags = set((1, 2, 3)).difference(pm25_lags)
        if missing_lags:
            raise ValueError(
                "Missing exact PM2.5 lags: "
                + ", ".join(str(value) for value in sorted(missing_lags))
            )
        row = pd.DataFrame(
            {
                "Station_No": [station],
                "pm25_lag_1h": [pm25_lags[1]],
                "pm25_lag_2h": [pm25_lags[2]],
                "pm25_lag_3h": [pm25_lags[3]],
                "hour": [origin.hour],
                "day_of_week": [origin.dayofweek],
                "month": [origin.month],
                "Temperature": [np.nan if temperature is None else temperature],
                "Humidity": [np.nan if humidity is None else humidity],
            }
        )
        prediction = self.models[int(delta_hours)].predict(
            feature_frame(row, self.version)
        )
        return float(prediction[0])


def _plot_outputs(
    selected_test: pd.DataFrame,
    metrics: pd.DataFrame,
    importance: pd.DataFrame,
    figures: Path,
) -> None:
    figures.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for horizon, ax in zip(HORIZONS, axes, strict=True):
        rows = selected_test.loc[selected_test["horizon_hours"].eq(horizon)]
        ax.hexbin(
            rows["target_pm25"],
            rows["prediction"],
            gridsize=40,
            mincnt=1,
            cmap="viridis",
        )
        lower = min(rows["target_pm25"].min(), rows["prediction"].min())
        upper = max(rows["target_pm25"].max(), rows["prediction"].max())
        ax.plot([lower, upper], [lower, upper], "k--", linewidth=1)
        ax.set(title=f"t+{horizon}h", xlabel="Observed PM2.5", ylabel="Predicted PM2.5")
    fig.tight_layout()
    fig.savefig(figures / "xgboost_prediction_vs_actual.png", dpi=300)
    plt.close(fig)

    test_horizon = metrics.loc[
        metrics["split"].eq("test")
        & metrics["Station_No"].eq("ALL")
        & metrics["horizon_hours"].isin(HORIZONS)
    ].copy()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for model, rows in test_horizon.groupby("model", sort=True):
        ax.plot(rows["horizon_hours"], rows["mae"], marker="o", label=model)
    ax.set(
        title="Held-out test MAE by horizon",
        xlabel="Forecast horizon (hours)",
        ylabel="MAE",
        xticks=list(HORIZONS),
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures / "xgboost_horizon_comparison.png", dpi=300)
    plt.close(fig)

    test_station = metrics.loc[
        metrics["split"].eq("test")
        & ~metrics["Station_No"].eq("ALL")
        & metrics["horizon_hours"].eq("ALL")
    ].copy()
    fig, ax = plt.subplots(figsize=(9, 4.5))
    pivot = test_station.pivot(index="Station_No", columns="model", values="mae")
    pivot.plot(kind="bar", ax=ax)
    ax.set(
        title="Held-out test MAE by station (horizons pooled)",
        xlabel="Station",
        ylabel="MAE",
    )
    fig.tight_layout()
    fig.savefig(figures / "xgboost_station_comparison.png", dpi=300)
    plt.close(fig)

    top = (
        importance.groupby("feature", as_index=False)["importance"]
        .mean()
        .nlargest(15, "importance")
        .sort_values("importance")
    )
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(top["feature"], top["importance"])
    ax.set(title="Mean XGBoost feature importance", xlabel="Gain importance")
    fig.tight_layout()
    fig.savefig(figures / "xgboost_feature_importance.png", dpi=300)
    plt.close(fig)


def _table(frame: pd.DataFrame) -> str:
    return (
        "_No observations._"
        if frame.empty
        else frame.to_markdown(index=False, floatfmt=".4f")
    )


def render_report(
    boundaries: pd.DataFrame,
    selected_parameters: Mapping[int, Mapping[str, float | int]],
    search: pd.DataFrame,
    metrics: pd.DataFrame,
    improvements: pd.DataFrame,
    selected_version: str,
    imputation: pd.DataFrame,
    importance: pd.DataFrame,
    shap_importance: pd.DataFrame,
) -> str:
    aggregate = metrics.loc[
        metrics["Station_No"].eq("ALL")
        & (
            metrics["horizon_hours"].eq("ALL")
            | metrics["horizon_hours"].isin(HORIZONS)
        )
    ]
    station_test = metrics.loc[
        metrics["split"].eq("test")
        & ~metrics["Station_No"].eq("ALL")
        & metrics["horizon_hours"].eq("ALL")
    ]
    station_horizon_test = metrics.loc[
        metrics["split"].eq("test")
        & ~metrics["Station_No"].eq("ALL")
        & metrics["horizon_hours"].isin(HORIZONS)
    ]
    aggregate_improvement = improvements.loc[
        improvements["Station_No"].eq("ALL")
        & (
            improvements["horizon_hours"].eq("ALL")
            | improvements["horizon_hours"].isin(HORIZONS)
        )
    ]
    selected_rows = [
        {"horizon_hours": horizon, **parameters}
        for horizon, parameters in selected_parameters.items()
    ]
    top_importance = importance.groupby(
        ["horizon_hours"], group_keys=False
    ).head(10)
    top_shap = shap_importance.groupby(
        ["horizon_hours"], group_keys=False
    ).head(10)
    v1_validation = aggregate.loc[
        aggregate["model"].eq("xgboost_v1")
        & aggregate["split"].eq("validation")
    ]
    v1_test = aggregate.loc[
        aggregate["model"].eq("xgboost_v1") & aggregate["split"].eq("test")
    ]
    v2_results = aggregate.loc[aggregate["model"].eq("xgboost_v2")]

    return f"""# AIRPATH-AI XGBoost forecasting foundation

## Protocol

This remains an **hourly monitored-station forecasting experiment**. Three
direct models are pooled across stations, one each for t+1h, t+2h, and t+3h.
Station identity is one-hot encoded and is not interpreted as ordinal.

V1 uses exact PM2.5(t-1h), PM2.5(t-2h), PM2.5(t-3h), origin hour, day of week,
month, and station. V2 adds temperature and humidity observed at prediction
time. Current PM2.5(t), future values, secondary pollutants, target-quality
flags, and test information are not model features.

{_table(boundaries)}

Hyperparameters were selected independently by horizon using validation MAE
from four declared candidates. Test rows were not accepted by the selection
function. V2 used the selected V1 parameters unchanged as a controlled feature
ablation. Version selection used pooled validation MAE. The selected version was
**{selected_version.upper()}**. After freezing this decision, V1 and V2 were
refit on train+validation and each evaluated once on the locked test partition.

## Selected V1 hyperparameters

{_table(pd.DataFrame(selected_rows))}

Complete search results are saved in
`reports/tables/xgboost_validation_search.csv`.

## A. V1 validation results

{_table(v1_validation)}

## B. V1 final locked-test results

{_table(v1_test)}

## C–D. Comparison with persistence and historical baseline

{_table(aggregate)}

Positive MAE/RMSE improvement means lower error than persistence. R² is reported
as an absolute difference because percentage changes in R² are not meaningful
when baseline R² can be zero or negative.

{_table(aggregate_improvement)}

### Scientific interpretation of baseline comparison

The selected V1 configuration does **not** uniformly outperform persistence.
On the locked test set its pooled MAE is higher by 0.8565 (19.84% worse), while
its pooled RMSE is lower by 0.4602 (5.26% better) and R² is higher by 0.0597.
Persistence is stronger at t+1h on all three metrics. At t+2h and t+3h, V1 has
lower RMSE and higher R² but still higher MAE. Thus the evidence depends on the
error functional; AIRPATH should not claim that V1 supersedes persistence.

V1 is materially better than the historical-time baseline on the locked test
set. However, V1 deliberately follows the requested feature contract and omits
PM2.5(t), whereas persistence uses PM2.5(t). The recency mismatch is an important
methodological limitation and plausibly contributes to persistence's MAE
advantage. It was not changed after observing test results.

## E. Locked-test station-level results

{_table(station_test)}

## F. Locked-test station-by-horizon results

{_table(station_horizon_test)}

## G. V2 weather ablation

{_table(v2_results)}

V2 did not improve pooled validation performance: MAE increased from 5.5771
(V1) to 5.5951 and RMSE increased from 8.9357 to 9.0573. V1 was therefore frozen
as the selected configuration before test access. The one-shot test evaluation
also showed higher error for V2, but that result was not used for selection.

Temperature and humidity are exact origin-time observations. Missing values are
median-imputed separately inside each horizon pipeline; medians are learned
from train only for validation and train+validation only for final test fitting.
Missing indicators are added. No row is dropped for weather missingness.

{_table(imputation)}

## H. Interpretability

Built-in gain importance:

{_table(top_importance)}

Mean absolute TreeSHAP values were computed on a deterministic sample of at most
500 locked-test rows per horizon after configuration was frozen. They are for
interpretation only and were not used to revise model selection.

{_table(top_shap)}

Importance and SHAP describe model behavior, not causal effects.

Across all horizons, PM2.5(t-1h) is the dominant feature. Its gain importance and
mean absolute SHAP contribution decrease with horizon, while calendar and
station contributions become relatively more prominent. This is consistent with
weakening short-term persistence, but it does not establish causal effects.

## I. Limitations of hourly HealthyAir data

- Predictions are validated only at exact hourly monitored-station timestamps.
- No minute-level ground truth, accuracy, or road-level concentration is claimed.
- Gaps reduce samples unevenly, and station observations do not directly measure
  road segments.
- The model covers only the six observed station identities and this historical
  period; generalization to roads, new monitors, or later years is unverified.
- Zero and extreme observations remain included. Audit IQR flags are metadata,
  not predictors or removal rules.
- Test results are now locked evidence and must not be used for iterative tuning.

## J. Requirements for finer temporal-resolution validation

Arrival-time-aware segment validation would require PM2.5 observations at the
temporal resolution of intended routing decisions (for example, genuine
minute-scale or appropriately frequent measurements), not interpolated hourly
labels. Required properties include:

- calibrated PM2.5 observations with documented units and quality control;
- synchronized clocks/time zones across pollution, weather, traffic, and route
  traversal records;
- continuous station/mobile-sensor operation sufficient to construct exact lags
  and targets without treating outages as observations;
- spatial coverage representative of roads and route microenvironments;
- an overlap period with HealthyAir where available for cross-instrument checks;
- documentation of sensor, season, traffic, land-use, and policy distribution
  shifts.

Newer data should first be treated as external temporal validation. It should not
be blindly merged into training until comparability, calibration, overlap, and
distribution shift have been assessed.

## K. Target-time forecasting API

```python
HourlyStationForecaster.predict_pm25(
    station_or_location,
    target_time,
    *,
    prediction_time,
    pm25_lags={{1: ..., 2: ..., 3: ...}},
    temperature=None,
    humidity=None,
) -> float
```

The API requires exact hourly prediction/target times and a 1–3 hour difference.
It currently accepts only known monitored stations. Unknown/geographic locations
are rejected explicitly: a future, separate spatial layer must translate road
locations into defensible concentration estimates. Routing and exposure logic
remain separate and unimplemented.

## L. Recommended Milestone 3

Before routing, design and validate the spatial-estimation layer and its
uncertainty using real station coordinates and defensible spatial covariates.
Define how a road location and arrival time will request a forecast without
claiming road-level direct measurement or sub-hourly accuracy. Do not use the
locked test set for further XGBoost tuning.

AIRPATH's intended direction is an arrival-time-aware, segment-level exposure
framework followed by route selection under a user-defined travel-time
constraint. No claim of being the first pollution-aware routing system is made.
"""


def run_xgboost_experiment(
    input_path: Path,
    root: Path,
) -> dict[str, object]:
    raw = load_air_quality_csv(input_path)
    clean, _ = audit_dataset(raw)
    samples, _ = build_forecasting_samples(clean)
    samples = attach_origin_weather(samples, clean)
    boundaries = split_boundaries(clean)

    selected_parameters, search = select_v1_hyperparameters(samples)

    # Validation-stage models: train only. This block decides V1 versus V2.
    validation_models: dict[str, dict[int, Pipeline]] = {}
    validation_predictions: list[pd.DataFrame] = []
    for version in ("v1", "v2"):
        models = fit_horizon_models(
            samples, version, selected_parameters, ("train",)
        )
        validation_models[version] = models
        validation_predictions.append(
            predict_horizon_models(models, samples, version, "validation")
        )
    validation_prediction_rows = pd.concat(
        validation_predictions, ignore_index=True
    )
    validation_metrics = _metrics_for_prediction_rows(
        validation_prediction_rows
    )
    pooled_validation = validation_metrics.loc[
        validation_metrics["Station_No"].eq("ALL")
        & validation_metrics["horizon_hours"].eq("ALL")
    ].sort_values(["mae", "model"])
    selected_version = str(pooled_validation.iloc[0]["model"]).removeprefix(
        "xgboost_"
    )

    # Configuration is now frozen. Test is first accessed below.
    final_models: dict[str, dict[int, Pipeline]] = {}
    test_predictions: list[pd.DataFrame] = []
    for version in ("v1", "v2"):
        models = fit_horizon_models(
            samples, version, selected_parameters, ("train", "validation")
        )
        final_models[version] = models
        test_predictions.append(
            predict_horizon_models(models, samples, version, "test")
        )
    test_prediction_rows = pd.concat(test_predictions, ignore_index=True)
    xgb_predictions = pd.concat(
        [validation_prediction_rows, test_prediction_rows], ignore_index=True
    )
    xgb_metrics = _metrics_for_prediction_rows(xgb_predictions)

    baseline_predictions, baseline_metrics = _baseline_prediction_rows(
        samples, clean
    )
    metrics = pd.concat([baseline_metrics, xgb_metrics], ignore_index=True)
    all_predictions = pd.concat(
        [baseline_predictions, xgb_predictions], ignore_index=True, sort=False
    )
    improvements = improvement_over_persistence(metrics)

    imputation = pd.concat(
        [
            weather_imputation_summary(
                validation_models["v2"], samples, ("train",), "validation_fit"
            ),
            weather_imputation_summary(
                final_models["v2"],
                samples,
                ("train", "validation"),
                "final_test_fit",
            ),
        ],
        ignore_index=True,
    )
    importance = feature_importance(
        final_models[selected_version], selected_version
    )
    shap_importance = tree_shap_importance(
        final_models[selected_version], samples, selected_version
    )

    processed = root / "data" / "processed"
    models_directory = processed / "models"
    reports = root / "reports"
    tables = reports / "tables"
    figures = reports / "figures"
    for directory in (processed, models_directory, reports, tables, figures):
        directory.mkdir(parents=True, exist_ok=True)

    for version, models in final_models.items():
        for horizon, model in models.items():
            joblib.dump(
                model, models_directory / f"xgboost_{version}_t_plus_{horizon}h.joblib"
            )
    forecaster = HourlyStationForecaster(
        models=final_models[selected_version],
        version=selected_version,
        station_ids=tuple(
            sorted(samples["Station_No"].astype(str).unique().tolist())
        ),
    )
    forecaster.save(models_directory / "hourly_station_forecaster.joblib")
    metadata = {
        "selected_version": selected_version,
        "horizons_hours": list(HORIZONS),
        "station_ids": list(forecaster.station_ids),
        "random_seed": RANDOM_SEED,
        "selected_parameters": selected_parameters,
        "time_resolution": "hourly",
        "spatial_support": "observed HealthyAir stations only",
    }
    (models_directory / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    all_predictions.to_csv(
        processed / "xgboost_forecasting_predictions.csv", index=False
    )
    search.to_csv(tables / "xgboost_validation_search.csv", index=False)
    metrics.to_csv(tables / "xgboost_metrics.csv", index=False)
    improvements.to_csv(
        tables / "xgboost_improvement_over_persistence.csv", index=False
    )
    imputation.to_csv(tables / "xgboost_weather_imputation.csv", index=False)
    importance.to_csv(tables / "xgboost_feature_importance.csv", index=False)
    shap_importance.to_csv(
        tables / "xgboost_shap_importance.csv", index=False
    )

    selected_test = test_prediction_rows.loc[
        test_prediction_rows["model"].eq(f"xgboost_{selected_version}")
    ]
    _plot_outputs(selected_test, metrics, importance, figures)
    report = render_report(
        boundaries,
        selected_parameters,
        search,
        metrics,
        improvements,
        selected_version,
        imputation,
        importance,
        shap_importance,
    )
    (reports / "xgboost_forecasting.md").write_text(report, encoding="utf-8")

    return {
        "selected_version": selected_version,
        "selected_parameters": selected_parameters,
        "search": search,
        "metrics": metrics,
        "improvements": improvements,
        "imputation": imputation,
        "importance": importance,
        "shap_importance": shap_importance,
        "predictions": all_predictions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw/Air Quality Ho Chi Minh City.csv"),
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    run_xgboost_experiment(args.input, args.root)


if __name__ == "__main__":
    main()
