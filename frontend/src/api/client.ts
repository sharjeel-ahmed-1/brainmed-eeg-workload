import type {
  DemoDashboard,
  LiveReplay,
  MethodsInfo,
  ModelMode,
  RangeName,
  SubjectListItem,
  SubjectReport,
} from "../data/types";

const BASE = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => json<{ ok: boolean; model_exists: boolean }>("/api/health"),
  methods: () => json<MethodsInfo>("/api/methods"),
  subjects: () => json<{ subjects: SubjectListItem[] }>("/api/subjects"),
  subjectReport: (id: number, modelMode: ModelMode = "demo_all_subject") =>
    json<SubjectReport>(`/api/subjects/${id}/report?model_mode=${modelMode}`),
  upload: async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return json<SubjectReport>("/api/upload", { method: "POST", body: fd });
  },
  demoDashboard: (range: RangeName, subjectId?: number | null) => {
    const q = new URLSearchParams({ range });
    if (subjectId != null) q.set("subject_id", String(subjectId));
    return json<DemoDashboard>(`/api/demo/dashboard?${q}`);
  },
  liveReplay: (id: number, maxWindows = 24) =>
    json<LiveReplay>(`/api/live/replay/${id}?max_windows=${maxWindows}`),
  calibrateStew: (id: number, nBaseline = 10, nTask = 10) =>
    json<SubjectReport>(
      `/api/calibrate/stew/${id}?n_baseline=${nBaseline}&n_task=${nTask}`,
      { method: "POST" }
    ),
  calibrateUpload: async (baseline: File, task: File) => {
    const fd = new FormData();
    fd.append("baseline", baseline);
    fd.append("task", task);
    return json<SubjectReport>("/api/calibrate/upload", { method: "POST", body: fd });
  },
  scoreWithCalib: async (calibId: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return json<SubjectReport>(`/api/calibrate/${calibId}/score`, {
      method: "POST",
      body: fd,
    });
  },
};
