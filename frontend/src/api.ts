/**
 * Typed API client for WindWise backend.
 */

import type {
  BreakdownItem,
  DecisionResponse,
  ForecastItem,
  HorizonMetricItem,
  MetaResponse,
  MetricsResponse,
} from "./types";

const API_BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `HTTP ${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // keep fallback detail
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function fetchMeta(): Promise<MetaResponse> {
  const res = await fetch(`${API_BASE_URL}/meta`);
  return handleResponse<MetaResponse>(res);
}

export async function fetchForecast(
  date: string,
  cutoffHour: number,
  cutoffMinute: number = 0
): Promise<ForecastItem[]> {
  const params = new URLSearchParams({
    date,
    cutoff_hour: String(cutoffHour),
    cutoff_minute: String(cutoffMinute),
  });
  const res = await fetch(`${API_BASE_URL}/forecast?${params.toString()}`);
  return handleResponse<ForecastItem[]>(res);
}

export async function fetchMetrics(
  cutoffHour: number,
  cutoffMinute: number = 0
): Promise<MetricsResponse> {
  const params = new URLSearchParams({
    cutoff_hour: String(cutoffHour),
    cutoff_minute: String(cutoffMinute),
  });
  const res = await fetch(`${API_BASE_URL}/metrics?${params.toString()}`);
  return handleResponse<MetricsResponse>(res);
}

export async function fetchMetricsByHorizon(
  horizons?: number[],
  cutoffHour: number = 9,
  cutoffMinute: number = 0
): Promise<HorizonMetricItem[]> {
  const params = new URLSearchParams({
    cutoff_hour: String(cutoffHour),
    cutoff_minute: String(cutoffMinute),
  });
  if (horizons && horizons.length > 0) {
    params.set("horizons", horizons.join(","));
  }
  const res = await fetch(`${API_BASE_URL}/metrics/by-horizon?${params.toString()}`);
  return handleResponse<HorizonMetricItem[]>(res);
}

export async function fetchBreakdown(
  by: "hour" | "wind_level" | "day",
  cutoffHour: number,
  cutoffMinute: number = 0
): Promise<BreakdownItem[]> {
  const params = new URLSearchParams({
    by,
    cutoff_hour: String(cutoffHour),
    cutoff_minute: String(cutoffMinute),
  });
  const res = await fetch(`${API_BASE_URL}/metrics/breakdown?${params.toString()}`);
  return handleResponse<BreakdownItem[]>(res);
}

export async function fetchDecision(
  date: string,
  cutoffHour: number,
  cutoffMinute: number = 0,
  confidence: number = 0.9
): Promise<DecisionResponse> {
  const params = new URLSearchParams({
    date,
    cutoff_hour: String(cutoffHour),
    cutoff_minute: String(cutoffMinute),
    confidence: String(confidence),
  });
  const res = await fetch(`${API_BASE_URL}/decision?${params.toString()}`);
  return handleResponse<DecisionResponse>(res);
}
