"""Connect route ETAs, frozen station forecasts, and spatial PM2.5 estimation.

Current HealthyAir forecasts support exact hourly targets at t+1h, t+2h, and
t+3h. Route midpoint ETAs are therefore mapped explicitly by ceiling to the next
hour: an ETA at 17:03 requests the 18:00 hourly forecast. No interpolation or
sub-hourly observation is created.
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Mapping, Protocol, Sequence

import numpy as np
import pandas as pd

from .eta_engine import SegmentETA, propagate_segment_etas
from .road_network import RoadNetwork, load_network
from .route_candidates import (
    EXAMPLE_DESTINATION,
    EXAMPLE_ORIGIN,
    CandidateRoute,
    generate_candidate_routes,
)
from .spatial_estimation import SpatialEstimate, estimate_with_diagnostics


HOURLY_RESOLUTION: Final[pd.Timedelta] = pd.Timedelta(hours=1)
DEFAULT_SUPPORTED_HORIZONS: Final[tuple[int, ...]] = (1, 2, 3)
DEFAULT_SPATIAL_METHOD: Final[str] = "idw"
DEFAULT_IDW_POWER: Final[float] = 1.0
EXAMPLE_FORECASTING_ORIGIN: Final[pd.Timestamp] = pd.Timestamp(
    "2022-02-28 06:00:00"
)


class UnsupportedTargetTimeError(ValueError):
    """Raised when a mapped target is outside the frozen forecast horizons."""


class StationValueError(ValueError):
    """Raised when station-value provenance or timestamps are inconsistent."""


class StationForecaster(Protocol):
    station_ids: tuple[str, ...]
    models: Mapping[int, object]

    def predict_pm25(
        self,
        station_or_location: str | int,
        target_time: pd.Timestamp | str,
        *,
        prediction_time: pd.Timestamp | str,
        pm25_lags: Mapping[int, float],
        temperature: float | None = None,
        humidity: float | None = None,
    ) -> float: ...


@dataclass(frozen=True)
class TargetTimeMapping:
    requested_target_time: pd.Timestamp
    supported_target_time: pd.Timestamp
    forecasting_origin_time: pd.Timestamp
    available_resolution: str
    mapping_method: str
    is_exact: bool
    mapping_offset_seconds: float
    forecast_horizon_hours: int
    supported: bool
    status: str

    def require_supported(self) -> None:
        if not self.supported:
            raise UnsupportedTargetTimeError(
                f"{self.status}: requested={self.requested_target_time.isoformat()}, "
                f"mapped={self.supported_target_time.isoformat()}, "
                f"horizon={self.forecast_horizon_hours}h"
            )


@dataclass(frozen=True)
class StationLagBundle:
    """Exact pre-origin lag values accepted by deployment mode."""

    forecasting_origin_time: pd.Timestamp
    values_by_station: Mapping[int, Mapping[int, float]]
    source_times_by_station: Mapping[int, Mapping[int, pd.Timestamp]]


@dataclass(frozen=True)
class StationValueBundle:
    """Station values with an explicit target and provenance."""

    target_time: pd.Timestamp
    values: Mapping[int, float]
    source_mode: str


@dataclass(frozen=True)
class SegmentPM25Record:
    route_id: str
    segment_id: str
    segment_index: int
    mode: str
    latitude: float
    longitude: float
    segment_geometry: tuple[tuple[float, float], ...]
    segment_duration_seconds: float
    route_departure_time: pd.Timestamp
    segment_entry_time: pd.Timestamp
    requested_target_time: pd.Timestamp
    supported_target_time: pd.Timestamp
    segment_endpoint_arrival_time: pd.Timestamp
    forecasting_origin_time: pd.Timestamp
    forecast_horizon_hours: int
    target_time_mapping_method: str
    target_time_is_exact: bool
    mapping_offset_seconds: float
    station_values_target_time: pd.Timestamp
    station_value_source: str
    station_values_used: Mapping[int, float]
    predicted_pm25: float
    spatial_method: str
    spatial_power: float
    nearest_station_id: int
    nearest_station_distance_km: float
    second_nearest_station_distance_km: float | None
    contributing_station_count: int
    maximum_idw_weight: float
    idw_weight_concentration: float
    effective_station_count: float
    reliability_status: str

    def to_dict(self, *, serializable: bool = True) -> dict[str, object]:
        payload = asdict(self)
        if not serializable:
            return payload
        payload["segment_geometry"] = [
            list(point) for point in self.segment_geometry
        ]
        payload["station_values_used"] = {
            str(station_id): value
            for station_id, value in sorted(self.station_values_used.items())
        }
        for key in (
            "route_departure_time",
            "segment_entry_time",
            "requested_target_time",
            "supported_target_time",
            "segment_endpoint_arrival_time",
            "forecasting_origin_time",
            "station_values_target_time",
        ):
            payload[key] = pd.Timestamp(payload[key]).isoformat()
        return payload


def _normalise_timestamp(value: object, label: str) -> pd.Timestamp:
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be a valid timestamp.") from error
    if pd.isna(timestamp):
        raise ValueError(f"{label} must not be missing.")
    return timestamp


def _is_exact_hour(timestamp: pd.Timestamp) -> bool:
    return (
        timestamp.minute == 0
        and timestamp.second == 0
        and timestamp.microsecond == 0
        and timestamp.nanosecond == 0
    )


def map_target_time(
    requested_target_time: object,
    forecasting_origin_time: object,
    *,
    available_resolution: str = "hourly",
    supported_horizons: Sequence[int] = DEFAULT_SUPPORTED_HORIZONS,
) -> TargetTimeMapping:
    """Map an ETA to the next exact hour without interpolation.

    Ceiling is conservative in time: the supported target is never earlier than
    the requested passage time. Exact hourly ETAs remain unchanged.
    """
    requested = _normalise_timestamp(requested_target_time, "requested_target_time")
    origin = _normalise_timestamp(
        forecasting_origin_time, "forecasting_origin_time"
    )
    if available_resolution != "hourly":
        raise ValueError("Current integration supports declared 'hourly' resolution.")
    if not _is_exact_hour(origin):
        raise ValueError("forecasting_origin_time must be an exact hour.")
    if requested.tzinfo != origin.tzinfo:
        raise ValueError(
            "requested target and forecasting origin must use matching timezones."
        )
    horizons = tuple(sorted({int(horizon) for horizon in supported_horizons}))
    if not horizons or any(horizon <= 0 for horizon in horizons):
        raise ValueError("Supported horizons must be positive integer hours.")

    exact = _is_exact_hour(requested)
    supported_target = requested if exact else requested.ceil("h")
    delta = (supported_target - origin) / HOURLY_RESOLUTION
    if not float(delta).is_integer():
        raise ValueError("Mapped target must differ from origin by whole hours.")
    horizon = int(delta)
    if horizon <= 0:
        status = "unsupported_non_future_target"
        supported = False
    elif horizon not in horizons:
        status = "unsupported_forecast_horizon"
        supported = False
    else:
        status = "supported"
        supported = True
    return TargetTimeMapping(
        requested_target_time=requested,
        supported_target_time=supported_target,
        forecasting_origin_time=origin,
        available_resolution="hourly",
        mapping_method=(
            "exact_hour"
            if exact
            else "ceiling_to_next_hour_no_interpolation"
        ),
        is_exact=exact,
        mapping_offset_seconds=float(
            (supported_target - requested).total_seconds()
        ),
        forecast_horizon_hours=horizon,
        supported=supported,
        status=status,
    )


def build_station_lag_bundle(
    clean: pd.DataFrame,
    forecasting_origin_time: object,
    station_ids: Sequence[int | str],
) -> StationLagBundle:
    """Read only exact t-1h/t-2h/t-3h observations for deployment features."""
    origin = _normalise_timestamp(
        forecasting_origin_time, "forecasting_origin_time"
    )
    if not _is_exact_hour(origin):
        raise ValueError("forecasting_origin_time must be an exact hour.")
    required = {"date", "Station_No", "PM2.5"}
    missing = required.difference(clean.columns)
    if missing:
        raise StationValueError(
            "Lag construction missing columns: " + ", ".join(sorted(missing))
        )
    prepared = clean.copy()
    prepared["date"] = pd.to_datetime(prepared["date"], errors="raise")
    if prepared.duplicated(["Station_No", "date"]).any():
        raise StationValueError("Duplicate station-time rows invalidate lag lookup.")
    lookup = prepared.set_index(["Station_No", "date"])["PM2.5"]
    values: dict[int, dict[int, float]] = {}
    source_times: dict[int, dict[int, pd.Timestamp]] = {}
    for raw_station_id in station_ids:
        station_id = int(raw_station_id)
        values[station_id] = {}
        source_times[station_id] = {}
        for lag in (1, 2, 3):
            source_time = origin - pd.Timedelta(hours=lag)
            try:
                value = float(lookup.loc[(station_id, source_time)])
            except KeyError as error:
                raise StationValueError(
                    f"Missing station {station_id} PM2.5 at exact lag time "
                    f"{source_time.isoformat()}."
                ) from error
            if not np.isfinite(value):
                raise StationValueError(
                    f"Station {station_id} lag {lag}h PM2.5 is not finite."
                )
            values[station_id][lag] = value
            source_times[station_id][lag] = source_time
    return StationLagBundle(origin, values, source_times)


def _validate_lag_bundle(
    bundle: StationLagBundle,
    expected_origin: pd.Timestamp,
    station_ids: Sequence[int | str],
) -> None:
    if pd.Timestamp(bundle.forecasting_origin_time) != expected_origin:
        raise StationValueError("Lag bundle origin differs from forecasting origin.")
    expected_stations = {int(station_id) for station_id in station_ids}
    if set(bundle.values_by_station) != expected_stations:
        raise StationValueError("Lag bundle does not contain exactly all model stations.")
    for station_id in expected_stations:
        if set(bundle.values_by_station[station_id]) != {1, 2, 3}:
            raise StationValueError(
                f"Station {station_id} requires exact lag keys 1, 2, and 3."
            )
        if set(bundle.source_times_by_station.get(station_id, {})) != {1, 2, 3}:
            raise StationValueError(
                f"Station {station_id} requires timestamp provenance for all lags."
            )
        for lag in (1, 2, 3):
            source_time = pd.Timestamp(
                bundle.source_times_by_station[station_id][lag]
            )
            expected_time = expected_origin - pd.Timedelta(hours=lag)
            if source_time != expected_time or source_time >= expected_origin:
                raise StationValueError(
                    "Deployment lag provenance must be exact and strictly pre-origin."
                )
            if not np.isfinite(float(bundle.values_by_station[station_id][lag])):
                raise StationValueError("Deployment lag values must be finite.")


def forecast_station_values(
    forecaster: StationForecaster,
    mapping: TargetTimeMapping,
    lag_bundle: StationLagBundle,
) -> StationValueBundle:
    """Mode B station forecasts using strictly pre-origin lag features."""
    mapping.require_supported()
    model_horizons = {int(horizon) for horizon in forecaster.models}
    if mapping.forecast_horizon_hours not in model_horizons:
        raise UnsupportedTargetTimeError(
            f"Frozen model does not contain t+{mapping.forecast_horizon_hours}h."
        )
    _validate_lag_bundle(
        lag_bundle, mapping.forecasting_origin_time, forecaster.station_ids
    )
    values = {
        int(station_id): float(
            forecaster.predict_pm25(
                station_id,
                mapping.supported_target_time,
                prediction_time=mapping.forecasting_origin_time,
                pm25_lags=lag_bundle.values_by_station[int(station_id)],
            )
        )
        for station_id in forecaster.station_ids
    }
    if not all(np.isfinite(value) for value in values.values()):
        raise StationValueError("Frozen forecaster returned a non-finite PM2.5 value.")
    return StationValueBundle(
        target_time=mapping.supported_target_time,
        values=values,
        source_mode="deployment_forecast",
    )


def observed_station_values_at_time(
    clean: pd.DataFrame,
    target_time: object,
    station_ids: Sequence[int | str],
) -> StationValueBundle:
    """Mode A lookup of actual observations, never used by deployment mode."""
    target = _normalise_timestamp(target_time, "target_time")
    prepared = clean.copy()
    prepared["date"] = pd.to_datetime(prepared["date"], errors="raise")
    rows = prepared.loc[prepared["date"].eq(target), ["Station_No", "PM2.5"]]
    values: dict[int, float] = {}
    for raw_station_id in station_ids:
        station_id = int(raw_station_id)
        matches = rows.loc[rows["Station_No"].astype(int).eq(station_id), "PM2.5"]
        if len(matches) != 1 or not np.isfinite(float(matches.iloc[0])):
            raise StationValueError(
                f"Oracle requires one finite observation for station {station_id} "
                f"at {target.isoformat()}."
            )
        values[station_id] = float(matches.iloc[0])
    return StationValueBundle(target, values, "oracle_observed")


def classify_spatial_reliability(estimate: SpatialEstimate) -> str:
    """Qualitative geometry heuristic, not a calibrated confidence interval."""
    second = estimate.second_nearest_distance_km
    if (
        estimate.nearest_distance_km <= 5
        and second is not None
        and second <= 8
        and estimate.contributing_stations >= 5
        and estimate.maximum_weight <= 0.5
        and estimate.effective_station_count >= 3
    ):
        return "supported"
    if (
        estimate.nearest_distance_km <= 10
        and estimate.contributing_stations >= 4
        and estimate.effective_station_count >= 2
    ):
        return "moderate reliability"
    return "weak spatial support"


def _estimate_segment(
    segment: SegmentETA,
    route_departure_time: pd.Timestamp,
    mapping: TargetTimeMapping,
    station_bundle: StationValueBundle,
    expected_mode: str,
) -> SegmentPM25Record:
    mapping.require_supported()
    if station_bundle.source_mode != expected_mode:
        raise StationValueError(
            f"Expected {expected_mode} station values, got "
            f"{station_bundle.source_mode}."
        )
    if pd.Timestamp(station_bundle.target_time) != mapping.supported_target_time:
        raise StationValueError(
            "Spatial station values do not match the segment's supported target time."
        )
    estimate = estimate_with_diagnostics(
        segment.representative_latitude,
        segment.representative_longitude,
        mapping.supported_target_time,
        station_bundle.values,
        method=DEFAULT_SPATIAL_METHOD,
        power=DEFAULT_IDW_POWER,
    )
    return SegmentPM25Record(
        route_id=segment.route_id,
        segment_id=segment.edge_id,
        segment_index=segment.segment_index,
        mode=segment.mode,
        latitude=segment.representative_latitude,
        longitude=segment.representative_longitude,
        segment_geometry=segment.segment_geometry,
        segment_duration_seconds=segment.segment_duration_seconds,
        route_departure_time=route_departure_time,
        segment_entry_time=segment.entry_timestamp,
        requested_target_time=segment.target_arrival_timestamp,
        supported_target_time=mapping.supported_target_time,
        segment_endpoint_arrival_time=segment.estimated_arrival_timestamp,
        forecasting_origin_time=mapping.forecasting_origin_time,
        forecast_horizon_hours=mapping.forecast_horizon_hours,
        target_time_mapping_method=mapping.mapping_method,
        target_time_is_exact=mapping.is_exact,
        mapping_offset_seconds=mapping.mapping_offset_seconds,
        station_values_target_time=pd.Timestamp(station_bundle.target_time),
        station_value_source=station_bundle.source_mode,
        station_values_used=dict(station_bundle.values),
        predicted_pm25=estimate.predicted_pm25,
        spatial_method=estimate.method,
        spatial_power=float(estimate.power),
        nearest_station_id=estimate.nearest_station_id,
        nearest_station_distance_km=estimate.nearest_distance_km,
        second_nearest_station_distance_km=estimate.second_nearest_distance_km,
        contributing_station_count=estimate.contributing_stations,
        maximum_idw_weight=estimate.maximum_weight,
        idw_weight_concentration=estimate.weight_concentration,
        effective_station_count=estimate.effective_station_count,
        reliability_status=classify_spatial_reliability(estimate),
    )


def integrate_route_deployment(
    segments: Sequence[SegmentETA],
    forecasting_origin_time: object,
    forecaster: StationForecaster,
    lag_bundle: StationLagBundle,
) -> list[SegmentPM25Record]:
    """Mode B: frozen station forecasts → IDW p=1, with no future observations."""
    if not segments:
        raise ValueError("At least one ordered route segment is required.")
    origin = _normalise_timestamp(
        forecasting_origin_time, "forecasting_origin_time"
    )
    departure = pd.Timestamp(segments[0].entry_timestamp)
    cache: dict[pd.Timestamp, StationValueBundle] = {}
    records: list[SegmentPM25Record] = []
    for expected_index, segment in enumerate(segments, start=1):
        if segment.segment_index != expected_index:
            raise ValueError("Route segment ordering is not contiguous.")
        mapping = map_target_time(
            segment.target_arrival_timestamp,
            origin,
            supported_horizons=tuple(int(key) for key in forecaster.models),
        )
        mapping.require_supported()
        if mapping.supported_target_time not in cache:
            cache[mapping.supported_target_time] = forecast_station_values(
                forecaster, mapping, lag_bundle
            )
        records.append(
            _estimate_segment(
                segment,
                departure,
                mapping,
                cache[mapping.supported_target_time],
                "deployment_forecast",
            )
        )
    return records


def integrate_route_oracle(
    segments: Sequence[SegmentETA],
    forecasting_origin_time: object,
    observed_values_by_target: Mapping[object, Mapping[int | str, float]],
    *,
    supported_horizons: Sequence[int] = DEFAULT_SUPPORTED_HORIZONS,
) -> list[SegmentPM25Record]:
    """Mode A: explicitly supplied future observations → IDW p=1."""
    if not segments:
        raise ValueError("At least one ordered route segment is required.")
    origin = _normalise_timestamp(
        forecasting_origin_time, "forecasting_origin_time"
    )
    departure = pd.Timestamp(segments[0].entry_timestamp)
    normalised_observations = {
        pd.Timestamp(target): {int(key): float(value) for key, value in values.items()}
        for target, values in observed_values_by_target.items()
    }
    records: list[SegmentPM25Record] = []
    for expected_index, segment in enumerate(segments, start=1):
        if segment.segment_index != expected_index:
            raise ValueError("Route segment ordering is not contiguous.")
        mapping = map_target_time(
            segment.target_arrival_timestamp,
            origin,
            supported_horizons=supported_horizons,
        )
        mapping.require_supported()
        if mapping.supported_target_time not in normalised_observations:
            raise StationValueError(
                "Oracle observations are unavailable at mapped target "
                f"{mapping.supported_target_time.isoformat()}."
            )
        bundle = StationValueBundle(
            mapping.supported_target_time,
            normalised_observations[mapping.supported_target_time],
            "oracle_observed",
        )
        records.append(
            _estimate_segment(
                segment, departure, mapping, bundle, "oracle_observed"
            )
        )
    return records


def _records_to_frame(records: Sequence[SegmentPM25Record]) -> pd.DataFrame:
    rows = [record.to_dict() for record in records]
    frame = pd.DataFrame(rows)
    frame["station_values_used"] = frame["station_values_used"].map(
        lambda values: json.dumps(values, sort_keys=True, separators=(",", ":"))
    )
    frame["segment_geometry"] = frame["segment_geometry"].map(
        lambda geometry: json.dumps(geometry, separators=(",", ":"))
    )
    return frame


def _save_json_gzip(payload: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw_handle:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=raw_handle, mtime=0
        ) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8") as handle:
                json.dump(
                    payload, handle, separators=(",", ":"), sort_keys=True
                )


def _summary(records: Sequence[SegmentPM25Record], pipeline_mode: str) -> dict[str, object]:
    values = np.asarray([record.predicted_pm25 for record in records])
    return {
        "pipeline_mode": pipeline_mode,
        "travel_mode": records[0].mode,
        "route_id": records[0].route_id,
        "segments": len(records),
        "mapped_target_hours": len(
            {record.supported_target_time for record in records}
        ),
        "pm25_min": float(values.min()),
        "pm25_mean": float(values.mean()),
        "pm25_max": float(values.max()),
        "supported_reliability_segments": sum(
            record.reliability_status == "supported" for record in records
        ),
        "moderate_reliability_segments": sum(
            record.reliability_status == "moderate reliability"
            for record in records
        ),
        "weak_spatial_support_segments": sum(
            record.reliability_status == "weak spatial support"
            for record in records
        ),
    }


def _markdown_table(frame: pd.DataFrame, digits: int = 3) -> str:
    display = frame.copy()
    numeric = display.select_dtypes(include="number").columns
    display[numeric] = display[numeric].round(digits)
    return display.to_markdown(index=False)


def _render_report(
    summary: pd.DataFrame,
    sample: pd.DataFrame,
    forecast_values: StationValueBundle,
    oracle_values: StationValueBundle,
) -> str:
    station_comparison = pd.DataFrame(
        [
            {
                "station_id": station_id,
                "oracle_observed_pm25": oracle_values.values[station_id],
                "deployment_forecast_pm25": forecast_values.values[station_id],
            }
            for station_id in sorted(forecast_values.values)
        ]
    )
    sample_columns = [
        "station_value_source",
        "mode",
        "route_id",
        "segment_index",
        "requested_target_time",
        "supported_target_time",
        "forecast_horizon_hours",
        "predicted_pm25",
        "nearest_station_distance_km",
        "effective_station_count",
        "reliability_status",
    ]
    return f"""# AIRPATH-AI Milestone 3C — target-time PM2.5 integration

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
**{EXAMPLE_FORECASTING_ORIGIN}** in the existing validation period. All route
midpoints map to t+1h. This is an integration demonstration, not new model
selection or an untouched final evaluation.

## D–E. Oracle and deployment results

{_markdown_table(summary, 4)}

Station values at mapped target {forecast_values.target_time}:

{_markdown_table(station_comparison, 4)}

- **Oracle mode** reads actual station observations at the mapped hour solely to
  isolate the spatial pathway.
- **Deployment mode** accepts only an exact `StationLagBundle` containing
  station t-1h/t-2h/t-3h values and timestamps strictly before the forecasting
  origin. It calls the frozen forecaster and has no future-observation argument.

The two pathways are separate and their station-value provenance is attached to
every segment.

## F. Route-segment PM2.5 example

Small ordered excerpts (first three and final segment per route/pathway):

{_markdown_table(sample[sample_columns], 4)}

Complete records are saved under `data/processed/target_time/`. Each includes
segment geometry/duration, requested and supported target times, mapping rule,
horizon, all station values used, IDW result, and reliability proxies.

## G. Reliability flags

The propagated geometry proxies are nearest and second-nearest station distance,
contributing station count, maximum IDW weight, weight concentration, and
effective station count.

Qualitative flags are deterministic heuristics:

- `supported`: nearest ≤5 km, second-nearest ≤8 km, at least five contributors,
  maximum weight ≤0.5, effective count ≥3;
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
"""


def generate_integration_outputs(
    *,
    network_path: str | Path = (
        "data/processed/road_network/healthyair_pilot_osm.json.gz"
    ),
    clean_csv: str | Path = "data/processed/airquality_hcmc_clean.csv",
    forecaster_path: str | Path = (
        "data/processed/models/hourly_station_forecaster.joblib"
    ),
    processed_directory: str | Path = "data/processed/target_time",
    report_root: str | Path = "reports",
    forecasting_origin_time: object = EXAMPLE_FORECASTING_ORIGIN,
) -> dict[str, object]:
    """Run one reproducible walking/motorbike oracle and deployment example."""
    from .xgboost_forecasting import HourlyStationForecaster

    origin = _normalise_timestamp(
        forecasting_origin_time, "forecasting_origin_time"
    )
    network: RoadNetwork = load_network(network_path)
    clean = pd.read_csv(clean_csv, parse_dates=["date"])
    forecaster = HourlyStationForecaster.load(forecaster_path)
    lag_bundle = build_station_lag_bundle(
        clean, origin, forecaster.station_ids
    )

    routes: dict[str, CandidateRoute] = {}
    segments_by_mode: dict[str, list[SegmentETA]] = {}
    for mode in ("walking", "motorbike"):
        route = generate_candidate_routes(
            network, EXAMPLE_ORIGIN, EXAMPLE_DESTINATION, mode, k=1
        )[0]
        routes[mode] = route
        segments_by_mode[mode] = propagate_segment_etas(
            network, route, origin
        )

    supported_targets = {
        map_target_time(segment.target_arrival_timestamp, origin).supported_target_time
        for segments in segments_by_mode.values()
        for segment in segments
    }
    observed_by_target = {
        target: observed_station_values_at_time(
            clean, target, forecaster.station_ids
        ).values
        for target in supported_targets
    }

    oracle_records: list[SegmentPM25Record] = []
    deployment_records: list[SegmentPM25Record] = []
    for mode in ("walking", "motorbike"):
        oracle_records.extend(
            integrate_route_oracle(
                segments_by_mode[mode], origin, observed_by_target
            )
        )
        deployment_records.extend(
            integrate_route_deployment(
                segments_by_mode[mode], origin, forecaster, lag_bundle
            )
        )

    all_records = oracle_records + deployment_records
    output_directory = Path(processed_directory)
    report_root = Path(report_root)
    table_directory = report_root / "tables"
    output_directory.mkdir(parents=True, exist_ok=True)
    table_directory.mkdir(parents=True, exist_ok=True)

    _save_json_gzip(
        [record.to_dict() for record in oracle_records],
        output_directory / "oracle_route_segments.json.gz",
    )
    _save_json_gzip(
        [record.to_dict() for record in deployment_records],
        output_directory / "deployment_route_segments.json.gz",
    )
    frame = _records_to_frame(all_records)
    frame.to_csv(output_directory / "route_segment_pm25.csv", index=False)

    summary_rows = [
        _summary(records, pipeline_mode)
        for pipeline_mode, source_records in (
            ("oracle", oracle_records),
            ("deployment", deployment_records),
        )
        for mode in ("walking", "motorbike")
        for records in [
            [record for record in source_records if record.mode == mode]
        ]
    ]
    summary = pd.DataFrame(summary_rows)
    sample_parts = []
    for source in ("oracle_observed", "deployment_forecast"):
        for mode in ("walking", "motorbike"):
            rows = frame.loc[
                frame["station_value_source"].eq(source)
                & frame["mode"].eq(mode)
            ]
            sample_parts.extend([rows.head(3), rows.tail(1)])
    sample = pd.concat(sample_parts, ignore_index=True)
    summary.to_csv(
        table_directory / "target_time_integration_summary.csv", index=False
    )
    sample.to_csv(
        table_directory / "target_time_segment_examples.csv", index=False
    )

    example_mapping = map_target_time(
        segments_by_mode["walking"][0].target_arrival_timestamp, origin
    )
    forecast_values = forecast_station_values(
        forecaster, example_mapping, lag_bundle
    )
    oracle_values = StationValueBundle(
        example_mapping.supported_target_time,
        observed_by_target[example_mapping.supported_target_time],
        "oracle_observed",
    )
    (report_root / "target_time_integration.md").write_text(
        _render_report(summary, sample, forecast_values, oracle_values),
        encoding="utf-8",
    )
    return {
        "routes": routes,
        "segments_by_mode": segments_by_mode,
        "oracle_records": oracle_records,
        "deployment_records": deployment_records,
        "records": frame,
        "summary": summary,
        "sample": sample,
        "lag_bundle": lag_bundle,
    }


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--network",
        default="data/processed/road_network/healthyair_pilot_osm.json.gz",
    )
    parser.add_argument(
        "--clean-csv", default="data/processed/airquality_hcmc_clean.csv"
    )
    parser.add_argument(
        "--forecaster",
        default="data/processed/models/hourly_station_forecaster.joblib",
    )
    parser.add_argument(
        "--processed-directory", default="data/processed/target_time"
    )
    parser.add_argument("--report-root", default="reports")
    return parser.parse_args()


def main() -> None:
    arguments = _parse_arguments()
    outputs = generate_integration_outputs(
        network_path=arguments.network,
        clean_csv=arguments.clean_csv,
        forecaster_path=arguments.forecaster,
        processed_directory=arguments.processed_directory,
        report_root=arguments.report_root,
    )
    print(outputs["summary"].to_string(index=False))


if __name__ == "__main__":
    main()
