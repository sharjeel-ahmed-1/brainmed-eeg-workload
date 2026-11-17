import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell,
} from "recharts";
import type { DemoDashboard } from "../../data/types";
import "./charts.css";

export function TimeSpendChart({ demo }: { demo: DemoDashboard }) {
  return (
    <div className="chart-card glass">
      <div className="chart-head">
        <h3>Time Spend</h3>
        <span className="demo-pill">DEMO</span>
      </div>
      <p className="muted tiny">{demo.disclaimer}</p>
      <div className="chart-body">
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={demo.time_spend} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
            <XAxis
              dataKey="category"
              tick={{ fill: "#8aa0b5", fontSize: 10 }}
              interval={0}
              angle={-18}
              textAnchor="end"
              height={50}
            />
            <YAxis tick={{ fill: "#8aa0b5", fontSize: 11 }} unit="h" width={36} />
            <Tooltip
              contentStyle={{
                background: "#0b1a2a",
                border: "1px solid rgba(54,217,245,0.25)",
                borderRadius: 10,
              }}
              formatter={(v) => [`${v} h`, "Hours"]}
            />
            <Bar dataKey="hours" radius={[6, 6, 0, 0]}>
              {demo.time_spend.map((e) => (
                <Cell key={e.category} fill={e.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
