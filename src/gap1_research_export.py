"""Package frozen P0-2A/P0-2B Gap 1 results for Direction A (research exhibit).

Does not retrain, change IDW, regenerate candidates, or use demo street-PM
simulation. It only reads already-frozen comparison tables.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Final, Sequence

import pandas as pd

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
P0_2A_DIR: Final[Path] = REPO_ROOT / "data" / "processed" / "static_vs_arrival_exposure"
P0_2B_DIR: Final[Path] = REPO_ROOT / "data" / "processed" / "temporal_gap_analysis"
FREEZE_MANIFEST_PATH: Final[Path] = (
    REPO_ROOT / "data" / "processed" / "final_robustness" / "freeze_manifest.json"
)
DEFAULT_OUTPUT: Final[Path] = (
    REPO_ROOT / "data" / "processed" / "gap1_research" / "exhibit.json"
)

DESIRED_QUANTITY: Final[str] = (
    "PM2.5 at the road segment at the exact minute the traveller arrives there."
)
AVAILABLE_SUBSTITUTION: Final[str] = (
    "Ceiling the segment ETA to the next HealthyAir hour, take Model C "
    "station forecasts for that hour from an origin one hour before departure, "
    "then IDW p=1 from six stations onto the segment midpoint."
)
NOT_AVAILABLE: Final[list[str]] = [
    "On-road / mobile-monitoring PM2.5 at the segment",
    "Minute-level station PM2.5",
    "Live traffic or signal delay in ETA",
    "Inhaled dose or medical risk",
]
DATA_REQUIRED_FOR_STREET_PM: Final[list[str]] = [
    "PM2.5 sampled on or beside the roadway (mobile monitoring or a dense street network), time-aligned to the trajectory",
    "Sub-hourly timestamps so the concentration at the arrival minute is observed, not ceiled to a station hour",
    "Enough spatial coverage that segment D is measured, not interpolated from six distant stations",
]
WORKED_EXAMPLE: Final[dict[str, str]] = {
    "departure": "06:00",
    "forecast_origin": "05:00",
    "segment_passage": "06:17",
    "hour_used": "07:00",
    "note": (
        "06:17 is not interpolated. The supported HealthyAir hour is 07:00 "
        "(t+2h from 05:00). Static ranking would still use the 06:00 snapshot."
    ),
}


def _round(value: float, digits: int = 6) -> float:
    return round(float(value), digits)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _representative_disagreements(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """One row per experiment cell that disagrees at δ>0; prefer δ=5."""
    differ = frame.loc[
        frame["selections_differ"].astype(bool)
        & (frame["delta_time_allowed_minutes"].astype(float) > 0)
    ].copy()
    if differ.empty:
        return []
    differ["_delta_pref"] = (
        differ["delta_time_allowed_minutes"].astype(float) - 5.0
    ).abs()
    sort_cols = ["scenario_id", "mode", "_delta_pref", "delta_time_allowed_minutes"]
    if "departure_time" in differ.columns:
        sort_cols = ["departure_time", *sort_cols]
    differ = differ.sort_values(sort_cols, kind="mergesort")
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for row in differ.itertuples(index=False):
        if "departure_time" in differ.columns:
            key = (str(row.departure_time), str(row.scenario_id), str(row.mode))
        else:
            key = (str(row.scenario_id), str(row.mode))
        if key in seen:
            continue
        seen.add(key)
        payload: dict[str, Any] = {
            "scenario_id": str(row.scenario_id),
            "mode": str(row.mode),
            "delta_minutes": _round(float(row.delta_time_allowed_minutes), 1),
            "fastest_route_id": str(row.fastest_route_id),
            "static_selected_route_id": str(row.static_selected_route_id),
            "airpath_selected_route_id": str(row.airpath_selected_route_id),
            "oracle_percent_improvement_airpath_over_static": _round(
                float(row.oracle_percent_improvement_airpath_over_static)
            ),
        }
        if hasattr(row, "departure_time"):
            payload["departure_time"] = str(row.departure_time)
        rows.append(payload)
    return rows


def _clock_band(clock_time: str) -> str:
    hour = int(str(clock_time).split(":")[0])
    if hour in {6, 7, 8, 9}:
        return "morning_peak"
    if hour in {11, 12, 13, 14}:
        return "midday"
    if hour in {16, 17, 18, 19}:
        return "evening_peak"
    return "off_peak"


def _selection_proof(frame: pd.DataFrame) -> dict[str, Any]:
    nontrivial = frame.loc[frame["delta_time_allowed_minutes"].astype(float) > 0]
    differ = nontrivial.loc[nontrivial["selections_differ"].astype(bool)]
    n = int(len(nontrivial))
    d = int(len(differ))
    by_mode: list[dict[str, Any]] = []
    for mode, group in nontrivial.groupby("mode", sort=True):
        differ_mode = group.loc[group["selections_differ"].astype(bool)]
        n_mode = int(len(group))
        d_mode = int(len(differ_mode))
        by_mode.append(
            {
                "mode": str(mode),
                "differ_count": d_mode,
                "nontrivial_count": n_mode,
                "rate": _round(d_mode / n_mode) if n_mode else 0.0,
            }
        )
    return {
        "differ_count": d,
        "nontrivial_count": n,
        "rate": _round(d / n) if n else 0.0,
        "by_mode": by_mode,
    }


def _clock_mode_proof(frame: pd.DataFrame) -> list[dict[str, Any]]:
    nontrivial = frame.loc[frame["delta_time_allowed_minutes"].astype(float) > 0]
    rows: list[dict[str, Any]] = []
    grouped = nontrivial.groupby(["departure_time", "mode"], sort=True)
    for (departure, mode), group in grouped:
        differ = group.loc[group["selections_differ"].astype(bool)]
        clock = str(departure)[11:16] if len(str(departure)) >= 16 else str(departure)
        n = int(len(group))
        d = int(len(differ))
        rows.append(
            {
                "clock_time": clock,
                "departure_time": str(departure),
                "band": _clock_band(clock),
                "mode": str(mode),
                "differ_count": d,
                "nontrivial_count": n,
                "rate": _round(d / n) if n else 0.0,
            }
        )
    return rows


def build_gap1_exhibit(
    *,
    p0_2a_dir: Path = P0_2A_DIR,
    p0_2b_dir: Path = P0_2B_DIR,
    freeze_manifest_path: Path = FREEZE_MANIFEST_PATH,
) -> dict[str, Any]:
    p0_2a_decision = _load_json(p0_2a_dir / "evidence_decision.json")
    p0_2b_decision = _load_json(p0_2b_dir / "evidence_decision.json")
    freeze = _load_json(freeze_manifest_path) if freeze_manifest_path.is_file() else {}
    p0_2a_sel = pd.read_csv(p0_2a_dir / "constrained_selection_comparison.csv")
    p0_2b_sel = pd.read_csv(p0_2b_dir / "constrained_selection_comparison.csv")
    clocks = pd.read_csv(p0_2b_dir / "departure_time_summary.csv")

    clock_rows = []
    for row in clocks.itertuples(index=False):
        oracle = row.mean_oracle_pct_improvement_when_differ
        clock_rows.append(
            {
                "clock_time": str(row.clock_time),
                "departure_time": str(row.departure_time),
                "nontrivial_selection_difference_rate": _round(
                    float(row.nontrivial_selection_difference_rate)
                ),
                "mean_spearman": _round(float(row.mean_spearman)),
                "mean_oracle_pct_improvement_when_differ": (
                    None if pd.isna(oracle) else _round(float(oracle))
                ),
                "mean_abs_pct_exposure_diff": _round(
                    float(row.mean_abs_pct_exposure_diff)
                ),
                "band": _clock_band(str(row.clock_time)),
            }
        )

    p0_2a_proof = _selection_proof(p0_2a_sel)
    p0_2b_proof = _selection_proof(p0_2b_sel)
    p0_2b_proof["by_clock_and_mode"] = _clock_mode_proof(p0_2b_sel)

    return {
        "pack_name": "airpath_gap1_direction_a_v1",
        "uses_simulated_onroad_pm": False,
        "scientific_logic_modified": False,
        "question": (
            "Does ranking the same candidate routes by hourly arrival-time "
            "exposure change the constrained selection relative to a static "
            "departure-time PM snapshot?"
        ),
        "desired_quantity": DESIRED_QUANTITY,
        "available_substitution": AVAILABLE_SUBSTITUTION,
        "not_available": NOT_AVAILABLE,
        "data_required_for_street_pm": DATA_REQUIRED_FOR_STREET_PM,
        "worked_example": WORKED_EXAMPLE,
        "ceiling_rule": (
            "Exact hourly ETA stays on that hour. Any other ETA is ceiled to "
            "the next exact hour with no interpolation (17:03 → 18:00)."
        ),
        "exposure_definition": "sum_pm25_times_duration_minutes",
        "exposure_unit": "(µg/m³)·min",
        "forecaster": freeze.get("frozen_forecaster", "C_xgboost_current_pm"),
        "spatial_model": freeze.get("spatial_model", "idw_p1"),
        "freeze_gap1_conclusion": freeze.get("gap1_conclusion"),
        "p0_2a": {
            "label": "Single morning departure (2022-02-28 06:00)",
            "classification": p0_2a_decision.get("classification"),
            "rationale": p0_2a_decision.get("rationale"),
            "nontrivial_selection_difference_rate": p0_2a_decision["criteria"][
                "nontrivial_selection_difference_rate"
            ],
            "mean_oracle_percent_improvement_when_differ": p0_2a_decision["criteria"][
                "mean_oracle_percent_improvement_when_differ"
            ],
            "mean_spearman_static_vs_airpath": p0_2a_decision["criteria"][
                "mean_spearman_static_vs_airpath"
            ],
            "representative_disagreements": _representative_disagreements(p0_2a_sel),
        },
        "p0_2b": {
            "label": "Five clock times on 2022-02-27",
            "classification": p0_2b_decision.get("classification"),
            "rationale": p0_2b_decision.get("rationale"),
            "nontrivial_selection_difference_rate": p0_2b_decision["criteria"][
                "nontrivial_selection_difference_rate"
            ],
            "mean_oracle_percent_improvement_when_differ": p0_2b_decision["criteria"][
                "mean_oracle_percent_improvement_when_differ"
            ],
            "mean_spearman_static_vs_airpath": p0_2b_decision["criteria"][
                "mean_spearman_static_vs_airpath"
            ],
            "gap1_conclusion_changed_vs_p0_2a": bool(
                p0_2b_decision.get("gap1_conclusion_changed", False)
            ),
            "by_clock": clock_rows,
            "representative_disagreements": _representative_disagreements(p0_2b_sel),
        },
        "how_to_prove_rare": {
            "meaning": (
                "Rare means the chosen route changes, not that the exposure "
                "number is the same."
            ),
            "recipe": (
                "Open constrained_selection_comparison.csv. Keep rows with "
                "delta_time_allowed_minutes > 0. Count selections_differ == True "
                "divided by the number of remaining rows."
            ),
            "p0_2a": p0_2a_proof,
            "p0_2b": p0_2b_proof,
            "reviewer_sentence": (
                f"On P0-2A the two methods pick different routes in "
                f"{p0_2a_proof['differ_count']} of {p0_2a_proof['nontrivial_count']} "
                f"cells ({p0_2a_proof['rate'] * 100:.2f}%). "
                f"On P0-2B that is {p0_2b_proof['differ_count']} of "
                f"{p0_2b_proof['nontrivial_count']} ({p0_2b_proof['rate'] * 100:.2f}%). "
                "At 12:00, 17:00 and 20:00 the count is 0. When they do differ, "
                "mean oracle gain is about 0.11% (P0-2A) and 0.02% (P0-2B)."
            ),
        },
        "peak_hour_with_current_data": {
            "what_is_identifiable": (
                "City-wide hour from six stations (Model C diurnal pattern), "
                "separately for walking and motorbike because duration differs."
            ),
            "what_is_not_identifiable": (
                "Which specific street is congested, or PM on that street as a "
                "consequence of traffic."
            ),
            "result": (
                "Disagreements exist only at 06:00 and 08:00. Walking disagrees "
                "more often than motorbike because a walk crosses more hourly "
                "buckets. Midday and evening clocks never change the selected route."
            ),
            "future_when_street_data_exists": (
                "Learn E[PM | segment or road class, hour, mode] from "
                "on-road measurements, then reuse the same constrained selector. "
                "That is a new quantity, not a Gap 1 result from HealthyAir."
            ),
        },
        "paper_claim_allowed": (
            "Hourly forecast-bucket-aware exposure is a defined substitution "
            "for unavailable on-road arrival PM. Under six-station IDW it "
            "rarely changes constrained route selection versus a static snapshot "
            "(MIXED/WEAK)."
        ),
        "paper_claim_forbidden": [
            "AIRPATH knows PM2.5 on street D at the arrival minute.",
            "Arrival-time ranking yields a large exposure benefit in this dataset.",
            "The product map's simulated traffic-class PM is a Gap 1 result.",
        ],
    }


def write_gap1_exhibit(path: Path, exhibit: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(exhibit, indent=2) + "\n", encoding="utf-8")
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export frozen Gap 1 Direction-A research exhibit JSON."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    exhibit = build_gap1_exhibit()
    write_gap1_exhibit(args.output, exhibit)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "uses_simulated_onroad_pm": exhibit["uses_simulated_onroad_pm"],
                "p0_2a_disagreements": len(
                    exhibit["p0_2a"]["representative_disagreements"]
                ),
                "p0_2b_disagreements": len(
                    exhibit["p0_2b"]["representative_disagreements"]
                ),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
