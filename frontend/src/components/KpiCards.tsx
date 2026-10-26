import React from "react";
import { Gauge, Target, Compass, ShieldAlert, BarChart3 } from "lucide-react";
import type { MetricsResponse } from "../types";

interface KpiCardsProps {
  metrics: MetricsResponse | null;
  loading?: boolean;
}

export const KpiCards: React.FC<KpiCardsProps> = ({ metrics, loading = false }) => {
  if (loading || !metrics) {
    return (
      <div className="kpi-grid">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="kpi-card" style={{ opacity: 0.5 }}>
            <div className="kpi-title">Loading...</div>
            <div className="kpi-value">—</div>
          </div>
        ))}
      </div>
    );
  }

  const formatMw = (val: number | null) =>
    val !== null ? Math.round(val).toLocaleString() : "—";

  const biasSign = metrics.bias !== null && metrics.bias > 0 ? "+" : "";

  return (
    <div className="kpi-grid" id="kpi-cards-grid">
      {/* MAE */}
      <div className="kpi-card" id="kpi-mae">
        <div className="kpi-header">
          <span className="kpi-title">Mean Absolute Error</span>
          <Gauge size={16} color="#38bdf8" />
        </div>
        <div className="kpi-value-row">
          <span className="kpi-value tabular-nums">{formatMw(metrics.mae)}</span>
          <span className="kpi-unit">MW</span>
        </div>
        <span className="kpi-subtext">Average magnitude of forecast deviation</span>
      </div>

      {/* RMSE */}
      <div className="kpi-card" id="kpi-rmse">
        <div className="kpi-header">
          <span className="kpi-title">Root Mean Squared Error</span>
          <Target size={16} color="#818cf8" />
        </div>
        <div className="kpi-value-row">
          <span className="kpi-value tabular-nums">{formatMw(metrics.rmse)}</span>
          <span className="kpi-unit">MW</span>
        </div>
        <span className="kpi-subtext">Penalises severe forecast outliers</span>
      </div>

      {/* Bias */}
      <div className="kpi-card" id="kpi-bias">
        <div className="kpi-header">
          <span className="kpi-title">Forecast Bias (Mean Error)</span>
          <Compass size={16} color={metrics.bias && metrics.bias > 0 ? "#f59e0b" : "#34d399"} />
        </div>
        <div className="kpi-value-row">
          <span
            className="kpi-value tabular-nums"
            style={{
              color: metrics.bias && metrics.bias > 0 ? "#f59e0b" : "#34d399",
            }}
          >
            {biasSign}
            {formatMw(metrics.bias)}
          </span>
          <span className="kpi-unit">MW</span>
        </div>
        <span className="kpi-subtext">
          {metrics.bias && metrics.bias > 0
            ? "Persistent over-forecast (shortfall risk)"
            : "Under-forecast tendency"}
        </span>
      </div>

      {/* P90 Abs Error */}
      <div className="kpi-card" id="kpi-p90">
        <div className="kpi-header">
          <span className="kpi-title">P90 Absolute Error</span>
          <ShieldAlert size={16} color="#f59e0b" />
        </div>
        <div className="kpi-value-row">
          <span className="kpi-value tabular-nums" style={{ color: "#f59e0b" }}>
            {formatMw(metrics.p90_abs_error)}
          </span>
          <span className="kpi-unit">MW</span>
        </div>
        <span className="kpi-subtext">90% of observed errors fall below this</span>
      </div>

      {/* Coverage */}
      <div className="kpi-card" id="kpi-coverage">
        <div className="kpi-header">
          <span className="kpi-title">Forecast Coverage</span>
          <BarChart3 size={16} color="#34d399" />
        </div>
        <div className="kpi-value-row">
          <span className="kpi-value tabular-nums" style={{ color: "#34d399" }}>
            {(metrics.coverage * 100).toFixed(1)}
          </span>
          <span className="kpi-unit">%</span>
        </div>
        <span className="kpi-subtext">
          {metrics.n_paired} paired of {metrics.n_targets} periods
        </span>
      </div>
    </div>
  );
};
