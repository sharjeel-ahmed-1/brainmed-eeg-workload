"""
Phase 3 — descriptive interpretation of frozen RF / variant-A LR.

Fits on all subjects for visualization only (not a held-out claim).
Channel montage uses config.EMOTIV_CH_NAMES (assumption; not in STEW .mat).
See data/MONTAGE_AND_UNITS.md — maps are descriptive only given null LOSO.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from sklearn.pipeline import Pipeline

import config
from src.load import load_stew_labels
from src.train import (
    feature_cache_path,
    load_feature_cache,
    make_lr,
    make_rf,
)

FIG_DIR = config.ROOT / "figures"
BAND_NAMES = list(config.BANDS.keys())  # delta θ α β γ order
N_BANDS = len(BAND_NAMES)
N_CH = config.N_CHANNELS

# Approximate Emotiv EPOC 2-D layout (unit circle-ish); ASSUMPTION for maps only.
EMOTIV_XY = {
    "AF3": (-0.30, 0.85),
    "F7": (-0.70, 0.50),
    "F3": (-0.40, 0.55),
    "FC5": (-0.55, 0.25),
    "T7": (-0.90, 0.00),
    "P7": (-0.70, -0.50),
    "O1": (-0.30, -0.85),
    "O2": (0.30, -0.85),
    "P8": (0.70, -0.50),
    "T8": (0.90, 0.00),
    "FC6": (0.55, 0.25),
    "F4": (0.40, 0.55),
    "F8": (0.70, 0.50),
    "AF4": (0.30, 0.85),
}


def feature_names() -> List[str]:
    """Match band_power_features layout: 14×5 rel bands + 14 θ/α."""
    names = []
    for ch in config.EMOTIV_CH_NAMES:
        for band in BAND_NAMES:
            names.append(f"{ch}_{band}")
    for ch in config.EMOTIV_CH_NAMES:
        names.append(f"{ch}_theta_alpha")
    return names


def _epoch_y(groups: np.ndarray, y_subject: np.ndarray) -> np.ndarray:
    return np.array([int(y_subject[g]) for g in groups], dtype=int)


def fit_primary_rf(X: np.ndarray, groups: np.ndarray) -> Tuple[Pipeline, np.ndarray]:
    y_subject = load_stew_labels("2class")
    y = _epoch_y(groups, y_subject)
    model = make_rf().fit(X, y)
    return model, model.named_steps["clf"].feature_importances_


def fit_variant_a_lr() -> Tuple[Pipeline, np.ndarray, List[str]]:
    """Rebuild compact frontal features via cache of full X is wrong dim — refit from STEW slow.
    Use LR on two columns derived conceptually: we rebuild A features from full cache
    by re-running compact path only if needed. Prefer small rebuild via train helper.
    """
    from src.train import build_feature_cache
    from src.features import compact_frontal_features

    cache = build_feature_cache(feature_fn=compact_frontal_features, n_jobs=-1)
    X = cache["X"]
    groups = cache["groups"]
    y_subject = load_stew_labels("2class")
    y = _epoch_y(groups, y_subject)
    model = make_lr().fit(X, y)
    coef = model.named_steps["clf"].coef_.ravel()
    return model, coef, ["frontal_mean_theta", "frontal_mean_theta_alpha"]


def reshape_importance(imp: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Return (band_by_ch [n_ch, n_bands], ratio_by_ch [n_ch])."""
    if imp.shape[0] != N_CH * N_BANDS + N_CH:
        raise ValueError(f"Expected {N_CH * N_BANDS + N_CH} features, got {imp.shape[0]}")
    band_flat = imp[: N_CH * N_BANDS].reshape(N_CH, N_BANDS)
    ratio = imp[N_CH * N_BANDS :]
    return band_flat, ratio


def plot_top_features(names: List[str], imp: np.ndarray, path: Path, top_k: int = 20) -> None:
    order = np.argsort(imp)[::-1][:top_k]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(range(top_k), imp[order][::-1], color="#2c5f7c")
    ax.set_yticks(range(top_k))
    ax.set_yticklabels([names[i] for i in order[::-1]], fontsize=9)
    ax.set_xlabel("RF feature importance (Gini)")
    ax.set_title("Top features — all-subject RF (descriptive; LOSO was null)")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_band_channel_heat(band_by_ch: np.ndarray, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    im = ax.imshow(band_by_ch, aspect="auto", cmap="YlOrRd")
    ax.set_xticks(range(N_BANDS))
    ax.set_xticklabels(BAND_NAMES)
    ax.set_yticks(range(N_CH))
    ax.set_yticklabels(config.EMOTIV_CH_NAMES)
    ax.set_title("RF importance: relative band power (Emotiv-14 assumption)")
    fig.colorbar(im, ax=ax, fraction=0.046, label="importance")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_channel_map(ch_scores: np.ndarray, path: Path, title: str) -> None:
    """Scatter 'topomap-style' on assumed Emotiv XY."""
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    xs, ys, cs = [], [], []
    for i, name in enumerate(config.EMOTIV_CH_NAMES):
        x, y = EMOTIV_XY[name]
        xs.append(x)
        ys.append(y)
        cs.append(ch_scores[i])
    sc = ax.scatter(xs, ys, c=cs, s=420, cmap="YlOrRd", edgecolors="k", linewidths=0.6)
    for i, name in enumerate(config.EMOTIV_CH_NAMES):
        ax.text(xs[i], ys[i], name, ha="center", va="center", fontsize=7, color="k")
    # head outline
    circ = plt.Circle((0, 0), 1.05, fill=False, color="0.4", lw=1.2)
    ax.add_patch(circ)
    ax.plot([0, 0], [1.05, 1.2], color="0.4", lw=1.2)  # nose
    ax.set_aspect("equal")
    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-1.35, 1.35)
    ax.axis("off")
    ax.set_title(title)
    fig.colorbar(sc, ax=ax, fraction=0.046, label="importance")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_variant_a_coefs(names: List[str], coef: np.ndarray, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(5, 3.2))
    colors = ["#2c5f7c" if c >= 0 else "#a33" for c in coef]
    ax.barh(names, coef, color=colors)
    ax.axvline(0, color="0.4", lw=0.8)
    ax.set_xlabel("LR coefficient (scaled features)")
    ax.set_title("Variant A — frontal θ / θ/α (descriptive fit)")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def write_lit_note(path: Path, top_names: List[str], a_coef: np.ndarray) -> None:
    text = f"""# Interpretation note (Phase 3)

## Framing

Primary LOSO accuracy was **below majority** (acc 0.356 vs majority 0.556) with
permutation p≈0.98. Figures below are **descriptive** (RF / LR fit on all subjects)
and must not be read as evidence of a reliable held-out workload classifier.

Channel labels use the **Emotiv-14 order assumption** in `config.EMOTIV_CH_NAMES`
(names are not stored in STEW `.mat`).

## What literature often reports

Cognitive-workload EEG reviews commonly associate **increased frontal/midline theta**
and **decreased posterior alpha** (or elevated θ/α) with higher mental effort
(e.g. n-back / multitasking paradigms; consumer-headset studies on STEW-like tasks).
Those effects are typically modest, session- and subject-dependent, and weaker under
noisy dry-electrode / consumer hardware than lab wet systems.

## What we see here

- Top RF features (all-subject fit): {", ".join(top_names[:8])}…
- Variant A LR coefs: frontal_mean_theta={a_coef[0]:+.3f},
  frontal_mean_theta_alpha={a_coef[1]:+.3f}
  (sign/magnitude are exploratory; LOSO for A was also ≤ majority).

Honest read: feature ranks may echo band/channel variance more than a true
workload label association. Positive-control (α boost) proved the pipeline can
detect injected spectral change; the **natural STEW `rating≥7` label did not**.

## Takeaway for portfolio

Methods rigor (LOSO, perm, posctrl, frozen protocol) > cherry-picked accuracy.
Null primary result is still a valid computational-neuroscience / BCI methods story
when framed with limitations (label coarseness, consumer EEG, montage assumption).
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = feature_cache_path()
    print(f"Loading cache: {cache_path}")
    cache = load_feature_cache(cache_path)
    X, groups = cache["X"], cache["groups"]
    names = feature_names()
    if X.shape[1] != len(names):
        raise RuntimeError(f"Feature dim {X.shape[1]} != expected {len(names)}")

    print("Fitting all-subject RF (descriptive)…")
    _, imp = fit_primary_rf(X, groups)
    band_by_ch, ratio = reshape_importance(imp)
    ch_total = band_by_ch.sum(axis=1) + ratio

    plot_top_features(names, imp, FIG_DIR / "rf_top_features.png")
    plot_band_channel_heat(band_by_ch, FIG_DIR / "rf_band_channel_heat.png")
    plot_channel_map(
        ch_total,
        FIG_DIR / "rf_channel_importance_map.png",
        "Channel importance sum (Emotiv-14 assumption)",
    )
    plot_channel_map(
        band_by_ch[:, BAND_NAMES.index("theta")],
        FIG_DIR / "rf_theta_importance_map.png",
        "θ-band importance (Emotiv-14 assumption)",
    )

    print("Fitting variant A LR (rebuild compact features)…")
    _, a_coef, a_names = fit_variant_a_lr()
    plot_variant_a_coefs(a_names, a_coef, FIG_DIR / "variant_a_lr_coefs.png")

    order = np.argsort(imp)[::-1]
    top_names = [names[i] for i in order[:12]]
    note_path = config.ROOT / "data" / "INTERPRETATION.md"
    write_lit_note(note_path, top_names, a_coef)

    print("Wrote figures →", FIG_DIR)
    for p in sorted(FIG_DIR.glob("*.png")):
        print(" ", p.name)
    print("Wrote", note_path)
    print("Top-8 RF features:", ", ".join(top_names[:8]))
    print(f"Variant A coefs: {dict(zip(a_names, a_coef.round(4)))}")


if __name__ == "__main__":
    main()
