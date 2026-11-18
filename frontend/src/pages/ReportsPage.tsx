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
  const [calibNote, setCalibNote] = useState<string>("");
  const [nBaseline, setNBaseline] = useState(10);
  const [nTask, setNTask] = useState(10);
  const [calibId, setCalibId] = useState<string | null>(null);

  useEffect(() => {
    api.subjects().then((r) => setSubjects(r.subjects.map((s) => ({ id: s.id, true_label_name: s.true_label_name }))));
    api.methods().then((m) => {
      setMethodsMsg(m.message);
      setCalibNote(m.calibration ?? "");
    }).catch(() => undefined);
  }, []);

  const applyReport = (rep: SubjectReport, label: string) => {
    setReport(rep);
    if (rep.calib_id) setCalibId(rep.calib_id);
    pushHistory(rep, label);
  };

  const scoreSubject = async () => {
    setBusy(true);
    setError(null);
    try {
      const rep = await api.subjectReport(sid, modelMode);
      applyReport(rep, `Report S${String(sid).padStart(2, "0")} · ${modelMode}`);
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
      applyReport(rep, file.name);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  };

  const calibrateStew = async () => {
    setBusy(true);
    setError(null);
    try {
      const rep = await api.calibrateStew(sid, nBaseline, nTask);
      applyReport(rep, `Calib S${String(sid).padStart(2, "0")} · within-subject`);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  };

  const calibrateFiles = async (baseline: File | null, task: File | null) => {
    if (!baseline || !task) return;
    setBusy(true);
    setError(null);
    try {
      const rep = await api.calibrateUpload(baseline, task);
      applyReport(rep, `Calib ${baseline.name}→${task.name}`);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  };

  const scoreCalibUpload = async (file: File | null) => {
    if (!file || !calibId) return;
    setBusy(true);
    setError(null);
    try {
      const rep = await api.scoreWithCalib(calibId, file);
      applyReport(rep, `Score w/ calib ${calibId.slice(0, 6)} · ${file.name}`);
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
            Upload EEG, score STEW, or run within-subject calibration — not clinical / not LOSO-validated product.
          </p>
        </div>
      </div>

      {methodsMsg && (
        <div className="methods-banner">
          <strong>Methods:</strong> {methodsMsg}
        </div>
      )}
      {calibNote && (
        <div className="methods-banner calib-banner">
          <strong>Calibration:</strong> {calibNote}
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

          <hr />
          <h3>Within-subject calibration</h3>
          <p className="muted tiny">
            Personal relative score: fit on this session only (baseline vs task). Best product angle while
            cross-subject LOSO stays null.
          </p>
          <div className="calib-row">
            <label className="muted tiny">
              Baseline epochs
              <input
                type="number"
                min={2}
                max={30}
                value={nBaseline}
                onChange={(e) => setNBaseline(Number(e.target.value))}
              />
            </label>
            <label className="muted tiny">
              Task epochs
              <input
                type="number"
                min={2}
                max={30}
                value={nTask}
                onChange={(e) => setNTask(Number(e.target.value))}
              />
            </label>
          </div>
          <button type="button" className="primary-btn secondary-tone" disabled={busy} onClick={calibrateStew}>
            {busy ? "Calibrating…" : "Calibrate STEW (first/last split)"}
          </button>
          <p className="muted tiny" style={{ marginTop: 10 }}>
            Or upload real baseline + task recordings
          </p>
          <label className="muted tiny" style={{ display: "block" }}>
            Baseline (low)
            <input
              type="file"
              accept=".edf,.fif,.bdf,.set"
              id="calib-baseline"
              style={{ display: "block", marginTop: 4 }}
            />
          </label>
          <label className="muted tiny" style={{ display: "block", marginTop: 8 }}>
            Task (high)
            <input
              type="file"
              accept=".edf,.fif,.bdf,.set"
              id="calib-task"
              style={{ display: "block", marginTop: 4 }}
            />
          </label>
          <button
            type="button"
            className="primary-btn secondary-tone"
            disabled={busy}
            onClick={() => {
              const b = (document.getElementById("calib-baseline") as HTMLInputElement)?.files?.[0] ?? null;
              const t = (document.getElementById("calib-task") as HTMLInputElement)?.files?.[0] ?? null;
              void calibrateFiles(b, t);
            }}
          >
            Fit calibrator from uploads
          </button>
          {calibId && (
            <>
              <p className="muted tiny" style={{ marginTop: 10 }}>
                Active calib: <code>{calibId}</code> — score another file
              </p>
              <input
                type="file"
                accept=".edf,.fif,.bdf,.set"
                onChange={(e) => void scoreCalibUpload(e.target.files?.[0] ?? null)}
              />
            </>
          )}
        </section>

        <section className="glass report-out">
          {error && <div className="error-banner">{error}</div>}
          {!report && !error && <p className="muted empty">Score a subject, upload, or calibrate to see output.</p>}
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
                  {report.calib_id ? ` · calib ${report.calib_id}` : ""}
                </div>
              </div>
              {report.calib && (
                <p className="muted tiny">
                  Calib: {report.calib.mode}
                  {report.calib.score_set ? ` · score set=${report.calib.score_set}` : ""}
                  {report.calib.n_baseline != null
                    ? ` · low=${report.calib.n_baseline} high=${report.calib.n_task}`
                    : ""}
                </p>
              )}
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
