"""Pure forecast-selection, error, and metric functions.

No I/O, no FastAPI, no global cutoff constants. Callers pass cutoff hour/minute.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

BreakdownBy = Literal["hour", "wind_level", "day", "horizon"]

# Default bins are parameters to breakdown helpers so they are not buried in route code.
DEFAULT_HORIZON_EDGES_HOURS = (0.0, 12.0, 24.0, 36.0, 48.0, np.inf)
DEFAULT_WIND_EDGES_MW = (0.0, 4000.0, 8000.0, 12000.0, np.inf)
MAPE_MIN_ABS_ACTUAL_MW = 1.0


@dataclass(frozen=True)
class Metrics:
    n_targets: int
    n_paired: int
    coverage: float
    mae: float | None
    rmse: float | None
    bias: float | None
    p50_abs_error: float | None
    p90_abs_error: float | None
    p95_abs_error: float | None
    mape: float | None
    p90_positive_error: float | None


def cutoff_for_start(
    start_time: pd.Timestamp,
    cutoff_hour: int,
    cutoff_minute: int,
) -> pd.Timestamp:
    """Decision cutoff is 09:00-style clock time on D-1, not a per-period offset.

    Every half-hour on delivery day D shares the same cutoff so the buyer sees
    the information set they had at gate close the previous morning.
    """
    start = _as_utc(start_time)
    delivery_midnight = start.normalize()
    return (
        delivery_midnight
        - pd.Timedelta(days=1)
        + pd.Timedelta(hours=cutoff_hour, minutes=cutoff_minute)
    )


def horizon_hours(start_time: pd.Timestamp, publish_time: pd.Timestamp) -> float:
    """Lead time of a forecast: how many hours before the target it was published."""
    delta = _as_utc(start_time) - _as_utc(publish_time)
    return float(delta.total_seconds() / 3600.0)


def select_latest_forecast_for_target(
    forecasts: pd.DataFrame,
    start_time: pd.Timestamp,
    cutoff: pd.Timestamp,
) -> pd.Series | None:
    """Latest forecast for one target whose publishTime is at or before cutoff.

    A publishTime exactly equal to cutoff is eligible (the buyer could have used it).
    Returns None when nothing was published in time.
    """
    start = _as_utc(start_time)
    cutoff_ts = _as_utc(cutoff)
    eligible = forecasts.loc[
        (_as_utc_series(forecasts["startTime"]) == start)
        & (_as_utc_series(forecasts["publishTime"]) <= cutoff_ts)
    ]
    if eligible.empty:
        return None
    idx = eligible["publishTime"].idxmax()
    return eligible.loc[idx]


def select_forecast_closest_horizon(
    forecasts: pd.DataFrame,
    start_time: pd.Timestamp,
    horizon_hours_target: float,
) -> pd.Series | None:
    """Forecast for one target whose lead time is closest to N hours.

    Used for the accuracy-vs-horizon view, not for the day-ahead decision.
    Ignores publishes after the target (those are not forecasts of the period).
    """
    start = _as_utc(start_time)
    for_target = forecasts.loc[_as_utc_series(forecasts["startTime"]) == start].copy()
    if for_target.empty:
        return None
    for_target = for_target.loc[_as_utc_series(for_target["publishTime"]) <= start]
    if for_target.empty:
        return None
    leads = (start - _as_utc_series(for_target["publishTime"])).dt.total_seconds() / 3600.0
    distance = (leads - horizon_hours_target).abs()
    best = distance.min()
    tied = for_target.loc[distance == best]
    idx = tied["publishTime"].idxmax()
    return tied.loc[idx]


def select_latest_forecasts(
    forecasts: pd.DataFrame,
    targets: pd.Series,
    cutoff_hour: int,
    cutoff_minute: int,
) -> pd.DataFrame:
    """Vectorised latest-before-cutoff selection for many target startTimes."""
    if forecasts.empty or len(targets) == 0:
        return pd.DataFrame(columns=["startTime", "publishTime", "generation", "horizon_hours"])

    fc = forecasts.copy()
    fc["startTime"] = _as_utc_series(fc["startTime"])
    fc["publishTime"] = _as_utc_series(fc["publishTime"])

    tg = pd.DataFrame({"startTime": _as_utc_series(pd.Series(targets)).drop_duplicates()})
    tg["cutoff"] = (
        tg["startTime"].dt.normalize()
        - pd.Timedelta(days=1)
        + pd.Timedelta(hours=cutoff_hour, minutes=cutoff_minute)
    )

    merged = fc.merge(tg, on="startTime", how="inner")
    eligible = merged.loc[merged["publishTime"] <= merged["cutoff"]]
    if eligible.empty:
        return pd.DataFrame(columns=["startTime", "publishTime", "generation", "horizon_hours"])

    chosen_idx = eligible.groupby("startTime", sort=False)["publishTime"].idxmax()
    selected = eligible.loc[chosen_idx, ["startTime", "publishTime", "generation"]].copy()
    selected["horizon_hours"] = (
        selected["startTime"] - selected["publishTime"]
    ).dt.total_seconds() / 3600.0
    return selected.reset_index(drop=True)


def pair_actuals_and_forecasts(
    actuals: pd.DataFrame,
    forecasts: pd.DataFrame,
    cutoff_hour: int,
    cutoff_minute: int,
) -> pd.DataFrame:
    """Left-join selected forecasts onto actuals. Missing forecasts stay as NA (not zero)."""
    actual = actuals.copy()
    actual["startTime"] = _as_utc_series(actual["startTime"])
    if "publishTime" in actual.columns:
        actual = actual.drop(columns=["publishTime"])
    actual = actual.rename(columns={"generation": "actual"})

    selected = select_latest_forecasts(forecasts, actual["startTime"], cutoff_hour, cutoff_minute)
    selected = selected.rename(columns={"generation": "forecast"})

    paired = actual.merge(selected, on="startTime", how="left")
    paired["error"] = paired["forecast"] - paired["actual"]
    paired["abs_error"] = paired["error"].abs()
    return paired


def compute_metrics(paired: pd.DataFrame) -> Metrics:
    """MAE / RMSE / bias / abs-error percentiles on rows that have both series.

    Coverage is paired / all target rows, so missing forecasts reduce coverage
    instead of pretending error is zero.
    """
    n_targets = int(len(paired))
    both = paired["actual"].notna() & paired["forecast"].notna()
    n_paired = int(both.sum())
    coverage = float(n_paired / n_targets) if n_targets else 0.0
    if n_paired == 0:
        return Metrics(
            n_targets=n_targets,
            n_paired=0,
            coverage=coverage,
            mae=None,
            rmse=None,
            bias=None,
            p50_abs_error=None,
            p90_abs_error=None,
            p95_abs_error=None,
            mape=None,
            p90_positive_error=None,
        )

    errors = paired.loc[both, "error"].to_numpy(dtype=float)
    abs_errors = np.abs(errors)
    actuals = paired.loc[both, "actual"].to_numpy(dtype=float)

    mape: float | None = None
    mape_mask = np.abs(actuals) >= MAPE_MIN_ABS_ACTUAL_MW
    if mape_mask.any():
        mape = float(np.mean(np.abs(errors[mape_mask] / actuals[mape_mask])))

    positive = errors[errors > 0]
    p90_positive = float(np.percentile(positive, 90)) if len(positive) else 0.0

    return Metrics(
        n_targets=n_targets,
        n_paired=n_paired,
        coverage=coverage,
        mae=float(np.mean(abs_errors)),
        rmse=float(np.sqrt(np.mean(errors**2))),
        bias=float(np.mean(errors)),
        p50_abs_error=float(np.percentile(abs_errors, 50)),
        p90_abs_error=float(np.percentile(abs_errors, 90)),
        p95_abs_error=float(np.percentile(abs_errors, 95)),
        mape=mape,
        p90_positive_error=p90_positive,
    )


def error_band(forecast_mw: float, p90_abs_error: float) -> tuple[float, float]:
    """Symmetric band around a forecast using month-wide (or subset) P90 |error|."""
    return forecast_mw - p90_abs_error, forecast_mw + p90_abs_error


def decision_from_paired(
    paired: pd.DataFrame,
    confidence: float = 0.9,
) -> dict[str, float | str | None]:
    """Buffer size from historical errors plus a shortfall-oriented over-forecast number."""
    both = paired["actual"].notna() & paired["forecast"].notna()
    if not both.any():
        return {
            "confidence": confidence,
            "buffer_mw": None,
            "shortfall_buffer_mw": None,
            "statement": "Not enough paired forecast and actual values to recommend a buffer.",
        }

    errors = paired.loc[both, "error"].to_numpy(dtype=float)
    q = confidence * 100.0
    buffer_mw = float(np.percentile(np.abs(errors), q))
    positive = errors[errors > 0]
    shortfall = float(np.percentile(positive, q)) if len(positive) else 0.0
    pct = int(round(confidence * 100))
    statement = (
        f"To cover ~{pct}% of historical forecast errors, hold a buffer of about "
        f"{round(buffer_mw)} MW. Over-forecast wind (positive error) is the shortfall "
        f"risk for the buyer; the {pct}th percentile of those over-forecasts is about "
        f"{round(shortfall)} MW."
    )
    return {
        "confidence": confidence,
        "buffer_mw": buffer_mw,
        "shortfall_buffer_mw": shortfall,
        "statement": statement,
    }


def metrics_by_group(
    paired: pd.DataFrame,
    by: BreakdownBy,
    horizon_edges: tuple[float, ...] = DEFAULT_HORIZON_EDGES_HOURS,
    wind_edges: tuple[float, ...] = DEFAULT_WIND_EDGES_MW,
) -> list[dict[str, object]]:
    """Compute the same metrics inside each breakdown bucket."""
    frame = paired.copy()
    if by == "hour":
        frame["group"] = _as_utc_series(frame["startTime"]).dt.hour.astype(str)
    elif by == "day":
        frame["group"] = _as_utc_series(frame["startTime"]).dt.strftime("%Y-%m-%d")
    elif by == "horizon":
        frame["group"] = pd.cut(
            frame["horizon_hours"],
            bins=list(horizon_edges),
            right=False,
            include_lowest=True,
        ).astype(str)
    elif by == "wind_level":
        frame["group"] = pd.cut(
            frame["actual"],
            bins=list(wind_edges),
            right=False,
            include_lowest=True,
        ).astype(str)
    else:
        raise ValueError(f"Unsupported breakdown: {by}")

    rows: list[dict[str, object]] = []
    for group_name, subset in frame.groupby("group", dropna=False, observed=False):
        metrics = compute_metrics(subset)
        rows.append({"group": str(group_name), **metrics.__dict__})
    return rows


def _as_utc(value: pd.Timestamp) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def _as_utc_series(series: pd.Series) -> pd.Series:
    converted = pd.to_datetime(series, utc=True)
    return converted
