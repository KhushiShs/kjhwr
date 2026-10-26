import React, { useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import { Timer, Info } from "lucide-react";
import type { HorizonMetricItem } from "../types";

interface HorizonChartProps {
  fixedHorizonItems: HorizonMetricItem[];
  bucketedHorizonItems: HorizonMetricItem[];
  loading?: boolean;
}

export const HorizonChart: React.FC<HorizonChartProps> = ({
  fixedHorizonItems,
  bucketedHorizonItems,
  loading = false,
}) => {
  const [viewMode, setViewMode] = useState<"fixed" | "buckets">("fixed");

  const activeItems = viewMode === "fixed" ? fixedHorizonItems : bucketedHorizonItems;

  const chartData = activeItems.map((item) => ({
    group: item.group,
    mae: item.mae !== null ? Math.round(item.mae) : null,
    rmse: item.rmse !== null ? Math.round(item.rmse) : null,
    p90: item.p90_abs_error !== null ? Math.round(item.p90_abs_error) : null,
    coverage: Math.round(item.coverage * 100),
    n_paired: item.n_paired,
  }));

  return (
    <div className="card" id="horizon-accuracy-chart-card">
      <div className="card-header">
        <div>
          <div className="card-title-group">
            <Timer size={18} color="#38bdf8" />
            <h2 className="card-title">Forecast Accuracy vs Lead Time Horizon</h2>
          </div>
          <p className="card-help-text">
            Examines how forecast errors scale as delivery approaches
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <div className="btn-toggle-group">
            <button
              type="button"
              className={`btn-toggle ${viewMode === "fixed" ? "active" : ""}`}
              onClick={() => setViewMode("fixed")}
            >
              Fixed Lead Times (12h–48h)
            </button>
            <button
              type="button"
              className={`btn-toggle ${viewMode === "buckets" ? "active" : ""}`}
              onClick={() => setViewMode("buckets")}
            >
              Day-Ahead Cutoff Bins
            </button>
          </div>
        </div>
      </div>

      <div className="chart-wrapper">
        {loading ? (
          <div className="state-box">
            <div className="spinner" />
            <span>Calculating horizon breakdown...</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 15, right: 20, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
              <XAxis
                dataKey="group"
                stroke="#6b7280"
                tick={{ fontSize: 12, fill: "#9ca3af" }}
                tickLine={false}
              />
              <YAxis
                stroke="#6b7280"
                tick={{ fontSize: 12, fill: "#9ca3af" }}
                tickLine={false}
                unit=" MW"
                width={70}
              />
              <Tooltip content={<HorizonTooltip />} />
              <Legend
                verticalAlign="top"
                align="right"
                iconType="circle"
                wrapperStyle={{ paddingBottom: "10px", fontSize: "0.8rem" }}
              />
              <Bar dataKey="mae" name="MAE (MW)" fill="#38bdf8" radius={[4, 4, 0, 0]} />
              <Bar dataKey="rmse" name="RMSE (MW)" fill="#818cf8" radius={[4, 4, 0, 0]} />
              <Bar dataKey="p90" name="P90 Abs Error (MW)" fill="#f59e0b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="sign-explainer">
        <Info size={14} style={{ flexShrink: 0, marginTop: "2px", color: "#38bdf8" }} />
        <span>
          <strong>Insight for buyers:</strong> Forecast error increases monotonically with lead time
          (e.g. ~1,887 MW MAE at 12 hours out vs ~2,351 MW MAE at 48 hours). If decisions are locked
          early, larger safety buffers are required.
        </span>
      </div>
    </div>
  );
};

const HorizonTooltip: React.FC<any> = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null;

  return (
    <div className="custom-chart-tooltip">
      <div className="tooltip-time">Horizon: {label}</div>
      {payload.map((item: any) => (
        <div key={item.name} className="tooltip-row">
          <span>{item.name}:</span>
          <strong style={{ color: item.fill }}>
            {item.value !== null ? `${Number(item.value).toLocaleString()} MW` : "N/A"}
          </strong>
        </div>
      ))}
    </div>
  );
};
