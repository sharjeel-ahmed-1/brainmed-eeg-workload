export type RangeName = "today" | "week" | "month";

export interface BandInfo {
  id: string;
  name: string;
  label: string;
  symbol: string;
  range_hz: number[];
  relative_power: number;
  hz_proxy: number;
  hz_note: string;
  series: number[];
}

export type ModelMode = "demo_all_subject" | "loso_held_out";

export interface CalibMeta {
  mode?: string;
  subject_idx?: number;
  n_baseline?: number;
  n_task?: number;
  n_total_epochs?: number;
  n_score_epochs?: number;
  score_set?: string;
  baseline_file?: string;
  task_file?: string;
  message?: string;
}

export interface SubjectReport {
  source: string;
  subject_idx?: number | null;
  file_name?: string | null;
  y_true?: number | null;
  pred: number;
  pred_label: string;
  p_high: number;
  n_epochs: number;
  mean_proba: Record<string, number>;
  p_high_series: number[];
  bands: BandInfo[];
  band_profile: Record<string, number>;
  model_type?: ModelMode | string;
  train_subjects?: number[] | null;
  calib_id?: string | null;
  calib?: CalibMeta | null;
  honest: {
    loso_null: boolean;
    message: string;
    loso_acc?: number;
    majority_acc?: number;
    hz_proxy_note?: string;
    units_note?: string;
  };
}

export interface MethodsInfo {
  loso_null: boolean;
  loso_acc: number;
  majority_acc: number;
  perm_p_acc: number;
  message: string;
  calibration?: string;
  montage: { assumed: boolean; names: string[]; note: string };
  units: string;
  lifestyle: string;
}

export interface LiveReplay {
  source: string;
  live: boolean;
  simulated: boolean;
  subject_idx: number;
  n_windows: number;
  windows: {
    i: number;
    t_start_sec: number;
    t_end_sec: number;
    p_high: number;
    pred_label: string;
    band_profile: Record<string, number>;
  }[];
  honest: { message: string };
}

export interface SubjectListItem {
  id: number;
  true_label: number;
  true_label_name: string;
}

export interface DemoDashboard {
  source: "demo";
  range: RangeName;
  disclaimer: string;
  time_spend: { category: string; hours: number; color: string }[];
  concentration_series: { t: number; value: number }[];
  general: {
    avg_label: string;
    avg_value: number;
    avg_hours_per_day: number;
    progress_pct: number;
    target_pct: number;
    highest_day: number;
  };
  target: { on_target_pct: number; target_pct: number };
  band_profile_used: Record<string, number>;
}

export interface HistoryEntry {
  id: string;
  at: string;
  label: string;
  pred_label: string;
  p_high: number;
  source: string;
  subject_idx?: number | null;
  model_type?: string | null;
}
