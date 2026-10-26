"""HTTP route handlers for WindWise day-ahead wind forecast decision dashboard."""

from __future__ import annotations

import re
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config import Settings, get_settings
from app.core import (
    compute_metrics,
    decision_from_paired,
    metrics_by_group,
)
from app.data_store import DataStore, get_data_store
from app.schemas import (
    BreakdownItem,
    DecisionResponse,
    ForecastItem,
    HealthResponse,
    HorizonMetricItem,
    MetaResponse,
    MetricsResponse,
)

router = APIRouter()
DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_date(date: str, data_store: DataStore) -> None:
    """Validate that date is YYYY-MM-DD and exists within the January 2026 dataset."""
    if not DATE_REGEX.match(date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format '{date}'. Expected YYYY-MM-DD.",
        )
    if date not in data_store.available_dates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Date '{date}' is outside available range "
                f"({data_store.min_date} to {data_store.max_date})."
            ),
        )


@router.get("/health", response_model=HealthResponse, tags=["System"])
def get_health() -> HealthResponse:
    """Service liveness probe."""
    return HealthResponse(status="ok")


@router.get("/meta", response_model=MetaResponse, tags=["Metadata"])
def get_meta(
    data_store: Annotated[DataStore, Depends(get_data_store)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MetaResponse:
    """Dataset metadata, available dates, and system defaults."""
    default_paired = data_store.get_paired(
        settings.default_cutoff_hour, settings.default_cutoff_minute
    )
    metrics = compute_metrics(default_paired)
    coverage_pct = round(metrics.coverage * 100.0, 2)

    return MetaResponse(
        min_date=data_store.min_date,
        max_date=data_store.max_date,
        available_dates=data_store.available_dates,
        default_cutoff_hour=settings.default_cutoff_hour,
        default_cutoff_minute=settings.default_cutoff_minute,
        total_actual_periods=data_store.total_actual_periods,
        forecast_coverage_pct=coverage_pct,
    )


@router.get("/forecast", response_model=list[ForecastItem], tags=["Forecast"])
def get_forecast(
    date: Annotated[str, Query(description="Target delivery date (YYYY-MM-DD)")],
    cutoff_hour: Annotated[
        int, Query(ge=0, le=23, description="Decision cutoff hour (0-23 UTC on D-1)")
    ] = 9,
    cutoff_minute: Annotated[
        int, Query(ge=0, le=59, description="Decision cutoff minute (0-59 UTC on D-1)")
    ] = 0,
    data_store: Annotated[DataStore, Depends(get_data_store)] = None,  # type: ignore[assignment]
) -> list[ForecastItem]:
    """Retrieve 48 half-hour intervals for delivery date with selected forecast and P90 band."""
    validate_date(date, data_store)

    paired = data_store.get_paired(cutoff_hour, cutoff_minute)
    month_metrics = compute_metrics(paired)
    p90 = month_metrics.p90_abs_error or 0.0

    target_date = pd.Timestamp(date, tz="UTC").date()
    day_slice = paired.loc[paired["startTime"].dt.date == target_date]

    items: list[ForecastItem] = []
    for _, row in day_slice.iterrows():
        actual = None if pd.isna(row["actual"]) else float(row["actual"])
        forecast = None if pd.isna(row["forecast"]) else float(row["forecast"])
        publish_time = (
            None
            if pd.isna(row.get("publishTime"))
            else row["publishTime"].strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        lead = None if pd.isna(row.get("horizon_hours")) else round(float(row["horizon_hours"]), 2)
        err = None if pd.isna(row.get("error")) else round(float(row["error"]), 2)

        band_low: float | None = None
        band_high: float | None = None
        if forecast is not None:
            band_low = round(forecast - p90, 2)
            band_high = round(forecast + p90, 2)

        items.append(
            ForecastItem(
                startTime=row["startTime"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                actual=actual,
                forecast=forecast,
                publishTime=publish_time,
                horizonHours=lead,
                errorBandLow=band_low,
                errorBandHigh=band_high,
                error=err,
            )
        )

    return items


@router.get("/metrics", response_model=MetricsResponse, tags=["Metrics"])
def get_metrics(
    cutoff_hour: Annotated[int, Query(ge=0, le=23)] = 9,
    cutoff_minute: Annotated[int, Query(ge=0, le=59)] = 0,
    data_store: Annotated[DataStore, Depends(get_data_store)] = None,  # type: ignore[assignment]
) -> MetricsResponse:
    """Compute overall month-wide forecast accuracy metrics at given decision cutoff."""
    paired = data_store.get_paired(cutoff_hour, cutoff_minute)
    metrics = compute_metrics(paired)
    return MetricsResponse(**metrics.__dict__)


@router.get("/metrics/by-horizon", response_model=list[HorizonMetricItem], tags=["Metrics"])
def get_metrics_by_horizon(
    horizons: Annotated[
        list[str] | None,
        Query(
            description=(
                "Optional target lead times in hours (e.g. ['12', '24', '36', '48'] "
                "or comma-separated '12,24,36,48'). If omitted, returns lead-time bins."
            )
        ),
    ] = None,
    cutoff_hour: Annotated[int, Query(ge=0, le=23)] = 9,
    cutoff_minute: Annotated[int, Query(ge=0, le=59)] = 0,
    data_store: Annotated[DataStore, Depends(get_data_store)] = None,  # type: ignore[assignment]
) -> list[HorizonMetricItem]:
    """Metrics breakdown across forecast lead times."""
    # Parse potential comma-separated string or array of numbers
    target_horizons: list[float] = []
    if horizons:
        for item in horizons:
            for part in str(item).split(","):
                part_clean = part.strip()
                if part_clean:
                    try:
                        target_horizons.append(float(part_clean))
                    except ValueError:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid horizon value '{part_clean}'. Expected a number.",
                        )

    if not target_horizons:
        # Default bucketed breakdown using paired day-ahead data
        paired = data_store.get_paired(cutoff_hour, cutoff_minute)
        rows = metrics_by_group(paired, by="horizon")
        return [HorizonMetricItem(**r) for r in rows]

    # Target specific lead-time horizons (e.g. 12h, 24h, 36h, 48h)
    actuals = data_store.actuals.rename(columns={"generation": "actual"})
    forecasts = data_store.forecasts.copy()
    forecasts["lead"] = (
        forecasts["startTime"] - forecasts["publishTime"]
    ).dt.total_seconds() / 3600.0
    forecasts = forecasts.loc[forecasts["lead"] >= 0]

    results: list[HorizonMetricItem] = []
    for h in sorted(target_horizons):
        forecasts["dist"] = (forecasts["lead"] - h).abs()
        best_idx = (
            forecasts.sort_values("publishTime", ascending=False)
            .groupby("startTime", sort=False)["dist"]
            .idxmin()
        )
        chosen = forecasts.loc[best_idx, ["startTime", "generation", "lead"]].rename(
            columns={"generation": "forecast"}
        )

        paired_h = actuals.merge(chosen, on="startTime", how="left")
        paired_h["error"] = paired_h["forecast"] - paired_h["actual"]
        paired_h["abs_error"] = paired_h["error"].abs()

        m = compute_metrics(paired_h)
        label = f"{int(h)}h" if h.is_integer() else f"{h}h"
        results.append(
            HorizonMetricItem(
                group=label,
                horizon_hours=h,
                **m.__dict__,
            )
        )

    return results


@router.get("/metrics/breakdown", response_model=list[BreakdownItem], tags=["Metrics"])
def get_metrics_breakdown(
    by: Annotated[
        str,
        Query(description="Breakdown dimension: 'hour', 'wind_level', or 'day'"),
    ],
    cutoff_hour: Annotated[int, Query(ge=0, le=23)] = 9,
    cutoff_minute: Annotated[int, Query(ge=0, le=59)] = 0,
    data_store: Annotated[DataStore, Depends(get_data_store)] = None,  # type: ignore[assignment]
) -> list[BreakdownItem]:
    """Metrics broken down by target hour of day, actual wind generation level, or day."""
    if by not in ("hour", "wind_level", "day"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid breakdown dimension '{by}'. Must be one of: hour, wind_level, day.",
        )

    paired = data_store.get_paired(cutoff_hour, cutoff_minute)
    rows = metrics_by_group(paired, by=by)  # type: ignore[arg-type]
    return [BreakdownItem(**r) for r in rows]


@router.get("/decision", response_model=DecisionResponse, tags=["Decision"])
def get_decision(
    date: Annotated[str, Query(description="Target delivery date (YYYY-MM-DD)")],
    cutoff_hour: Annotated[int, Query(ge=0, le=23)] = 9,
    cutoff_minute: Annotated[int, Query(ge=0, le=59)] = 0,
    confidence: Annotated[
        float,
        Query(gt=0.0, lt=1.0, description="Confidence level for safety buffer (e.g. 0.90)"),
    ] = 0.9,
    data_store: Annotated[DataStore, Depends(get_data_store)] = None,  # type: ignore[assignment]
) -> DecisionResponse:
    """Calculate safety buffer recommendation and shortfall buffer for power buyer."""
    validate_date(date, data_store)

    paired = data_store.get_paired(cutoff_hour, cutoff_minute)
    decision = decision_from_paired(paired, confidence=confidence)

    return DecisionResponse(
        date=date,
        cutoff_hour=cutoff_hour,
        cutoff_minute=cutoff_minute,
        confidence=confidence,
        buffer_mw=round(decision["buffer_mw"], 1) if decision["buffer_mw"] is not None else None,
        shortfall_buffer_mw=(
            round(decision["shortfall_buffer_mw"], 1)
            if decision["shortfall_buffer_mw"] is not None
            else None
        ),
        statement=str(decision["statement"]),
    )
