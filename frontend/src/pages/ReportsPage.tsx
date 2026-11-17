import { useEffect, useState } from "react";
import { api } from "../api/client";
import { BandWaveRow } from "../components/bands/BandWaveRow";
import type { ModelMode, SubjectReport } from "../data/types";
import { pushHistory } from "../data/historyStore";
import "./pages.css";

const COLORS = ["#36d9f5", "#8275ff", "#5ecf7a", "#f0a05a", "#e85d4c"];

export function ReportsPage() {
  const [subjects, setSubjects] = useState<{ id: number; true_label_name: string }[]>([]);
  const [sid, setSid] = useState(0);
  const [modelMode, setModelMode] = useState<ModelMode>("demo_all_subject");
  const [report, setReport] = useState<SubjectReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [methodsMsg, setMethodsMsg] = useState<string>("");

  useEffect(() => {
    api.subjects().then((r) => setSubjects(r.subjects.map((s) => ({ id: s.id, true_label_name: s.true_label_name }))));
    api.methods().then((m) => setMethodsMsg(m.message)).catch(() => undefined);
  }, []);

  const scoreSubject = async () => {
    setBusy(true);
    setError(null);
    try {
      const rep = await api.subjectReport(sid, modelMode);
      setReport(rep);
      pushHistory(rep, `Report S${String(sid).padStart(2, "0")} · ${modelMode}`);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  };

  const onUpload = async (file: File | null) => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const rep = await api.upload(file);
      setReport(rep);
      pushHistory(rep, file.name);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <div className="page-toolbar glass">
        <div>
          <h2>Reports</h2>
          <p className="muted">
            Upload EEG or score a STEW subject — pipeline score, not clinical / not LOSO-validated product.
          </p>
        </div>
      </div>

      {methodsMsg && (
        <div className="methods-banner">
          <strong>Methods:</strong> {methodsMsg}
        </div>
      )}

      <div className="reports-grid">
        <section className="glass report-controls">
          <h3>Upload EEG</h3>
          <input
            type="file"
            accept=".edf,.fif,.bdf,.set"
            onChange={(e) => onUpload(e.target.files?.[0] ?? null)}
          />
          <p className="muted tiny">14 channels · edf/fif/bdf/set · scored with demo_all_subject model</p>
          <hr />
          <h3>STEW subject</h3>
          <select value={sid} onChange={(e) => setSid(Number(e.target.value))}>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                S{String(s.id).padStart(2, "0")} ({s.true_label_name})
              </option>
            ))}
          </select>
          <label className="muted tiny" style={{ display: "block", marginTop: 10 }}>
            Model mode
            <select
              value={modelMode}
              onChange={(e) => setModelMode(e.target.value as ModelMode)}
              style={{ display: "block", width: "100%", marginTop: 4 }}
            >
              <option value="demo_all_subject">demo_all_subject (fit on all)</option>
              <option value="loso_held_out">loso_held_out (N−1 train)</option>
            </select>
          </label>
          <button type="button" className="primary-btn" disabled={busy} onClick={scoreSubject}>
            {busy ? "Scoring…" : "Score subject"}
          </button>
        </section>

        <section className="glass report-out">
          {error && <div className="error-banner">{error}</div>}
          {!report && !error && <p className="muted empty">Score a subject or upload a file to see output.</p>}
          {report && (
            <>
              <div className={`verdict ${report.pred_label === "HIGH" ? "high" : "low"}`}>
                <div className="verdict-title">{report.pred_label} workload</div>
                <div>
                  P(high) {(report.p_high * 100).toFixed(0)}% · {report.n_epochs} epochs · {report.source}
                </div>
                <div className="muted tiny" style={{ marginTop: 6 }}>
                  model: {report.model_type ?? "demo_all_subject"}
                  {report.train_subjects
                    ? ` · trained on ${report.train_subjects.length} subjects`
                    : ""}
                </div>
              </div>
              {report.y_true != null && (
                <p className="muted">
                  True label: {report.y_true === 1 ? "HIGH" : "LOW"} ·{" "}
                  {report.y_true === report.pred ? "match" : "mismatch"}
                </p>
              )}
              <div className="band-panel" style={{ minHeight: 0, padding: 0 }}>
                {report.bands.map((b, i) => (
                  <BandWaveRow key={b.id} band={b} color={COLORS[i % COLORS.length]} />
                ))}
              </div>
              <p className="honest muted">{report.honest.message}</p>
              {report.honest.hz_proxy_note && (
                <p className="honest muted">{report.honest.hz_proxy_note}</p>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
