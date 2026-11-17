"""
Protocol v2 Track B: Control vs Stress LOSO on cached newdataset.

Requires:
  python -m src.cache_newdataset --conditions AC1

Example:
  python -m src.train_v2_newdataset --condition AC1 --log-dir logs/v2
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Tuple

import numpy as np
from sklearn.metrics import accuracy_score, balanced_accuracy_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

import config
import config_ext
from src.features import band_power_features
from src.load_newdataset import Arm, Condition, cache_path, list_subject_ids, to_mne_raw
from src.preprocess import reject_epochs_amplitude


def _make_rf() -> Pipeline:
    return Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "clf",
                RandomForestClassifier(
                    n_estimators=300,
                    class_weight="balanced",
                    random_state=config.SEED,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def _features_from_cache(arm: Arm, condition: Condition, sid: str) -> np.ndarray:
    import mne

    path = cache_path(arm, condition, sid)
    z = np.load(path)
    data = np.nan_to_num(np.asarray(z["data"], dtype=np.float64), nan=0.0)
    sfreq = float(z["sfreq"])
    if data.shape[1] < int(sfreq * 2):
        raise ValueError(f"Too short for features: {path} shape={data.shape}")
    raw = to_mne_raw(data, sfreq=sfreq)
    raw.filter(config.BANDPASS[0], config.BANDPASS[1], verbose="ERROR")
    if config.NOTCH_HZ < raw.info["sfreq"] / 2:
        raw.notch_filter(config.NOTCH_HZ, verbose="ERROR")
    raw.set_eeg_reference("average", verbose="ERROR")
    epochs = mne.make_fixed_length_epochs(
        raw, duration=config.EPOCH_SEC, preload=True, verbose="ERROR"
    )
    # Paper: reject |amp| > 150 µV — data already µV-like before to_mne (*1e-6)
    epochs, _, _ = reject_epochs_amplitude(epochs, z=config.EPOCH_REJECT_Z)
    if len(epochs) == 0:
        raise ValueError(f"All epochs rejected for {arm}/{condition}/S{sid}")
    return band_power_features(epochs)


def build_xy(
    condition: Condition, subject_ids: List[str]
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
    """
    X epochs, y stress(1)/control(0), groups=subject index, recording_keys.
    """
    Xs: List[np.ndarray] = []
    ys: List[np.ndarray] = []
    gs: List[np.ndarray] = []
    keys: List[str] = []
    sid_to_i = {s: i for i, s in enumerate(subject_ids)}

    for sid in subject_ids:
        for arm, y in (("control", 0), ("stress", 1)):
            path = cache_path(arm, condition, sid)  # type: ignore[arg-type]
            if not path.exists():
                print(f"skip missing cache {path}", flush=True)
                continue
            try:
                X = _features_from_cache(arm, condition, sid)  # type: ignore[arg-type]
            except Exception as e:
                print(f"skip {sid}:{arm}: {type(e).__name__}: {e}", flush=True)
                continue
            if len(X) < 1:
                print(f"skip {sid}:{arm}: zero epochs", flush=True)
                continue
            g = sid_to_i[sid]
            Xs.append(X)
            ys.append(np.full(len(X), y, dtype=int))
            gs.append(np.full(len(X), g, dtype=int))
            keys.append(f"{sid}:{arm}")
            print(f"features {sid}:{arm} epochs={len(X)}", flush=True)

    if not Xs:
        raise FileNotFoundError("No cached recordings found — run cache_newdataset first")
    return np.vstack(Xs), np.concatenate(ys), np.concatenate(gs), keys


def loso_recording_preds(
    X: np.ndarray, y: np.ndarray, groups: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    LOSO by subject. For each held-out subject, mean-proba per class among their
    control epochs and stress epochs → two recording predictions.
    Returns y_true_rec, y_pred_rec, subject_ids_for_rec
    """
    logo = LeaveOneGroupOut()
    y_true_rec: List[int] = []
    y_pred_rec: List[int] = []
    subj_rec: List[int] = []

    for tr, te in logo.split(X, y, groups):
        held = int(np.unique(groups[te])[0])
        clf = _make_rf().fit(X[tr], y[tr])
        proba = clf.predict_proba(X[te])
        classes = list(clf.named_steps["clf"].classes_)
        hi = classes.index(1) if 1 in classes else int(np.argmax(classes))
        # split held epochs by true label (control vs stress recordings)
        y_te = y[te]
        for lab in (0, 1):
            mask = y_te == lab
            if not np.any(mask):
                continue
            mean_p_high = float(proba[mask][:, hi].mean())
            pred = 1 if mean_p_high >= 0.5 else 0
            y_true_rec.append(lab)
            y_pred_rec.append(pred)
            subj_rec.append(held)
    return np.asarray(y_true_rec), np.asarray(y_pred_rec), np.asarray(subj_rec)


def run(condition: Condition, log_dir: Path) -> dict:
    log_dir.mkdir(parents=True, exist_ok=True)
    ids = list_subject_ids("control", condition)
    # only subjects with both arms cached
    ids = [
        s
        for s in ids
        if cache_path("control", condition, s).exists()
        and cache_path("stress", condition, s).exists()
    ]
    print(f"subjects with both arms cached: {len(ids)}", flush=True)
    X, y, groups, _keys = build_xy(condition, ids)
    y_true, y_pred, subj = loso_recording_preds(X, y, groups)
    acc = float(accuracy_score(y_true, y_pred))
    bal = float(balanced_accuracy_score(y_true, y_pred))
    maj = float(np.mean(y_true == np.bincount(y_true).argmax()))
    summary = {
        "protocol": "v2_newdataset_control_vs_stress",
        "condition": condition,
        "citation": config_ext.NEWDATASET_CITATION,
        "sfreq_original": config_ext.NEWDATASET_SFREQ,
        "sfreq_analysis": config_ext.NEWDATASET_RESAMPLE_HZ,
        "n_subjects": len(ids),
        "n_recordings_scored": int(len(y_true)),
        "majority_acc": maj,
        "loso_recording_acc": acc,
        "loso_recording_bal_acc": bal,
        "subject_ids": ids,
    }
    np.savez(
        log_dir / f"newdataset_{condition}_preds.npz",
        y_true=y_true,
        y_pred=y_pred,
        subject=subj,
    )
    (log_dir / f"newdataset_{condition}_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    md = log_dir / f"NEWDATASET_{condition}_LOSO.md"
    md.write_text(
        "\n".join(
            [
                f"# Newdataset Control vs Stress LOSO — {condition}",
                "",
                f"- Citation: {config_ext.NEWDATASET_CITATION}",
                f"- Subjects: {len(ids)}",
                f"- Recording-level LOSO acc: **{acc:.3f}** (bal {bal:.3f}, majority {maj:.3f})",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--condition", default="AC1")
    p.add_argument("--log-dir", type=Path, default=config.ROOT / "logs" / "v2")
    args = p.parse_args()
    run(args.condition, args.log_dir)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
