/**
 * TypeScript types matching backend schemas for WindWise dashboard.
 */

export interface MetaResponse {
  min_date: string;
  max_date: string;
  available_dates: string[];
  default_cutoff_hour: number;
  default_cutoff_minute: number;
  total_actual_periods: number;
  forecast_coverage_pct: number;
}

export interface ForecastItem {
  startTime: string;
  actual: number | null;
  forecast: number | null;
  publishTime: string | null;
  horizonHours: number | null;
  errorBandLow: number | null;
  errorBandHigh: number | null;
  error: number | null;
}

export interface MetricsResponse {
  n_targets: number;
  n_paired: number;
  coverage: number;
  mae: number | null;
  rmse: number | null;
  bias: number | null;
  p50_abs_error: number | null;
  p90_abs_error: number | null;
  p95_abs_error: number | null;
  mape: number | null;
  p90_positive_error: number | null;
}

export interface HorizonMetricItem {
  group: string;
  horizon_hours: number | null;
  n_targets: number;
  n_paired: number;
  coverage: number;
  mae: number | null;
  rmse: number | null;
  bias: number | null;
  p50_abs_error: number | null;
  p90_abs_error: number | null;
  p95_abs_error: number | null;
  mape: number | null;
  p90_positive_error: number | null;
}

export interface BreakdownItem {
  group: string;
  n_targets: number;
  n_paired: number;
  coverage: number;
  mae: number | null;
  rmse: number | null;
  bias: number | null;
  p50_abs_error: number | null;
  p90_abs_error: number | null;
  p95_abs_error: number | null;
  mape: number | null;
  p90_positive_error: number | null;
}

export interface DecisionResponse {
  date: string;
  cutoff_hour: number;
  cutoff_minute: number;
  confidence: number;
  buffer_mw: number | null;
  shortfall_buffer_mw: number | null;
  statement: string;
}
