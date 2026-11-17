import { Line, LineChart, ResponsiveContainer, Tooltip } from "recharts";
import type { DemoDashboard } from "../../data/types";
import "./widgets.css";

export function GeneralInfoCard({ demo }: { demo: DemoDashboard }) {
  const g = demo.general;
  return (
    <aside className="float-card glass general-card">
      <div className="float-head">
        <span>General information</span>
        <span className="demo-pill">DEMO · Monthly</span>
      </div>
      <div className="general-stats">
        <div>
          <strong>{(g.avg_value * 100).toFixed(1)}%</strong>
          <span className="muted"> avg · {g.avg_hours_per_day}h / day</span>
        </div>
        <div className="muted">Highest: {(g.highest_day * 100).toFixed(1)}%</div>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${Math.min(100, g.progress_pct)}%` }} />
      </div>
      <div className="muted tiny">
        {g.progress_pct}% out of {g.target_pct}% target
      </div>
      <div style={{ width: "100%", height: 70 }}>
        <ResponsiveContainer>
          <LineChart data={demo.concentration_series}>
            <Tooltip
              contentStyle={{ background: "#0b1a2a", border: "1px solid rgba(154,216,255,.4)" }}
            />
            <Line type="monotone" dataKey="value" stroke="#8275ff" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </aside>
  );
}
