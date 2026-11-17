"""
Loader / cache for data/raw/newdataset (Control vs Stress Excel EEG).

Citation: Atiwiwat & Hemakom, Mendeley Data s87jk3p5ws — EEG 2000 Hz.
Prefer cache_condition() (calamine, all subjects per sheet) over per-subject openpyxl.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Dict, List, Literal, Optional

import numpy as np

import config
import config_ext

Condition = Literal["EO", "AC1", "AC2", "AC3", "AC4"]
Arm = Literal["control", "stress"]

_ARM_FOLDER = {
    "control": "Mental workload",
    "stress": "Stress",
}
_ARM_TAG = {
    "control": "Control",
    "stress": "Experiment",
}


def newdataset_root() -> Path:
    root = config_ext.NEWDATASET_DIR
    if not root.is_dir():
        raise FileNotFoundError(f"newdataset not found: {root}")
    return root


def eeg_xlsx_path(arm: Arm, condition: Condition) -> Path:
    folder = newdataset_root() / _ARM_FOLDER[arm]
    path = folder / f"{condition} - {_ARM_TAG[arm]}.xlsx"
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def list_subject_ids(arm: Arm = "control", condition: Condition = "AC1") -> List[str]:
    path = eeg_xlsx_path(arm, condition)
    with zipfile.ZipFile(path) as z:
        ss = z.read("xl/sharedStrings.xml").decode("utf-8", errors="replace")
        strings = re.findall(r"<t[^>]*>([^<]*)</t>", ss)
    ids: List[str] = []
    for s in strings:
        if re.fullmatch(r"\d{3}", s):
            ids.append(s)
        elif ids:
            break
    return ids


def require_sfreq() -> float:
    hz = config_ext.NEWDATASET_SFREQ
    if hz is None or float(hz) <= 0:
        raise ValueError(
            "config_ext.NEWDATASET_SFREQ is unset. "
            "Confirm sampling rate from study docs, then set it in config_ext.py."
        )
    return float(hz)


def _resample_poly(data: np.ndarray, orig_hz: float, new_hz: float) -> np.ndarray:
    """data (n_ch, n_times) → resampled along time."""
    from scipy.signal import resample_poly

    up = int(new_hz)
    down = int(orig_hz)
    # reduce fraction
    g = np.gcd(up, down)
    up //= g
    down //= g
    return np.stack([resample_poly(ch, up, down) for ch in data], axis=0)


def to_mne_raw(data: np.ndarray, sfreq: Optional[float] = None):
    """Build mne.io.RawArray; data in µV-like units → volts."""
    import mne

    hz = float(sfreq) if sfreq is not None else require_sfreq()
    info = mne.create_info(
        ch_names=list(config_ext.NEWDATASET_CH_NAMES),
        sfreq=hz,
        ch_types="eeg",
    )
    return mne.io.RawArray(data * 1e-6, info, verbose=False)


def cache_path(arm: Arm, condition: Condition, subject_id: str) -> Path:
    sid = f"{int(subject_id):03d}" if str(subject_id).isdigit() else str(subject_id)
    return config_ext.NEWDATASET_CACHE_DIR / arm / condition / f"S{sid}.npz"


def _sheet_numeric(rows) -> tuple[List[str], np.ndarray]:
    """Header subject ids + float body (n_times, n_cols)."""
    import pandas as pd

    header = [str(x).zfill(3) if str(x).isdigit() else str(x) for x in rows[0]]
    df = pd.DataFrame(rows[1:])
    arr = df.iloc[:, : len(header)].apply(pd.to_numeric, errors="coerce").to_numpy(
        dtype=np.float32
    )
    return header, arr


def cache_condition(
    arm: Arm,
    condition: Condition,
    *,
    resample_hz: Optional[float] = None,
    overwrite: bool = False,
    max_subjects: Optional[int] = None,
) -> List[Path]:
    """
    Cache all subjects for one arm×condition at NEWDATASET_RESAMPLE_HZ (default 250).

    Streams one channel sheet at a time (low memory) — needed for large EO workbooks.
    """
    from python_calamine import CalamineWorkbook

    resample_hz = float(resample_hz or config_ext.NEWDATASET_RESAMPLE_HZ)
    orig = require_sfreq()
    out_dir = config_ext.NEWDATASET_CACHE_DIR / arm / condition
    out_dir.mkdir(parents=True, exist_ok=True)

    sids = list_subject_ids(arm, condition)
    if max_subjects is not None:
        sids = sids[:max_subjects]

    if not overwrite:
        existing = [cache_path(arm, condition, s) for s in sids]
        if existing and all(p.exists() for p in existing):
            return existing

    path = eeg_xlsx_path(arm, condition)
    print(f"loading {path.name} (channel-stream)…", flush=True)
    wb = CalamineWorkbook.from_path(path)
    channels = list(config_ext.NEWDATASET_CH_NAMES)

    # sid -> list of channel segments (float32), ranges from channel 0
    per_ch: Dict[str, List[np.ndarray]] = {s: [] for s in sids}
    ranges: Dict[str, tuple[int, int]] = {}
    header_ref: Optional[List[str]] = None

    for ci, ch in enumerate(channels):
        rows = wb.get_sheet_by_name(ch).to_python()
        if not rows:
            raise ValueError(f"Empty sheet {ch} in {path}")
        header, arr = _sheet_numeric(rows)
        del rows
        if header_ref is None:
            header_ref = header
        col_index = {h: i for i, h in enumerate(header)}
        print(f"  sheet {ch}: {arr.shape}", flush=True)

        for sid in sids:
            if sid not in col_index:
                continue
            col = arr[:, col_index[sid]]
            if ci == 0:
                finite = np.isfinite(col)
                if not np.any(finite):
                    continue
                idx = np.where(finite)[0]
                start, end = int(idx[0]), int(idx[-1]) + 1
                ranges[sid] = (start, end)
                seg = col[start:end].copy()
            else:
                if sid not in ranges:
                    continue
                start, end = ranges[sid]
                end = min(end, col.shape[0])
                seg = col[start:end].copy()
            nans = ~np.isfinite(seg)
            if np.any(nans) and np.any(~nans):
                good = np.where(~nans)[0]
                seg[nans] = np.interp(np.where(nans)[0], good, seg[good])
            per_ch[sid].append(seg.astype(np.float32, copy=False))
        del arr

    paths: List[Path] = []
    for sid in sids:
        out = cache_path(arm, condition, sid)
        if out.exists() and not overwrite:
            paths.append(out)
            continue
        chans = per_ch.get(sid) or []
        if len(chans) != len(channels):
            print(f"skip {arm}/{condition}/S{sid}: channels={len(chans)}", flush=True)
            continue
        n_t = min(c.shape[0] for c in chans)
        data = np.stack([c[:n_t] for c in chans], axis=0)
        if abs(resample_hz - orig) > 1e-6:
            data = _resample_poly(data.astype(np.float64), orig, resample_hz).astype(
                np.float32
            )
        np.savez_compressed(
            out,
            data=data,
            subject_id=np.array(sid),
            arm=np.array(arm),
            condition=np.array(condition),
            ch_names=np.array(config_ext.NEWDATASET_CH_NAMES),
            sfreq=np.array(resample_hz),
            sfreq_original=np.array(orig),
            citation=np.array(config_ext.NEWDATASET_CITATION),
        )
        paths.append(out)
        print(
            f"cached {arm}/{condition}/S{sid} shape={data.shape} "
            f"({data.shape[1] / resample_hz:.1f}s)",
            flush=True,
        )
    return paths


def load_cached(arm: Arm, condition: Condition, subject_id: str) -> Dict:
    path = cache_path(arm, condition, subject_id)
    if not path.exists():
        raise FileNotFoundError(path)
    z = np.load(path, allow_pickle=True)
    return {k: z[k] for k in z.files}


def paired_label_table(conditions: tuple = ("EO", "AC1", "AC2", "AC3", "AC4")) -> List[Dict[str, object]]:
    ids = list_subject_ids("control", "AC1")
    rows: List[Dict[str, object]] = []
    for sid in ids:
        for cond in conditions:
            for arm, y in (("control", 0), ("stress", 1)):
                rows.append(
                    {
                        "subject_id": sid,
                        "arm": arm,
                        "condition": cond,
                        "y_stress": y,
                        "path": str(eeg_xlsx_path(arm, cond)),  # type: ignore[arg-type]
                    }
                )
    return rows
