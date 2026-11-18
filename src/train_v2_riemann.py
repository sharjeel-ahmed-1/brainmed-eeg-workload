"""
Protocol v2 Track D: Riemannian OAS cov → tangent → LR on newdataset Control vs Stress.

Same LOSO recording aggregation as train_v2_newdataset (mean epoch proba per arm).
Does not overwrite Track B band-power results.

Requires cached NPZ:
  python -m src.cache_newdataset --conditions EO,AC1,AC2,AC3,AC4 --arms control,stress

Example:
  python -m src.train_v2_riemann --conditions AC1,EO,AC2,AC3,AC4 --log-dir logs/v2
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Sequence, Tuple

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import LeaveOneGroupOut

import config
import config_ext
from src.features_riemann import make_riemann_lr_pipeline
from src.load_newdataset import Arm, Condition, cache_path, list_subject_ids, to_mne_raw
from src.preprocess import reject_epochs_amplitude


def _epochs_from_cache(arm: Arm, condition: Condition, sid: str) -> np.ndarray:
    """Return epoch tensor (n_epochs, n_ch, n_times) after Track-B preprocess/reject."""
    import mne

    path = cache_path(arm, condition, sid)
    z = np.load(path)
    data = np.nan_to_num(np.asarray(z["data"], dtype=np.float64), nan=0.0)
    sfreq = float(z["sfreq"])
    if data.shape[1] < int(sfreq * 2):
        raise ValueError(f"Too short for epochs: {path} shape={data.shape}")
    raw = to_mne_raw(data, sfreq=sfreq)
    raw.filter(config.BANDPASS[0], config.BANDPASS[1], verbose="ERROR")
    if config.NOTCH_HZ < raw.info["sfreq"] / 2:
        raw.notch_filter(config.NOTCH_HZ, verbose="ERROR")
    raw.set_eeg_reference("average", verbose="ERROR")
    epochs = mne.make_fixed_length_epochs(
        raw, duration=config.EPOCH_SEC, preload=True, verbose="ERROR"
    )
    epochs, _, _ = reject_epochs_amplitude(epochs, z=config.EPOCH_REJECT_Z)
    if len(epochs) == 0:
        raise ValueError(f"All epochs rejected for {arm}/{condition}/S{sid}")
    return np.asarray(epochs.get_data(copy=True), dtype=np.float64)


def build_xy(
    condition: Condition, subject_ids: List[str]
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
    """X epochs (n, ch, time), y stress/control, groups=subject index."""
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
                X = _epochs_from_cache(arm, condition, sid)  # type: ignore[arg-type]
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
            print(f"epochs {sid}:{arm} n={len(X)} shape={X.shape[1:]}", flush=True)

    if not Xs:
        raise FileNotFoundError("No cached recordings found — run cache_newdataset first")
    return np.concatenate(Xs, axis=0), np.concatenate(ys), np.concatenate(gs), keys


def loso_recording_preds(
    X: np.ndarray, y: np.ndarray, groups: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    LOSO by subject. Mean-proba per control/stress recording → two preds per subject.
    """
    logo = LeaveOneGroupOut()
    y_true_rec: List[int] = []
    y_pred_rec: List[int] = []
    subj_rec: List[int] = []
    n_folds = logo.get_n_splits(X, y, groups)
    fold_i = 0

    for tr, te in logo.split(X, y, groups):
        fold_i += 1
        held = int(np.unique(groups[te])[0])
        clf = make_riemann_lr_pipeline().fit(X[tr], y[tr])
        proba = clf.predict_proba(X[te])
        classes = list(clf.named_steps["clf"].classes_)
        hi = classes.index(1) if 1 in classes else int(np.argmax(classes))
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
        if fold_i % 10 == 0 or fold_i == n_folds:
            print(f"  LOSO fold {fold_i}/{n_folds} held={held}", flush=True)

    return np.asarray(y_true_rec), np.asarray(y_pred_rec), np.asarray(subj_rec)


def run(condition: Condition, log_dir: Path) -> dict:
    log_dir.mkdir(parents=True, exist_ok=True)
    ids = list_subject_ids("control", condition)
    ids = [
        s
        for s in ids
        if cache_path("control", condition, s).exists()
        and cache_path("stress", condition, s).exists()
    ]
    print(f"[{condition}] subjects with both arms cached: {len(ids)}", flush=True)
    X, y, groups, _keys = build_xy(condition, ids)
    print(
        f"[{condition}] epochs total={len(X)} X.shape={X.shape} "
        f"y0={int((y == 0).sum())} y1={int((y == 1).sum())}",
        flush=True,
    )
    y_true, y_pred, subj = loso_recording_preds(X, y, groups)
    acc = float(accuracy_score(y_true, y_pred))
    bal = float(balanced_accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist()
    maj = float(np.mean(y_true == np.bincount(y_true).argmax()))
    summary = {
        "protocol": "v2_riemann_oas_tangent_lr",
        "condition": condition,
        "citation": config_ext.NEWDATASET_CITATION,
        "sfreq_original": config_ext.NEWDATASET_SFREQ,
        "sfreq_analysis": config_ext.NEWDATASET_RESAMPLE_HZ,
        "pipeline": "Covariances(oas)|TangentSpace(riemann)|StandardScaler|LogisticRegression",
        "n_subjects": len(ids),
        "n_epochs": int(len(X)),
        "n_recordings_scored": int(len(y_true)),
        "majority_acc": maj,
        "loso_recording_acc": acc,
        "loso_recording_bal_acc": bal,
        "loso_recording_macro_f1": macro_f1,
        "confusion_matrix_labels_01": cm,
        "subject_ids": ids,
        "seed": config.SEED,
    }
    np.savez(
        log_dir / f"riemann_{condition}_preds.npz",
        y_true=y_true,
        y_pred=y_pred,
        subject=subj,
    )
    (log_dir / f"riemann_{condition}_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    md = log_dir / f"RIEMANN_{condition}_LOSO.md"
    md.write_text(
        "\n".join(
            [
                f"# Riemannian Control vs Stress LOSO — {condition}",
                "",
                f"- Protocol: OAS cov → Riemann tangent → balanced LR (seed={config.SEED})",
                f"- Citation: {config_ext.NEWDATASET_CITATION}",
                f"- Subjects: {len(ids)}; epochs: {len(X)}; recordings scored: {len(y_true)}",
                f"- Majority: {maj:.3f}",
                f"- Recording-level LOSO acc: **{acc:.3f}** (bal {bal:.3f}, macro-F1 {macro_f1:.3f})",
                f"- Confusion matrix [rows true 0/1, cols pred 0/1]: {cm}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2), flush=True)
    return summary


def run_all(conditions: Sequence[Condition], log_dir: Path) -> List[dict]:
    results = [run(c, log_dir) for c in conditions]
    lines = [
        "# Riemannian newdataset Control vs Stress — all conditions",
        "",
        "Pipeline: `Covariances(oas) → TangentSpace(riemann) → StandardScaler → LogisticRegression`",
        "Split: leave-one-subject-out; recording = mean epoch probability.",
        "",
        "| condition | n_subjects | n_rec | majority | LOSO acc | LOSO bal-acc | macro-F1 |",
        "|-----------|------------|-------|----------|----------|--------------|----------|",
    ]
    for s in results:
        lines.append(
            f"| {s['condition']} | {s['n_subjects']} | {s['n_recordings_scored']} | "
            f"{s['majority_acc']:.3f} | **{s['loso_recording_acc']:.3f}** | "
            f"{s['loso_recording_bal_acc']:.3f} | {s['loso_recording_macro_f1']:.3f} |"
        )
    lines.append("")
    (log_dir / "RIEMANN_ALL_CONDITIONS.md").write_text("\n".join(lines), encoding="utf-8")
    (log_dir / "riemann_all_summary.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    return results


def main():
    p = argparse.ArgumentParser(description="Track D Riemannian LOSO on newdataset")
    p.add_argument(
        "--conditions",
        default="AC1,EO,AC2,AC3,AC4",
        help="Comma-separated conditions (default: AC1,EO,AC2,AC3,AC4)",
    )
    p.add_argument("--log-dir", type=Path, default=config.ROOT / "logs" / "v2")
    args = p.parse_args()
    conditions: List[Condition] = [
        c.strip().upper() for c in args.conditions.split(",") if c.strip()
    ]  # type: ignore[misc]
    run_all(conditions, args.log_dir)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
