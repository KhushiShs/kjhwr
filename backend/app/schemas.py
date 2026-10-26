"""Pydantic v2 response and request schemas for WindWise API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Health check endpoint response."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(default="ok", description="Service health status")


class MetaResponse(BaseModel):
    """Metadata about the dataset range, available dates, and cutoff defaults."""

    model_config = ConfigDict(extra="forbid")

    min_date: str = Field(description="Earliest available target date (YYYY-MM-DD)")
    max_date: str = Field(description="Latest available target date (YYYY-MM-DD)")
    available_dates: list[str] = Field(description="List of available target dates in YYYY-MM-DD")
    default_cutoff_hour: int = Field(description="Default decision cutoff hour (UTC) on D-1")
    default_cutoff_minute: int = Field(description="Default decision cutoff minute (UTC) on D-1")
    total_actual_periods: int = Field(description="Total target half-hour periods in dataset")
    forecast_coverage_pct: float = Field(
        description="Percentage of actual periods that have an eligible forecast at default cutoff"
    )


class ForecastItem(BaseModel):
    """One half-hour interval for a delivery day with paired forecast and error band."""

    model_config = ConfigDict(extra="forbid")

    startTime: str = Field(description="Target period start time (ISO 8601 UTC)")
    actual: float | None = Field(default=None, description="Actual generation in MW")
    forecast: float | None = Field(default=None, description="Selected forecast generation in MW")
    publishTime: str | None = Field(
        default=None, description="Publish time of the selected forecast (ISO 8601 UTC)"
    )
    horizonHours: float | None = Field(
        default=None, description="Lead time in hours (startTime - publishTime)"
    )
    errorBandLow: float | None = Field(
        default=None, description="Lower bound of forecast error band (MW)"
    )
    errorBandHigh: float | None = Field(
        default=None, description="Upper bound of forecast error band (MW)"
    )
    error: float | None = Field(
        default=None, description="Forecast error: forecast - actual (positive = over-forecast)"
    )


class MetricsResponse(BaseModel):
    """Error metrics computed across paired targets."""

    model_config = ConfigDict(extra="forbid")

    n_targets: int = Field(description="Total target periods in sample")
    n_paired: int = Field(description="Periods with both actual and forecast")
    coverage: float = Field(description="Coverage ratio: n_paired / n_targets (0.0 to 1.0)")
    mae: float | None = Field(default=None, description="Mean Absolute Error in MW")
    rmse: float | None = Field(default=None, description="Root Mean Squared Error in MW")
    bias: float | None = Field(
        default=None, description="Mean error in MW (positive = over-forecast)"
    )
    p50_abs_error: float | None = Field(
        default=None, description="50th percentile (median) of absolute error (MW)"
    )
    p90_abs_error: float | None = Field(
        default=None, description="90th percentile of absolute error (MW)"
    )
    p95_abs_error: float | None = Field(
        default=None, description="95th percentile of absolute error (MW)"
    )
    mape: float | None = Field(
        default=None, description="Mean Absolute Percentage Error (ratio, where actual >= 1 MW)"
    )
    p90_positive_error: float | None = Field(
        default=None,
        description="90th percentile of positive errors (over-forecast shortfall risk, MW)",
    )


class HorizonMetricItem(BaseModel):
    """Metrics for a specific forecast horizon bucket or target lead time."""

    model_config = ConfigDict(extra="forbid")

    group: str = Field(
        description="Horizon bucket or target lead time label (e.g. '12h' or '[0.0, 12.0)')"
    )
    horizon_hours: float | None = Field(
        default=None, description="Nominal horizon hours if fixed target horizon"
    )
    n_targets: int
    n_paired: int
    coverage: float
    mae: float | None = None
    rmse: float | None = None
    bias: float | None = None
    p50_abs_error: float | None = None
    p90_abs_error: float | None = None
    p95_abs_error: float | None = None
    mape: float | None = None
    p90_positive_error: float | None = None


class BreakdownItem(BaseModel):
    """Metrics grouped by hour of day, wind generation level, or calendar day."""

    model_config = ConfigDict(extra="forbid")

    group: str = Field(
        description="Bucket identifier (e.g. hour '0'..'23', wind bucket, or YYYY-MM-DD)"
    )
    n_targets: int
    n_paired: int
    coverage: float
    mae: float | None = None
    rmse: float | None = None
    bias: float | None = None
    p50_abs_error: float | None = None
    p90_abs_error: float | None = None
    p95_abs_error: float | None = None
    mape: float | None = None
    p90_positive_error: float | None = None


class DecisionResponse(BaseModel):
    """Decision buffer recommendation for a day-ahead electricity buyer."""

    model_config = ConfigDict(extra="forbid")

    date: str = Field(description="Target delivery date (YYYY-MM-DD)")
    cutoff_hour: int = Field(description="Decision cutoff hour on D-1")
    cutoff_minute: int = Field(description="Decision cutoff minute on D-1")
    confidence: float = Field(description="Target confidence level (e.g. 0.90 for 90%)")
    buffer_mw: float | None = Field(
        default=None, description="Recommended safety buffer in MW based on |error| percentile"
    )
    shortfall_buffer_mw: float | None = Field(
        default=None,
        description="Shortfall buffer in MW based on over-forecast (positive error) percentile",
    )
    statement: str = Field(description="Plain-language recommendation for the buyer")
