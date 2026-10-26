"""API integration tests for WindWise endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Create a test client with loaded data store."""
    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_meta(client: TestClient) -> None:
    response = client.get("/meta")
    assert response.status_code == 200
    data = response.json()

    assert data["min_date"] == "2026-01-01"
    assert data["max_date"] == "2026-01-31"
    assert len(data["available_dates"]) == 31
    assert data["default_cutoff_hour"] == 9
    assert data["default_cutoff_minute"] == 0
    assert data["total_actual_periods"] == 1488
    assert data["forecast_coverage_pct"] == 50.0  # 744 / 1488 hourly forecasts


def test_forecast_valid_date(client: TestClient) -> None:
    response = client.get("/forecast?date=2026-01-15&cutoff_hour=9&cutoff_minute=0")
    assert response.status_code == 200
    items = response.json()

    # 48 half-hour slots per day
    assert len(items) == 48

    first = items[0]
    assert "startTime" in first
    assert "actual" in first
    assert "forecast" in first
    assert "publishTime" in first
    assert "horizonHours" in first
    assert "errorBandLow" in first
    assert "errorBandHigh" in first
    assert "error" in first

    # In January data, :00 slots have forecasts, :30 slots do not
    hour_slot = next(i for i in items if i["startTime"].endswith("T00:00:00Z"))
    half_slot = next(i for i in items if i["startTime"].endswith("T00:30:00Z"))

    assert hour_slot["forecast"] is not None
    assert hour_slot["publishTime"] is not None
    assert hour_slot["horizonHours"] is not None
    assert hour_slot["errorBandLow"] is not None
    assert hour_slot["errorBandHigh"] is not None
    assert hour_slot["errorBandLow"] < hour_slot["forecast"] < hour_slot["errorBandHigh"]

    assert half_slot["actual"] is not None
    assert half_slot["forecast"] is None
    assert half_slot["errorBandLow"] is None


def test_forecast_invalid_dates(client: TestClient) -> None:
    # Malformed date string
    r1 = client.get("/forecast?date=not-a-date")
    assert r1.status_code == 400

    # Outside January 2026
    r2 = client.get("/forecast?date=2026-02-01")
    assert r2.status_code == 400

    # Sane range on cutoff hour
    r3 = client.get("/forecast?date=2026-01-15&cutoff_hour=25")
    assert r3.status_code == 422


def test_metrics(client: TestClient) -> None:
    response = client.get("/metrics?cutoff_hour=9&cutoff_minute=0")
    assert response.status_code == 200
    m = response.json()

    assert m["n_targets"] == 1488
    assert m["n_paired"] == 744
    assert m["coverage"] == 0.5
    assert m["mae"] is not None and m["mae"] > 0
    assert m["rmse"] is not None and m["rmse"] >= m["mae"]
    assert m["bias"] is not None
    assert m["p50_abs_error"] is not None
    assert m["p90_abs_error"] is not None
    assert m["p95_abs_error"] is not None
    assert m["p50_abs_error"] <= m["p90_abs_error"] <= m["p95_abs_error"]
    assert m["p90_positive_error"] is not None


def test_metrics_by_horizon_default(client: TestClient) -> None:
    response = client.get("/metrics/by-horizon?cutoff_hour=9&cutoff_minute=0")
    assert response.status_code == 200
    buckets = response.json()

    assert len(buckets) > 0
    for b in buckets:
        assert "group" in b
        assert "coverage" in b
        assert "n_targets" in b


def test_metrics_by_horizon_custom(client: TestClient) -> None:
    response = client.get("/metrics/by-horizon?horizons=12,24,36,48")
    assert response.status_code == 200
    items = response.json()

    assert len(items) == 4
    groups = [i["group"] for i in items]
    assert groups == ["12h", "24h", "36h", "48h"]

    # Verify each item contains metrics
    for item in items:
        assert item["n_paired"] == 744
        assert item["mae"] is not None
        assert item["rmse"] is not None


def test_metrics_breakdown(client: TestClient) -> None:
    # Hour breakdown
    r_hour = client.get("/metrics/breakdown?by=hour")
    assert r_hour.status_code == 200
    assert len(r_hour.json()) == 24

    # Day breakdown
    r_day = client.get("/metrics/breakdown?by=day")
    assert r_day.status_code == 200
    assert len(r_day.json()) == 31

    # Wind level breakdown
    r_wind = client.get("/metrics/breakdown?by=wind_level")
    assert r_wind.status_code == 200
    assert len(r_wind.json()) > 0

    # Invalid breakdown
    r_invalid = client.get("/metrics/breakdown?by=unsupported")
    assert r_invalid.status_code == 400


def test_decision(client: TestClient) -> None:
    response = client.get("/decision?date=2026-01-10&cutoff_hour=9&confidence=0.9")
    assert response.status_code == 200
    d = response.json()

    assert d["date"] == "2026-01-10"
    assert d["cutoff_hour"] == 9
    assert d["confidence"] == 0.9
    assert d["buffer_mw"] is not None and d["buffer_mw"] > 0
    assert d["shortfall_buffer_mw"] is not None and d["shortfall_buffer_mw"] > 0
    assert "To cover ~90% of historical forecast errors" in d["statement"]
    assert "shortfall risk" in d["statement"]


def test_decision_invalid_date(client: TestClient) -> None:
    response = client.get("/decision?date=2025-12-31")
    assert response.status_code == 400
