import pandas as pd
import pytest

import src.xgboost_forecasting as xgf
from src.xgboost_forecasting import (
    HourlyStationForecaster,
    attach_origin_weather,
    build_pipeline,
    feature_frame,
    select_v1_hyperparameters,
)


SMALL_PARAMETERS = {
    "n_estimators": 5,
    "max_depth": 2,
    "learning_rate": 0.1,
    "subsample": 1.0,
    "colsample_bytree": 1.0,
    "min_child_weight": 1,
}


def _model_rows() -> pd.DataFrame:
    rows = []
    for horizon in (1, 2, 3):
        for index in range(12):
            split = "train" if index < 6 else "validation" if index < 9 else "test"
            rows.append(
                {
                    "Station_No": 1 if index % 2 == 0 else 2,
                    "origin_time": pd.Timestamp("2024-01-01") + pd.Timedelta(
                        hours=index
                    ),
                    "target_time": pd.Timestamp("2024-01-01")
                    + pd.Timedelta(hours=index + horizon),
                    "horizon_hours": horizon,
                    "split": split,
                    "pm25_lag_1h": float(index + 3),
                    "pm25_lag_2h": float(index + 2),
                    "pm25_lag_3h": float(index + 1),
                    "hour": index,
                    "day_of_week": 0,
                    "month": 1,
                    "Temperature": 20.0 if index != 1 else float("nan"),
                    "Humidity": 70.0 if index != 2 else float("nan"),
                    "pm25_current": float(index + 4),
                    "target_pm25": float(index + 4 + horizon),
                }
            )
    return pd.DataFrame(rows)


def test_v1_feature_contract_excludes_current_future_and_weather() -> None:
    rows = _model_rows()
    features = feature_frame(rows, "v1")

    assert list(features.columns) == [
        "pm25_lag_1h",
        "pm25_lag_2h",
        "pm25_lag_3h",
        "hour",
        "day_of_week",
        "month",
        "Station_No",
    ]
    assert "pm25_current" not in features
    assert "target_pm25" not in features
    assert "Temperature" not in features
    assert "Humidity" not in features


def test_station_is_one_hot_encoded_not_continuous() -> None:
    rows = _model_rows().loc[lambda frame: frame["horizon_hours"].eq(1)]
    pipeline = build_pipeline("v1", SMALL_PARAMETERS)
    pipeline.fit(feature_frame(rows, "v1"), rows["target_pm25"])

    names = pipeline.named_steps["preprocessor"].get_feature_names_out().tolist()

    assert "station__Station_No_1" in names
    assert "station__Station_No_2" in names
    assert "history_time__Station_No" not in names


def test_weather_imputation_is_learned_from_fit_rows_only() -> None:
    rows = _model_rows().loc[lambda frame: frame["horizon_hours"].eq(1)].copy()
    train = rows.loc[rows["split"].eq("train")].copy()
    train["Temperature"] = [10.0, float("nan"), 10.0, 10.0, 10.0, 10.0]
    train["Humidity"] = [50.0, 50.0, float("nan"), 50.0, 50.0, 50.0]
    rows.loc[rows["split"].eq("validation"), ["Temperature", "Humidity"]] = 9999.0
    pipeline = build_pipeline("v2", SMALL_PARAMETERS)
    pipeline.fit(feature_frame(train, "v2"), train["target_pm25"])

    imputer = pipeline.named_steps["preprocessor"].named_transformers_["weather"]

    assert imputer.statistics_.tolist() == [10.0, 50.0]


def test_weather_attachment_uses_exact_origin_timestamp() -> None:
    samples = pd.DataFrame(
        {
            "Station_No": [1],
            "origin_time": pd.to_datetime(["2024-01-01 02:00"]),
        }
    )
    clean = pd.DataFrame(
        {
            "Station_No": [1, 1],
            "date": pd.to_datetime(["2024-01-01 01:00", "2024-01-01 03:00"]),
            "Temperature": [10.0, 30.0],
            "Humidity": [50.0, 70.0],
        }
    )

    attached = attach_origin_weather(samples, clean)

    assert pd.isna(attached.loc[0, "Temperature"])
    assert pd.isna(attached.loc[0, "Humidity"])


def test_hyperparameter_selection_is_independent_of_test_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(xgf, "PARAMETER_CANDIDATES", (SMALL_PARAMETERS,))
    rows = _model_rows()
    selected_a, search_a = select_v1_hyperparameters(rows)
    changed = rows.copy()
    changed.loc[changed["split"].eq("test"), "target_pm25"] = 1_000_000.0
    selected_b, search_b = select_v1_hyperparameters(changed)

    assert selected_a == selected_b
    pd.testing.assert_frame_equal(search_a, search_b)


class _ConstantModel:
    def predict(self, features: pd.DataFrame) -> list[float]:
        assert "target_pm25" not in features
        return [12.5] * len(features)


def test_target_time_interface_enforces_hourly_station_scope() -> None:
    forecaster = HourlyStationForecaster(
        models={1: _ConstantModel(), 2: _ConstantModel(), 3: _ConstantModel()},
        version="v1",
        station_ids=("1",),
    )
    prediction = forecaster.predict_pm25(
        1,
        "2024-01-01 03:00",
        prediction_time="2024-01-01 01:00",
        pm25_lags={1: 10.0, 2: 9.0, 3: 8.0},
    )
    assert prediction == 12.5

    with pytest.raises(ValueError, match="exact hourly"):
        forecaster.predict_pm25(
            1,
            "2024-01-01 02:30",
            prediction_time="2024-01-01 01:00",
            pm25_lags={1: 10.0, 2: 9.0, 3: 8.0},
        )
    with pytest.raises(ValueError, match="Unknown monitored station"):
        forecaster.predict_pm25(
            "road-node-C",
            "2024-01-01 02:00",
            prediction_time="2024-01-01 01:00",
            pm25_lags={1: 10.0, 2: 9.0, 3: 8.0},
        )


def test_xgboost_training_is_reproducible() -> None:
    rows = _model_rows().loc[lambda frame: frame["horizon_hours"].eq(1)]
    first = build_pipeline("v1", SMALL_PARAMETERS)
    second = build_pipeline("v1", SMALL_PARAMETERS)
    features = feature_frame(rows, "v1")
    first.fit(features, rows["target_pm25"])
    second.fit(features, rows["target_pm25"])

    assert first.predict(features).tolist() == second.predict(features).tolist()
