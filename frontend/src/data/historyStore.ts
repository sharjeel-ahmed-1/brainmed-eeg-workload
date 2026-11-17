import type { HistoryEntry, SubjectReport } from "./types";

const KEY = "brainmed_history_v1";

export function loadHistory(): HistoryEntry[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "[]") as HistoryEntry[];
  } catch {
    return [];
  }
}

export function pushHistory(report: SubjectReport, label: string) {
  const entry: HistoryEntry = {
    id: `${Date.now()}`,
    at: new Date().toISOString(),
    label,
    pred_label: report.pred_label,
    p_high: report.p_high,
    source: report.source,
    subject_idx: report.subject_idx ?? null,
    model_type: report.model_type ?? null,
  };
  const next = [entry, ...loadHistory()].slice(0, 40);
  localStorage.setItem(KEY, JSON.stringify(next));
  return next;
}
