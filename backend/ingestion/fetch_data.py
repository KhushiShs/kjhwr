"""Build cached Elexon BMRS parquet snapshots (FUELHH actuals, WINDFOR forecasts).

This script is the only place that calls Elexon. The running API must not.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from collections.abc import Iterator

import httpx
import pandas as pd

# Confirmed from https://data.elexon.co.uk/swagger/v1/swagger.json
# servers[0].url
BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
FUELHH_PATH = "/datasets/FUELHH/stream"
WINDFOR_PATH = "/datasets/WINDFOR/stream"

# Target delivery window (UTC). Last half-hour of January starts at 23:30.
TARGET_START = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
TARGET_END = datetime(2026, 1, 31, 23, 30, tzinfo=timezone.utc)

# WINDFOR only filters by publish time. Early-January targets were published in late December.
FORECAST_PUBLISH_START = datetime(2025, 12, 15, 0, 0, tzinfo=timezone.utc)
FORECAST_PUBLISH_END_EXCLUSIVE = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)

CHUNK_DAYS = 7
MAX_RETRIES = 6
RETRY_BASE_SECONDS = 2.0
REQUEST_PAUSE_SECONDS = 0.4
REQUEST_TIMEOUT = 180.0

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("DATA_DIR", REPO_ROOT / "data"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("ingestion")


def iso_z(dt: datetime) -> str:
    """Format a UTC datetime the way the Insights examples use (RFC 3339 with Z)."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def week_date_chunks(start: date, end: date) -> Iterator[tuple[date, date]]:
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=CHUNK_DAYS - 1), end)
        yield current, chunk_end
        current = chunk_end + timedelta(days=1)


def week_datetime_chunks(start: datetime, end_exclusive: datetime) -> Iterator[tuple[datetime, datetime]]:
    current = start
    while current < end_exclusive:
        chunk_end = min(current + timedelta(days=CHUNK_DAYS), end_exclusive)
        yield current, chunk_end
        current = chunk_end


def fetch_json(client: httpx.Client, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    """GET a stream endpoint with retries on 429/5xx and network errors."""
    url = f"{BASE_URL}{path}"
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.get(url, params=params)
            if response.status_code == 429 or response.status_code >= 500:
                wait = RETRY_BASE_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "HTTP %s on %s (attempt %s/%s); sleeping %.1fs",
                    response.status_code,
                    path,
                    attempt,
                    MAX_RETRIES,
                    wait,
                )
                time.sleep(wait)
                last_error = httpx.HTTPStatusError(
                    f"{response.status_code}",
                    request=response.request,
                    response=response,
                )
                continue
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError(f"Expected a JSON array from {path}, got {type(payload)}")
            time.sleep(REQUEST_PAUSE_SECONDS)
            return payload
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            wait = RETRY_BASE_SECONDS * (2 ** (attempt - 1))
            logger.warning(
                "Transport error on %s (attempt %s/%s): %s; sleeping %.1fs",
                path,
                attempt,
                MAX_RETRIES,
                exc,
                wait,
            )
            time.sleep(wait)
            last_error = exc
    raise RuntimeError(f"Failed to fetch {path} after {MAX_RETRIES} attempts") from last_error


def parse_utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True)


def fetch_actuals(client: httpx.Client) -> pd.DataFrame:
    """National wind outturn for January 2026 settlement dates."""
    rows: list[dict[str, Any]] = []
    for start, end in week_date_chunks(date(2026, 1, 1), date(2026, 1, 31)):
        params = {
            "settlementDateFrom": start.isoformat(),
            "settlementDateTo": end.isoformat(),
            "fuelType": "WIND",
        }
        logger.info("FUELHH %s to %s", start, end)
        chunk = fetch_json(client, FUELHH_PATH, params)
        logger.info("  %s rows", len(chunk))
        rows.extend(chunk)

    frame = pd.DataFrame(rows)
    if frame.empty:
        raise RuntimeError("FUELHH returned no rows")

    if "fuelType" in frame.columns:
        frame = frame.loc[frame["fuelType"] == "WIND"].copy()

    frame["startTime"] = parse_utc(frame["startTime"])
    if "publishTime" in frame.columns:
        frame["publishTime"] = parse_utc(frame["publishTime"])
    frame["generation"] = pd.to_numeric(frame["generation"], errors="coerce")

    before = len(frame)
    frame = frame.drop_duplicates()
    logger.info("FUELHH dropped %s exact duplicate rows", before - len(frame))

    frame = frame.loc[
        (frame["startTime"] >= TARGET_START) & (frame["startTime"] <= TARGET_END)
    ].copy()
    frame = frame.sort_values("startTime").reset_index(drop=True)
    return frame


def fetch_forecasts(client: httpx.Client) -> pd.DataFrame:
    """All WINDFOR rows published in the wide window, then keep January 2026 targets."""
    rows: list[dict[str, Any]] = []
    for start, end in week_datetime_chunks(FORECAST_PUBLISH_START, FORECAST_PUBLISH_END_EXCLUSIVE):
        params = {
            "publishDateTimeFrom": iso_z(start),
            "publishDateTimeTo": iso_z(end),
        }
        logger.info("WINDFOR publish %s to %s", iso_z(start), iso_z(end))
        chunk = fetch_json(client, WINDFOR_PATH, params)
        logger.info("  %s rows", len(chunk))
        rows.extend(chunk)

    frame = pd.DataFrame(rows)
    if frame.empty:
        raise RuntimeError("WINDFOR returned no rows")

    frame["startTime"] = parse_utc(frame["startTime"])
    frame["publishTime"] = parse_utc(frame["publishTime"])
    frame["generation"] = pd.to_numeric(frame["generation"], errors="coerce")

    before = len(frame)
    frame = frame.drop_duplicates()
    logger.info("WINDFOR dropped %s exact duplicate rows", before - len(frame))

    frame = frame.loc[
        (frame["startTime"] >= TARGET_START) & (frame["startTime"] <= TARGET_END)
    ].copy()
    frame = frame.sort_values(["startTime", "publishTime"]).reset_index(drop=True)
    return frame


def expected_half_hours() -> pd.DatetimeIndex:
    return pd.date_range(TARGET_START, TARGET_END, freq="30min", tz="UTC")


def report_gaps(name: str, start_times: pd.Series) -> None:
    expected = expected_half_hours()
    unique = pd.DatetimeIndex(start_times.dropna().unique()).sort_values()
    missing = expected.difference(unique)
    extra = unique.difference(expected)
    logger.info("%s unique target periods: %s (expected %s)", name, len(unique), len(expected))
    logger.info("%s missing periods: %s", name, len(missing))
    if len(missing) and len(missing) <= 20:
        logger.info("  missing: %s", list(missing.astype(str)))
    elif len(missing):
        logger.info("  first missing: %s last missing: %s", missing[0], missing[-1])
    logger.info("%s unexpected periods (outside Jan 2026 30-min grid): %s", name, len(extra))


def sanity_checks(actuals: pd.DataFrame, forecasts: pd.DataFrame) -> None:
    logger.info("=== sanity checks ===")
    logger.info("actuals rows=%s", len(actuals))
    logger.info("actuals startTime min=%s max=%s", actuals["startTime"].min(), actuals["startTime"].max())
    logger.info("actuals null generation=%s", int(actuals["generation"].isna().sum()))
    logger.info("actuals duplicate startTime rows=%s", int(actuals.duplicated(subset=["startTime"]).sum()))
    report_gaps("actuals", actuals["startTime"])

    logger.info("forecasts rows=%s", len(forecasts))
    logger.info(
        "forecasts startTime min=%s max=%s",
        forecasts["startTime"].min(),
        forecasts["startTime"].max(),
    )
    logger.info(
        "forecasts publishTime min=%s max=%s",
        forecasts["publishTime"].min(),
        forecasts["publishTime"].max(),
    )
    logger.info("forecasts null generation=%s", int(forecasts["generation"].isna().sum()))
    report_gaps("forecasts (any publish)", forecasts["startTime"])
    logger.info(
        "forecasts exact duplicate rows remaining=%s",
        int(forecasts.duplicated().sum()),
    )


def save_parquet(actuals: pd.DataFrame, forecasts: pd.DataFrame) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    actual_cols = [c for c in ["startTime", "generation", "publishTime", "settlementDate", "settlementPeriod", "fuelType"] if c in actuals.columns]
    forecast_cols = [c for c in ["startTime", "publishTime", "generation"] if c in forecasts.columns]
    actual_path = DATA_DIR / "actuals.parquet"
    forecast_path = DATA_DIR / "forecasts.parquet"
    actuals[actual_cols].to_parquet(actual_path, index=False)
    forecasts[forecast_cols].to_parquet(forecast_path, index=False)
    logger.info("wrote %s (%s rows)", actual_path, len(actuals))
    logger.info("wrote %s (%s rows)", forecast_path, len(forecasts))


def main() -> int:
    logger.info("DATA_DIR=%s", DATA_DIR)
    with httpx.Client(timeout=REQUEST_TIMEOUT, headers={"Accept": "application/json"}) as client:
        actuals = fetch_actuals(client)
        forecasts = fetch_forecasts(client)
    sanity_checks(actuals, forecasts)
    save_parquet(actuals, forecasts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
