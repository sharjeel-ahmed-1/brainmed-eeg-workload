from __future__ import annotations

import argparse
import hashlib
import os
import time
from collections import Counter
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import joblib
import numpy as np
from joblib import Parallel, delayed
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import config
from src.features import band_power_features, compact_frontal_features
from src.load import load_stew_labels, load_subject_raw
from src.metrics import format_metrics, subject_metrics
from src.preprocess import (
    boost_alpha,
    flat_zero_bad_mask,
    make_raw_epochs,
    preprocess,
    reject_epochs_amplitude,
    reject_epochs_flat_zero,
)
from src.raw_qc import audit_all_subjects, format_raw_qc


def protocol_hash() -> str:
    """Hash preprocess.py + config.py so cache invalidates when they change."""
    h = hashlib.sha256()
    for rel in ("config.py", "src/preprocess.py"):
        h.update(Path(config.ROOT / rel).read_bytes())
        h.update(b"\0")
    return h.hexdigest()[:16]


def feature_cache_path() -> Path:
    return config.FEATURE_CACHE_DIR / f"epoch_features_{protocol_hash()}.npz"


def _stage_log(log_path: Optional[Path], msg: str) -> None:
    line = msg if msg.endswith("\n") else msg + "\n"
    print(line, end="", flush=True)
    if log_path is not None:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)


def _elapsed(t0: float) -> str:
    return f"{time.perf_counter() - t0:.1f}s"


# Main-path RF: unchanged (n_jobs=-1)
def make_rf() -> Pipeline:
    return Pipeline([
        ("scale", StandardScaler()),
        ("clf", RandomForestClassifier(
            n_estimators=300,
            class_weight="balanced",
            random_state=config.SEED,
            n_jobs=-1,
        )),
    ])


# Worker RF for Parallel outer loops: n_jobs=1 to avoid oversubscription
def make_rf_worker() -> Pipeline:
    return make_rf_worker_seeded(config.SEED)


def make_rf_worker_seeded(seed: int) -> Pipeline:
    """RF for Parallel workers: n_jobs=1; seed often SEED+k per permutation."""
    return Pipeline([
        ("scale", StandardScaler()),
        ("clf", RandomForestClassifier(
            n_estimators=300,
            class_weight="balanced",
            random_state=seed,
            n_jobs=1,
        )),
    ])


def make_lr() -> Pipeline:
    return Pipeline([
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=config.SEED,
        )),
    ])


def _aggregate_subject_pred(proba: np.ndarray, classes: np.ndarray) -> int:
    mean_p = proba.mean(axis=0)
    return int(classes[int(np.argmax(mean_p))])


def _baselines(y_subject: np.ndarray) -> Tuple[float, float, int]:
    counts = Counter(y_subject.tolist())
    n = len(y_subject)
    majority_label, majority_n = counts.most_common(1)[0]
    return majority_n / n, 1.0 / len(counts), int(majority_label)


def _epoch_y(groups: np.ndarray, y_subject: np.ndarray) -> np.ndarray:
    return np.array([int(y_subject[g]) for g in groups], dtype=int)


def _build_clf(clf_kind: str, seed: int = None) -> Pipeline:
    """Pickle-friendly model factory for Parallel workers (RF uses n_jobs=1)."""
    if seed is None:
        seed = config.SEED
    if clf_kind == "rf":
        return make_rf_worker_seeded(seed)
    if clf_kind == "lr":
        return make_lr()
    raise ValueError(f"Unknown clf_kind={clf_kind!r}")


def _loso_epoch_fold(
    X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    y_subject: np.ndarray,
    tr: np.ndarray,
    te: np.ndarray,
    clf_kind: str,
    seed: int,
) -> Tuple[int, int, int]:
    held = int(np.unique(groups[te])[0])
    model = _build_clf(clf_kind, seed).fit(X[tr], y[tr])
    proba = model.predict_proba(X[te])
    classes = model.named_steps["clf"].classes_
    pred = _aggregate_subject_pred(proba, classes)
    return held, int(y_subject[held]), pred


def loso_subject_preds(
    X: np.ndarray,
    groups: np.ndarray,
    y_subject: np.ndarray,
    clf_kind: str = "rf",
    n_jobs: int = -1,
    seed: int = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    LOSO on epochs; one prediction per held-out subject via mean proba.
    Outer folds Parallel(n_jobs=-1); RF inside each fold uses n_jobs=1.
    """
    if seed is None:
        seed = config.SEED
    assert_finite_features(X, "loso_subject_preds")
    y = _epoch_y(groups, y_subject)
    splits = list(LeaveOneGroupOut().split(X, y, groups))
    if n_jobs == 1:
        results = [
            _loso_epoch_fold(X, y, groups, y_subject, tr, te, clf_kind, seed)
            for tr, te in splits
        ]
    else:
        results = Parallel(n_jobs=n_jobs, prefer="processes")(
            delayed(_loso_epoch_fold)(X, y, groups, y_subject, tr, te, clf_kind, seed)
            for tr, te in splits
        )
    results = sorted(results, key=lambda r: r[0])
    y_true = np.array([t for _, t, _ in results])
    y_pred = np.array([p for _, _, p in results])
    return y_true, y_pred


def _loso_subj_fold(
    X_subj: np.ndarray,
    y_subject: np.ndarray,
    tr: np.ndarray,
    te: np.ndarray,
    clf_kind: str,
    seed: int,
) -> Tuple[int, int, int]:
    held = int(te[0])
    model = _build_clf(clf_kind, seed).fit(X_subj[tr], y_subject[tr])
    pred = int(model.predict(X_subj[te])[0])
    return held, int(y_subject[held]), pred


def loso_subject_samples(
    X_subj: np.ndarray,
    y_subject: np.ndarray,
    clf_kind: str = "rf",
    n_jobs: int = -1,
    seed: int = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """LOSO where each row is one subject (45 samples). Parallel over folds unless n_jobs=1."""
    if seed is None:
        seed = config.SEED
    assert_finite_features(X_subj, "loso_subject_samples")
    groups = np.arange(len(y_subject))
    splits = list(LeaveOneGroupOut().split(X_subj, y_subject, groups))
    if n_jobs == 1:
        # Plain loop — safe inside an outer Parallel (avoids nested-joblib deadlock)
        results = [
            _loso_subj_fold(X_subj, y_subject, tr, te, clf_kind, seed)
            for tr, te in splits
        ]
    else:
        results = Parallel(n_jobs=n_jobs, prefer="processes")(
            delayed(_loso_subj_fold)(X_subj, y_subject, tr, te, clf_kind, seed)
            for tr, te in splits
        )
    results = sorted(results, key=lambda r: r[0])
    y_true = np.array([t for _, t, _ in results])
    y_pred = np.array([p for _, _, p in results])
    return y_true, y_pred


def report_eval(
    title: str,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_subject: np.ndarray,
    lines: List[str],
    log_path: Optional[Path] = None,
) -> Dict:
    labels = sorted(set(y_subject.tolist()))
    maj, chance, maj_lbl = _baselines(y_subject)
    m = subject_metrics(y_true, y_pred, labels)
    block = format_metrics(m, title)
    block.insert(
        1,
        f"Baselines: majority-class acc={maj:.3f} (label={maj_lbl}) | chance={chance:.3f}",
    )
    for ln in block:
        _stage_log(log_path, ln)
        lines.append(ln)
    lines.append("")
    return m


# ---------------------------------------------------------------------------
# Feature build + audit (outer loop Parallel)
# ---------------------------------------------------------------------------

AUDIT_CACHE_KEYS = (
    "protocol_hash",
    "epochs_fixed",
    "dropped_flat",
    "dropped_amp",
    "dropped_nonfinite",
    "epochs_kept",
    "amp_min",
    "amp_max",
)


def assert_finite_features(X: np.ndarray, where: str) -> None:
    if X.size == 0:
        raise AssertionError(f"{where}: empty feature matrix")
    n_nan = int(np.isnan(X).sum())
    n_inf = int(np.isinf(X).sum())
    if n_nan or n_inf:
        raise AssertionError(f"{where}: features have nan={n_nan} inf={n_inf}")


def _process_one_subject(
    s: int,
    feature_fn_name: str,
    boost: bool,
    gain: float,
) -> Dict:
    """Worker: build features for one subject. feature_fn by name for pickling."""
    feature_fn = band_power_features if feature_fn_name == "band" else compact_frontal_features
    raw = load_subject_raw(s)
    if boost:
        raw = boost_alpha(raw, gain)

    # Flat/zero on RAW epoch segments (pre-filter), index-aligned to filtered epochs
    raw_epochs = make_raw_epochs(raw)
    raw_data = raw_epochs.get_data(copy=True)
    flat_bad = flat_zero_bad_mask(raw_data)

    epochs = preprocess(raw)
    n_fixed = len(epochs)
    if len(raw_epochs) != n_fixed:
        raise AssertionError(
            f"Subject {s}: raw epoch count {len(raw_epochs)} != filtered {n_fixed}"
        )

    # Apply flat/zero first (same indices)
    epochs, _, n_dropped_flat = reject_epochs_flat_zero(epochs, flat_bad)
    # Re-align amp stats on remaining filtered epochs
    data = epochs.get_data(copy=True)
    if not np.isfinite(data).all():
        raise AssertionError(
            f"Subject {s}: non-finite epoch data before amp reject "
            f"(nan={int(np.isnan(data).sum())} inf={int(np.isinf(data).sum())})"
        )
    amp_min = float(np.min(data))
    amp_max = float(np.max(data))
    if not np.isfinite(amp_min) or not np.isfinite(amp_max):
        raise AssertionError(f"Subject {s}: non-finite amp_min/max ({amp_min}, {amp_max})")

    n_before_amp = len(epochs)
    epochs, n_before_amp2, n_dropped_amp = reject_epochs_amplitude(epochs)
    assert n_before_amp == n_before_amp2

    feats = feature_fn(epochs)
    n_nan = int(np.isnan(feats).sum()) if feats.size else 0
    n_inf = int(np.isinf(feats).sum()) if feats.size else 0
    if n_nan or n_inf:
        raise AssertionError(
            f"Subject {s}: non-finite features (nan={n_nan} inf={n_inf}); "
            "refusing silent drop"
        )
    return {
        "s": s,
        "feats": feats,
        "n_fixed": n_fixed,
        "n_dropped_flat": n_dropped_flat,
        "n_dropped_amp": n_dropped_amp,
        "n_dropped_nonfinite": 0,
        "n_kept": len(feats),
        "amp_min": amp_min,
        "amp_max": amp_max,
    }


def build_feature_cache(
    feature_fn: Callable = band_power_features,
    alpha_boost_subjects: Optional[np.ndarray] = None,
    gain: float = None,
    n_jobs: int = -1,
) -> Dict:
    if gain is None:
        gain = config.POSCTRL_ALPHA_GAIN
    feature_fn_name = "band" if feature_fn is band_power_features else "compact"

    boost_flags = [
        bool(alpha_boost_subjects[s]) if alpha_boost_subjects is not None else False
        for s in range(config.N_SUBJECTS)
    ]

    results = Parallel(n_jobs=n_jobs, prefer="processes")(
        delayed(_process_one_subject)(s, feature_fn_name, boost_flags[s], gain)
        for s in range(config.N_SUBJECTS)
    )
    results = sorted(results, key=lambda r: r["s"])

    X_list, groups_list = [], []
    audit = {
        "epochs_fixed": [],
        "dropped_flat": [],
        "dropped_amp": [],
        "dropped_nonfinite": [],
        "epochs_kept": [],
        "epochs_before": [],
        "epochs_after": [],
        "dropped": [],
        "amp_min": [],
        "amp_max": [],
        "nan_epochs": 0,
        "inf_epochs": 0,
        "reused_cache": False,
        "protocol_hash": protocol_hash(),
    }
    for r in results:
        audit["epochs_fixed"].append(r["n_fixed"])
        audit["dropped_flat"].append(r["n_dropped_flat"])
        audit["dropped_amp"].append(r["n_dropped_amp"])
        audit["dropped_nonfinite"].append(r["n_dropped_nonfinite"])
        audit["epochs_kept"].append(r["n_kept"])
        audit["epochs_before"].append(r["n_fixed"])
        audit["epochs_after"].append(r["n_kept"])
        audit["dropped"].append(r["n_dropped_amp"] + r["n_dropped_flat"])
        audit["amp_min"].append(r["amp_min"])
        audit["amp_max"].append(r["amp_max"])
        X_list.append(r["feats"])
        groups_list.extend([r["s"]] * r["n_kept"])

    X = np.vstack(X_list)
    groups = np.array(groups_list, dtype=int)
    assert_finite_features(X, "build_feature_cache")
    if not np.isfinite(audit["amp_min"]).all() or not np.isfinite(audit["amp_max"]).all():
        raise AssertionError("build_feature_cache: non-finite amp_min/amp_max in audit")

    audit["total_before"] = int(sum(audit["epochs_before"]))
    audit["total_dropped"] = int(sum(audit["dropped"]))
    audit["total_dropped_flat"] = int(sum(audit["dropped_flat"]))
    audit["total_dropped_amp"] = int(sum(audit["dropped_amp"]))
    audit["total_dropped_nonfinite"] = int(sum(audit["dropped_nonfinite"]))
    audit["total_after"] = len(X)
    audit["feature_dim"] = int(X.shape[1])
    return {"X": X, "groups": groups, "audit": audit}


def save_feature_cache(cache: Dict, path: Path = None) -> None:
    path = path or feature_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    audit = cache["audit"]
    np.savez_compressed(
        path,
        protocol_hash=np.asarray(protocol_hash()),
        X=cache["X"],
        groups=cache["groups"],
        epochs_fixed=np.asarray(audit["epochs_fixed"], dtype=int),
        dropped_flat=np.asarray(audit["dropped_flat"], dtype=int),
        dropped_amp=np.asarray(audit["dropped_amp"], dtype=int),
        dropped_nonfinite=np.asarray(audit["dropped_nonfinite"], dtype=int),
        epochs_kept=np.asarray(audit["epochs_kept"], dtype=int),
        amp_min=np.asarray(audit["amp_min"], dtype=float),
        amp_max=np.asarray(audit["amp_max"], dtype=float),
    )


def load_feature_cache(path: Path = None) -> Dict:
    path = path or feature_cache_path()
    if not path.exists():
        raise FileNotFoundError(
            f"No cache at {path} (protocol_hash={protocol_hash()}). Rebuild without --reuse-cache."
        )
    data = np.load(path, allow_pickle=True)
    missing = [k for k in AUDIT_CACHE_KEYS if k not in data.files]
    if missing:
        raise RuntimeError(
            f"{path} is missing audit keys {missing}. Delete and rebuild."
        )
    stored = str(np.asarray(data["protocol_hash"]).item())
    current = protocol_hash()
    if stored != current:
        raise RuntimeError(
            f"Cache protocol_hash mismatch: file={stored} current={current}. Rebuild."
        )
    X, groups = data["X"], data["groups"]
    assert_finite_features(X, f"load_feature_cache({path})")
    amp_min = data["amp_min"].astype(float).tolist()
    amp_max = data["amp_max"].astype(float).tolist()
    if not np.isfinite(amp_min).all() or not np.isfinite(amp_max).all():
        raise AssertionError(f"{path}: stored amp_min/amp_max contain NaN/Inf")
    epochs_fixed = data["epochs_fixed"].astype(int).tolist()
    dropped_flat = data["dropped_flat"].astype(int).tolist()
    dropped_amp = data["dropped_amp"].astype(int).tolist()
    dropped_nonfinite = data["dropped_nonfinite"].astype(int).tolist()
    epochs_kept = data["epochs_kept"].astype(int).tolist()
    audit = {
        "epochs_fixed": epochs_fixed,
        "dropped_flat": dropped_flat,
        "dropped_amp": dropped_amp,
        "dropped_nonfinite": dropped_nonfinite,
        "epochs_kept": epochs_kept,
        "epochs_before": epochs_fixed,
        "epochs_after": epochs_kept,
        "dropped": [a + f for a, f in zip(dropped_amp, dropped_flat)],
        "amp_min": amp_min,
        "amp_max": amp_max,
        "nan_epochs": int(sum(dropped_nonfinite)),
        "inf_epochs": 0,
        "total_before": int(sum(epochs_fixed)),
        "total_dropped": int(sum(dropped_amp) + sum(dropped_flat)),
        "total_dropped_flat": int(sum(dropped_flat)),
        "total_dropped_amp": int(sum(dropped_amp)),
        "total_dropped_nonfinite": int(sum(dropped_nonfinite)),
        "total_after": len(X),
        "feature_dim": int(X.shape[1]),
        "reused_cache": True,
        "protocol_hash": current,
    }
    return {"X": X, "groups": groups, "audit": audit}


def print_audit(
    audit: Dict,
    y_subject: np.ndarray,
    lines: List[str],
    log_path: Optional[Path] = None,
) -> None:
    assert len(y_subject) == config.N_SUBJECTS
    if not np.isfinite(audit["amp_min"]).all() or not np.isfinite(audit["amp_max"]).all():
        raise AssertionError(
            "AUDIT FAIL: amp_min/amp_max contain NaN/Inf — refusing to print fake amplitudes. "
            "Rebuild feature cache with real audit fields."
        )
    reused = audit.get("reused_cache", False)
    expected_fixed = int(config.N_TIMES / config.SFREQ // config.EPOCH_SEC)
    header = [
        "=== PIPELINE AUDIT ===",
        f"Subjects: {config.N_SUBJECTS}",
        f"Cache reused: {reused}",
        f"Protocol hash: {audit.get('protocol_hash', protocol_hash())}",
        "Epoch removal steps:",
        f"  1) fixed-length: floor(150/4)={expected_fixed} epochs/subject",
        f"  2) flat/zero (RAW epochs): zero sample OR ≥{config.EPOCH_FLAT_RUN_MIN} identical samples",
        f"  3) amplitude (FILTERED epochs): median+{config.EPOCH_REJECT_Z}*1.4826*MAD",
        "  4) non-finite features: ASSERT (no silent drop)",
        "  No subject exclusions.",
        f"Epochs after fixed-length (sum): {audit['total_before']}",
        f"n_dropped_flat: {audit.get('total_dropped_flat', 0)}",
        f"n_dropped_amp: {audit.get('total_dropped_amp', audit['total_dropped'])}",
        f"n_dropped_nonfinite: {audit.get('total_dropped_nonfinite', 0)}",
        f"Epochs kept (sum): {audit['total_after']}",
        f"Feature dim: {audit['feature_dim']}",
        f"Amplitude range (post-flat, pre-amp-reject filtered data): "
        f"global_min={min(audit['amp_min']):.4g} global_max={max(audit['amp_max']):.4g}",
        "Label↔subject alignment: OK "
        f"(len(labels)={len(y_subject)} == N_SUBJECTS={config.N_SUBJECTS})",
        "Per-subject: fixed | drop_flat | drop_amp | frac_drop | kept | amp[min,max]",
    ]
    for ln in header:
        _stage_log(log_path, ln)
        lines.append(ln)

    heavy = []
    for s in range(config.N_SUBJECTS):
        fixed = audit["epochs_fixed"][s]
        d_flat = audit["dropped_flat"][s]
        d_amp = audit["dropped_amp"][s]
        kept = audit["epochs_kept"][s]
        frac = (d_flat + d_amp) / max(fixed, 1)
        if frac > 0.5:
            heavy.append(s)
        row = (
            f"  s={s:02d} y={int(y_subject[s])} "
            f"fixed={fixed:02d} "
            f"drop_flat={d_flat:02d} "
            f"drop_amp={d_amp:02d} "
            f"frac_drop={frac:.2f} "
            f"kept={kept:02d} "
            f"amp=[{audit['amp_min'][s]:.4g}, {audit['amp_max'][s]:.4g}]"
        )
        _stage_log(log_path, row)
        lines.append(row)

    heavy_line = (
        f"Subjects with >50% epochs dropped: {heavy if heavy else 'none'} "
        f"(still included; no subject exclusions)"
    )
    _stage_log(log_path, heavy_line)
    lines.append(heavy_line)
    lines.append("")
    _stage_log(log_path, "")


# ---------------------------------------------------------------------------
# Permutation (Parallel over permutations; RF n_jobs=1 in workers)
# ---------------------------------------------------------------------------

def _one_permutation(
    X_subj: np.ndarray,
    y_perm: np.ndarray,
    labels: List[int],
    perm_seed: int,
) -> Tuple[float, float]:
    # Inner LOSO folds also parallel; keep n_jobs=1 here to avoid nested oversubscription
    # when outer Parallel already uses all cores across permutations.
    yt, yp = loso_subject_samples(
        X_subj, y_perm, clf_kind="rf", n_jobs=1, seed=perm_seed
    )
    m = subject_metrics(yt, yp, labels)
    return m["accuracy"], m["balanced_accuracy"]


def permutation_test(
    X: np.ndarray,
    groups: np.ndarray,
    y_subject: np.ndarray,
    n_perm: int,
    observed_acc: float,
    observed_bal: float,
    lines: List[str],
    seed: int = None,
    log_path: Optional[Path] = None,
    n_jobs: int = -1,
) -> None:
    """
    Shuffle the 45 SUBJECT-level labels (y_subject), not epoch rows.
    For epoch-level LOSO elsewhere, epoch labels are always derived as y_subject[group_id].
    Here the null uses subject-mean features (45 rows) with the permuted subject labels.
    """
    if seed is None:
        seed = config.SEED
    rng = np.random.default_rng(seed)
    labels = sorted(set(y_subject.tolist()))

    X_subj = np.vstack([X[groups == s].mean(axis=0) for s in range(config.N_SUBJECTS)])

    # Subject-level label shuffles only (length 45), never epoch-label shuffles
    y_perms = [rng.permutation(y_subject) for _ in range(n_perm)]
    assert all(len(yp) == config.N_SUBJECTS for yp in y_perms)
    # RF seeds: SEED+k per permutation
    perm_seeds = [seed + k for k in range(n_perm)]

    _stage_log(
        log_path,
        f"=== PERMUTATION TEST (n={n_perm}, subject-mean features, "
        f"Parallel n_jobs={n_jobs}, RF n_jobs=1, rf_seed=SEED+k) ===",
    )
    lines.append(
        f"=== PERMUTATION TEST (n={n_perm}, subject-mean features, "
        f"Parallel n_jobs={n_jobs}, RF n_jobs=1, rf_seed=SEED+k) ==="
    )
    _stage_log(
        log_path,
        "Permutes the 45 SUBJECT labels; epoch labels elsewhere = y_subject[subject_id]. "
        f"Label RNG default_rng({seed}); RF random_state={seed}+k.",
    )

    t0 = time.perf_counter()
    # Cap workers to CPU count; each task is sequential LOSO (n_jobs=1) — no nesting.
    workers = os.cpu_count() or 4
    if n_jobs == -1:
        n_jobs = workers
    _stage_log(log_path, f"Permutation Parallel workers={n_jobs} (cpu_count={workers})")
    results = Parallel(n_jobs=n_jobs, prefer="processes", batch_size=1)(
        delayed(_one_permutation)(X_subj, y_perms[i], labels, perm_seeds[i])
        for i in range(n_perm)
    )
    null_acc = np.array([a for a, _ in results])
    null_bal = np.array([b for _, b in results])
    _stage_log(log_path, f"Permutation wall time: {_elapsed(t0)}")

    yt_obs, yp_obs = loso_subject_samples(
        X_subj, y_subject, clf_kind="rf", n_jobs=-1, seed=seed
    )
    m_obs = subject_metrics(yt_obs, yp_obs, labels)
    obs_acc_s = m_obs["accuracy"]
    obs_bal_s = m_obs["balanced_accuracy"]

    p_acc = (1 + np.sum(null_acc >= obs_acc_s)) / (1 + n_perm)
    p_bal = (1 + np.sum(null_bal >= obs_bal_s)) / (1 + n_perm)

    summary = [
        f"Observed (epoch-LOSO, for reference): acc={observed_acc:.3f} bal={observed_bal:.3f}",
        f"Observed (subject-mean LOSO, matched null): acc={obs_acc_s:.3f} bal={obs_bal_s:.3f}",
        f"Null accuracy: mean={null_acc.mean():.3f} std={null_acc.std():.3f} "
        f"min={null_acc.min():.3f} max={null_acc.max():.3f}",
        f"Null balanced accuracy: mean={null_bal.mean():.3f} std={null_bal.std():.3f} "
        f"min={null_bal.min():.3f} max={null_bal.max():.3f}",
        f"p-value (acc, right-tailed): {p_acc:.4f}",
        f"p-value (balanced acc, right-tailed): {p_bal:.4f}",
    ]
    for ln in summary:
        _stage_log(log_path, ln)
        lines.append(ln)
    lines.append("")
    _stage_log(log_path, "")


def _posctrl_at_gain(
    y_subject: np.ndarray,
    boost_mask: np.ndarray,
    gain: float,
) -> Tuple[float, Dict]:
    """Build boosted features + LOSO; return (gain, subject_metrics)."""
    cache = build_feature_cache(
        feature_fn=band_power_features,
        alpha_boost_subjects=boost_mask,
        gain=gain,
        n_jobs=-1,
    )
    yt, yp = loso_subject_preds(
        cache["X"], cache["groups"], y_subject, clf_kind="rf", n_jobs=-1
    )
    labels = sorted(set(y_subject.tolist()))
    return float(gain), subject_metrics(yt, yp, labels)


def positive_control(
    y_subject: np.ndarray,
    lines: List[str],
    log_path: Optional[Path] = None,
    run_sensitivity: bool = True,
) -> None:
    _stage_log(log_path, "=== POSITIVE CONTROL (alpha boost → class 1) ===")
    lines.append("=== POSITIVE CONTROL (alpha boost → class 1) ===")
    boost_mask = y_subject == 1
    gain = config.POSCTRL_ALPHA_GAIN
    pct = (gain - 1.0) * 100.0
    note = (
        f"Primary check: alpha gain={gain:g}× "
        f"(+{pct:.0f}% vs original alpha component) for "
        f"{int(boost_mask.sum())} class-1 subjects"
    )
    _stage_log(log_path, note)
    lines.append(note)

    t0 = time.perf_counter()
    cache = build_feature_cache(
        feature_fn=band_power_features,
        alpha_boost_subjects=boost_mask,
        gain=gain,
        n_jobs=-1,
    )
    _stage_log(log_path, f"Positive-control feature build: {_elapsed(t0)}")

    t1 = time.perf_counter()
    yt, yp = loso_subject_preds(
        cache["X"], cache["groups"], y_subject, clf_kind="rf", n_jobs=-1
    )
    _stage_log(log_path, f"Positive-control LOSO (parallel folds): {_elapsed(t1)}")
    m = report_eval(
        f"POSITIVE CONTROL RF (gain={gain:g}×, +{pct:.0f}%)",
        yt, yp, y_subject, lines, log_path,
    )
    ok = m["accuracy"] >= 0.85
    verdict = (
        f"POSITIVE CONTROL {'PASSED' if ok else 'FAILED'} "
        f"(require acc>=0.85, got {m['accuracy']:.3f}; boost={gain:g}× / +{pct:.0f}%)"
    )
    _stage_log(log_path, verdict)
    lines.append(verdict)
    lines.append("")
    if not ok:
        warn = "WARNING: positive control failed — likely a pipeline bug."
        _stage_log(log_path, warn)
        lines.append(warn)

    if not run_sensitivity:
        return

    # Sensitivity: run all gain levels in Parallel (each uses all-core LOSO folds)
    _stage_log(log_path, "=== POSITIVE CONTROL SENSITIVITY SWEEP ===")
    lines.append("=== POSITIVE CONTROL SENSITIVITY SWEEP ===")
    hdr = (
        "gain = 1 + pct/100 on alpha component "
        f"(levels={list(config.POSCTRL_SENSITIVITY_GAINS)}); "
        "levels + LOSO folds parallelized"
    )
    _stage_log(log_path, hdr)
    lines.append(hdr)
    _stage_log(log_path, f"{'pct':>6} {'gain':>6} {'acc':>7} {'bal_acc':>8} {'wilson_95':>20}")
    lines.append(f"{'pct':>6} {'gain':>6} {'acc':>7} {'bal_acc':>8} {'wilson_95':>20}")

    t_sw = time.perf_counter()
    # Sequential gains; each gain's feature-build + LOSO folds use all cores (n_jobs=-1).
    # Avoids nested Parallel oversubscription.
    for g in config.POSCTRL_SENSITIVITY_GAINS:
        p = (g - 1.0) * 100.0
        t_g = time.perf_counter()
        _, mg = _posctrl_at_gain(y_subject, boost_mask, g)
        row = (
            f"{p:6.0f}% {g:6.2f} {mg['accuracy']:7.3f} {mg['balanced_accuracy']:8.3f} "
            f"[{mg['wilson_95'][0]:.3f}, {mg['wilson_95'][1]:.3f}]  ({_elapsed(t_g)})"
        )
        _stage_log(log_path, row)
        lines.append(row)
    _stage_log(log_path, f"Sensitivity sweep done: {_elapsed(t_sw)}")
    lines.append("")
    _stage_log(log_path, "")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _run_perm_and_variants(
    X: np.ndarray,
    groups: np.ndarray,
    y_primary: np.ndarray,
    n_perm: int,
    observed_acc: float,
    observed_bal: float,
    lines: List[str],
    log_path: Optional[Path],
    target: str,
) -> None:
    t0 = time.perf_counter()
    _stage_log(log_path, f"STAGE permutation n={n_perm}…")
    permutation_test(
        X, groups, y_primary, n_perm,
        observed_acc=observed_acc,
        observed_bal=observed_bal,
        lines=lines,
        log_path=log_path,
        n_jobs=-1,
    )
    _stage_log(log_path, f"STAGE permutation done: {_elapsed(t0)}")

    t0 = time.perf_counter()
    _stage_log(log_path, "STAGE variant A (LR frontal)…")
    lines.append("=== VARIANT A (PRE-SPECIFIED): LR on frontal theta + theta/alpha ===")
    lines.append(
        "Assumption: Emotiv-14 channel order "
        f"{config.EMOTIV_CH_NAMES}; frontal idx={config.FRONTAL_IDX}"
    )
    _stage_log(log_path, lines[-2])
    _stage_log(log_path, lines[-1])
    try:
        cache_a = build_feature_cache(feature_fn=compact_frontal_features, n_jobs=-1)
        yt_a, yp_a = loso_subject_preds(
            cache_a["X"], cache_a["groups"], y_primary, clf_kind="lr", n_jobs=-1
        )
        report_eval(
            f"VARIANT A LR compact | PRIMARY {target}",
            yt_a, yp_a, y_primary, lines, log_path,
        )
    except Exception as e:
        msg = f"VARIANT A FAILED: {type(e).__name__}: {e}"
        _stage_log(log_path, msg)
        lines.append(msg)
        lines.append("")
    _stage_log(log_path, f"STAGE variant A done: {_elapsed(t0)}")

    t0 = time.perf_counter()
    _stage_log(log_path, "STAGE variant B (subject-mean RF)…")
    lines.append(
        "=== VARIANT B (PRE-SPECIFIED): subject-mean features (45 samples) + RF ==="
    )
    _stage_log(log_path, lines[-1])
    try:
        X_subj = np.vstack(
            [X[groups == s].mean(axis=0) for s in range(config.N_SUBJECTS)]
        )
        assert X_subj.shape[0] == config.N_SUBJECTS
        yt_b, yp_b = loso_subject_samples(
            X_subj, y_primary, clf_kind="rf", n_jobs=-1
        )
        report_eval(
            f"VARIANT B subject-mean RF | PRIMARY {target}",
            yt_b, yp_b, y_primary, lines, log_path,
        )
    except Exception as e:
        msg = f"VARIANT B FAILED: {type(e).__name__}: {e}"
        _stage_log(log_path, msg)
        lines.append(msg)
        lines.append("")
    _stage_log(log_path, f"STAGE variant B done: {_elapsed(t0)}")


def main(
    save: bool,
    target: str,
    n_perm: int,
    skip_perm: bool,
    skip_posctrl: bool,
    reuse_cache: bool,
    log_path: Optional[Path],
    only_posctrl: bool = False,
    only_perm_variants: bool = False,
):
    lines: List[str] = []
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # Append mode for resume; still start fresh file for clarity
        log_path.write_text("", encoding="utf-8")

    t_all = time.perf_counter()
    y_primary = load_stew_labels(target)

    if only_perm_variants:
        _stage_log(log_path, "MODE: --only-perm-variants (skip baseline/posctrl)")
        cache = load_feature_cache(feature_cache_path())
        X, groups = cache["X"], cache["groups"]
        assert_finite_features(X, "only-perm-variants")
        # Observed epoch-LOSO from frozen run already completed
        _stage_log(log_path, "Recomputing PRIMARY baseline quickly for matched observed metrics…")
        yt, yp = loso_subject_preds(X, groups, y_primary, clf_kind="rf", n_jobs=-1)
        m = subject_metrics(yt, yp, sorted(set(y_primary.tolist())))
        report_eval(f"BASELINE RF | PRIMARY {target} (refresh)", yt, yp, y_primary, lines, log_path)
        _run_perm_and_variants(
            X, groups, y_primary, n_perm,
            m["accuracy"], m["balanced_accuracy"],
            lines, log_path, target,
        )
        report_path = config.ROOT / "docs" / "SANITY_REPORT.md"
        # Prepend note that earlier stages are in sanity_frozen_parallel.log
        header = (
            "# Sanity / LOSO report (perm + variants)\n\n"
            "Earlier stages (audit/baseline/posctrl/sensitivity): "
            "`logs/sanity_frozen_parallel.log`\n\n```\n"
        )
        report_path.write_text(header + "\n".join(lines) + "\n```\n", encoding="utf-8")
        _stage_log(log_path, f"Wrote {report_path}")
        _stage_log(log_path, f"ALL STAGES done: {_elapsed(t_all)}")
        return

    if only_posctrl:
        _stage_log(log_path, "MODE: --only-posctrl (skip baseline/perm/variants)")
        t0 = time.perf_counter()
        _stage_log(log_path, "STAGE positive control + sensitivity…")
        positive_control(y_primary, lines, log_path, run_sensitivity=True)
        _stage_log(log_path, f"STAGE positive control done: {_elapsed(t0)}")
        report_path = config.ROOT / "data" / "POSCTRL_SENSITIVITY.md"
        report_path.write_text(
            "# Positive control + sensitivity\n\n```\n" + "\n".join(lines) + "\n```\n",
            encoding="utf-8",
        )
        _stage_log(log_path, f"Wrote {report_path}")
        _stage_log(log_path, f"ALL STAGES done: {_elapsed(t_all)}")
        return

    other = "3class" if target == "2class" else "2class"
    y_secondary = load_stew_labels(other)

    # --- Features ---
    t0 = time.perf_counter()
    cache_path = feature_cache_path()
    _stage_log(log_path, f"Protocol hash: {protocol_hash()} → cache {cache_path.name}")
    if reuse_cache and cache_path.exists():
        _stage_log(log_path, f"STAGE cache: reusing {cache_path}")
        cache = load_feature_cache(cache_path)
    else:
        if reuse_cache and not cache_path.exists():
            _stage_log(log_path, f"STAGE cache: --reuse-cache but missing {cache_path}; rebuilding")
        _stage_log(log_path, "STAGE cache: building epoch features (Parallel n_jobs=-1)…")
        cache = build_feature_cache(feature_fn=band_power_features, n_jobs=-1)
        save_feature_cache(cache, cache_path)
        _stage_log(log_path, f"Wrote feature cache → {cache_path}")
    X, groups, audit = cache["X"], cache["groups"], cache["audit"]
    assert_finite_features(X, "main/features")
    _stage_log(log_path, f"STAGE cache done: {_elapsed(t0)}")

    print_audit(audit, y_primary, lines, log_path)

    # Raw zeros / flats (flag only; no dedicated reject yet)
    t_qc = time.perf_counter()
    qc_lines = format_raw_qc(audit_all_subjects())
    for ln in qc_lines:
        _stage_log(log_path, ln)
        lines.append(ln)
    _stage_log(log_path, f"STAGE raw QC done: {_elapsed(t_qc)}")
    lines.append("")

    # --- Baseline RF (PRIMARY) ---
    t0 = time.perf_counter()
    _stage_log(log_path, f"STAGE baseline PRIMARY {target} LOSO…")
    yt, yp = loso_subject_preds(X, groups, y_primary, clf_kind="rf", n_jobs=-1)
    m_primary = report_eval(
        f"BASELINE RF | PRIMARY {target}", yt, yp, y_primary, lines, log_path
    )
    _stage_log(log_path, f"STAGE baseline PRIMARY done: {_elapsed(t0)}")

    # --- Baseline RF (SECONDARY) ---
    t0 = time.perf_counter()
    _stage_log(log_path, f"STAGE baseline SECONDARY {other} LOSO…")
    yt2, yp2 = loso_subject_preds(X, groups, y_secondary, clf_kind="rf", n_jobs=-1)
    report_eval(
        f"BASELINE RF | SECONDARY {other}", yt2, yp2, y_secondary, lines, log_path
    )
    _stage_log(log_path, f"STAGE baseline SECONDARY done: {_elapsed(t0)}")

    # --- Positive control ---
    if not skip_posctrl:
        t0 = time.perf_counter()
        _stage_log(log_path, "STAGE positive control…")
        positive_control(y_primary, lines, log_path, run_sensitivity=True)
        _stage_log(log_path, f"STAGE positive control done: {_elapsed(t0)}")

    # --- Permutation ---
    if not skip_perm:
        t0 = time.perf_counter()
        _stage_log(log_path, f"STAGE permutation n={n_perm}…")
        permutation_test(
            X, groups, y_primary, n_perm,
            observed_acc=m_primary["accuracy"],
            observed_bal=m_primary["balanced_accuracy"],
            lines=lines,
            log_path=log_path,
            n_jobs=-1,
        )
        _stage_log(log_path, f"STAGE permutation done: {_elapsed(t0)}")

    # --- Variant A ---
    t0 = time.perf_counter()
    _stage_log(log_path, "STAGE variant A (LR frontal)…")
    lines.append("=== VARIANT A (PRE-SPECIFIED): LR on frontal theta + theta/alpha ===")
    lines.append(
        "Assumption: Emotiv-14 channel order "
        f"{config.EMOTIV_CH_NAMES}; frontal idx={config.FRONTAL_IDX}"
    )
    _stage_log(log_path, lines[-2])
    _stage_log(log_path, lines[-1])
    try:
        cache_a = build_feature_cache(feature_fn=compact_frontal_features, n_jobs=-1)
        yt_a, yp_a = loso_subject_preds(
            cache_a["X"], cache_a["groups"], y_primary, clf_kind="lr", n_jobs=-1
        )
        report_eval(
            f"VARIANT A LR compact | PRIMARY {target}",
            yt_a, yp_a, y_primary, lines, log_path,
        )
    except Exception as e:
        msg = f"VARIANT A FAILED: {type(e).__name__}: {e}"
        _stage_log(log_path, msg)
        lines.append(msg)
        lines.append("")
    _stage_log(log_path, f"STAGE variant A done: {_elapsed(t0)}")

    # --- Variant B ---
    t0 = time.perf_counter()
    _stage_log(log_path, "STAGE variant B (subject-mean RF)…")
    lines.append(
        "=== VARIANT B (PRE-SPECIFIED): subject-mean features (45 samples) + RF ==="
    )
    _stage_log(log_path, lines[-1])
    try:
        X_subj = np.vstack(
            [X[groups == s].mean(axis=0) for s in range(config.N_SUBJECTS)]
        )
        assert X_subj.shape[0] == config.N_SUBJECTS
        yt_b, yp_b = loso_subject_samples(
            X_subj, y_primary, clf_kind="rf", n_jobs=-1
        )
        report_eval(
            f"VARIANT B subject-mean RF | PRIMARY {target}",
            yt_b, yp_b, y_primary, lines, log_path,
        )
    except Exception as e:
        msg = f"VARIANT B FAILED: {type(e).__name__}: {e}"
        _stage_log(log_path, msg)
        lines.append(msg)
        lines.append("")
    _stage_log(log_path, f"STAGE variant B done: {_elapsed(t0)}")

    report_path = config.ROOT / "docs" / "SANITY_REPORT.md"
    report_path.write_text(
        "# Sanity / LOSO report\n\n```\n" + "\n".join(lines) + "\n```\n",
        encoding="utf-8",
    )
    _stage_log(log_path, f"Wrote {report_path}")
    _stage_log(log_path, f"ALL STAGES done: {_elapsed(t_all)}")

    if save:
        y_ep = _epoch_y(groups, y_primary)
        config.MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(make_rf().fit(X, y_ep), config.MODEL_PATH)
        _stage_log(log_path, f"Saved PRIMARY model → {config.MODEL_PATH}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true")
    ap.add_argument(
        "--target",
        choices=("2class", "3class"),
        default="2class",
        help="PRIMARY label target (default: 2class). Also reports the other as SECONDARY.",
    )
    ap.add_argument("--n-perm", type=int, default=config.N_PERMUTATIONS)
    ap.add_argument("--skip-perm", action="store_true")
    ap.add_argument("--skip-posctrl", action="store_true")
    ap.add_argument(
        "--only-posctrl",
        action="store_true",
        help="Run primary positive control + sensitivity sweep only.",
    )
    ap.add_argument(
        "--only-perm-variants",
        action="store_true",
        help="Skip baseline/posctrl; run permutation + variants A/B (reuse cache).",
    )
    ap.add_argument(
        "--reuse-cache",
        action="store_true",
        help="Load data/cache/epoch_features.npz instead of rebuilding.",
    )
    ap.add_argument(
        "--log",
        type=Path,
        default=None,
        help="Stage log path (default: logs/sanity_YYYYMMDD_HHMMSS.log)",
    )
    args = ap.parse_args()
    log_path = args.log
    if log_path is None:
        ts = time.strftime("%Y%m%d_%H%M%S")
        log_path = config.ROOT / "logs" / f"sanity_{ts}.log"
    main(
        args.save,
        args.target,
        args.n_perm,
        args.skip_perm,
        args.skip_posctrl,
        args.reuse_cache,
        log_path,
        only_posctrl=args.only_posctrl,
        only_perm_variants=args.only_perm_variants,
    )
