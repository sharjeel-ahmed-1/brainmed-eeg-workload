import type { DemoDashboard, RangeName } from "../../data/types";
import "./timeline.css";

export function DayTimeline({
  demo,
  range,
  onRange,
  hour,
  onHour,
}: {
  demo: DemoDashboard;
  range: RangeName;
  onRange: (r: RangeName) => void;
  hour: number;
  onHour: (h: number) => void;
}) {
  const series = demo.concentration_series;
  const maxT = Math.max(...series.map((c) => c.t), 1);
  const minT = series[0]?.t ?? 0;
  const active = series.find((c) => c.t === hour) ?? series[0];
  const pct = ((hour - minT) / Math.max(maxT - minT, 1)) * 100;

  return (
    <div className="timeline glass">
      <div className="timeline-head">
        <h3>Performance timeline</h3>
        <div className="range-pills">
          {(["today", "week", "month"] as RangeName[]).map((r) => (
            <button
              key={r}
              type="button"
              className={range === r ? "active" : ""}
              onClick={() => onRange(r)}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      <div className="ruler" aria-hidden>
        <div className="ruler-fill" style={{ width: `${pct}%` }} />
        <div className="ruler-knob" style={{ left: `${pct}%` }} />
      </div>

      <input
        className="timeline-slider"
        type="range"
        min={minT}
        max={maxT}
        step={1}
        value={hour}
        onChange={(e) => onHour(Number(e.target.value))}
      />

      <div className="timeline-ticks muted">
        {range === "today" ? (
          <>
            <span>12AM</span>
            <span>6AM</span>
            <span>12PM</span>
            <span>6PM</span>
            <span>12AM</span>
          </>
        ) : (
          <>
            <span>Start</span>
            <span>Mid</span>
            <span>End</span>
          </>
        )}
      </div>

      <div className="timeline-meta">
        Cursor <strong>{hour}</strong> · concentration{" "}
        <strong>{((active?.value ?? 0) * 100).toFixed(1)}%</strong>
        <span className="demo-pill" style={{ marginLeft: 8 }}>
          DEMO
        </span>
      </div>
    </div>
  );
}
