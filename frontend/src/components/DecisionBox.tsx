import React from "react";
import { ShieldCheck, AlertTriangle } from "lucide-react";
import type { DecisionResponse } from "../types";

interface DecisionBoxProps {
  decision: DecisionResponse | null;
  loading?: boolean;
}

export const DecisionBox: React.FC<DecisionBoxProps> = ({
  decision,
  loading = false,
}) => {
  if (loading || !decision) {
    return (
      <div className="decision-card" style={{ opacity: 0.6 }}>
        <p>Calculating day-ahead safety buffer recommendations...</p>
      </div>
    );
  }

  const confidencePct = Math.round(decision.confidence * 100);

  return (
    <div className="decision-card" id="buyer-decision-card">
      <div className="decision-grid">
        <div className="decision-main">
          <div className="decision-tag">
            <ShieldCheck size={16} />
            Day-Ahead Buyer Recommendation ({confidencePct}% Target Confidence)
          </div>

          <p className="decision-statement">{decision.statement}</p>

          <div className="sign-explainer">
            <AlertTriangle
              size={15}
              style={{ flexShrink: 0, marginTop: "2px", color: "#f59e0b" }}
            />
            <span>
              <strong>Market Risk Convention:</strong> When the wind forecast is higher than
              actual generation (<strong>positive error / over-forecast</strong>), the trader
              buys less dispatchable thermal/gas power in the day-ahead auction. If real-time wind
              underdelivers, the utility faces an expensive <strong>cashout imbalance shortfall</strong>.
              Holding the recommended buffer mitigates this physical volume shortfall.
            </span>
          </div>
        </div>

        <div className="decision-stats">
          <div className="decision-stat-box">
            <span className="decision-stat-label">Symmetric Buffer ({confidencePct}%)</span>
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.25rem" }}>
              <span className="decision-stat-value buffer tabular-nums">
                {decision.buffer_mw !== null ? Math.round(decision.buffer_mw).toLocaleString() : "—"}
              </span>
              <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>MW</span>
            </div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-subtle)" }}>
              Based on empirical |error|
            </span>
          </div>

          <div className="decision-stat-box">
            <span className="decision-stat-label">Shortfall Buffer (Over-forecast)</span>
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.25rem" }}>
              <span className="decision-stat-value shortfall tabular-nums">
                {decision.shortfall_buffer_mw !== null
                  ? Math.round(decision.shortfall_buffer_mw).toLocaleString()
                  : "—"}
              </span>
              <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>MW</span>
            </div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-subtle)" }}>
              P90 of positive error only
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
