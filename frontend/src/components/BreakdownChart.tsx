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
  ReferenceLine,
} from "recharts";
import { Layers, Info } from "lucide-react";
import type { BreakdownItem } from "../types";

interface BreakdownChartProps {
  hourBreakdown: BreakdownItem[];
  windLevelBreakdown: BreakdownItem[];
  loading?: boolean;
}

export const BreakdownChart: React.FC<BreakdownChartProps> = ({
  hourBreakdown,
  windLevelBreakdown,
  loading = false,
}) => {
  const [dimension, setDimension] = useState<"hour" | "wind_level">("hour");

  const rawData = dimension === "hour" ? hourBreakdown : windLevelBreakdown;

  const chartData = rawData.map((item) => {
    let groupLabel = item.group;
    if (dimension === "hour") {
      groupLabel = `${String(item.group).padStart(2, "0")}:00`;
    } else if (dimension === "wind_level") {
      groupLabel = item.group
        .replace("[", "")
        .replace(")", "")
        .replace("inf", "Max")
        .replace(",", " to ")
        .replace("0.0 to 4000.0", "0–4 GW")
        .replace("4000.0 to 8000.0", "4–8 GW")
        .replace("8000.0 to 12000.0", "8–12 GW")
        .replace("12000.0 to inf", "> 12 GW");
    }

    return {
      group: groupLabel,
      mae: item.mae !== null ? Math.round(item.mae) : null,
      bias: item.bias !== null ? Math.round(item.bias) : null,
      rmse: item.rmse !== null ? Math.round(item.rmse) : null,
      coverage: Math.round(item.coverage * 100),
      n_paired: item.n_paired,
    };
  });

  return (
    <div className="card" id="breakdown-chart-card">
      <div className="card-header">
        <div>
          <div className="card-title-group">
            <Layers size={18} color="#38bdf8" />
            <h2 className="card-title">Forecast Error Breakdown</h2>
          </div>
          <p className="card-help-text">
            Identify systematic bias across diurnal hours and generation regimes
          </p>
        </div>

        <div className="btn-toggle-group">
          <button
            type="button"
            className={`btn-toggle ${dimension === "hour" ? "active" : ""}`}
            onClick={() => setDimension("hour")}
          >
            By Target Hour
          </button>
          <button
            type="button"
            className={`btn-toggle ${dimension === "wind_level" ? "active" : ""}`}
            onClick={() => setDimension("wind_level")}
          >
            By Wind Generation Level
          </button>
        </div>
      </div>

      <div className="chart-wrapper">
        {loading ? (
          <div className="state-box">
            <div className="spinner" />
            <span>Calculating breakdown...</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 15, right: 20, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
              <XAxis
                dataKey="group"
                stroke="#6b7280"
                tick={{ fontSize: 11, fill: "#9ca3af" }}
                tickLine={false}
              />
              <YAxis
                stroke="#6b7280"
                tick={{ fontSize: 12, fill: "#9ca3af" }}
                tickLine={false}
                unit=" MW"
                width={70}
              />
              <Tooltip content={<BreakdownTooltip dimension={dimension} />} />
              <ReferenceLine y={0} stroke="#4b5563" />
              <Legend
                verticalAlign="top"
                align="right"
                iconType="circle"
                wrapperStyle={{ paddingBottom: "10px", fontSize: "0.8rem" }}
              />
              <Bar dataKey="mae" name="MAE (MW)" fill="#38bdf8" radius={[4, 4, 0, 0]} />
              <Bar dataKey="bias" name="Bias (Mean Error MW)" fill="#f59e0b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="sign-explainer">
        <Info size={14} style={{ flexShrink: 0, marginTop: "2px", color: "#38bdf8" }} />
        <span>
          <strong>Buyer tip:</strong> A high positive bias in certain hours (or at high wind levels)
          means the forecast regularly predicts more wind than materialises. Buyers in those hours
          face elevated under-procurement risks.
        </span>
      </div>
    </div>
  );
};

const BreakdownTooltip: React.FC<any> = ({ active, payload, label, dimension }) => {
  if (!active || !payload || !payload.length) return null;

  return (
    <div className="custom-chart-tooltip">
      <div className="tooltip-time">
        {dimension === "hour" ? `Target Hour: ${label}` : `Wind Bucket: ${label}`}
      </div>
      {payload.map((item: any) => (
        <div key={item.name} className="tooltip-row">
          <span>{item.name}:</span>
          <strong style={{ color: item.fill }}>
            {item.value !== null
              ? `${item.value > 0 && item.name.includes("Bias") ? "+" : ""}${Number(item.value).toLocaleString()} MW`
              : "N/A"}
          </strong>
        </div>
      ))}
    </div>
  );
};
