import React, { useState } from "react";
import { Table } from "lucide-react";
import type { BreakdownItem } from "../types";

interface WorstDaysTableProps {
  dayBreakdown: BreakdownItem[];
  selectedDate: string;
  onSelectDate: (date: string) => void;
  loading?: boolean;
}

export const WorstDaysTable: React.FC<WorstDaysTableProps> = ({
  dayBreakdown,
  selectedDate,
  onSelectDate,
  loading = false,
}) => {
  const [sortOrder, setSortOrder] = useState<"worst" | "best">("worst");

  const sortedDays = [...dayBreakdown].sort((a, b) => {
    const valA = a.mae ?? 0;
    const valB = b.mae ?? 0;
    return sortOrder === "worst" ? valB - valA : valA - valB;
  });

  return (
    <div className="card" id="worst-best-days-card">
      <div className="card-header">
        <div>
          <div className="card-title-group">
            <Table size={18} color="#38bdf8" />
            <h2 className="card-title">Best & Worst Forecast Days (January 2026)</h2>
          </div>
          <p className="card-help-text">
            Click any row to view its 48 half-hour intervals in the top chart
          </p>
        </div>

        <div className="btn-toggle-group">
          <button
            type="button"
            className={`btn-toggle ${sortOrder === "worst" ? "active" : ""}`}
            onClick={() => setSortOrder("worst")}
          >
            Highest MAE (Worst Days)
          </button>
          <button
            type="button"
            className={`btn-toggle ${sortOrder === "best" ? "active" : ""}`}
            onClick={() => setSortOrder("best")}
          >
            Lowest MAE (Best Days)
          </button>
        </div>
      </div>

      <div className="table-wrapper">
        {loading ? (
          <div className="state-box">
            <div className="spinner" />
            <span>Loading daily summary...</span>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Delivery Date</th>
                <th>MAE (MW)</th>
                <th>RMSE (MW)</th>
                <th>Bias (MW)</th>
                <th>P90 Abs Error</th>
                <th>Coverage</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {sortedDays.map((item, index) => {
                const isSelected = item.group === selectedDate;
                const biasSign = item.bias !== null && item.bias > 0 ? "+" : "";

                return (
                  <tr
                    key={item.group}
                    className={`clickable ${isSelected ? "selected" : ""}`}
                    onClick={() => onSelectDate(item.group)}
                  >
                    <td className="tabular-nums" style={{ color: "var(--text-subtle)" }}>
                      #{index + 1}
                    </td>
                    <td className="tabular-nums" style={{ fontWeight: 600 }}>
                      {item.group}
                    </td>
                    <td className="tabular-nums" style={{ color: "#38bdf8", fontWeight: 600 }}>
                      {item.mae !== null ? Math.round(item.mae).toLocaleString() : "—"}
                    </td>
                    <td className="tabular-nums">
                      {item.rmse !== null ? Math.round(item.rmse).toLocaleString() : "—"}
                    </td>
                    <td
                      className="tabular-nums"
                      style={{
                        color: item.bias && item.bias > 0 ? "#f59e0b" : "#34d399",
                      }}
                    >
                      {biasSign}
                      {item.bias !== null ? Math.round(item.bias).toLocaleString() : "—"}
                    </td>
                    <td className="tabular-nums">
                      {item.p90_abs_error !== null
                        ? Math.round(item.p90_abs_error).toLocaleString()
                        : "—"}
                    </td>
                    <td className="tabular-nums">
                      {Math.round(item.coverage * 100)}% ({item.n_paired}/48)
                    </td>
                    <td>
                      <button
                        type="button"
                        className={`quick-date-btn ${isSelected ? "active" : ""}`}
                        style={{ padding: "0.2rem 0.5rem", fontSize: "0.75rem" }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectDate(item.group);
                        }}
                      >
                        {isSelected ? "Active" : "Inspect"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
