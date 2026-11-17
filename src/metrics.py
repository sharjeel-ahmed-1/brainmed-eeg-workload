from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    recall_score,
)


def wilson_ci(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score 95% CI for a binomial proportion k/n."""
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = (p + z2 / (2.0 * n)) / denom
    margin = z * np.sqrt((p * (1.0 - p) + z2 / (4.0 * n)) / n) / denom
    return float(centre - margin), float(centre + margin)


def subject_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: Sequence[int],
) -> Dict:
    labels = list(labels)
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    acc = float(accuracy_score(y_true, y_pred))
    bal = float(balanced_accuracy_score(y_true, y_pred))
    recalls = recall_score(
        y_true, y_pred, labels=labels, average=None, zero_division=0
    )
    n = len(y_true)
    k = int(np.sum(y_true == y_pred))
    ci_lo, ci_hi = wilson_ci(k, n)
    per_class = {int(lbl): float(rec) for lbl, rec in zip(labels, recalls)}
    return {
        "accuracy": acc,
        "balanced_accuracy": bal,
        "per_class_recall": per_class,
        "wilson_95": (ci_lo, ci_hi),
        "n_correct": k,
        "n": n,
        "cm": cm,
        "labels": labels,
    }


def format_metrics(m: Dict, title: str) -> List[str]:
    lines = [
        f"=== {title} ===",
        f"Pooled confusion (rows=true, cols=pred, labels={m['labels']}):",
        str(m["cm"]),
        (
            f"Accuracy {m['accuracy']:.3f} | balanced accuracy {m['balanced_accuracy']:.3f} | "
            f"Wilson 95% CI [{m['wilson_95'][0]:.3f}, {m['wilson_95'][1]:.3f}] "
            f"(k={m['n_correct']}/{m['n']})"
        ),
        "Per-class recall: "
        + ", ".join(f"{c}={m['per_class_recall'][c]:.3f}" for c in m["labels"]),
    ]
    return lines
