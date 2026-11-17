"""Inference helpers for the Streamlit demo (recorded STEW / optional upload)."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import joblib
import numpy as np
from sklearn.pipeline import Pipeline

import config
from src.features import band_power_features
from src.load import load_raw, load_stew_labels, load_subject_raw
from src.preprocess import (
    flat_zero_bad_mask,
    make_raw_epochs,
    preprocess,
    reject_epochs_amplitude,
    reject_epochs_flat_zero,
)
from src.train import feature_cache_path, load_feature_cache, make_rf


def _epoch_y(groups: np.ndarray, y_subject: np.ndarray) -> np.ndarray:
    return np.array([int(y_subject[g]) for g in groups], dtype=int)


def save_primary_model(path: Path = None) -> Path:
    """
    Fit PRIMARY RF on all cached epochs and save.
    Demo only — not a held-out model (see docs/PROJECT.md).
    """
    path = path or config.MODEL_PATH
    cache = load_feature_cache(feature_cache_path())
    X, groups = cache["X"], cache["groups"]
    y = _epoch_y(groups, load_stew_labels("2class"))
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(make_rf().fit(X, y), path)
    return path


def load_model(path: Path = None) -> Pipeline:
    path = path or config.MODEL_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"No model at {path}. Run: python -c \"from src.predict import save_primary_model; save_primary_model()\""
        )
    return joblib.load(path)


def aggregate_subject(
    model: Pipeline, X_epochs: np.ndarray
) -> Dict[str, object]:
    """Mean-proba subject decision (matches LOSO aggregation)."""
    if X_epochs.size == 0:
        raise ValueError("No epochs to score")
    proba = model.predict_proba(X_epochs)
    classes = model.named_steps["clf"].classes_
    mean_p = proba.mean(axis=0)
    pred = int(classes[int(np.argmax(mean_p))])
    # P(high) if class 1 exists, else max mean proba
    if 1 in classes:
        p_high = float(mean_p[list(classes).index(1)])
    else:
        p_high = float(mean_p.max())
    return {
        "pred": pred,
        "p_high": p_high,
        "mean_proba": mean_p,
        "classes": classes,
        "epoch_proba": proba,
        "n_epochs": int(len(X_epochs)),
        "X": X_epochs,
    }


def predict_stew_subject(subject_idx: int, model: Pipeline = None) -> Dict[str, object]:
    """Score one STEW subject with the all-subject demo model (not held-out)."""
    model = model or load_model()
    cache = load_feature_cache(feature_cache_path())
    X, groups = cache["X"], cache["groups"]
    mask = groups == subject_idx
    if not np.any(mask):
        raise ValueError(f"No cached epochs for subject {subject_idx}")
    out = aggregate_subject(model, X[mask])
    y_true = int(load_stew_labels("2class")[subject_idx])
    out["y_true"] = y_true
    out["subject_idx"] = subject_idx
    out["source"] = "stew_cache"
    out["model_type"] = "demo_all_subject"
    out["train_subjects"] = [i for i in range(config.N_SUBJECTS)]
    return out


def predict_stew_subject_loso(subject_idx: int) -> Dict[str, object]:
    """
    Honest held-out score: fit PRIMARY RF on all subjects except subject_idx,
    then score that subject's cached epochs (matches LOSO aggregation).
    """
    if subject_idx < 0 or subject_idx >= config.N_SUBJECTS:
        raise IndexError(f"subject_idx {subject_idx} out of range")
    cache = load_feature_cache(feature_cache_path())
    X, groups = cache["X"], cache["groups"]
    y_subject = load_stew_labels("2class")
    y = _epoch_y(groups, y_subject)
    train_mask = groups != subject_idx
    test_mask = groups == subject_idx
    if not np.any(test_mask):
        raise ValueError(f"No cached epochs for subject {subject_idx}")
    model = make_rf().fit(X[train_mask], y[train_mask])
    out = aggregate_subject(model, X[test_mask])
    out["y_true"] = int(y_subject[subject_idx])
    out["subject_idx"] = subject_idx
    out["source"] = "stew_loso_held_out"
    out["model_type"] = "loso_held_out"
    out["train_subjects"] = sorted({int(g) for g in groups[train_mask]})
    return out


def features_from_raw_path(path: Path) -> np.ndarray:
    """Upload path: same preprocess + reject rules as training (single recording)."""
    raw = load_raw(path)
    if raw.info["nchan"] != config.N_CHANNELS:
        raise ValueError(
            f"Expected {config.N_CHANNELS} EEG channels, got {raw.info['nchan']}"
        )
    raw_ep = make_raw_epochs(raw)
    flat_mask = flat_zero_bad_mask(raw_ep.get_data())
    epochs = preprocess(raw)
    epochs, _, _ = reject_epochs_flat_zero(epochs, flat_mask)
    epochs, _, _ = reject_epochs_amplitude(epochs, z=config.EPOCH_REJECT_Z)
    if len(epochs) == 0:
        raise ValueError("All epochs rejected (flat/zero or amplitude)")
    return band_power_features(epochs)


def predict_upload(path: Path, model: Pipeline = None) -> Dict[str, object]:
    model = model or load_model()
    X = features_from_raw_path(path)
    out = aggregate_subject(model, X)
    out["y_true"] = None
    out["subject_idx"] = None
    out["source"] = "upload"
    out["file_name"] = path.name
    out["model_type"] = "demo_all_subject"
    out["train_subjects"] = [i for i in range(config.N_SUBJECTS)]
    return out


def export_stew_subject_fif(subject_idx: int, out_path: Path = None) -> Path:
    """Write one STEW subject as FIF so the upload flow can be tested without a headset."""
    raw = load_subject_raw(subject_idx)
    if out_path is None:
        out_dir = config.ROOT / "data" / "exports"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"stew_S{subject_idx:02d}_raw.fif"
    raw.save(out_path, overwrite=True)
    return out_path


def predict_stew_live(subject_idx: int, model: Pipeline = None) -> Dict[str, object]:
    """Recompute features from STEW .mat (slower; for sanity vs cache)."""
    model = model or load_model()
    raw = load_subject_raw(subject_idx)
    raw_ep = make_raw_epochs(raw)
    flat_mask = flat_zero_bad_mask(raw_ep.get_data())
    epochs = preprocess(raw)
    epochs, _, _ = reject_epochs_flat_zero(epochs, flat_mask)
    epochs, _, _ = reject_epochs_amplitude(epochs, z=config.EPOCH_REJECT_Z)
    if len(epochs) == 0:
        raise ValueError(f"Subject {subject_idx}: all epochs rejected")
    X = band_power_features(epochs)
    out = aggregate_subject(model, X)
    out["y_true"] = int(load_stew_labels("2class")[subject_idx])
    out["subject_idx"] = subject_idx
    out["source"] = "stew_live"
    return out
