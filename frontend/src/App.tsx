import React, { useEffect, useState, useCallback } from "react";
import { Wind, Shield, Database, AlertCircle, RefreshCw } from "lucide-react";
import {
  fetchMeta,
  fetchForecast,
  fetchMetrics,
  fetchDecision,
  fetchMetricsByHorizon,
  fetchBreakdown,
} from "./api";
import type {
  BreakdownItem,
  DecisionResponse,
  ForecastItem,
  HorizonMetricItem,
  MetaResponse,
  MetricsResponse,
} from "./types";
import { Controls } from "./components/Controls";
import { ForecastChart } from "./components/ForecastChart";
import { KpiCards } from "./components/KpiCards";
import { DecisionBox } from "./components/DecisionBox";
import { HorizonChart } from "./components/HorizonChart";
import { BreakdownChart } from "./components/BreakdownChart";
import { WorstDaysTable } from "./components/WorstDaysTable";

export const App: React.FC = () => {
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [date, setDate] = useState<string>("2026-01-15");
  const [cutoffHour, setCutoffHour] = useState<number>(9);
  const [cutoffMinute, setCutoffMinute] = useState<number>(0);

  // Data states
  const [forecastItems, setForecastItems] = useState<ForecastItem[]>([]);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [decision, setDecision] = useState<DecisionResponse | null>(null);
  const [fixedHorizonItems, setFixedHorizonItems] = useState<HorizonMetricItem[]>([]);
  const [bucketedHorizonItems, setBucketedHorizonItems] = useState<HorizonMetricItem[]>([]);
  const [hourBreakdown, setHourBreakdown] = useState<BreakdownItem[]>([]);
  const [windLevelBreakdown, setWindLevelBreakdown] = useState<BreakdownItem[]>([]);
  const [dayBreakdown, setDayBreakdown] = useState<BreakdownItem[]>([]);

  // Loading and error states
  const [initialLoading, setInitialLoading] = useState<boolean>(true);
  const [forecastLoading, setForecastLoading] = useState<boolean>(false);
  const [metricsLoading, setMetricsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load metadata once
  useEffect(() => {
    let isMounted = true;
    async function loadMeta() {
      try {
        const data = await fetchMeta();
        if (isMounted) {
          setMeta(data);
          if (data.default_cutoff_hour !== undefined) {
            setCutoffHour(data.default_cutoff_hour);
          }
          if (data.default_cutoff_minute !== undefined) {
            setCutoffMinute(data.default_cutoff_minute);
          }
          if (data.available_dates && data.available_dates.length > 0) {
            // Keep default 2026-01-15 if present, else pick middle or first
            if (!data.available_dates.includes("2026-01-15")) {
              setDate(data.available_dates[0]);
            }
          }
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Failed to load API metadata");
        }
      } finally {
        if (isMounted) {
          setInitialLoading(false);
        }
      }
    }
    loadMeta();
    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch Day-Specific Data (Forecast intervals & decision recommendation)
  const loadDayData = useCallback(async (targetDate: string, hour: number, minute: number) => {
    setForecastLoading(true);
    try {
      const [fData, dData] = await Promise.all([
        fetchForecast(targetDate, hour, minute),
        fetchDecision(targetDate, hour, minute, 0.9),
      ]);
      setForecastItems(fData);
      setDecision(dData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load forecast for selected date");
    } finally {
      setForecastLoading(false);
    }
  }, []);

  // Fetch Month-Wide Metrics (Breakdowns & Horizon stats based on cutoff)
  const loadMonthMetrics = useCallback(async (hour: number, minute: number) => {
    setMetricsLoading(true);
    try {
      const [m, hFixed, hBucket, bHour, bWind, bDay] = await Promise.all([
        fetchMetrics(hour, minute),
        fetchMetricsByHorizon([12, 24, 36, 48], hour, minute),
        fetchMetricsByHorizon(undefined, hour, minute),
        fetchBreakdown("hour", hour, minute),
        fetchBreakdown("wind_level", hour, minute),
        fetchBreakdown("day", hour, minute),
      ]);
      setMetrics(m);
      setFixedHorizonItems(hFixed);
      setBucketedHorizonItems(hBucket);
      setHourBreakdown(bHour);
      setWindLevelBreakdown(bWind);
      setDayBreakdown(bDay);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load forecast error metrics");
    } finally {
      setMetricsLoading(false);
    }
  }, []);

  // Re-fetch day data when date or cutoff changes
  useEffect(() => {
    if (!initialLoading) {
      loadDayData(date, cutoffHour, cutoffMinute);
    }
  }, [date, cutoffHour, cutoffMinute, initialLoading, loadDayData]);

  // Re-fetch month metrics when cutoff changes
  useEffect(() => {
    if (!initialLoading) {
      loadMonthMetrics(cutoffHour, cutoffMinute);
    }
  }, [cutoffHour, cutoffMinute, initialLoading, loadMonthMetrics]);

  return (
    <div className="app-container">
      {/* 1. Header */}
      <header className="app-header">
        <div className="header-top">
          <div className="brand-wrapper">
            <div className="brand-logo">
              <Wind size={22} />
            </div>
            <div>
              <h1 className="brand-title">WindWise</h1>
            </div>
          </div>

          <div className="brand-badges">
            <span className="badge active">
              <Database size={12} /> Elexon BMRS (FUELHH + WINDFOR)
            </span>
            <span className="badge">
              <Shield size={12} /> January 2026 Delivery
            </span>
            <span className="badge">
              Gate Close: 09:20 UTC D-1
            </span>
          </div>
        </div>

        <p className="header-tagline">
          UK Day-Ahead Wind Forecast Decision Dashboard — Shows the latest wind forecast
          available when power buyers make day-ahead procurement decisions, measures accuracy
          quantitatively, and sizes safety buffers to mitigate volume shortfall risks.
        </p>
      </header>

      {/* Global Error Banner */}
      {error && (
        <div className="error-banner">
          <AlertCircle size={18} />
          <span>{error}</span>
          <button
            type="button"
            className="quick-date-btn"
            style={{ marginLeft: "auto" }}
            onClick={() => {
              setError(null);
              loadDayData(date, cutoffHour, cutoffMinute);
              loadMonthMetrics(cutoffHour, cutoffMinute);
            }}
          >
            <RefreshCw size={12} style={{ verticalAlign: "middle" }} /> Retry
          </button>
        </div>
      )}

      {/* 2. Controls */}
      <Controls
        date={date}
        onDateChange={setDate}
        cutoffHour={cutoffHour}
        onCutoffHourChange={setCutoffHour}
        cutoffMinute={cutoffMinute}
        onCutoffMinuteChange={setCutoffMinute}
        availableDates={meta?.available_dates || []}
        disabled={initialLoading}
      />

      {/* 3. Chart 1: Actual vs Forecast with Shaded Error Band */}
      <ForecastChart
        items={forecastItems}
        date={date}
        cutoffHour={cutoffHour}
        cutoffMinute={cutoffMinute}
      />

      {/* 4. KPI Cards */}
      <KpiCards metrics={metrics} loading={metricsLoading || initialLoading} />

      {/* 5. Decision Box */}
      <DecisionBox decision={decision} loading={forecastLoading || initialLoading} />

      {/* 6. Chart 2: Error vs Forecast Horizon */}
      <HorizonChart
        fixedHorizonItems={fixedHorizonItems}
        bucketedHorizonItems={bucketedHorizonItems}
        loading={metricsLoading || initialLoading}
      />

      {/* 7. Bottom Section: Chart 3 & Best/Worst Days Table */}
      <div className="dashboard-grid-2">
        <BreakdownChart
          hourBreakdown={hourBreakdown}
          windLevelBreakdown={windLevelBreakdown}
          loading={metricsLoading || initialLoading}
        />

        <WorstDaysTable
          dayBreakdown={dayBreakdown}
          selectedDate={date}
          onSelectDate={setDate}
          loading={metricsLoading || initialLoading}
        />
      </div>

      {/* Footer */}
      <footer
        style={{
          marginTop: "1.5rem",
          paddingTop: "1.25rem",
          borderTop: "1px solid var(--border-subtle)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
          fontSize: "0.8rem",
          color: "var(--text-subtle)",
        }}
      >
        <div>
          Data source: Elexon Insights Solution (BMRS) • National-level Great Britain wind generation
        </div>
        <div>
          All timestamps in UTC • Built with React, Vite & FastAPI
        </div>
      </footer>
    </div>
  );
};
