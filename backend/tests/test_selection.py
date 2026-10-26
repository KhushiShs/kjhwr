"""Hand-made selection tests from PROJECT_PLAN section 8."""

from __future__ import annotations

import pandas as pd

from app.core import (
    cutoff_for_start,
    horizon_hours,
    pair_actuals_and_forecasts,
    select_forecast_closest_horizon,
    select_latest_forecast_for_target,
    select_latest_forecasts,
)

START = pd.Timestamp("2026-01-02T12:00:00Z")

# Three publishes for the same target: two before a 09:00 cutoff, one after.
FORECASTS = pd.DataFrame(
    {
        "startTime": [START, START, START],
        "publishTime": [
            pd.Timestamp("2026-01-01T07:00:00Z"),
            pd.Timestamp("2026-01-01T08:30:00Z"),
            pd.Timestamp("2026-01-01T10:00:00Z"),
        ],
        "generation": [100.0, 200.0, 300.0],
    }
)


def test_ignores_forecast_published_after_cutoff() -> None:
    cutoff = pd.Timestamp("2026-01-01T09:00:00Z")
    chosen = select_latest_forecast_for_target(FORECASTS, START, cutoff)
    assert chosen is not None
    assert chosen["generation"] == 200.0
    assert chosen["publishTime"] == pd.Timestamp("2026-01-01T08:30:00Z")


def test_publish_exactly_at_cutoff_is_included() -> None:
    forecasts = pd.DataFrame(
        {
            "startTime": [START, START],
            "publishTime": [
                pd.Timestamp("2026-01-01T08:00:00Z"),
                pd.Timestamp("2026-01-01T09:00:00Z"),
            ],
            "generation": [111.0, 222.0],
        }
    )
    cutoff = pd.Timestamp("2026-01-01T09:00:00Z")
    chosen = select_latest_forecast_for_target(forecasts, START, cutoff)
    assert chosen is not None
    assert chosen["generation"] == 222.0


def test_missing_when_nothing_published_before_cutoff() -> None:
    cutoff = pd.Timestamp("2026-01-01T06:00:00Z")
    chosen = select_latest_forecast_for_target(FORECASTS, START, cutoff)
    assert chosen is None


def test_changing_cutoff_changes_selected_forecast() -> None:
    early = select_latest_forecast_for_target(
        FORECASTS, START, pd.Timestamp("2026-01-01T07:30:00Z")
    )
    late = select_latest_forecast_for_target(FORECASTS, START, pd.Timestamp("2026-01-01T10:00:00Z"))
    assert early is not None and late is not None
    assert early["generation"] == 100.0
    assert late["generation"] == 300.0


def test_cutoff_is_d_minus_1_clock_time_not_hard_coded() -> None:
    start = pd.Timestamp("2026-01-15T23:30:00Z")
    cutoff = cutoff_for_start(start, cutoff_hour=9, cutoff_minute=15)
    assert cutoff == pd.Timestamp("2026-01-14T09:15:00Z")


def test_horizon_hours_is_start_minus_publish() -> None:
    hours = horizon_hours(
        pd.Timestamp("2026-01-02T12:00:00Z"),
        pd.Timestamp("2026-01-01T09:00:00Z"),
    )
    assert hours == 27.0


def test_batch_selection_left_joins_missing_as_na() -> None:
    actuals = pd.DataFrame(
        {
            "startTime": [
                START,
                pd.Timestamp("2026-01-02T12:30:00Z"),  # no forecast rows at all
            ],
            "generation": [1000.0, 1100.0],
        }
    )
    paired = pair_actuals_and_forecasts(actuals, FORECASTS, cutoff_hour=9, cutoff_minute=0)
    assert len(paired) == 2
    first = paired.loc[paired["startTime"] == START].iloc[0]
    assert first["forecast"] == 200.0
    assert first["horizon_hours"] == 27.5
    second = paired.loc[paired["startTime"] != START].iloc[0]
    assert pd.isna(second["forecast"])


def test_closest_horizon_picks_nearest_lead_time() -> None:
    forecasts = pd.DataFrame(
        {
            "startTime": [START, START, START],
            "publishTime": [
                pd.Timestamp("2026-01-01T12:00:00Z"),  # 24h
                pd.Timestamp("2026-01-02T00:00:00Z"),  # 12h
                pd.Timestamp("2026-01-01T00:00:00Z"),  # 36h
            ],
            "generation": [24.0, 12.0, 36.0],
        }
    )
    chosen = select_forecast_closest_horizon(forecasts, START, 13.0)
    assert chosen is not None
    assert chosen["generation"] == 12.0


def test_select_latest_forecasts_matches_single_target() -> None:
    selected = select_latest_forecasts(
        FORECASTS, pd.Series([START]), cutoff_hour=9, cutoff_minute=0
    )
    assert len(selected) == 1
    assert selected.iloc[0]["generation"] == 200.0
