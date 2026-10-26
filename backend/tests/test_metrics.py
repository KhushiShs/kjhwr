"""Hand-calculated metric tests from PROJECT_PLAN section 8."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from app.core import (
    compute_metrics,
    decision_from_paired,
    error_band,
    metrics_by_group,
    pair_actuals_and_forecasts,
)


def _paired() -> pd.DataFrame:
    # actual = 10, 20, 30
    # forecast = 12, 18, 40
    # error = 2, -2, 10   (positive = over-forecast)
    # abs    = 2,  2, 10
    return pd.DataFrame(
        {
            "startTime": pd.to_datetime(
                ["2026-01-01T00:00Z", "2026-01-01T01:00Z", "2026-01-01T02:00Z"],
                utc=True,
            ),
            "actual": [10.0, 20.0, 30.0],
            "forecast": [12.0, 18.0, 40.0],
            "error": [2.0, -2.0, 10.0],
            "abs_error": [2.0, 2.0, 10.0],
            "horizon_hours": [24.0, 24.0, 36.0],
        }
    )


def test_overforecast_is_positive_error() -> None:
    actuals = pd.DataFrame(
        {
            "startTime": [pd.Timestamp("2026-01-02T12:00:00Z")],
            "generation": [100.0],
        }
    )
    forecasts = pd.DataFrame(
        {
            "startTime": [pd.Timestamp("2026-01-02T12:00:00Z")],
            "publishTime": [pd.Timestamp("2026-01-01T08:00:00Z")],
            "generation": [130.0],
        }
    )
    paired = pair_actuals_and_forecasts(actuals, forecasts, 9, 0)
    assert paired.iloc[0]["error"] == 30.0


def test_mae_rmse_bias_percentiles_hand_calculated() -> None:
    metrics = compute_metrics(_paired())
    errors = np.array([2.0, -2.0, 10.0])
    abs_errors = np.abs(errors)

    assert metrics.n_targets == 3
    assert metrics.n_paired == 3
    assert metrics.coverage == 1.0
    assert metrics.mae == 14.0 / 3.0
    assert metrics.rmse == math.sqrt(36.0)
    assert metrics.bias == 10.0 / 3.0
    assert metrics.p50_abs_error == float(np.percentile(abs_errors, 50))
    assert metrics.p90_abs_error == float(np.percentile(abs_errors, 90))
    assert metrics.p95_abs_error == float(np.percentile(abs_errors, 95))
    assert metrics.p50_abs_error == 2.0
    # numpy linear percentile on [2, 2, 10]
    assert metrics.p90_abs_error == 8.4
    assert metrics.p95_abs_error == 9.2


def test_coverage_counts_missing_forecasts() -> None:
    frame = _paired()
    frame.loc[2, "forecast"] = np.nan
    frame.loc[2, "error"] = np.nan
    metrics = compute_metrics(frame)
    assert metrics.n_targets == 3
    assert metrics.n_paired == 2
    assert metrics.coverage == 2 / 3
    assert metrics.mae == 2.0
    assert metrics.bias == 0.0


def test_mape_skips_near_zero_actuals() -> None:
    frame = pd.DataFrame(
        {
            "actual": [0.0, 50.0],
            "forecast": [10.0, 40.0],
            "error": [10.0, -10.0],
        }
    )
    metrics = compute_metrics(frame)
    assert metrics.mape == 10.0 / 50.0


def test_error_band_is_forecast_plus_minus_p90() -> None:
    low, high = error_band(100.0, 15.0)
    assert (low, high) == (85.0, 115.0)


def test_decision_buffer_uses_abs_and_positive_error() -> None:
    result = decision_from_paired(_paired(), confidence=0.9)
    assert result["buffer_mw"] == 8.4
    # positive errors: 2 and 10; P90 linear = 9.2
    assert result["shortfall_buffer_mw"] == float(np.percentile(np.array([2.0, 10.0]), 90))
    assert "buffer of about" in str(result["statement"])
    assert "over-forecast" in str(result["statement"]).lower()


def test_breakdown_by_hour() -> None:
    rows = metrics_by_group(_paired(), by="hour")
    hours = {row["group"] for row in rows}
    assert hours == {"0", "1", "2"}
    noonish = next(row for row in rows if row["group"] == "0")
    assert noonish["n_paired"] == 1
    assert noonish["bias"] == 2.0
