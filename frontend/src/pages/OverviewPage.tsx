import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { BrainScene } from "../components/brain/BrainScene";
import { BandWaveRow } from "../components/bands/BandWaveRow";
import { FrequencyCard, FrequencyModal } from "../components/bands/FrequencyCard";
import { TimeSpendChart } from "../components/charts/TimeSpendChart";
import { ConcentrationWidget } from "../components/widgets/ConcentrationWidget";
import { TargetWidget } from "../components/widgets/TargetWidget";
import { GeneralInfoCard } from "../components/widgets/GeneralInfoCard";
import { DayTimeline } from "../components/timeline/DayTimeline";
import type { BandInfo, DemoDashboard, LiveReplay, RangeName, SubjectReport } from "../data/types";
import { pushHistory } from "../data/historyStore";
import "./pages.css";

const COLORS = ["#36d9f5", "#8275ff", "#f0a05a", "#5ecf7a", "#e85d4c"];
const BAND_ORDER = ["gamma", "beta", "alpha", "delta", "theta"];

export function OverviewPage() {
  const [subjectId, setSubjectId] = useState(0);
  const [subjects, setSubjects] = useState<{ id: number; true_label_name: string }[]>([]);
  const [report, setReport] = useState<SubjectReport | null>(null);
  const [demo, setDemo] = useState<DemoDashboard | null>(null);
  const [range, setRange] = useState<RangeName>("today");
  const [hour, setHour] = useState(12);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openBand, setOpenBand] = useState<BandInfo | null>(null);
  const [methodsMsg, setMethodsMsg] = useState("");
  const [live, setLive] = useState<LiveReplay | null>(null);
  const [liveBusy, setLiveBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api
      .subjects()
      .then((r) => setSubjects(r.subjects.map((s) => ({ id: s.id, true_label_name: s.true_label_name }))))
      .catch((e) => setError(String(e.message ?? e)));
    api
      .methods()
      .then((m) => setMethodsMsg(m.message))
      .catch(() => undefined);
  }, []);

  // Heavy STEW score only when subject changes (not on DEMO range change)
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .subjectReport(subjectId)
      .then((rep) => {
        if (!cancelled) setReport(rep);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e.message ?? e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [subjectId]);

  useEffect(() => {
    let cancelled = false;
    api
      .demoDashboard(range, subjectId)
      .then((dem) => {
        if (cancelled) return;
        setDemo(dem);
        const mid = dem.concentration_series[Math.floor(dem.concentration_series.length / 2)]?.t ?? 0;
        setHour(mid);
      })
      .catch(() => {
        /* demo optional if API down mid-session */
      });
    return () => {
      cancelled = true;
    };
  }, [range, subjectId]);

  const onUpload = async (file: File | null) => {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const rep = await api.upload(file);
      setReport(rep);
      pushHistory(rep, file.name);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const bands = useMemo(() => {
    const raw = report?.bands ?? [];
    return BAND_ORDER.map((id) => raw.find((b) => b.id === id)).filter(Boolean) as BandInfo[];
  }, [report]);

  const gamma = useMemo(() => bands.find((b) => b.id === "gamma"), [bands]);
  const openColor = openBand
    ? COLORS[Math.max(0, bands.findIndex((b) => b.id === openBand.id)) % COLORS.length]
    : COLORS[0];

  return (
    <div className="page overview-page">
      <div className="page-toolbar glass compact-bar">
        <div className="toolbar-left">
          <strong>Overview</strong>
          <span className="muted tiny-inline">
            STEW EEG · lifestyle <span className="demo-pill">DEMO</span>
          </span>
        </div>
        <div className="toolbar-actions">
          <input
            ref={fileRef}
            type="file"
            accept=".edf,.fif,.bdf,.set"
            hidden
            onChange={(e) => onUpload(e.target.files?.[0] ?? null)}
          />
          <button
            type="button"
            className="primary-upload"
            disabled={uploading}
            onClick={() => fileRef.current?.click()}
          >
            {uploading ? "Uploading…" : "Upload EEG report"}
          </button>
          <Link className="ghost-btn link-btn" to="/reports">
            Reports page
          </Link>
          <label className="subject-pick">
            Subject
            <select value={subjectId} onChange={(e) => setSubjectId(Number(e.target.value))}>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  S{String(s.id).padStart(2, "0")} ({s.true_label_name})
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="ghost-btn"
            disabled={!report}
            onClick={() => {
              if (!report) return;
              pushHistory(report, `STEW S${String(subjectId).padStart(2, "0")}`);
              alert("Saved to My History");
            }}
          >
            Save
          </button>
          <button
            type="button"
            className="ghost-btn"
            disabled={liveBusy}
            onClick={async () => {
              setLiveBusy(true);
              setError(null);
              try {
                const rep = await api.liveReplay(subjectId, 20);
                setLive(rep);
              } catch (e) {
                setError(String((e as Error).message ?? e));
              } finally {
                setLiveBusy(false);
              }
            }}
          >
            {liveBusy ? "Replaying…" : "LIVE replay"}
          </button>
        </div>
      </div>

      {methodsMsg && (
        <div className="methods-banner">
          <strong>Methods:</strong> LOSO acc 0.356 (null vs majority 0.556). {methodsMsg} Lifestyle charts stay{" "}
          <span className="demo-pill">DEMO</span>; band Hz are proxies.
        </div>
      )}

      {error && <div className="error-banner">{error} — is API on :8000?</div>}
      {loading && !report && <div className="skeleton overview-skel" />}

      {report && demo && (
        <div className="dash">
          <div className="dash-status">
            <span>
              Workload <strong>{report.pred_label}</strong>
              <span className="muted">
                {" "}
                · P(high) {(report.p_high * 100).toFixed(0)}% · {report.n_epochs} ep
                {report.file_name ? ` · ${report.file_name}` : ""}
                {report.model_type ? ` · ${report.model_type}` : ""}
              </span>
            </span>
            <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {live && <span className="live-pill">LIVE · replay</span>}
              <span className="recorded-pill">{report.source}</span>
            </span>
          </div>
          {live && (
            <p className="muted tiny" style={{ marginTop: 0 }}>
              {live.honest.message} · {live.n_windows} windows · last P(high){" "}
              {((live.windows[live.windows.length - 1]?.p_high ?? 0) * 100).toFixed(0)}%
            </p>
          )}

          <div className="dash-main">
            <section className="dash-brain-stage">
              <BrainScene bands={bands} />
              <div className="float-target">
                <TargetWidget demo={demo} />
              </div>
              <div className="float-conc">
                <ConcentrationWidget gamma={gamma} recorded={report.source !== "demo"} />
              </div>
            </section>

            <aside className="dash-right">
              <div className="band-panel glass">
                <div className="band-panel-head">
                  <div>
                    <h3>Activity &amp; productivity</h3>
                    <p className="muted tiny">Relative-power Hz proxies from recording</p>
                  </div>
                  <select
                    className="range-select"
                    value={range}
                    onChange={(e) => setRange(e.target.value as RangeName)}
                    aria-label="Time range"
                  >
                    <option value="today">Today</option>
                    <option value="week">Week</option>
                    <option value="month">Month</option>
                  </select>
                </div>
                <div className="band-rows">
                  {bands.map((b, i) => (
                    <BandWaveRow key={b.id} band={b} color={COLORS[i % COLORS.length]} />
                  ))}
                </div>
              </div>
              <TimeSpendChart demo={demo} />
            </aside>
          </div>

          <div className="freq-row">
            {bands.map((b, i) => (
              <FrequencyCard
                key={b.id}
                band={b}
                color={COLORS[i % COLORS.length]}
                onOpen={setOpenBand}
              />
            ))}
          </div>

          <div className="dash-bottom">
            <GeneralInfoCard demo={demo} />
            <DayTimeline
              demo={demo}
              range={range}
              onRange={setRange}
              hour={hour}
              onHour={setHour}
            />
          </div>
        </div>
      )}

      {openBand && (
        <FrequencyModal band={openBand} color={openColor} onClose={() => setOpenBand(null)} />
      )}
    </div>
  );
}
