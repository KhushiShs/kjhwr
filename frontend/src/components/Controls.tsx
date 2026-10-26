import React from "react";
import { Calendar, Clock, Info } from "lucide-react";

interface ControlsProps {
  date: string;
  onDateChange: (date: string) => void;
  cutoffHour: number;
  onCutoffHourChange: (hour: number) => void;
  cutoffMinute: number;
  onCutoffMinuteChange: (minute: number) => void;
  availableDates: string[];
  disabled?: boolean;
}

export const Controls: React.FC<ControlsProps> = ({
  date,
  onDateChange,
  cutoffHour,
  onCutoffHourChange,
  cutoffMinute,
  onCutoffMinuteChange,
  availableDates,
  disabled = false,
}) => {
  const minDate = availableDates[0] || "2026-01-01";
  const maxDate = availableDates[availableDates.length - 1] || "2026-01-31";

  // Pre-configured sample dates for quick access
  const sampleDates = [
    { label: "Jan 01", date: "2026-01-01" },
    { label: "Jan 10", date: "2026-01-10" },
    { label: "Jan 15", date: "2026-01-15" },
    { label: "Jan 20", date: "2026-01-20" },
    { label: "Jan 31", date: "2026-01-31" },
  ];

  return (
    <div className="controls-bar" id="dashboard-controls">
      <div className="controls-group">
        {/* Date Selector */}
        <div className="control-item">
          <label className="control-label" htmlFor="delivery-date-input">
            <Calendar size={14} />
            Delivery Day (Jan 2026)
          </label>
          <input
            id="delivery-date-input"
            type="date"
            className="control-input tabular-nums"
            min={minDate}
            max={maxDate}
            value={date}
            disabled={disabled}
            onChange={(e) => onDateChange(e.target.value)}
          />
        </div>

        {/* Quick Date Pills */}
        <div className="control-item">
          <span className="control-label">Quick Jump</span>
          <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
            {sampleDates.map((item) => (
              <button
                key={item.date}
                type="button"
                className={`quick-date-btn ${date === item.date ? "active" : ""}`}
                disabled={disabled}
                onClick={() => onDateChange(item.date)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {/* Cutoff Time Selector */}
        <div className="control-item">
          <label className="control-label" htmlFor="cutoff-hour-select">
            <Clock size={14} />
            Decision Cutoff (D-1 UTC)
          </label>
          <div style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
            <select
              id="cutoff-hour-select"
              className="control-select tabular-nums"
              value={cutoffHour}
              disabled={disabled}
              onChange={(e) => onCutoffHourChange(Number(e.target.value))}
            >
              {Array.from({ length: 24 }).map((_, i) => (
                <option key={i} value={i}>
                  {String(i).padStart(2, "0")}h
                </option>
              ))}
            </select>
            <span style={{ color: "var(--text-subtle)" }}>:</span>
            <select
              id="cutoff-minute-select"
              className="control-select tabular-nums"
              value={cutoffMinute}
              disabled={disabled}
              onChange={(e) => onCutoffMinuteChange(Number(e.target.value))}
            >
              {[0, 15, 30, 45].map((m) => (
                <option key={m} value={m}>
                  {String(m).padStart(2, "0")}m
                </option>
              ))}
            </select>
            <span
              style={{
                fontSize: "0.75rem",
                color: "var(--text-subtle)",
                marginLeft: "0.25rem",
              }}
              title="EPEX day-ahead auction order book closes at 09:20 GMT/BST. 09:00 provides a 20-min operational buffer."
            >
              <Info size={13} style={{ verticalAlign: "middle" }} /> 09:20 Gate Close
            </span>
          </div>
        </div>
      </div>

      <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
        Active Market: <span style={{ color: "var(--color-forecast)", fontWeight: 600 }}>GB National Grid</span>
      </div>
    </div>
  );
};
