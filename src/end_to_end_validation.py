"""Development-only validation of forecast plus spatial PM2.5 error.

The experiment reuses persisted XGBoost V1 validation predictions generated
from training-period fits. It does not retrain models or use the exposed final
forecasting test period. IDW p=1 is identical in oracle and forecast pathways.
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
import numpy as np
import pandas as pd

from .eta_engine import SegmentETA, propagate_segment_etas
from .road_network import load_network
from .route_candidates import (
    EXAMPLE_DESTINATION,
    EXAMPLE_ORIGIN,
    generate_candidate_routes,
)
from .spatial_estimation import (
    STATION_BY_ID,
    estimate_with_diagnostics,
    regression_metrics,
)
from .target_time_integration import classify_spatial_reliability


PIPELINES: Final[tuple[str, ...]] = (
    "forecast_only",
    "oracle_spatial",
    "forecast_spatial",
)
MAPPING_RULES: Final[tuple[str, ...]] = ("ceiling", "floor", "nearest")
HORIZONS: Final[tuple[int, ...]] = (1, 2, 3)
ROUTE_FORECAST_ORIGIN: Final[pd.Timestamp] = pd.Timestamp("2022-02-28 05:00:00")
ROUTE_DEPARTURE_TIME: Final[pd.Timestamp] = pd.Timestamp("2022-02-28 06:00:00")


@dataclass(frozen=True)
class MappingSensitivityResult:
    requested_target_time: pd.Timestamp
    mapped_target_time: pd.Timestamp
    forecasting_origin_time: pd.Timestamp
    mapping_rule: str
    mapping_method: str
    mapping_offset_seconds: float
    horizon_hours: int
    supported: bool


@dataclass(frozen=True)
class ReadinessDecision:
    classification: str
    rationale: str
    criteria: Mapping[str, object]


def _normalise_forecast_rows(predictions: pd.DataFrame) -> pd.DataFrame:
    required = {
        "Station_No",
        "origin_time",
        "target_time",
        "horizon_hours",
        "target_pm25",
        "prediction",
        "split",
        "model",
    }
    missing = required.difference(predictions.columns)
    if missing:
        raise ValueError(
            "Forecast validation data missing columns: "
            + ", ".join(sorted(missing))
        )
    rows = predictions.copy()
    rows["origin_time"] = pd.to_datetime(rows["origin_time"], errors="raise")
    rows["target_time"] = pd.to_datetime(rows["target_time"], errors="raise")
    rows["Station_No"] = rows["Station_No"].astype(int)
    rows["horizon_hours"] = rows["horizon_hours"].astype(int)
    rows = rows.loc[
        rows["split"].eq("validation")
        & rows["model"].eq("xgboost_v1")
        & rows["horizon_hours"].isin(HORIZONS)
    ].copy()
    if rows.empty:
        raise ValueError("No frozen V1 development-validation predictions found.")
    if rows.duplicated(["origin_time", "horizon_hours", "Station_No"]).any():
        raise ValueError("Forecast rows contain duplicate origin/horizon/station keys.")
    return rows.sort_values(
        ["origin_time", "horizon_hours", "Station_No"]
    ).reset_index(drop=True)


def evaluate_heldout_stations(predictions: pd.DataFrame) -> pd.DataFrame:
    """Evaluate three pathways on identical complete six-station cases."""
    rows = _normalise_forecast_rows(predictions)
    expected_stations = set(STATION_BY_ID)
    result: list[dict[str, object]] = []
    for (origin_time, horizon), group in rows.groupby(
        ["origin_time", "horizon_hours"], sort=True
    ):
        if set(group["Station_No"]) != expected_stations:
            continue
        if not (
            np.isfinite(group["target_pm25"]).all()
            and np.isfinite(group["prediction"]).all()
        ):
            continue
        if group["target_time"].nunique() != 1:
            raise ValueError("One origin/horizon group has inconsistent target times.")
        target_time = pd.Timestamp(group["target_time"].iloc[0])
        expected_target = pd.Timestamp(origin_time) + pd.Timedelta(hours=int(horizon))
        if target_time != expected_target:
            raise ValueError("Forecast target does not match origin plus horizon.")
        observed = dict(zip(group["Station_No"], group["target_pm25"]))
        forecasted = dict(zip(group["Station_No"], group["prediction"]))

        for held_out_station in sorted(expected_stations):
            station = STATION_BY_ID[held_out_station]
            oracle_values = {
                station_id: float(value)
                for station_id, value in observed.items()
                if station_id != held_out_station
            }
            forecast_values = {
                station_id: float(value)
                for station_id, value in forecasted.items()
                if station_id != held_out_station
            }
            oracle = estimate_with_diagnostics(
                station.latitude,
                station.longitude,
                target_time,
                oracle_values,
                method="idw",
                power=1,
            )
            combined = estimate_with_diagnostics(
                station.latitude,
                station.longitude,
                target_time,
                forecast_values,
                method="idw",
                power=1,
            )
            actual = float(observed[held_out_station])
            result.append(
                {
                    "origin_time": pd.Timestamp(origin_time),
                    "target_time": target_time,
                    "horizon_hours": int(horizon),
                    "held_out_station": held_out_station,
                    "actual_pm25": actual,
                    "forecast_only_prediction": float(
                        forecasted[held_out_station]
                    ),
                    "oracle_spatial_prediction": oracle.predicted_pm25,
                    "forecast_spatial_prediction": combined.predicted_pm25,
                    "forecast_only_absolute_error": abs(
                        float(forecasted[held_out_station]) - actual
                    ),
                    "oracle_spatial_absolute_error": abs(
                        oracle.predicted_pm25 - actual
                    ),
                    "forecast_spatial_absolute_error": abs(
                        combined.predicted_pm25 - actual
                    ),
                    "nearest_station_distance_km": oracle.nearest_distance_km,
                    "second_nearest_station_distance_km": (
                        oracle.second_nearest_distance_km
                    ),
                    "contributing_station_count": oracle.contributing_stations,
                    "maximum_idw_weight": oracle.maximum_weight,
                    "idw_weight_concentration": oracle.weight_concentration,
                    "effective_station_count": oracle.effective_station_count,
                    "reliability_status": classify_spatial_reliability(oracle),
                }
            )
    frame = pd.DataFrame(result)
    if frame.empty:
        raise ValueError("No complete six-station validation cases were available.")
    return frame


def aggregate_heldout_metrics(evaluation: pd.DataFrame) -> pd.DataFrame:
    """Return pooled, per-station, per-horizon, and station×horizon metrics."""
    prediction_columns = {
        "forecast_only": "forecast_only_prediction",
        "oracle_spatial": "oracle_spatial_prediction",
        "forecast_spatial": "forecast_spatial_prediction",
    }
    rows: list[dict[str, object]] = []
    group_specs: list[tuple[str, list[str]]] = [
        ("pooled", []),
        ("per_station", ["held_out_station"]),
        ("per_horizon", ["horizon_hours"]),
        ("station_horizon", ["held_out_station", "horizon_hours"]),
    ]
    for pipeline, prediction_column in prediction_columns.items():
        for aggregation, group_columns in group_specs:
            grouped = (
                [((), evaluation)]
                if not group_columns
                else evaluation.groupby(group_columns, sort=True)
            )
            for key, group in grouped:
                keys = key if isinstance(key, tuple) else (key,)
                labels = dict(zip(group_columns, keys))
                rows.append(
                    {
                        "pipeline": pipeline,
                        "aggregation": aggregation,
                        "held_out_station": labels.get(
                            "held_out_station", "ALL"
                        ),
                        "horizon_hours": labels.get("horizon_hours", "ALL"),
                        "n": len(group),
                        "unique_target_timestamps": group["target_time"].nunique(),
                        **regression_metrics(
                            group["actual_pm25"], group[prediction_column]
                        ),
                    }
                )
    return pd.DataFrame(rows)


def error_decomposition(metrics: pd.DataFrame) -> pd.DataFrame:
    """Compare errors; differences are descriptive and not additive/causal."""
    selected = metrics.loc[
        metrics["held_out_station"].eq("ALL")
        & (
            metrics["horizon_hours"].eq("ALL")
            | metrics["aggregation"].eq("per_horizon")
        )
    ]
    index_columns = ["horizon_hours"]
    rows: list[dict[str, object]] = []
    for horizon, group in selected.groupby(index_columns, sort=False):
        by_pipeline = group.set_index("pipeline")
        if not set(PIPELINES).issubset(by_pipeline.index):
            continue
        horizon_value = horizon[0] if isinstance(horizon, tuple) else horizon
        row: dict[str, object] = {"horizon_hours": horizon_value}
        for metric in ("mae", "rmse", "r2"):
            forecast_only = float(by_pipeline.loc["forecast_only", metric])
            oracle = float(by_pipeline.loc["oracle_spatial", metric])
            combined = float(by_pipeline.loc["forecast_spatial", metric])
            row[f"forecast_only_{metric}"] = forecast_only
            row[f"oracle_spatial_{metric}"] = oracle
            row[f"forecast_spatial_{metric}"] = combined
            row[f"combined_minus_oracle_{metric}"] = combined - oracle
            row[f"combined_minus_forecast_only_{metric}"] = (
                combined - forecast_only
            )
        rows.append(row)
    return pd.DataFrame(rows)


def map_target_time_for_sensitivity(
    requested_target_time: object,
    forecasting_origin_time: object,
    rule: str,
    *,
    supported_horizons: Sequence[int] = HORIZONS,
) -> MappingSensitivityResult:
    """Map without interpolation using ceiling, floor, or nearest hour."""
    requested = pd.Timestamp(requested_target_time)
    origin = pd.Timestamp(forecasting_origin_time)
    if pd.isna(requested) or pd.isna(origin):
        raise ValueError("Mapping timestamps must not be missing.")
    if rule not in MAPPING_RULES:
        raise ValueError("rule must be 'ceiling', 'floor', or 'nearest'.")
    if (
        origin.minute != 0
        or origin.second != 0
        or origin.microsecond != 0
        or origin.nanosecond != 0
    ):
        raise ValueError("forecasting_origin_time must be an exact hour.")
    floor = requested.floor("h")
    ceiling = requested.ceil("h")
    if rule == "floor":
        mapped = floor
        method = "floor_to_current_hour_no_interpolation"
    elif rule == "ceiling":
        mapped = ceiling
        method = "ceiling_to_next_hour_no_interpolation"
    else:
        seconds_after_floor = (requested - floor).total_seconds()
        # Deterministic half-up tie: exactly hh:30 maps to the next hour.
        mapped = ceiling if seconds_after_floor >= 1800 else floor
        method = "nearest_hour_half_up_no_interpolation"
    delta = (mapped - origin) / pd.Timedelta(hours=1)
    if not float(delta).is_integer():
        raise ValueError("Mapped target must be a whole-hour horizon.")
    horizon = int(delta)
    return MappingSensitivityResult(
        requested_target_time=requested,
        mapped_target_time=mapped,
        forecasting_origin_time=origin,
        mapping_rule=rule,
        mapping_method=method,
        mapping_offset_seconds=float((mapped - requested).total_seconds()),
        horizon_hours=horizon,
        supported=horizon in {int(value) for value in supported_horizons},
    )


def _forecast_case(
    rows: pd.DataFrame,
    origin_time: pd.Timestamp,
    horizon_hours: int,
) -> tuple[pd.Timestamp, dict[int, float], dict[int, float]]:
    group = rows.loc[
        rows["origin_time"].eq(origin_time)
        & rows["horizon_hours"].eq(horizon_hours)
    ]
    if set(group["Station_No"]) != set(STATION_BY_ID):
        raise ValueError(
            f"Incomplete saved forecast case at {origin_time}, t+{horizon_hours}h."
        )
    if group["target_time"].nunique() != 1:
        raise ValueError("Saved forecast case has inconsistent target times.")
    target = pd.Timestamp(group["target_time"].iloc[0])
    observed = {
        int(station_id): float(value)
        for station_id, value in zip(
            group["Station_No"], group["target_pm25"]
        )
    }
    forecasted = {
        int(station_id): float(value)
        for station_id, value in zip(group["Station_No"], group["prediction"])
    }
    if not all(
        np.isfinite(value)
        for value in (*observed.values(), *forecasted.values())
    ):
        raise ValueError("Saved route forecast case contains missing values.")
    return target, observed, forecasted


def evaluate_route_mapping_sensitivity(
    predictions: pd.DataFrame,
    segments_by_mode: Mapping[str, Sequence[SegmentETA]],
    *,
    forecasting_origin_time: object = ROUTE_FORECAST_ORIGIN,
) -> pd.DataFrame:
    """Compare forecast+spatial against hourly oracle-spatial pseudo-reference."""
    rows = _normalise_forecast_rows(predictions)
    origin = pd.Timestamp(forecasting_origin_time)
    result: list[dict[str, object]] = []
    case_cache: dict[
        int, tuple[pd.Timestamp, dict[int, float], dict[int, float]]
    ] = {}
    for mode, segments in segments_by_mode.items():
        for expected_index, segment in enumerate(segments, start=1):
            if segment.segment_index != expected_index:
                raise ValueError("Route segments must remain in contiguous order.")
            for rule in MAPPING_RULES:
                mapping = map_target_time_for_sensitivity(
                    segment.target_arrival_timestamp, origin, rule
                )
                if not mapping.supported:
                    raise ValueError(
                        f"Route mapping produced unsupported t+{mapping.horizon_hours}h."
                    )
                if mapping.horizon_hours not in case_cache:
                    case_cache[mapping.horizon_hours] = _forecast_case(
                        rows, origin, mapping.horizon_hours
                    )
                target, observed, forecasted = case_cache[mapping.horizon_hours]
                if target != mapping.mapped_target_time:
                    raise ValueError("Saved forecast target differs from mapped ETA.")
                oracle = estimate_with_diagnostics(
                    segment.representative_latitude,
                    segment.representative_longitude,
                    target,
                    observed,
                    method="idw",
                    power=1,
                )
                combined = estimate_with_diagnostics(
                    segment.representative_latitude,
                    segment.representative_longitude,
                    target,
                    forecasted,
                    method="idw",
                    power=1,
                )
                error = combined.predicted_pm25 - oracle.predicted_pm25
                result.append(
                    {
                        "mode": mode,
                        "route_id": segment.route_id,
                        "segment_index": segment.segment_index,
                        "segment_id": segment.edge_id,
                        "latitude": segment.representative_latitude,
                        "longitude": segment.representative_longitude,
                        "segment_geometry": json.dumps(
                            [list(point) for point in segment.segment_geometry],
                            separators=(",", ":"),
                        ),
                        "segment_duration_seconds": (
                            segment.segment_duration_seconds
                        ),
                        "eta": segment.target_arrival_timestamp,
                        "mapping_rule": rule,
                        "mapping_method": mapping.mapping_method,
                        "mapped_target_time": mapping.mapped_target_time,
                        "mapping_offset_seconds": mapping.mapping_offset_seconds,
                        "forecast_horizon_hours": mapping.horizon_hours,
                        "oracle_spatial_pm25": oracle.predicted_pm25,
                        "forecast_spatial_pm25": combined.predicted_pm25,
                        "forecast_minus_oracle_error": error,
                        "absolute_error": abs(error),
                        "squared_error": error**2,
                        "nearest_station_distance_km": (
                            oracle.nearest_distance_km
                        ),
                        "second_nearest_station_distance_km": (
                            oracle.second_nearest_distance_km
                        ),
                        "contributing_station_count": (
                            oracle.contributing_stations
                        ),
                        "maximum_idw_weight": oracle.maximum_weight,
                        "idw_weight_concentration": (
                            oracle.weight_concentration
                        ),
                        "effective_station_count": (
                            oracle.effective_station_count
                        ),
                        "reliability_status": (
                            classify_spatial_reliability(oracle)
                        ),
                        "reference_type": (
                            "hourly oracle IDW pseudo-reference; "
                            "not a road measurement"
                        ),
                    }
                )
    return pd.DataFrame(result)


def mapping_sensitivity_metrics(route_rows: pd.DataFrame) -> pd.DataFrame:
    result = []
    for (mode, rule), group in route_rows.groupby(
        ["mode", "mapping_rule"], sort=True
    ):
        result.append(
            {
                "mode": mode,
                "mapping_rule": rule,
                "segments": len(group),
                "mapped_target_hours": group["mapped_target_time"].nunique(),
                "mae_vs_oracle_spatial": float(group["absolute_error"].mean()),
                "rmse_vs_oracle_spatial": float(
                    np.sqrt(group["squared_error"].mean())
                ),
                "max_absolute_error": float(group["absolute_error"].max()),
            }
        )
    return pd.DataFrame(result)


def _rank_correlation(first: pd.Series, second: pd.Series) -> float:
    valid = first.notna() & second.notna()
    if valid.sum() < 3:
        return float("nan")
    return float(first.loc[valid].rank().corr(second.loc[valid].rank()))


def reliability_error_relationship(
    heldout: pd.DataFrame,
    route_rows: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Describe proxy/error associations without calibrated uncertainty claims."""
    station_level = (
        heldout.groupby("held_out_station", as_index=False)
        .agg(
            combined_mae=("forecast_spatial_absolute_error", "mean"),
            oracle_spatial_mae=("oracle_spatial_absolute_error", "mean"),
            nearest_station_distance_km=("nearest_station_distance_km", "first"),
            second_nearest_station_distance_km=(
                "second_nearest_station_distance_km",
                "first",
            ),
            maximum_idw_weight=("maximum_idw_weight", "first"),
            effective_station_count=("effective_station_count", "first"),
        )
    )
    proxy_columns = (
        "nearest_station_distance_km",
        "second_nearest_station_distance_km",
        "maximum_idw_weight",
        "effective_station_count",
    )
    rows: list[dict[str, object]] = []
    for proxy in proxy_columns:
        rows.append(
            {
                "analysis": "heldout_station_aggregate",
                "error_measure": "combined_mae",
                "proxy": proxy,
                "n": len(station_level),
                "spearman_rank_correlation": _rank_correlation(
                    station_level[proxy], station_level["combined_mae"]
                ),
            }
        )
    ceiling = route_rows.loc[route_rows["mapping_rule"].eq("ceiling")]
    for proxy in proxy_columns:
        rows.append(
            {
                "analysis": "route_segments_ceiling",
                "error_measure": "absolute_forecast_minus_oracle_spatial",
                "proxy": proxy,
                "n": len(ceiling),
                "spearman_rank_correlation": _rank_correlation(
                    ceiling[proxy], ceiling["absolute_error"]
                ),
            }
        )
    status = (
        ceiling.groupby(["mode", "reliability_status"], as_index=False)
        .agg(
            segments=("segment_id", "size"),
            mae_vs_oracle_spatial=("absolute_error", "mean"),
            rmse_vs_oracle_spatial=(
                "squared_error",
                lambda values: float(np.sqrt(values.mean())),
            ),
        )
    )
    return pd.DataFrame(rows), status


def decide_readiness(metrics: pd.DataFrame) -> ReadinessDecision:
    """Apply transparent relative-error criteria to observed metrics."""
    pooled_rows = metrics.loc[metrics["aggregation"].eq("pooled")].set_index(
        "pipeline"
    )
    pooled = pooled_rows.loc["forecast_spatial"]
    component_mae_reference = max(
        float(pooled_rows.loc["forecast_only", "mae"]),
        float(pooled_rows.loc["oracle_spatial", "mae"]),
    )
    component_r2_floor = min(
        float(pooled_rows.loc["forecast_only", "r2"]),
        float(pooled_rows.loc["oracle_spatial", "r2"]),
    )
    mae_ratio = float(pooled["mae"]) / component_mae_reference
    per_station = metrics.loc[
        metrics["pipeline"].eq("forecast_spatial")
        & metrics["aggregation"].eq("per_station")
    ]
    positive_station_r2 = int(per_station["r2"].gt(0).sum())
    criteria = {
        "combined_mae_relative_to_worse_component": mae_ratio,
        "combined_mae_degradation_le_50_percent": mae_ratio <= 1.5,
        "pooled_r2_positive": bool(pooled["r2"] > 0),
        "at_least_four_of_six_station_r2_positive": positive_station_r2 >= 4,
        "positive_station_r2_count": positive_station_r2,
        "ready_strict_mae_degradation_le_10_percent": mae_ratio <= 1.1,
        "ready_strict_r2_no_worse_than_component_floor": bool(
            pooled["r2"] >= component_r2_floor
        ),
        "ready_strict_all_station_r2_nonnegative": bool(
            per_station["r2"].ge(0).all()
        ),
    }
    strict_ready = (
        criteria["ready_strict_mae_degradation_le_10_percent"]
        and criteria["ready_strict_r2_no_worse_than_component_floor"]
        and criteria["ready_strict_all_station_r2_nonnegative"]
    )
    restricted_ready = (
        criteria["combined_mae_degradation_le_50_percent"]
        and criteria["pooled_r2_positive"]
        and criteria["at_least_four_of_six_station_r2_positive"]
    )
    if strict_ready:
        classification = "A. READY"
        rationale = "Combined error meets all strict pooled and station criteria."
    elif restricted_ready:
        classification = "B. READY WITH RESTRICTIONS"
        rationale = (
            "Combined error meets pooled usability criteria and generalizes "
            "positively at at least four stations, but not every strict criterion."
        )
    else:
        classification = "C. NOT READY — NEED MODEL/SPATIAL IMPROVEMENT"
        rationale = (
            "Combined error fails one or more pooled or station-generalization "
            "criteria required before exposure aggregation."
        )
    return ReadinessDecision(classification, rationale, criteria)


def _plot_outputs(
    metrics: pd.DataFrame,
    decomposition: pd.DataFrame,
    mapping: pd.DataFrame,
    station_reliability: pd.DataFrame,
    output_directory: Path,
) -> None:
    pooled_horizon = metrics.loc[
        metrics["held_out_station"].eq("ALL")
        & metrics["aggregation"].isin(["pooled", "per_horizon"])
    ].copy()
    pooled_horizon["horizon_label"] = pooled_horizon["horizon_hours"].astype(str)
    figure, axis = plt.subplots(figsize=(9, 5))
    width = 0.24
    labels = ["ALL", "1", "2", "3"]
    x = np.arange(len(labels))
    for offset, pipeline in enumerate(PIPELINES):
        values = []
        rows = pooled_horizon.loc[pooled_horizon["pipeline"].eq(pipeline)]
        for label in labels:
            match = rows.loc[rows["horizon_label"].eq(label), "mae"]
            values.append(float(match.iloc[0]))
        axis.bar(x + (offset - 1) * width, values, width, label=pipeline)
    axis.set(
        xticks=x,
        xticklabels=labels,
        xlabel="Forecast horizon (hours; ALL is pooled)",
        ylabel="MAE (µg/m³)",
        title="Development-only held-out-station error",
    )
    axis.legend()
    axis.grid(axis="y", alpha=0.2)
    figure.tight_layout()
    figure.savefig(output_directory / "heldout_pipeline_mae.png", dpi=180)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(8, 5))
    for mode, group in mapping.groupby("mode", sort=True):
        axis.plot(
            group["mapping_rule"],
            group["mae_vs_oracle_spatial"],
            marker="o",
            label=mode,
        )
    axis.set(
        xlabel="Hourly mapping rule",
        ylabel="Segment MAE vs hourly oracle spatial (µg/m³)",
        title="Target-time mapping sensitivity (development example)",
    )
    axis.legend()
    axis.grid(alpha=0.2)
    figure.tight_layout()
    figure.savefig(output_directory / "mapping_sensitivity.png", dpi=180)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(7, 5))
    axis.scatter(
        station_reliability["nearest_station_distance_km"],
        station_reliability["combined_mae"],
        color="#c62828",
    )
    for row in station_reliability.itertuples():
        axis.annotate(
            f"S{row.held_out_station}",
            (row.nearest_station_distance_km, row.combined_mae),
            xytext=(4, 4),
            textcoords="offset points",
        )
    axis.set(
        xlabel="Nearest contributing station distance (km)",
        ylabel="Forecast+spatial MAE (µg/m³)",
        title="Geometry proxy versus held-out-station error (n=6)",
    )
    axis.grid(alpha=0.2)
    figure.tight_layout()
    figure.savefig(output_directory / "reliability_error_proxy.png", dpi=180)
    plt.close(figure)


def _markdown_table(frame: pd.DataFrame, digits: int = 4) -> str:
    display = frame.copy()
    numeric = display.select_dtypes(include="number").columns
    display[numeric] = display[numeric].round(digits)
    return display.to_markdown(index=False)


def _render_report(
    metrics: pd.DataFrame,
    decomposition: pd.DataFrame,
    route_sample: pd.DataFrame,
    mapping_metrics: pd.DataFrame,
    correlations: pd.DataFrame,
    status_metrics: pd.DataFrame,
    decision: ReadinessDecision,
) -> str:
    pooled = metrics.loc[metrics["aggregation"].eq("pooled")]
    per_station = metrics.loc[
        metrics["aggregation"].eq("per_station")
    ]
    per_horizon = metrics.loc[
        metrics["aggregation"].eq("per_horizon")
    ]
    route_columns = [
        "mode",
        "route_id",
        "segment_index",
        "eta",
        "mapping_method",
        "mapped_target_time",
        "oracle_spatial_pm25",
        "forecast_spatial_pm25",
        "absolute_error",
        "nearest_station_distance_km",
        "effective_station_count",
        "reliability_status",
    ]
    rule_mae = mapping_metrics.groupby("mapping_rule")[
        "mae_vs_oracle_spatial"
    ].mean()
    recommended_rule = str(rule_mae.idxmin())
    floor_mae = float(rule_mae["floor"])
    ceiling_mae = float(rule_mae["ceiling"])
    nearest_mae = float(rule_mae["nearest"])
    if decision.classification.startswith("B."):
        readiness_scope = (
            "Proceed only to an offline, pilot-area exposure-aggregation "
            "experiment with reliability flags and station-level diagnostics. "
            "Do not use it for route recommendation: station 5 has negative "
            "combined R² and no road-level ground truth exists."
        )
    elif decision.classification.startswith("A."):
        readiness_scope = (
            "Proceed to an offline exposure-aggregation experiment while "
            "retaining all documented resolution and road-reference caveats."
        )
    else:
        readiness_scope = (
            "Do not begin exposure aggregation until forecast/spatial "
            "generalization improves under the same development protocol."
        )
    return f"""# AIRPATH-AI Milestone 3D — end-to-end forecast + spatial validation

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

{_markdown_table(pooled[["pipeline", "n", "unique_target_timestamps", "mae", "rmse", "r2"]])}

### Per horizon

{_markdown_table(per_horizon[["pipeline", "horizon_hours", "n", "mae", "rmse", "r2"]])}

### Per held-out station

{_markdown_table(per_station[["pipeline", "held_out_station", "n", "mae", "rmse", "r2"]])}

Full station×horizon results are saved in `heldout_metrics.csv`.

## D. Error decomposition

{_markdown_table(decomposition)}

`combined_minus_oracle` describes the error change when station forecasts
replace simultaneous observations before the same IDW operation.
`combined_minus_forecast_only` describes the difference between predicting the
held-out station directly and transferring the other five forecasts spatially.
These differences are not additive variance components and do not establish
causality; forecast and spatial errors can reinforce or partially cancel.

## E. Route-segment end-to-end check

Two reproducible station-6-to-station-5 routes (walking and motorbike) depart at
{ROUTE_DEPARTURE_TIME}, using saved validation forecasts from origin
{ROUTE_FORECAST_ORIGIN}. The table shows selected segments under the current
ceiling rule:

{_markdown_table(route_sample[route_columns])}

The reference is hourly oracle IDW at the road midpoint using all six observed
station values. It is the best internal reference available but **is not an
observed road concentration**. Segment error is forecast+IDW minus oracle IDW;
no exposure is aggregated.

## F. Target-time mapping sensitivity

No method interpolates:

- `ceiling`: next hour;
- `floor`: containing hour;
- `nearest`: closest hour, with exact hh:30 ties going forward.

{_markdown_table(mapping_metrics)}

For this development example, mean segment MAE across modes is
**{floor_mae:.3f}** for floor, **{nearest_mae:.3f}** for nearest, and
**{ceiling_mae:.3f} µg/m³** for ceiling. The lowest-error rule is therefore
**{recommended_rule}**.

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

{_markdown_table(correlations)}

Ceiling-rule route errors by qualitative status:

{_markdown_table(status_metrics)}

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

### {decision.classification}

{decision.rationale}

{readiness_scope}

Decision criteria and observed pass/fail values:

```json
{json.dumps(dict(decision.criteria), indent=2)}
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
"""


def generate_validation_outputs(
    *,
    prediction_csv: str | Path = (
        "data/processed/xgboost_forecasting_predictions.csv"
    ),
    network_path: str | Path = (
        "data/processed/road_network/healthyair_pilot_osm.json.gz"
    ),
    output_directory: str | Path = "data/processed/end_to_end_validation",
    report_path: str | Path = "reports/end_to_end_validation.md",
) -> dict[str, object]:
    predictions = pd.read_csv(
        prediction_csv,
        parse_dates=["origin_time", "target_time"],
        low_memory=False,
    )
    heldout = evaluate_heldout_stations(predictions)
    metrics = aggregate_heldout_metrics(heldout)
    decomposition = error_decomposition(metrics)

    network = load_network(network_path)
    segments_by_mode: dict[str, list[SegmentETA]] = {}
    for mode in ("walking", "motorbike"):
        route = generate_candidate_routes(
            network, EXAMPLE_ORIGIN, EXAMPLE_DESTINATION, mode, k=1
        )[0]
        segments_by_mode[mode] = propagate_segment_etas(
            network, route, ROUTE_DEPARTURE_TIME
        )
    route_rows = evaluate_route_mapping_sensitivity(
        predictions,
        segments_by_mode,
        forecasting_origin_time=ROUTE_FORECAST_ORIGIN,
    )
    mapping_metrics = mapping_sensitivity_metrics(route_rows)
    correlations, status_metrics = reliability_error_relationship(
        heldout, route_rows
    )
    station_reliability = (
        heldout.groupby("held_out_station", as_index=False)
        .agg(
            combined_mae=("forecast_spatial_absolute_error", "mean"),
            nearest_station_distance_km=("nearest_station_distance_km", "first"),
        )
    )
    decision = decide_readiness(metrics)

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    heldout.to_csv(output_directory / "heldout_predictions.csv", index=False)
    metrics.to_csv(output_directory / "heldout_metrics.csv", index=False)
    decomposition.to_csv(output_directory / "error_decomposition.csv", index=False)
    route_rows.to_csv(output_directory / "route_segment_validation.csv", index=False)
    mapping_metrics.to_csv(
        output_directory / "mapping_sensitivity.csv", index=False
    )
    correlations.to_csv(
        output_directory / "reliability_error_correlations.csv", index=False
    )
    status_metrics.to_csv(
        output_directory / "reliability_status_errors.csv", index=False
    )
    (output_directory / "readiness_decision.json").write_text(
        json.dumps(asdict(decision), indent=2),
        encoding="utf-8",
    )
    _plot_outputs(
        metrics,
        decomposition,
        mapping_metrics,
        station_reliability,
        output_directory,
    )

    ceiling = route_rows.loc[route_rows["mapping_rule"].eq("ceiling")]
    sample = pd.concat(
        [
            group.head(3)
            for _, group in ceiling.groupby("mode", sort=True)
        ]
        + [
            group.tail(1)
            for _, group in ceiling.groupby("mode", sort=True)
        ],
        ignore_index=True,
    )
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        _render_report(
            metrics,
            decomposition,
            sample,
            mapping_metrics,
            correlations,
            status_metrics,
            decision,
        ),
        encoding="utf-8",
    )
    return {
        "heldout": heldout,
        "metrics": metrics,
        "decomposition": decomposition,
        "route_rows": route_rows,
        "mapping_metrics": mapping_metrics,
        "correlations": correlations,
        "status_metrics": status_metrics,
        "decision": decision,
        "route_sample": sample,
    }


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--predictions",
        default="data/processed/xgboost_forecasting_predictions.csv",
    )
    parser.add_argument(
        "--network",
        default="data/processed/road_network/healthyair_pilot_osm.json.gz",
    )
    parser.add_argument(
        "--output-directory",
        default="data/processed/end_to_end_validation",
    )
    parser.add_argument(
        "--report", default="reports/end_to_end_validation.md"
    )
    return parser.parse_args()


def main() -> None:
    arguments = _parse_arguments()
    outputs = generate_validation_outputs(
        prediction_csv=arguments.predictions,
        network_path=arguments.network,
        output_directory=arguments.output_directory,
        report_path=arguments.report,
    )
    pooled = outputs["metrics"].loc[
        outputs["metrics"]["aggregation"].eq("pooled")
    ]
    print(pooled.to_string(index=False))
    print(outputs["decision"])


if __name__ == "__main__":
    main()
