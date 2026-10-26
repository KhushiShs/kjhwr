import React from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { Activity, Info } from "lucide-react";
import type { ForecastItem } from "../types";

interface ForecastChartProps {
  items: ForecastItem[];
  date: string;
  cutoffHour: number;
  cutoffMinute: number;
}

interface ChartRow {
  timeLabel: string;
  fullTime: string;
  actual: number | null;
  forecast: number | null;
  bandRange: [number, number] | null;
  bandLow: number | null;
  bandHigh: number | null;
  horizonHours: number | null;
  publishTime: string | null;
  error: number | null;
}

export const ForecastChart: React.FC<ForecastChartProps> = ({
  items,
  date,
  cutoffHour,
  cutoffMinute,
}) => {
  const chartData: ChartRow[] = items.map((item) => {
    const d = new Date(item.startTime);
    const hours = String(d.getUTCHours()).padStart(2, "0");
    const minutes = String(d.getUTCMinutes()).padStart(2, "0");
    const timeLabel = `${hours}:${minutes}`;

    let bandRange: [number, number] | null = null;
    if (item.errorBandLow !== null && item.errorBandHigh !== null) {
      bandRange = [Math.max(0, item.errorBandLow), item.errorBandHigh];
    }

    return {
      timeLabel,
      fullTime: item.startTime,
      actual: item.actual,
      forecast: item.forecast,
      bandRange,
      bandLow: item.errorBandLow !== null ? Math.max(0, item.errorBandLow) : null,
      bandHigh: item.errorBandHigh,
      horizonHours: item.horizonHours,
      publishTime: item.publishTime,
      error: item.error,
    };
  });

  const cutoffStr = `${String(cutoffHour).padStart(2, "0")}:${String(cutoffMinute).padStart(2, "0")} UTC (D-1)`;

  return (
    <div className="card" id="forecast-actuals-chart-card">
      <div className="card-header">
        <div>
          <div className="card-title-group">
            <Activity size={18} color="#38bdf8" />
            <h2 className="card-title">Day-Ahead Wind Forecast vs Actual Generation</h2>
          </div>
          <p className="card-help-text">
            Delivery Date: <strong>{date}</strong> • Decision Cutoff: <strong>{cutoffStr}</strong>
          </p>
        </div>

        <div className="legend-inline">
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: "#10b981" }} />
            <span>Actual Wind (FUELHH)</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: "#38bdf8" }} />
            <span>Day-Ahead Forecast (WINDFOR)</span>
          </div>
          <div className="legend-item">
            <span
              className="legend-color"
              style={{
                backgroundColor: "rgba(56, 189, 248, 0.25)",
                border: "1px dashed #38bdf8",
              }}
            />
            <span>P90 Error Band (± Historical Coverage)</span>
          </div>
        </div>
      </div>

      <div className="chart-wrapper">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
            <XAxis
              dataKey="timeLabel"
              stroke="#6b7280"
              tick={{ fontSize: 12, fill: "#9ca3af" }}
              tickLine={false}
              interval={3}
            />
            <YAxis
              stroke="#6b7280"
              tick={{ fontSize: 12, fill: "#9ca3af" }}
              tickLine={false}
              unit=" MW"
              width={75}
            />
            <Tooltip content={<CustomTooltip />} />

            {/* Shaded P90 uncertainty band */}
            <Area
              type="monotone"
              dataKey="bandRange"
              fill="rgba(56, 189, 248, 0.12)"
              stroke="transparent"
              isAnimationActive={false}
              connectNulls
            />

            {/* Actual generation line */}
            <Line
              type="monotone"
              dataKey="actual"
              name="Actual Wind"
              stroke="#10b981"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 5, fill: "#10b981", stroke: "#064e3b" }}
              isAnimationActive={false}
            />

            {/* Selected day-ahead forecast line */}
            <Line
              type="monotone"
              dataKey="forecast"
              name="Day-Ahead Forecast"
              stroke="#38bdf8"
              strokeWidth={2.5}
              strokeDasharray="4 2"
              dot={{ r: 3, fill: "#38bdf8" }}
              activeDot={{ r: 6, fill: "#38bdf8", stroke: "#0c4a6e" }}
              connectNulls
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="sign-explainer">
        <Info size={14} style={{ flexShrink: 0, marginTop: "2px", color: "#38bdf8" }} />
        <span>
          <strong>How to read:</strong> The cyan dashed line indicates the newest forecast available
          prior to {cutoffStr}. Gaps on the forecast line indicate 30-minute intervals where no
          sub-hourly forecast was published before gate close (Elexon WINDFOR publishes hourly
          targets). The shaded band represents the empirical P90 absolute error margin.
        </span>
      </div>
    </div>
  );
};

const CustomTooltip: React.FC<any> = ({ active, payload }) => {
  if (!active || !payload || !payload.length) return null;

  const data: ChartRow = payload[0]?.payload;
  if (!data) return null;

  return (
    <div className="custom-chart-tooltip">
      <div className="tooltip-time">{data.timeLabel} UTC (Target Period)</div>
      <div className="tooltip-row">
        <span>Actual Generation:</span>
        <strong style={{ color: "#10b981" }}>
          {data.actual !== null ? `${Math.round(data.actual).toLocaleString()} MW` : "N/A"}
        </strong>
      </div>
      <div className="tooltip-row">
        <span>Day-Ahead Forecast:</span>
        <strong style={{ color: "#38bdf8" }}>
          {data.forecast !== null ? `${Math.round(data.forecast).toLocaleString()} MW` : "No forecast at cutoff"}
        </strong>
      </div>
      {data.error !== null && (
        <div className="tooltip-row">
          <span>Error (Forecast - Actual):</span>
          <strong style={{ color: data.error > 0 ? "#f59e0b" : "#93c5fd" }}>
            {data.error > 0 ? `+${Math.round(data.error).toLocaleString()} MW` : `${Math.round(data.error).toLocaleString()} MW`}
          </strong>
        </div>
      )}
      {data.bandLow !== null && data.bandHigh !== null && (
        <div className="tooltip-row" style={{ fontSize: "0.75rem", color: "#64748b" }}>
          <span>P90 Band:</span>
          <span>
            {Math.round(data.bandLow).toLocaleString()} – {Math.round(data.bandHigh).toLocaleString()} MW
          </span>
        </div>
      )}
      {data.publishTime && (
        <div className="tooltip-row" style={{ fontSize: "0.75rem", color: "#64748b" }}>
          <span>Published:</span>
          <span>{data.publishTime.replace("T", " ").replace("Z", " UTC")}</span>
        </div>
      )}
      {data.horizonHours !== null && (
        <div className="tooltip-row" style={{ fontSize: "0.75rem", color: "#64748b" }}>
          <span>Lead Time:</span>
          <span>{data.horizonHours} hours</span>
        </div>
      )}
    </div>
  );
};
