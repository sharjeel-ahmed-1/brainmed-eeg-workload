from __future__ import annotations

from typing import Tuple

import mne
import numpy as np

import config


def preprocess(raw: mne.io.BaseRaw) -> mne.Epochs:
    raw = raw.copy()
    raw.filter(*config.BANDPASS, verbose="ERROR")
    if config.NOTCH_HZ < raw.info["sfreq"] / 2:
        raw.notch_filter(config.NOTCH_HZ, verbose="ERROR")
    if abs(raw.info["sfreq"] - config.RESAMPLE_HZ) > 1e-6:
        raw.resample(config.RESAMPLE_HZ, verbose="ERROR")
    raw.set_eeg_reference("average", verbose="ERROR")
    return mne.make_fixed_length_epochs(
        raw, duration=config.EPOCH_SEC, preload=True, verbose="ERROR"
    )


def make_raw_epochs(raw: mne.io.BaseRaw) -> mne.Epochs:
    """Fixed-length epochs on unfiltered raw (for flat/zero QC), same duration as preprocess."""
    return mne.make_fixed_length_epochs(
        raw.copy(), duration=config.EPOCH_SEC, preload=True, verbose="ERROR"
    )


def _longest_constant_run(x: np.ndarray) -> int:
    """Longest run of identical consecutive samples in 1-D array."""
    if x.size == 0:
        return 0
    best = 1
    run = 1
    for i in range(1, x.size):
        if x[i] == x[i - 1]:
            run += 1
            if run > best:
                best = run
        else:
            run = 1
    return int(best)


def flat_zero_bad_mask(data: np.ndarray, run_min: int = None) -> np.ndarray:
    """
    data: (n_epochs, n_ch, n_times) — typically RAW (pre-filter) epochs.
    Returns boolean mask True = DROP.
    Pre-specified rule (data quality only, not tuned on accuracy):
      drop if any exact-zero sample OR any channel has >= run_min identical samples.
    """
    if run_min is None:
        run_min = config.EPOCH_FLAT_RUN_MIN
    n_ep = data.shape[0]
    bad = np.zeros(n_ep, dtype=bool)
    for e in range(n_ep):
        ep = data[e]
        if np.any(ep == 0):
            bad[e] = True
            continue
        for ch in range(ep.shape[0]):
            if _longest_constant_run(ep[ch]) >= run_min:
                bad[e] = True
                break
    return bad


def reject_epochs_flat_zero(
    epochs: mne.Epochs,
    bad_mask: np.ndarray,
) -> Tuple[mne.Epochs, int, int]:
    """
    Apply a precomputed flat/zero bad_mask (True=drop) to epochs.
    Returns (kept_epochs, n_before, n_dropped_flat).
    If all would be dropped, keep the first epoch and count n_before-1 dropped
    (no subject exclusion; pipeline must retain ≥1 epoch).
    """
    n_before = len(epochs)
    if n_before == 0:
        return epochs, 0, 0
    if len(bad_mask) != n_before:
        raise ValueError(f"flat mask length {len(bad_mask)} != n_epochs {n_before}")
    keep = ~bad_mask
    n_dropped = int(bad_mask.sum())
    if n_dropped == 0:
        return epochs, n_before, 0
    if keep.sum() == 0:
        keep = np.zeros(n_before, dtype=bool)
        keep[0] = True
        n_dropped = n_before - 1
    return epochs[keep], n_before, n_dropped


def reject_epochs_amplitude(
    epochs: mne.Epochs,
    z: float = None,
) -> Tuple[mne.Epochs, int, int]:
    """
    Drop epochs whose max-channel peak-to-peak exceeds
    median(ptp) + z * 1.4826 * MAD(ptp) within the subject.

    Applied on FILTERED epochs (after bandpass 1–40 Hz, notch, average reference,
    fixed-length epoching) — NOT on raw .mat samples. DC offset is already removed
    by the high-pass / average reference before PTP is computed.

    Units: same numeric scale as the .mat (µV-like). RawArray is not rescaled to volts.

    Threshold: config.EPOCH_REJECT_Z (default 5) — conventional robust rule chosen
    before any LOSO that used this rejection; NOT tuned on LOSO accuracy.

    Returns (kept_epochs, n_before, n_dropped).
    """
    if z is None:
        z = config.EPOCH_REJECT_Z
    data = epochs.get_data(copy=True)  # (n_epochs, n_ch, n_times)
    n_before = data.shape[0]
    if n_before == 0:
        return epochs, 0, 0
    ptp = np.ptp(data, axis=-1).max(axis=-1)
    med = float(np.median(ptp))
    mad = float(np.median(np.abs(ptp - med))) + 1e-12
    thresh = med + z * 1.4826 * mad
    keep = ptp <= thresh
    n_dropped = int((~keep).sum())
    if n_dropped == 0:
        return epochs, n_before, 0
    if keep.sum() == 0:
        keep = np.zeros(n_before, dtype=bool)
        keep[int(np.argmin(ptp))] = True
        n_dropped = n_before - 1
    return epochs[keep], n_before, n_dropped


def boost_alpha(raw: mne.io.BaseRaw, gain: float) -> mne.io.BaseRaw:
    """Positive-control injection: amplify alpha-band component in-place copy."""
    raw = raw.copy()
    alpha = raw.copy().filter(8.0, 13.0, verbose="ERROR")
    raw._data = raw.get_data() + (gain - 1.0) * alpha.get_data()
    return raw
