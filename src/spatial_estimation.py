"""Spatial PM2.5 estimation from externally supplied station values.

The estimators in this module are deliberately independent of the forecasting
pipeline.  At a target time, callers supply either observed station values
(oracle evaluation) or forecasted station values (deployment).  The spatial
algorithm never reads future observations from the HealthyAir dataset.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


EARTH_RADIUS_KM: Final[float] = 6371.0088
ZERO_DISTANCE_TOLERANCE_KM: Final[float] = 1e-9
SPATIAL_METHODS: Final[tuple[tuple[str, float | None], ...]] = (
    ("nearest", None),
    ("idw", 1.0),
    ("idw", 2.0),
)
DEVELOPMENT_SPLITS: Final[tuple[str, ...]] = ("train", "validation")


@dataclass(frozen=True)
class StationGeometry:
    """Authoritatively documented HealthyAir station metadata."""

    station_id: int
    latitude: float
    longitude: float
    station_type: str
    location: str


# Source: Rakholia et al. (2023), Data in Brief 46, 108774, Table 1,
# doi:10.1016/j.dib.2022.108774 (PMC9720438).  The paper's table headers appear
# transposed: values near 10.x are geographic latitude and values near 106.x
# are longitude for HCMC.  The station numbers and values are copied exactly.
STATION_GEOMETRY: Final[tuple[StationGeometry, ...]] = (
    StationGeometry(
        1,
        10.86994333,
        106.7960143,
        "Urban background: Industry + Traffic + Residential",
        "Vietnam National University, Linh Trung ward, Thu Duc city, HCMC",
    ),
    StationGeometry(
        2,
        10.74097081,
        106.6171323,
        "Traffic",
        "20 Nguyen Trong Tri street, An Lac ward, Binh Tan district, HCMC",
    ),
    StationGeometry(
        3,
        10.81621227,
        106.6204143,
        "Industry",
        "Tan Binh industrial zone, Tay Thanh ward, Tan Phu district, HCMC",
    ),
    StationGeometry(
        4,
        10.81584553,
        106.7174282,
        "Residential",
        "49 Thanh Da street, Ward 27, Binh Thanh district, HCMC",
    ),
    StationGeometry(
        5,
        10.77636612,
        106.6878094,
        "Traffic",
        "268 Nguyen Dinh Chieu street, Ward 6, District 3, HCMC",
    ),
    StationGeometry(
        6,
        10.78047163,
        106.6594579,
        "Traffic + Residential",
        "MM18 Truong Son street, Ward 14, District 10, HCMC",
    ),
)
STATION_BY_ID: Final[dict[int, StationGeometry]] = {
    station.station_id: station for station in STATION_GEOMETRY
}
COORDINATE_SOURCE: Final[str] = (
    "Rakholia et al. (2023), Data in Brief 46, 108774, Table 1, "
    "https://doi.org/10.1016/j.dib.2022.108774"
)


@dataclass(frozen=True)
class SpatialEstimate:
    """One estimate plus non-probabilistic spatial reliability proxies."""

    predicted_pm25: float
    target_time: pd.Timestamp
    method: str
    power: float | None
    nearest_station_id: int
    nearest_distance_km: float
    second_nearest_distance_km: float | None
    contributing_stations: int
    maximum_weight: float
    weight_concentration: float
    effective_station_count: float


def station_geometry_frame() -> pd.DataFrame:
    """Return the six documented stations as a deterministic table."""
    frame = pd.DataFrame(asdict(station) for station in STATION_GEOMETRY)
    frame["coordinate_source"] = COORDINATE_SOURCE
    return frame


def haversine_distance_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    """Great-circle distance between two WGS84 latitude/longitude pairs."""
    values = np.asarray(
        [latitude_a, longitude_a, latitude_b, longitude_b], dtype=float
    )
    if not np.isfinite(values).all():
        raise ValueError("Coordinates must be finite numbers.")
    if not (-90 <= latitude_a <= 90 and -90 <= latitude_b <= 90):
        raise ValueError("Latitude must be between -90 and 90 degrees.")
    if not (-180 <= longitude_a <= 180 and -180 <= longitude_b <= 180):
        raise ValueError("Longitude must be between -180 and 180 degrees.")

    lat_a, lat_b = np.radians([latitude_a, latitude_b])
    delta_lat = lat_b - lat_a
    delta_lon = np.radians(longitude_b - longitude_a)
    haversine = (
        np.sin(delta_lat / 2) ** 2
        + np.cos(lat_a) * np.cos(lat_b) * np.sin(delta_lon / 2) ** 2
    )
    haversine = float(np.clip(haversine, 0.0, 1.0))
    return float(
        2 * EARTH_RADIUS_KM * np.arctan2(np.sqrt(haversine), np.sqrt(1 - haversine))
    )


def pairwise_station_distances() -> pd.DataFrame:
    """Return each unique pairwise HealthyAir station distance."""
    rows: list[dict[str, float | int]] = []
    for index, first in enumerate(STATION_GEOMETRY):
        for second in STATION_GEOMETRY[index + 1 :]:
            rows.append(
                {
                    "station_a": first.station_id,
                    "station_b": second.station_id,
                    "distance_km": haversine_distance_km(
                        first.latitude,
                        first.longitude,
                        second.latitude,
                        second.longitude,
                    ),
                }
            )
    return pd.DataFrame(rows)


def _normalise_station_values(
    station_values: Mapping[int | str, float],
) -> dict[int, float]:
    if not station_values:
        raise ValueError("At least one station value is required.")
    normalised: dict[int, float] = {}
    for raw_station_id, raw_value in station_values.items():
        try:
            station_id = int(raw_station_id)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid station ID: {raw_station_id!r}") from error
        if station_id not in STATION_BY_ID:
            raise ValueError(f"Unknown HealthyAir station ID: {station_id}")
        if station_id in normalised:
            raise ValueError(f"Duplicate normalised station ID: {station_id}")
        value = float(raw_value)
        if not np.isfinite(value):
            raise ValueError(f"Station {station_id} PM2.5 must be finite.")
        normalised[station_id] = value
    return normalised


def _normalise_target_time(target_time: object) -> pd.Timestamp:
    try:
        timestamp = pd.Timestamp(target_time)
    except (TypeError, ValueError) as error:
        raise ValueError("target_time must be a valid exact timestamp.") from error
    if pd.isna(timestamp):
        raise ValueError("target_time must not be missing.")
    return timestamp


def _distances_to_available_stations(
    latitude: float,
    longitude: float,
    station_values: Mapping[int, float],
) -> list[tuple[int, float, float]]:
    # Calling haversine validates the target coordinate as well.
    distances = [
        (
            station_id,
            haversine_distance_km(
                latitude,
                longitude,
                STATION_BY_ID[station_id].latitude,
                STATION_BY_ID[station_id].longitude,
            ),
            value,
        )
        for station_id, value in station_values.items()
    ]
    return sorted(distances, key=lambda item: (item[1], item[0]))


def estimate_with_diagnostics(
    latitude: float,
    longitude: float,
    target_time: object,
    station_values: Mapping[int | str, float],
    *,
    method: str = "idw",
    power: float = 2.0,
) -> SpatialEstimate:
    """Estimate PM2.5 and return geometry-based reliability proxies.

    `station_values` is the only concentration input.  It can contain actual
    observations (oracle mode) or forecasts (deployment mode).  Missing station
    values should be omitted rather than represented by NaN.
    """
    timestamp = _normalise_target_time(target_time)
    values = _normalise_station_values(station_values)
    distances = _distances_to_available_stations(latitude, longitude, values)
    nearest_station_id, nearest_distance, nearest_value = distances[0]
    second_distance = distances[1][1] if len(distances) > 1 else None

    if method not in {"nearest", "idw"}:
        raise ValueError("method must be 'nearest' or 'idw'.")
    if method == "idw" and (not np.isfinite(power) or power <= 0):
        raise ValueError("IDW power must be a positive finite value.")

    coincident = [
        item for item in distances if item[1] <= ZERO_DISTANCE_TOLERANCE_KM
    ]
    if coincident:
        # Coordinates are unique, but averaging is safe if metadata ever changes.
        prediction = float(np.mean([item[2] for item in coincident]))
        weights = np.zeros(len(distances), dtype=float)
        for item in coincident:
            weights[distances.index(item)] = 1.0 / len(coincident)
    elif method == "nearest":
        prediction = float(nearest_value)
        weights = np.zeros(len(distances), dtype=float)
        weights[0] = 1.0
    else:
        raw_weights = np.asarray(
            [1.0 / (item[1] ** power) for item in distances], dtype=float
        )
        weights = raw_weights / raw_weights.sum()
        prediction = float(
            np.dot(weights, np.asarray([item[2] for item in distances], dtype=float))
        )

    concentration = float(np.square(weights).sum())
    return SpatialEstimate(
        predicted_pm25=prediction,
        target_time=timestamp,
        method=method,
        power=None if method == "nearest" else float(power),
        nearest_station_id=nearest_station_id,
        nearest_distance_km=float(nearest_distance),
        second_nearest_distance_km=(
            None if second_distance is None else float(second_distance)
        ),
        contributing_stations=int(np.count_nonzero(weights > 0)),
        maximum_weight=float(weights.max()),
        weight_concentration=concentration,
        effective_station_count=float(1.0 / concentration),
    )


def estimate_pm25(
    latitude: float,
    longitude: float,
    target_time: object,
    station_values: Mapping[int | str, float],
    *,
    method: str = "idw",
    power: float = 2.0,
) -> float:
    """Pure spatial interface returning PM2.5 at location X and exact time T."""
    return estimate_with_diagnostics(
        latitude,
        longitude,
        target_time,
        station_values,
        method=method,
        power=power,
    ).predicted_pm25


def estimate_oracle_pm25(
    latitude: float,
    longitude: float,
    target_time: object,
    observed_station_values: Mapping[int | str, float],
    *,
    method: str = "idw",
    power: float = 2.0,
) -> float:
    """Mode A: use caller-supplied observations to isolate spatial error."""
    return estimate_pm25(
        latitude,
        longitude,
        target_time,
        observed_station_values,
        method=method,
        power=power,
    )


def estimate_deployment_pm25(
    latitude: float,
    longitude: float,
    target_time: object,
    forecasted_station_values: Mapping[int | str, float],
    *,
    method: str = "idw",
    power: float = 2.0,
) -> float:
    """Mode B: use forecasts supplied by the forecasting layer.

    This function has no dataset argument and cannot retrieve observed future
    PM2.5.  It intentionally delegates to the same spatial algorithm as oracle
    mode.
    """
    return estimate_pm25(
        latitude,
        longitude,
        target_time,
        forecasted_station_values,
        method=method,
        power=power,
    )


def regression_metrics(actual: Sequence[float], predicted: Sequence[float]) -> dict[str, float]:
    """Return MAE, RMSE, and R-squared using a shared finite sample."""
    actual_array = np.asarray(actual, dtype=float)
    predicted_array = np.asarray(predicted, dtype=float)
    if actual_array.shape != predicted_array.shape or actual_array.size == 0:
        raise ValueError("Actual and predicted values require equal non-empty shapes.")
    if not (np.isfinite(actual_array).all() and np.isfinite(predicted_array).all()):
        raise ValueError("Metrics require finite actual and predicted values.")
    return {
        "mae": float(mean_absolute_error(actual_array, predicted_array)),
        "rmse": float(np.sqrt(mean_squared_error(actual_array, predicted_array))),
        "r2": float(r2_score(actual_array, predicted_array)),
    }


def _complete_development_pivot(
    clean: pd.DataFrame,
    development_splits: Sequence[str] = DEVELOPMENT_SPLITS,
) -> pd.DataFrame:
    required = {"date", "Station_No", "PM2.5", "temporal_split"}
    missing = required.difference(clean.columns)
    if missing:
        raise ValueError("Spatial evaluation missing columns: " + ", ".join(sorted(missing)))
    prepared = clean.copy()
    prepared["date"] = pd.to_datetime(prepared["date"], errors="raise")
    if prepared.duplicated(["date", "Station_No"]).any():
        raise ValueError("Duplicate station-timestamp rows invalidate spatial LOSO.")
    prepared = prepared.loc[prepared["temporal_split"].isin(development_splits)]
    expected_ids = set(STATION_BY_ID)
    observed_ids = set(prepared["Station_No"].dropna().astype(int).unique())
    if not expected_ids.issubset(observed_ids):
        raise ValueError("All six HealthyAir stations are required for LOSO evaluation.")
    pivot = prepared.pivot(index="date", columns="Station_No", values="PM2.5")
    pivot.columns = pivot.columns.astype(int)
    return pivot.reindex(columns=sorted(expected_ids)).dropna(how="any").sort_index()


def _model_label(method: str, power: float | None) -> str:
    if method == "nearest":
        return "nearest"
    return f"idw_p{int(power) if float(power).is_integer() else power}"


def evaluate_leave_one_station_out(
    clean: pd.DataFrame,
    *,
    development_splits: Sequence[str] = DEVELOPMENT_SPLITS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evaluate spatial generalisation using complete-case LOSO timestamps."""
    pivot = _complete_development_pivot(clean, development_splits)
    rows: list[dict[str, object]] = []
    for target_time, observations in pivot.iterrows():
        for held_out_id in sorted(STATION_BY_ID):
            target_station = STATION_BY_ID[held_out_id]
            available = {
                int(station_id): float(value)
                for station_id, value in observations.items()
                if int(station_id) != held_out_id
            }
            for method, power in SPATIAL_METHODS:
                estimate = estimate_with_diagnostics(
                    target_station.latitude,
                    target_station.longitude,
                    target_time,
                    available,
                    method=method,
                    power=2.0 if power is None else power,
                )
                rows.append(
                    {
                        "target_time": target_time,
                        "held_out_station": held_out_id,
                        "actual_pm25": float(observations[held_out_id]),
                        "predicted_pm25": estimate.predicted_pm25,
                        "model": _model_label(method, power),
                        "nearest_distance_km": estimate.nearest_distance_km,
                        "second_nearest_distance_km": estimate.second_nearest_distance_km,
                        "contributing_stations": estimate.contributing_stations,
                        "maximum_weight": estimate.maximum_weight,
                        "weight_concentration": estimate.weight_concentration,
                        "effective_station_count": estimate.effective_station_count,
                    }
                )
    predictions = pd.DataFrame(rows)
    metric_rows: list[dict[str, object]] = []
    for model in predictions["model"].drop_duplicates():
        model_rows = predictions.loc[predictions["model"].eq(model)]
        for station_id, group in model_rows.groupby("held_out_station", sort=True):
            metric_rows.append(
                {
                    "model": model,
                    "held_out_station": int(station_id),
                    "n": len(group),
                    "unique_timestamps": group["target_time"].nunique(),
                    **regression_metrics(group["actual_pm25"], group["predicted_pm25"]),
                }
            )
        metric_rows.append(
            {
                "model": model,
                "held_out_station": "ALL",
                "n": len(model_rows),
                "unique_timestamps": model_rows["target_time"].nunique(),
                **regression_metrics(
                    model_rows["actual_pm25"], model_rows["predicted_pm25"]
                ),
            }
        )
    metrics = pd.DataFrame(metric_rows)
    return predictions, metrics


def temporal_robustness_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    """Score the declared models in chronological early/middle/late thirds."""
    times = pd.Series(predictions["target_time"].drop_duplicates().sort_values())
    if len(times) < 3:
        raise ValueError("At least three timestamps are needed for temporal robustness.")
    period_by_time: dict[pd.Timestamp, str] = {}
    for period, index_chunk in zip(
        ("early", "middle", "late"),
        np.array_split(np.arange(len(times)), 3),
        strict=True,
    ):
        for index in index_chunk:
            period_by_time[pd.Timestamp(times.iloc[index])] = period
    scored = predictions.copy()
    scored["period"] = scored["target_time"].map(period_by_time)
    rows: list[dict[str, object]] = []
    for (period, model), group in scored.groupby(["period", "model"], sort=False):
        rows.append(
            {
                "period": period,
                "period_start": group["target_time"].min(),
                "period_end": group["target_time"].max(),
                "model": model,
                "n": len(group),
                "unique_timestamps": group["target_time"].nunique(),
                **regression_metrics(group["actual_pm25"], group["predicted_pm25"]),
            }
        )
    order = pd.CategoricalDtype(["early", "middle", "late"], ordered=True)
    result = pd.DataFrame(rows)
    result["period"] = result["period"].astype(order)
    return result.sort_values(["period", "model"]).reset_index(drop=True)


def held_out_reliability_diagnostics(predictions: pd.DataFrame) -> pd.DataFrame:
    """Return one geometry diagnostic row per held-out station and method."""
    columns = [
        "model",
        "held_out_station",
        "nearest_distance_km",
        "second_nearest_distance_km",
        "contributing_stations",
        "maximum_weight",
        "weight_concentration",
        "effective_station_count",
    ]
    return (
        predictions.loc[:, columns]
        .drop_duplicates()
        .sort_values(["model", "held_out_station"])
        .reset_index(drop=True)
    )


def _convex_hull(points: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    """Andrew monotone-chain hull in longitude/latitude plotting space."""
    unique = sorted(set(points))
    if len(unique) <= 1:
        return unique

    def cross(
        origin: tuple[float, float],
        first: tuple[float, float],
        second: tuple[float, float],
    ) -> float:
        return (first[0] - origin[0]) * (second[1] - origin[1]) - (
            first[1] - origin[1]
        ) * (second[0] - origin[0])

    lower: list[tuple[float, float]] = []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper: list[tuple[float, float]] = []
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def hull_area_km2(station_ids: Sequence[int]) -> float:
    """Approximate monitoring convex-hull area in a local planar projection."""
    selected = [STATION_BY_ID[int(station_id)] for station_id in station_ids]
    mean_latitude = float(np.mean([station.latitude for station in selected]))
    points = [
        (
            EARTH_RADIUS_KM
            * np.radians(station.longitude)
            * np.cos(np.radians(mean_latitude)),
            EARTH_RADIUS_KM * np.radians(station.latitude),
        )
        for station in selected
    ]
    hull = _convex_hull(points)
    if len(hull) < 3:
        return 0.0
    area = 0.0
    for first, second in zip(hull, hull[1:] + hull[:1]):
        area += first[0] * second[1] - second[0] * first[1]
    return abs(area) / 2.0


def _plot_station_geometry(output_path: Path) -> None:
    frame = station_geometry_frame()
    all_hull = _convex_hull(list(zip(frame["longitude"], frame["latitude"])))
    pilot = frame.loc[frame["station_id"].isin([2, 3, 4, 5, 6])]
    pilot_hull = _convex_hull(list(zip(pilot["longitude"], pilot["latitude"])))

    fig, axis = plt.subplots(figsize=(8, 7))
    for hull, color, label in (
        (all_hull, "#5c6bc0", "All-station convex hull"),
        (pilot_hull, "#2e7d32", "Recommended pilot support (stations 2–6)"),
    ):
        closed = hull + hull[:1]
        axis.plot(
            [point[0] for point in closed],
            [point[1] for point in closed],
            color=color,
            linewidth=1.8,
            label=label,
        )
    axis.scatter(
        frame["longitude"],
        frame["latitude"],
        s=75,
        color="#c62828",
        edgecolor="white",
        zorder=3,
    )
    for row in frame.itertuples():
        axis.annotate(
            f"S{row.station_id}",
            (row.longitude, row.latitude),
            xytext=(5, 5),
            textcoords="offset points",
            fontweight="bold",
        )
    axis.set(
        xlabel="Longitude (°E)",
        ylabel="Latitude (°N)",
        title="HealthyAir HCMC station geometry (no basemap)",
    )
    axis.grid(alpha=0.25)
    axis.legend(loc="best")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _grid_estimates(
    station_values: Mapping[int, float],
    target_time: pd.Timestamp,
    *,
    grid_size: int = 70,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    frame = station_geometry_frame()
    longitude = np.linspace(frame["longitude"].min(), frame["longitude"].max(), grid_size)
    latitude = np.linspace(frame["latitude"].min(), frame["latitude"].max(), grid_size)
    lon_grid, lat_grid = np.meshgrid(longitude, latitude)
    prediction = np.empty_like(lon_grid)
    nearest = np.empty_like(lon_grid)
    concentration = np.empty_like(lon_grid)
    for row, column in np.ndindex(lon_grid.shape):
        estimate = estimate_with_diagnostics(
            float(lat_grid[row, column]),
            float(lon_grid[row, column]),
            target_time,
            station_values,
            method="idw",
            power=2.0,
        )
        prediction[row, column] = estimate.predicted_pm25
        nearest[row, column] = estimate.nearest_distance_km
        concentration[row, column] = estimate.weight_concentration
    return lon_grid, lat_grid, prediction, nearest, concentration


def _plot_representative_prediction(
    pivot: pd.DataFrame,
    output_path: Path,
) -> tuple[pd.Timestamp, dict[int, float]]:
    target_time = pd.Timestamp(pivot.index[len(pivot) // 2])
    station_values = {
        int(station_id): float(value)
        for station_id, value in pivot.loc[target_time].items()
    }
    lon, lat, prediction, nearest, concentration = _grid_estimates(
        station_values, target_time
    )
    frame = station_geometry_frame()
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharex=True, sharey=True)
    panels = (
        (prediction, "IDW p=2 PM2.5 estimate", "µg/m³", "viridis"),
        (nearest, "Nearest-station distance proxy", "km", "magma"),
        (concentration, "IDW weight concentration proxy", "Σ normalized weight²", "cividis"),
    )
    for axis, (values, title, colorbar_label, color_map) in zip(axes, panels):
        image = axis.contourf(lon, lat, values, levels=18, cmap=color_map)
        axis.scatter(
            frame["longitude"],
            frame["latitude"],
            color="white",
            edgecolor="black",
            s=35,
        )
        for station in frame.itertuples():
            axis.annotate(
                str(station.station_id),
                (station.longitude, station.latitude),
                xytext=(3, 3),
                textcoords="offset points",
                fontsize=8,
            )
        axis.set_title(title)
        axis.set_xlabel("Longitude (°E)")
        axis.grid(alpha=0.12)
        fig.colorbar(image, ax=axis, shrink=0.82, label=colorbar_label)
    axes[0].set_ylabel("Latitude (°N)")
    fig.suptitle(
        f"Representative observed-station oracle at {target_time:%Y-%m-%d %H:%M} "
        "(hourly support only)",
        y=1.02,
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return target_time, station_values


def _markdown_table(frame: pd.DataFrame, digits: int = 3) -> str:
    display = frame.copy()
    numeric = display.select_dtypes(include=[np.number]).columns
    display[numeric] = display[numeric].round(digits)
    return display.to_markdown(index=False)


def _write_report(
    output_path: Path,
    geometry: pd.DataFrame,
    distances: pd.DataFrame,
    metrics: pd.DataFrame,
    temporal: pd.DataFrame,
    reliability: pd.DataFrame,
    example_time: pd.Timestamp,
    example_values: Mapping[int, float],
) -> None:
    pooled = metrics.loc[metrics["held_out_station"].eq("ALL")].copy()
    held_out = metrics.loc[~metrics["held_out_station"].eq("ALL")].copy()
    nearest_by_station = (
        distances.groupby("station_a")["distance_km"].min().to_dict()
    )
    # The preceding grouped view misses pairs where a station appears as station_b.
    nearest_distances: dict[int, float] = {}
    for station_id in STATION_BY_ID:
        related = distances.loc[
            distances["station_a"].eq(station_id)
            | distances["station_b"].eq(station_id),
            "distance_km",
        ]
        nearest_distances[station_id] = float(related.min())
    all_area = hull_area_km2(sorted(STATION_BY_ID))
    pilot_area = hull_area_km2([2, 3, 4, 5, 6])
    max_distance = float(distances["distance_km"].max())
    min_distance = float(distances["distance_km"].min())
    period_change = temporal.pivot(index="model", columns="period", values="mae")
    period_change["late_vs_early_mae_change_pct"] = (
        100 * (period_change["late"] - period_change["early"]) / period_change["early"]
    )
    example_location = (
        float(np.mean([STATION_BY_ID[5].latitude, STATION_BY_ID[6].latitude])),
        float(np.mean([STATION_BY_ID[5].longitude, STATION_BY_ID[6].longitude])),
    )
    example_estimate = estimate_with_diagnostics(
        example_location[0],
        example_location[1],
        example_time,
        example_values,
        method="idw",
        power=2,
    )
    station_values_text = ", ".join(
        f"S{station_id}={value:.2f}" for station_id, value in sorted(example_values.items())
    )

    report = f"""# AIRPATH-AI Milestone 3A — spatial PM2.5 estimation foundation

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

{_markdown_table(geometry[["station_id", "latitude", "longitude", "station_type", "location"]], 8)}

The station map is `reports/figures/spatial_station_map.png`; no external basemap
or geographic dataset is used.

## B. Spatial coverage and geometry limitations

Pairwise separation ranges from **{min_distance:.2f} km** (stations 5–6) to
**{max_distance:.2f} km** (stations 1–2). The six-station convex hull covers
approximately **{all_area:.1f} km²**. Stations 2–6 form a denser
central/western support polygon of approximately **{pilot_area:.1f} km²**;
station 1 is a relatively isolated north-eastern point.

{_markdown_table(distances, 3)}

Nearest-neighbour support by station:

{_markdown_table(pd.DataFrame([{{"station_id": key, "nearest_other_station_km": value}} for key, value in nearest_distances.items()]), 3)}

The geometry samples traffic, residential, industrial, and mixed contexts, but
six points are not sufficient for city-wide road-scale interpolation. The
network has no replicated local neighbourhoods, substantial edge/extrapolation
regions, a 24 km longest baseline, and no covariates for roads, land use,
elevation, meteorology, or local emission sources. IDW encodes smoothness by
distance only; it cannot represent barriers or near-road gradients.

## C–E. LOSO baseline results

Pooled development-period results:

{_markdown_table(pooled[["model", "n", "unique_timestamps", "mae", "rmse", "r2"]], 4)}

`nearest` is the nearest-station baseline. `idw_p1` and `idw_p2` use
`w_i = 1 / d_i^p`, with exact zero-distance queries returning the coincident
station value safely. The two IDW powers were declared in advance; there was no
large hyperparameter search.

## F. Held-out station performance

{_markdown_table(held_out[["model", "held_out_station", "n", "unique_timestamps", "mae", "rmse", "r2"]], 4)}

LOSO is genuine spatial generalisation: the held-out station never contributes
to its estimate. Negative R² values mean the interpolator performs worse than
predicting that held-out sample set's mean; they are retained rather than hidden.

## G. Temporal robustness

The common complete-case development timestamps were divided chronologically
into equal early, middle, and late thirds. These periods are diagnostics only
and do not tune the methods.

{_markdown_table(temporal[["period", "period_start", "period_end", "model", "n", "unique_timestamps", "mae", "rmse", "r2"]], 4)}

Late-versus-early MAE change:

{_markdown_table(period_change.reset_index()[["model", "early", "middle", "late", "late_vs_early_mae_change_pct"]], 3)}

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

{_markdown_table(reliability, 4)}

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

At the representative existing hourly timestamp **{example_time:%Y-%m-%d %H:%M}**,
the supplied oracle values are `{station_values_text}` µg/m³. At
X=({example_location[0]:.6f}, {example_location[1]:.6f}), IDW p=2 produces
**{example_estimate.predicted_pm25:.2f} µg/m³**. The architecture accepts an exact
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
5. The forecasting test set was previously exposed in Milestone 2C and was
   deliberately not reused here; no untouched final spatial test is claimed.
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
"""
    output_path.write_text(report, encoding="utf-8")


def generate_analysis_outputs(
    clean_csv: str | Path = "data/processed/airquality_hcmc_clean.csv",
    report_root: str | Path = "reports",
) -> dict[str, pd.DataFrame]:
    """Run the development-only spatial evaluation and save all artifacts."""
    clean = pd.read_csv(clean_csv, parse_dates=["date"])
    report_root = Path(report_root)
    table_dir = report_root / "tables"
    figure_dir = report_root / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    geometry = station_geometry_frame()
    distances = pairwise_station_distances()
    predictions, metrics = evaluate_leave_one_station_out(clean)
    temporal = temporal_robustness_metrics(predictions)
    reliability = held_out_reliability_diagnostics(predictions)
    held_out = metrics.loc[~metrics["held_out_station"].eq("ALL")].copy()
    pivot = _complete_development_pivot(clean)

    geometry.to_csv(table_dir / "spatial_station_geometry.csv", index=False)
    distances.to_csv(table_dir / "spatial_pairwise_distances.csv", index=False)
    metrics.to_csv(table_dir / "spatial_cv_metrics.csv", index=False)
    held_out.to_csv(table_dir / "spatial_heldout_results.csv", index=False)
    temporal.to_csv(table_dir / "spatial_temporal_robustness.csv", index=False)
    reliability.to_csv(
        table_dir / "spatial_reliability_diagnostics.csv", index=False
    )
    _plot_station_geometry(figure_dir / "spatial_station_map.png")
    example_time, example_values = _plot_representative_prediction(
        pivot, figure_dir / "spatial_prediction_example.png"
    )
    _write_report(
        report_root / "spatial_estimation.md",
        geometry,
        distances,
        metrics,
        temporal,
        reliability,
        example_time,
        example_values,
    )
    return {
        "geometry": geometry,
        "distances": distances,
        "predictions": predictions,
        "metrics": metrics,
        "temporal": temporal,
        "reliability": reliability,
    }


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clean-csv",
        default="data/processed/airquality_hcmc_clean.csv",
        help="Existing processed HealthyAir CSV (read-only).",
    )
    parser.add_argument("--report-root", default="reports")
    return parser.parse_args()


def main() -> None:
    arguments = _parse_arguments()
    outputs = generate_analysis_outputs(arguments.clean_csv, arguments.report_root)
    pooled = outputs["metrics"].loc[
        outputs["metrics"]["held_out_station"].eq("ALL")
    ]
    print(pooled.to_string(index=False))


if __name__ == "__main__":
    main()
