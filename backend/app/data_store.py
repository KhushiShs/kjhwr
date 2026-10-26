"""In-memory data store for Elexon actuals and forecasts parquet snapshots."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.config import get_settings
from app.core import pair_actuals_and_forecasts


class DataStore:
    """Loads and holds actuals and forecasts in memory for fast querying."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or get_settings().data_dir
        self._actuals: pd.DataFrame | None = None
        self._forecasts: pd.DataFrame | None = None
        self._available_dates: list[str] = []
        self._min_date: str = ""
        self._max_date: str = ""
        self._paired_cache: dict[tuple[int, int], pd.DataFrame] = {}

    def load(self) -> None:
        """Load parquet files into memory. Called once on application startup."""
        actuals_path = self.data_dir / "actuals.parquet"
        forecasts_path = self.data_dir / "forecasts.parquet"

        if not actuals_path.exists():
            raise FileNotFoundError(
                f"Actuals dataset not found at {actuals_path}. "
                "Run backend/ingestion/fetch_data.py to build the snapshot."
            )
        if not forecasts_path.exists():
            raise FileNotFoundError(
                f"Forecasts dataset not found at {forecasts_path}. "
                "Run backend/ingestion/fetch_data.py to build the snapshot."
            )

        actuals = pd.read_parquet(actuals_path)
        forecasts = pd.read_parquet(forecasts_path)

        # Ensure datetime columns are timezone-aware UTC
        actuals["startTime"] = pd.to_datetime(actuals["startTime"], utc=True)
        if "publishTime" in actuals.columns:
            actuals["publishTime"] = pd.to_datetime(actuals["publishTime"], utc=True)

        forecasts["startTime"] = pd.to_datetime(forecasts["startTime"], utc=True)
        forecasts["publishTime"] = pd.to_datetime(forecasts["publishTime"], utc=True)

        actuals = actuals.sort_values("startTime").reset_index(drop=True)
        forecasts = forecasts.sort_values(["startTime", "publishTime"]).reset_index(drop=True)

        self._actuals = actuals
        self._forecasts = forecasts

        dates = actuals["startTime"].dt.strftime("%Y-%m-%d").drop_duplicates().tolist()
        self._available_dates = sorted(dates)
        self._min_date = self._available_dates[0] if self._available_dates else ""
        self._max_date = self._available_dates[-1] if self._available_dates else ""
        self._paired_cache.clear()

    @property
    def actuals(self) -> pd.DataFrame:
        if self._actuals is None:
            raise RuntimeError("DataStore has not been loaded. Call load() first.")
        return self._actuals

    @property
    def forecasts(self) -> pd.DataFrame:
        if self._forecasts is None:
            raise RuntimeError("DataStore has not been loaded. Call load() first.")
        return self._forecasts

    @property
    def available_dates(self) -> list[str]:
        return self._available_dates

    @property
    def min_date(self) -> str:
        return self._min_date

    @property
    def max_date(self) -> str:
        return self._max_date

    @property
    def total_actual_periods(self) -> int:
        return len(self._actuals) if self._actuals is not None else 0

    def get_paired(self, cutoff_hour: int, cutoff_minute: int) -> pd.DataFrame:
        """Return cached or newly computed paired actuals and selected forecasts."""
        key = (cutoff_hour, cutoff_minute)
        if key not in self._paired_cache:
            paired = pair_actuals_and_forecasts(
                self.actuals, self.forecasts, cutoff_hour, cutoff_minute
            )
            self._paired_cache[key] = paired
        return self._paired_cache[key]


_data_store_instance: DataStore | None = None


def get_data_store() -> DataStore:
    """Return the global DataStore singleton, initializing if needed."""
    global _data_store_instance
    if _data_store_instance is None:
        _data_store_instance = DataStore()
        _data_store_instance.load()
    return _data_store_instance
