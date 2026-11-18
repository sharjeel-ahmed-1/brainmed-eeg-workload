import { api } from "../api/client";
import { getDisplayName } from "./clientId";
import type { HistoryEntry, SubjectReport } from "./types";

export { getClientKey, getDisplayName, setDisplayName } from "./clientId";

const KEY = "brainmed_history_v1";

export function loadHistoryLocal(): HistoryEntry[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "[]") as HistoryEntry[];
  } catch {
    return [];
  }
}

function saveLocal(entries: HistoryEntry[]) {
  localStorage.setItem(KEY, JSON.stringify(entries.slice(0, 40)));
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
  const next = [entry, ...loadHistoryLocal()].slice(0, 40);
  saveLocal(next);
  // Fire-and-forget cloud sync (free DB / SQLite)
  void api.postHistory(entry, getDisplayName()).catch(() => undefined);
  return next;
}

export async function refreshHistoryFromServer(): Promise<HistoryEntry[]> {
  try {
    const remote = await api.getHistory();
    if (remote.entries?.length) {
      saveLocal(remote.entries);
      return remote.entries;
    }
  } catch {
    /* offline / cold start — keep local */
  }
  return loadHistoryLocal();
}

export async function clearHistoryAll(): Promise<void> {
  localStorage.removeItem(KEY);
  try {
    await api.clearHistory();
  } catch {
    /* ignore */
  }
}
