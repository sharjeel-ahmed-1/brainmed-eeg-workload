"""
Protocol v2 Track A: STEW multi-threshold LOSO (does not overwrite v1 RESULTS.md).

Example:
  python -m src.train_v2_stew_thresholds --thresholds 6,7,8 --log-dir logs/v2
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, balanced_accuracy_score

import config
from src.load import load_stew_labels, load_stew_ratings
from src.train import feature_cache_path, load_feature_cache, loso_subject_preds


def run_thresholds(thresholds: list[int], log_dir: Path, n_jobs: int = -1) -> dict:
    log_dir.mkdir(parents=True, exist_ok=True)
    cache = load_feature_cache(feature_cache_path())
    X, groups = cache["X"], cache["groups"]
    ratings = load_stew_ratings()
    summary = {
        "protocol": "v2_stew_multi_threshold",
        "note": "Descriptive sensitivity; still one label per subject. Does not replace RESULTS.md.",
        "n_subjects": int(config.N_SUBJECTS),
        "ratings_minmax": [int(ratings.min()), int(ratings.max())],
        "thresholds": {},
    }

    for thr in thresholds:
        y_subject = load_stew_labels("2class", threshold=thr)
        y_true, y_pred = loso_subject_preds(X, groups, y_subject, clf_kind="rf", n_jobs=n_jobs)
        acc = float(accuracy_score(y_true, y_pred))
        bal = float(balanced_accuracy_score(y_true, y_pred))
        maj = float(np.mean(y_subject == np.bincount(y_subject).argmax()))
        row = {
            "threshold": thr,
            "n_high": int(y_subject.sum()),
            "n_low": int((1 - y_subject).sum()),
            "majority_acc": maj,
            "loso_acc": acc,
            "loso_bal_acc": bal,
        }
        summary["thresholds"][str(thr)] = row
        fold_path = log_dir / f"stew_threshold_{thr}_preds.npz"
        np.savez(fold_path, y_true=y_true, y_pred=y_pred, y_subject=y_subject)
        print(
            f"threshold>={thr}: loso_acc={acc:.3f} bal={bal:.3f} "
            f"majority={maj:.3f} n_high={row['n_high']}"
        )

    out_json = log_dir / "stew_multi_threshold_summary.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md = log_dir / "STEW_MULTI_THRESHOLD.md"
    lines = [
        "# STEW multi-threshold LOSO (protocol v2 Track A)",
        "",
        "Does **not** overwrite `RESULTS.md`.",
        "",
        "| threshold | n_high | majority | LOSO acc | LOSO bal-acc |",
        "|-----------|--------|----------|----------|--------------|",
    ]
    for thr in thresholds:
        r = summary["thresholds"][str(thr)]
        lines.append(
            f"| ≥{thr} | {r['n_high']} | {r['majority_acc']:.3f} | "
            f"{r['loso_acc']:.3f} | {r['loso_bal_acc']:.3f} |"
        )
    lines.append("")
    lines.append(f"Source JSON: `{out_json}`")
    md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_json} and {md}")
    return summary


def main():
    p = argparse.ArgumentParser(description="v2 STEW multi-threshold LOSO")
    p.add_argument("--thresholds", default="6,7,8", help="Comma-separated rating thresholds")
    p.add_argument("--log-dir", type=Path, default=config.ROOT / "logs" / "v2")
    p.add_argument("--n-jobs", type=int, default=-1)
    args = p.parse_args()
    thrs = [int(x) for x in args.thresholds.split(",") if x.strip()]
    run_thresholds(thrs, args.log_dir, n_jobs=args.n_jobs)


if __name__ == "__main__":
    main()
