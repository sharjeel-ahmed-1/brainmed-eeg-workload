"""
Within-subject session calibration.

Fits a small subject-specific classifier on that person's own baseline (low)
vs task (high) epochs, then scores held-out epochs from the same session.

This does NOT claim to fix cross-subject STEW LOSO — it is a personal relative
score for neuroadaptive / demo use.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import config
from src.predict import aggregate_subject, features_from_raw_path
from src.train import feature_cache_path, load_feature_cache

CALIB_DIR = config.ROOT / "models" / "calib"
CALIB_MSG = (
    "Within-subject calibration: model fit only on this person's baseline vs task "
    "epochs. Cross-subject STEW LOSO stays under-powered (n=45) — personal relative score only; "
    "not a population-validated or clinical detector."
)
STEW_SPLIT_MSG = (
    "STEW mode uses a simulated session split (first epochs = baseline/low, "
    "last epochs = task/high). STEW has no true rest/task markers in-file."
)


def make_within_subject_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    random_state=config.SEED,
                    solver="lbfgs",
                ),
            ),
        ]
    )


def fit_calibrator(X_low: np.ndarray, X_high: np.ndarray) -> Pipeline:
    if len(X_low) < 2 or len(X_high) < 2:
        raise ValueError("Need ≥2 baseline and ≥2 task epochs for calibration")
    X = np.vstack([X_low, X_high])
    y = np.concatenate(
        [np.zeros(len(X_low), dtype=int), np.ones(len(X_high), dtype=int)]
    )
    return make_within_subject_pipeline().fit(X, y)


def _stew_epochs(subject_idx: int) -> np.ndarray:
    cache = load_feature_cache(feature_cache_path())
    X, groups = cache["X"], cache["groups"]
    mask = groups == subject_idx
    if not np.any(mask):
        raise ValueError(f"No cached epochs for subject {subject_idx}")
    return np.asarray(X[mask], dtype=np.float64)


def split_stew_calib(
    X: np.ndarray, n_baseline: int, n_task: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    """
    First n_baseline → low, last n_task → high, middle → score set.
    If no middle remains, score all epochs and flag leakage.
    """
    n = len(X)
    if n < n_baseline + n_task:
        raise ValueError(
            f"Need ≥{n_baseline + n_task} epochs, got {n}. "
            "Lower n_baseline / n_task."
        )
    X_low = X[:n_baseline]
    X_high = X[-n_task:]
    mid = X[n_baseline : n - n_task]
    if len(mid) >= 1:
        return X_low, X_high, mid, "middle_held_out"
    return X_low, X_high, X, "includes_train_epochs"


def save_calibrator(
    pipe: Pipeline,
    meta: Dict[str, Any],
    calib_id: Optional[str] = None,
) -> str:
    CALIB_DIR.mkdir(parents=True, exist_ok=True)
    cid = calib_id or uuid.uuid4().hex[:12]
    joblib.dump({"pipeline": pipe, "meta": meta}, CALIB_DIR / f"{cid}.joblib")
    (CALIB_DIR / f"{cid}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return cid


def load_calibrator(calib_id: str) -> Tuple[Pipeline, Dict[str, Any]]:
    path = CALIB_DIR / f"{calib_id}.joblib"
    if not path.exists():
        raise FileNotFoundError(f"Unknown calibrator id: {calib_id}")
    blob = joblib.load(path)
    return blob["pipeline"], dict(blob.get("meta") or {})


def calibrate_stew_subject(
    subject_idx: int,
    n_baseline: int = 10,
    n_task: int = 10,
) -> Dict[str, Any]:
    if subject_idx < 0 or subject_idx >= config.N_SUBJECTS:
        raise IndexError(f"subject_idx {subject_idx} out of range")
    X = _stew_epochs(subject_idx)
    X_low, X_high, X_score, score_set = split_stew_calib(X, n_baseline, n_task)
    pipe = fit_calibrator(X_low, X_high)
    meta = {
        "mode": "stew_session_split",
        "subject_idx": subject_idx,
        "n_baseline": int(n_baseline),
        "n_task": int(n_task),
        "n_total_epochs": int(len(X)),
        "n_score_epochs": int(len(X_score)),
        "score_set": score_set,
        "message": CALIB_MSG + " " + STEW_SPLIT_MSG,
    }
    cid = save_calibrator(pipe, meta)
    out = aggregate_subject(pipe, X_score)
    out.update(
        {
            "y_true": None,
            "subject_idx": subject_idx,
            "source": "stew_within_subject_calib",
            "model_type": "within_subject_calib",
            "train_subjects": [subject_idx],
            "calib_id": cid,
            "calib": meta,
        }
    )
    return out


def calibrate_from_files(baseline_path: Path, task_path: Path) -> Dict[str, Any]:
    X_low = features_from_raw_path(baseline_path)
    X_high = features_from_raw_path(task_path)
    pipe = fit_calibrator(X_low, X_high)
    meta = {
        "mode": "upload_baseline_task",
        "baseline_file": baseline_path.name,
        "task_file": task_path.name,
        "n_baseline": int(len(X_low)),
        "n_task": int(len(X_high)),
        "message": CALIB_MSG,
    }
    cid = save_calibrator(pipe, meta)
    # Score task file as a first readout (user can re-score later)
    out = aggregate_subject(pipe, X_high)
    out.update(
        {
            "y_true": None,
            "subject_idx": None,
            "source": "upload_within_subject_calib",
            "file_name": task_path.name,
            "model_type": "within_subject_calib",
            "train_subjects": None,
            "calib_id": cid,
            "calib": meta,
        }
    )
    return out


def score_with_calibrator(calib_id: str, path: Path) -> Dict[str, Any]:
    pipe, meta = load_calibrator(calib_id)
    X = features_from_raw_path(path)
    out = aggregate_subject(pipe, X)
    out.update(
        {
            "y_true": None,
            "subject_idx": meta.get("subject_idx"),
            "source": "upload_scored_with_calib",
            "file_name": path.name,
            "model_type": "within_subject_calib",
            "train_subjects": meta.get("train_subjects")
            or (
                [meta["subject_idx"]]
                if meta.get("subject_idx") is not None
                else None
            ),
            "calib_id": calib_id,
            "calib": meta,
        }
    )
    return out
