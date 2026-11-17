import { useState } from "react";
import { loadHistory } from "../data/historyStore";
import type { HistoryEntry } from "../data/types";
import "./pages.css";

export function HistoryPage() {
  const [rows, setRows] = useState<HistoryEntry[]>(() => loadHistory());

  return (
    <div className="page">
      <div className="page-toolbar glass">
        <div>
          <h2>My History</h2>
          <p className="muted">Local scored sessions (browser storage). Not a server database.</p>
        </div>
        <button
          type="button"
          className="ghost-btn"
          onClick={() => {
            localStorage.removeItem("brainmed_history_v1");
            setRows([]);
          }}
        >
          Clear history
        </button>
      </div>
      <div className="glass table-wrap">
        {rows.length === 0 ? (
          <p className="muted empty">No sessions yet — open Overview or score a report.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Label</th>
                <th>Prediction</th>
                <th>P(high)</th>
                <th>Source</th>
                <th>Model</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>{new Date(r.at).toLocaleString()}</td>
                  <td>{r.label}</td>
                  <td>{r.pred_label}</td>
                  <td>{(r.p_high * 100).toFixed(1)}%</td>
                  <td>{r.source}</td>
                  <td>{r.model_type ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
