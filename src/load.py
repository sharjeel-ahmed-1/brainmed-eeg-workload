from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

import mne
import numpy as np
from scipy.io import loadmat

import config


def load_raw(path: Path) -> mne.io.BaseRaw:
    """Load a standard EEG file (EDF/FIF/etc.) for the Streamlit uploader path."""
    raw = mne.io.read_raw(path, preload=True, verbose="ERROR")
    raw.pick("eeg")
    return raw


@lru_cache(maxsize=1)
def _load_stew_dataset() -> np.ndarray:
    """Load full STEW tensor once: (n_channels, n_times, n_subjects)."""
    mat = loadmat(str(config.DATASET_MAT), squeeze_me=False, struct_as_record=False)
    if "dataset" not in mat:
        keys = [k for k in mat if not k.startswith("__")]
        raise KeyError(f"dataset.mat missing 'dataset'; keys={keys}")
    data = np.asarray(mat["dataset"], dtype=np.float64)
    if data.shape != (config.N_CHANNELS, config.N_TIMES, config.N_SUBJECTS):
        raise ValueError(
            f"Unexpected dataset shape {data.shape}; "
            f"expected {(config.N_CHANNELS, config.N_TIMES, config.N_SUBJECTS)} "
            "(channels, time, subjects). See data/DATA_SUMMARY.md."
        )
    return data


def _load_mat_vector(path: Path, key: str) -> np.ndarray:
    mat = loadmat(str(path), squeeze_me=False, struct_as_record=False)
    if key not in mat:
        keys = [k for k in mat if not k.startswith("__")]
        raise KeyError(f"{path.name} missing '{key}'; keys={keys}")
    values = np.asarray(mat[key]).reshape(-1)
    if values.shape[0] != config.N_SUBJECTS:
        raise ValueError(
            f"{path.name} length {values.shape[0]} != n_subjects {config.N_SUBJECTS}"
        )
    return values


def load_stew_ratings() -> np.ndarray:
    """Raw integer ratings (one per subject)."""
    return _load_mat_vector(config.RATING_MAT, "rating").astype(int)


def load_stew_labels(target: str = "2class", threshold: Optional[int] = None) -> np.ndarray:
    """
    Subject-level labels.
    - 2class (primary): rating >= threshold (default RATING_HIGH_THRESHOLD) → 1 else 0
    - 3class (secondary): class_012 ∈ {0, 1, 2}
    """
    if target == "2class":
        thr = config.RATING_HIGH_THRESHOLD if threshold is None else int(threshold)
        rating = load_stew_ratings()
        return (rating >= thr).astype(int)
    if target == "3class":
        return _load_mat_vector(config.CLASS012_MAT, "class_012").astype(int)
    raise ValueError(f"Unknown target {target!r}; use '2class' or '3class'")


def load_subject_raw(subject_idx: int) -> mne.io.RawArray:
    """
    One subject = one (n_channels, n_times) slice from dataset.mat.
    Channel names are generic (not provided in the .mat).
    """
    if subject_idx < 0 or subject_idx >= config.N_SUBJECTS:
        raise IndexError(f"subject_idx {subject_idx} out of range [0, {config.N_SUBJECTS})")
    data = _load_stew_dataset()
    x = data[:, :, subject_idx]
    ch_names = [f"EEG{i:03d}" for i in range(1, config.N_CHANNELS + 1)]
    info = mne.create_info(ch_names=ch_names, sfreq=config.SFREQ, ch_types="eeg")
    return mne.io.RawArray(x, info, verbose="ERROR")
