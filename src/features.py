from __future__ import annotations

from typing import Tuple

import mne
import numpy as np

import config


def _relative_band_tensor(epochs: mne.Epochs) -> Tuple[np.ndarray, np.ndarray]:
    """Return (rel, freqs) with rel shape (epochs, channels, bands) in config.BANDS order."""
    psd = epochs.compute_psd(
        method="welch",
        fmin=config.BANDPASS[0],
        fmax=config.BANDPASS[1],
        verbose="ERROR",
    )
    data, freqs = psd.get_data(return_freqs=True)
    total = data.sum(axis=-1) + 1e-12
    feats = []
    for lo, hi in config.BANDS.values():
        mask = (freqs >= lo) & (freqs < hi)
        feats.append(data[..., mask].sum(axis=-1) / total)
    rel = np.stack(feats, axis=-1)
    return rel, freqs


def band_power_features(epochs: mne.Epochs) -> np.ndarray:
    """Full feature vector: relative band power per channel + theta/alpha per channel."""
    rel, _ = _relative_band_tensor(epochs)
    ratio = rel[..., 1] / (rel[..., 2] + 1e-12)  # theta/alpha
    return np.concatenate([rel.reshape(len(rel), -1), ratio], axis=1)


def compact_frontal_features(epochs: mne.Epochs) -> np.ndarray:
    """
    PRE-SPECIFIED variant A features (2-D):
      - mean frontal relative theta
      - mean frontal theta/alpha
    Uses config.FRONTAL_IDX under Emotiv-14 order assumption.
    """
    rel, _ = _relative_band_tensor(epochs)
    frontal = list(config.FRONTAL_IDX)
    theta = rel[:, frontal, 1].mean(axis=1)
    alpha = rel[:, frontal, 2].mean(axis=1)
    ratio = theta / (alpha + 1e-12)
    return np.column_stack([theta, ratio])
