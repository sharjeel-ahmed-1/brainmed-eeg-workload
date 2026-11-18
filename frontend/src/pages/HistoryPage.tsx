import { useEffect, useState } from "react";
import { getDisplayName, setDisplayName } from "../data/clientId";
import {
  clearHistoryAll,
  loadHistoryLocal,
  refreshHistoryFromServer,
} from "../data/historyStore";
import type { HistoryEntry } from "../data/types";
import "./pages.css";

export function HistoryPage() {
  const [rows, setRows] = useState<HistoryEntry[]>(() => loadHistoryLocal());
  const [name, setName] = useState(() => getDisplayName());
  const [syncNote, setSyncNote] = useState("Syncing cloud history…");

  useEffect(() => {
    let cancelled = false;
    refreshHistoryFromServer()
      .then((entries) => {
        if (!cancelled) {
          setRows(entries);
          setSyncNote(
            entries.length
              ? "Synced from server database (free SQLite/Postgres)."
              : "Cloud history empty — score a report to save."
          );
        }
      })
      .catch(() => {
        if (!cancelled) setSyncNote("Offline — showing local browser cache.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="page">
      <div className="page-toolbar glass">
        <div>
          <h2>My History</h2>
          <p className="muted">
            Scored sessions saved to the free project database (keyed to this browser). {syncNote}
          </p>
        </div>
        <div className="toolbar-actions">
          <label className="muted tiny">
            Display name
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              onBlur={() => setDisplayName(name)}
              style={{ display: "block", marginTop: 4, minWidth: 160 }}
            />
          </label>
          <button
            type="button"
            className="ghost-btn"
            onClick={async () => {
              await clearHistoryAll();
              setRows([]);
              setSyncNote("History cleared locally and on server.");
            }}
          >
            Clear history
          </button>
        </div>
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
