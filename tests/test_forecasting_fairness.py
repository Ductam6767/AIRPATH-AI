import pandas as pd
import pytest

from src.forecasting_fairness import (
    CURRENT_AWARE_FEATURES,
    FROZEN_V1_PARAMETERS,
    MODEL_A,
    MODEL_B,
    MODEL_C,
    V1_FEATURES,
    build_fairness_pipeline,
    current_vs_v1_deltas,
    decide_fairness_recommendation,
    feature_matrix,
    fit_model_family,
    horizon_deltas,
    metrics_table,
    persistence_predictions,
    predict_model_family,
)


SMALL_PARAMETERS = {
    1: {
        "n_estimators": 8,
        "max_depth": 2,
        "learning_rate": 0.2,
        "subsample": 1.0,
        "colsample_bytree": 1.0,
        "min_child_weight": 1,
    },
    2: {
        "n_estimators": 8,
        "max_depth": 2,
        "learning_rate": 0.2,
        "subsample": 1.0,
        "colsample_bytree": 1.0,
        "min_child_weight": 1,
    },
    3: {
        "n_estimators": 8,
        "max_depth": 2,
        "learning_rate": 0.2,
        "subsample": 1.0,
        "colsample_bytree": 1.0,
        "min_child_weight": 1,
    },
}


def _samples() -> pd.DataFrame:
    rows = []
    for horizon in (1, 2, 3):
        for index in range(18):
            split = (
                "train"
                if index < 10
                else "validation"
                if index < 14
                else "test"
            )
            current = float(20 + index + horizon)
            rows.append(
                {
                    "Station_No": 1 if index % 2 == 0 else 2,
                    "origin_time": pd.Timestamp("2024-01-01")
                    + pd.Timedelta(hours=index),
                    "target_time": pd.Timestamp("2024-01-01")
                    + pd.Timedelta(hours=index + horizon),
                    "horizon_hours": horizon,
                    "split": split,
                    "pm25_current": current,
                    "pm25_lag_1h": current - 1,
                    "pm25_lag_2h": current - 2,
                    "pm25_lag_3h": current - 3,
                    "hour": index % 24,
                    "day_of_week": 0,
                    "month": 1,
                    "target_pm25": current + 0.1 * horizon,
                }
            )
    return pd.DataFrame(rows)


def test_model_b_excludes_current_pm_and_model_c_includes_it() -> None:
    assert "pm25_current" not in V1_FEATURES
    assert CURRENT_AWARE_FEATURES[0] == "pm25_current"
    assert list(CURRENT_AWARE_FEATURES[1:]) == list(V1_FEATURES)


def test_feature_matrix_rejects_target_leakage() -> None:
    with pytest.raises(ValueError, match="cannot be model features"):
        feature_matrix(_samples(), ("target_pm25", "Station_No"))


def test_persistence_uses_current_pm_only_on_validation() -> None:
    predictions = persistence_predictions(_samples())
    assert set(predictions["split"]) == {"validation"}
    assert predictions["model"].eq(MODEL_A).all()
    pd.testing.assert_series_equal(
        predictions["prediction"],
        predictions["pm25_current"],
        check_names=False,
    )


def test_fit_and_predict_never_requires_test_split() -> None:
    samples = _samples()
    models = fit_model_family(
        samples, V1_FEATURES, SMALL_PARAMETERS, model_name=MODEL_B
    )
    predictions = predict_model_family(
        models, samples, V1_FEATURES, model_name=MODEL_B
    )
    assert set(predictions["split"]) == {"validation"}
    assert "test" not in set(predictions["split"])


def test_current_aware_pipeline_encodes_station_and_keeps_current() -> None:
    rows = _samples().loc[lambda frame: frame["horizon_hours"].eq(1)]
    train = rows.loc[rows["split"].eq("train")]
    pipeline = build_fairness_pipeline(
        CURRENT_AWARE_FEATURES, SMALL_PARAMETERS[1]
    )
    pipeline.fit(feature_matrix(train, CURRENT_AWARE_FEATURES), train["target_pm25"])
    names = pipeline.named_steps["preprocessor"].get_feature_names_out().tolist()
    assert any(name.endswith("pm25_current") for name in names)
    assert any("Station_No_1" in name for name in names)


def test_metrics_and_deltas_are_deterministic() -> None:
    samples = _samples()
    model_a = persistence_predictions(samples)
    models_b = fit_model_family(
        samples, V1_FEATURES, SMALL_PARAMETERS, model_name=MODEL_B
    )
    models_c = fit_model_family(
        samples, CURRENT_AWARE_FEATURES, SMALL_PARAMETERS, model_name=MODEL_C
    )
    predictions = pd.concat(
        [
            model_a,
            predict_model_family(
                models_b, samples, V1_FEATURES, model_name=MODEL_B
            ),
            predict_model_family(
                models_c, samples, CURRENT_AWARE_FEATURES, model_name=MODEL_C
            ),
        ],
        ignore_index=True,
    )
    metrics = metrics_table(predictions)
    versus_a = horizon_deltas(metrics)
    versus_v1 = current_vs_v1_deltas(metrics)
    decision = decide_fairness_recommendation(metrics, versus_a, versus_v1)

    assert set(metrics["model"]) == {MODEL_A, MODEL_B, MODEL_C}
    assert metrics["evaluation_label"].eq(
        "development_validation_exploratory"
    ).all()
    assert decision.recommended_model in {MODEL_A, MODEL_B, MODEL_C}
    assert decision.criteria["test_partition_used_for_tuning"] is False
    assert decision.criteria["zeros_or_iqr_removed"] is False


def test_frozen_v1_parameters_cover_all_horizons() -> None:
    assert set(FROZEN_V1_PARAMETERS) == {1, 2, 3}
