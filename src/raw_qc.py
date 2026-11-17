"""Raw .mat QC: exact zeros and flat (constant) segments."""
from __future__ import annotations

from typing import Dict, List

import numpy as np
from scipy.io import loadmat

import config

# Pre-specified: flat = identical consecutive samples for >= 8 samples (~62.5 ms at 128 Hz)
FLAT_MIN_LEN = 8


def subject_zero_flat_stats(x: np.ndarray) -> Dict:
    """x: (n_channels, n_times). Scalars only."""
    n_zero = int((x == 0).sum())
    flat_runs = 0
    flat_samp = 0
    max_flat = 0
    for ch in range(x.shape[0]):
        row = x[ch]
        i = 0
        n = len(row)
        while i < n:
            j = i + 1
            while j < n and row[j] == row[i]:
                j += 1
            run = j - i
            if run >= FLAT_MIN_LEN:
                flat_runs += 1
                flat_samp += run
                if run > max_flat:
                    max_flat = run
            i = j
    return {
        "n_zero": n_zero,
        "pct_zero": 100.0 * n_zero / x.size,
        "n_flat_runs": flat_runs,
        "max_flat_len": max_flat,
        "n_flat_samp": flat_samp,
    }


def audit_all_subjects() -> List[Dict]:
    mat = loadmat(str(config.DATASET_MAT), squeeze_me=False, struct_as_record=False)
    data = np.asarray(mat["dataset"], dtype=np.float64)
    rows = []
    for s in range(data.shape[2]):
        st = subject_zero_flat_stats(data[:, :, s])
        st["subject"] = s
        rows.append(st)
    return rows


def format_raw_qc(rows: List[Dict]) -> List[str]:
    lines = [
        "=== RAW QC (exact zeros + flat segments) ===",
        f"flat = run of identical samples length>={FLAT_MIN_LEN} on any channel",
        "Handling: NOT specially rejected today; bandpass+avg-ref attenuates DC/flats; "
        "amp rejection uses FILTERED epoch PTP (low-PTP flats are NOT dropped by amp rule).",
        f"{'s':>3} {'n_zero':>7} {'pct_zero':>8} {'flat_runs':>9} {'max_flat':>8} {'flat_samp':>9} flag",
    ]
    for r in rows:
        flag = []
        if r["n_zero"] > 0:
            flag.append("HAS_ZERO")
        if r["n_flat_runs"] > 0:
            flag.append("HAS_FLAT")
        if r["n_flat_samp"] >= 1000:
            flag.append("HEAVY_FLAT")
        lines.append(
            f"{r['subject']:3d} {r['n_zero']:7d} {r['pct_zero']:8.3f} "
            f"{r['n_flat_runs']:9d} {r['max_flat_len']:8d} {r['n_flat_samp']:9d} "
            f"{','.join(flag) if flag else '-'}"
        )
    n_flag = sum(1 for r in rows if r["n_zero"] or r["n_flat_runs"])
    lines.append(f"Subjects with zero or flat flags: {n_flag}/{len(rows)}")
    return lines
