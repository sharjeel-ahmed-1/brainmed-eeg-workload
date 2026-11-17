"""
Visual EEG workload report figures for the Streamlit demo.
Uses 84-D band-power features (same layout as src.features.band_power_features).
Channel maps use Emotiv-14 name assumption (not stored in STEW .mat).
"""
from __future__ import annotations

from io import BytesIO
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np

import config

BAND_NAMES = list(config.BANDS.keys())
N_BANDS = len(BAND_NAMES)
N_CH = config.N_CHANNELS

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


def split_features(X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """X (n_epochs, 84) → band (n_ep, n_ch, n_bands), ratio (n_ep, n_ch)."""
    if X.ndim != 2 or X.shape[1] != N_CH * N_BANDS + N_CH:
        raise ValueError(f"Expected (*, {N_CH * N_BANDS + N_CH}) features, got {X.shape}")
    band = X[:, : N_CH * N_BANDS].reshape(-1, N_CH, N_BANDS)
    ratio = X[:, N_CH * N_BANDS :]
    return band, ratio


def mean_band_profile(X: np.ndarray) -> Dict[str, float]:
    band, _ = split_features(X)
    means = band.mean(axis=(0, 1))
    return {name: float(means[i]) for i, name in enumerate(BAND_NAMES)}


def fig_to_png_bytes(fig: plt.Figure) -> bytes:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def plot_output_summary(
    pred: int,
    p_high: float,
    n_epochs: int,
    source: str,
    y_true: Optional[int] = None,
) -> bytes:
    """Big visual: what came out — HIGH/LOW + confidence gauge."""
    high = pred == 1
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.6), gridspec_kw={"width_ratios": [1.1, 1]})
    fig.patch.set_facecolor("#f7f5f2")

    ax0 = axes[0]
    ax0.set_xlim(0, 1)
    ax0.set_ylim(0, 1)
    ax0.axis("off")
    color = "#c45c26" if high else "#2c5f7c"
    ax0.add_patch(plt.Rectangle((0.05, 0.15), 0.9, 0.7, fill=True, color=color, alpha=0.92, lw=0))
    ax0.text(0.5, 0.58, "HIGH LOAD" if high else "LOW LOAD", ha="center", va="center",
             fontsize=22, fontweight="bold", color="white")
    ax0.text(0.5, 0.32, f"P(high) = {p_high:.0%}", ha="center", va="center",
             fontsize=14, color="white")
    ax0.set_title("Model output", fontsize=12, pad=6)

    ax1 = axes[1]
    ax1.barh([0], [p_high], color="#c45c26", height=0.45)
    ax1.barh([0], [1 - p_high], left=[p_high], color="#2c5f7c", height=0.45)
    ax1.axvline(0.5, color="0.3", ls="--", lw=1)
    ax1.set_xlim(0, 1)
    ax1.set_yticks([])
    ax1.set_xlabel("Probability")
    ax1.set_title(f"Confidence · {n_epochs} epochs · {source}", fontsize=11)
    ax1.text(p_high / 2 if p_high > 0.08 else 0.02, 0, "HIGH", ha="center", va="center",
             color="white", fontsize=10, fontweight="bold")
    ax1.text(p_high + (1 - p_high) / 2 if (1 - p_high) > 0.08 else 0.85, 0, "LOW",
             ha="center", va="center", color="white", fontsize=10, fontweight="bold")
    if y_true is not None:
        fig.suptitle(
            f"True label={'HIGH' if y_true == 1 else 'LOW'} · "
            f"{'MATCH' if y_true == pred else 'MISMATCH'}",
            fontsize=10, y=1.02,
        )
    fig.tight_layout()
    return fig_to_png_bytes(fig)


def plot_band_bars(X: np.ndarray) -> bytes:
    profile = mean_band_profile(X)
    fig, ax = plt.subplots(figsize=(7, 3.4))
    fig.patch.set_facecolor("#f7f5f2")
    names = list(profile.keys())
    vals = [profile[n] for n in names]
    colors = ["#6b8cae", "#3d6b8a", "#2c5f7c", "#c45c26", "#8b3a1a"]
    ax.bar(names, vals, color=colors[: len(names)], edgecolor="white")
    ax.set_ylabel("Mean relative power")
    ax.set_title("EEG bands (average across channels & epochs)")
    ax.set_ylim(0, max(vals) * 1.25 if vals else 1)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.01, f"{v:.2f}", ha="center", fontsize=9)
    fig.tight_layout()
    return fig_to_png_bytes(fig)


def plot_channel_map(X: np.ndarray, band: str = "theta") -> bytes:
    band_t, ratio = split_features(X)
    if band == "theta_alpha":
        scores = ratio.mean(axis=0)
        title = "θ/α ratio by channel (Emotiv-14 assumption)"
    else:
        bi = BAND_NAMES.index(band)
        scores = band_t[:, :, bi].mean(axis=0)
        title = f"{band} relative power by channel (Emotiv-14 assumption)"

    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    fig.patch.set_facecolor("#f7f5f2")
    xs, ys = [], []
    for name in config.EMOTIV_CH_NAMES:
        x, y = EMOTIV_XY[name]
        xs.append(x)
        ys.append(y)
    sc = ax.scatter(xs, ys, c=scores, s=480, cmap="YlOrRd", edgecolors="k", linewidths=0.6)
    for i, name in enumerate(config.EMOTIV_CH_NAMES):
        ax.text(xs[i], ys[i], name, ha="center", va="center", fontsize=7)
    ax.add_patch(plt.Circle((0, 0), 1.05, fill=False, color="0.4", lw=1.2))
    ax.plot([0, 0], [1.05, 1.2], color="0.4", lw=1.2)
    ax.set_aspect("equal")
    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-1.35, 1.35)
    ax.axis("off")
    ax.set_title(title, fontsize=11)
    fig.colorbar(sc, ax=ax, fraction=0.046, shrink=0.8)
    fig.tight_layout()
    return fig_to_png_bytes(fig)


def plot_epoch_timeline(epoch_proba: np.ndarray, classes: np.ndarray, p_high_mean: float) -> bytes:
    classes = list(classes)
    if 1 in classes:
        p = epoch_proba[:, classes.index(1)]
    else:
        p = epoch_proba.max(axis=1)
    fig, ax = plt.subplots(figsize=(9, 3.2))
    fig.patch.set_facecolor("#f7f5f2")
    colors = ["#c45c26" if v >= 0.5 else "#2c5f7c" for v in p]
    ax.bar(range(len(p)), p, color=colors, width=0.9)
    ax.axhline(0.5, color="0.35", ls="--", lw=1, label="0.5 threshold")
    ax.axhline(p_high_mean, color="#8b3a1a", ls="-", lw=1.5, label=f"mean P(high)={p_high_mean:.2f}")
    ax.set_ylim(0, 1)
    ax.set_xlabel("Epoch index (4 s windows)")
    ax.set_ylabel("P(high)")
    ax.set_title("Per-epoch workload probability (orange ≥ 0.5)")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    return fig_to_png_bytes(fig)


def plot_band_channel_heat(X: np.ndarray) -> bytes:
    band, _ = split_features(X)
    heat = band.mean(axis=0)  # (ch, bands)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    fig.patch.set_facecolor("#f7f5f2")
    im = ax.imshow(heat, aspect="auto", cmap="YlOrRd")
    ax.set_xticks(range(N_BANDS))
    ax.set_xticklabels(BAND_NAMES)
    ax.set_yticks(range(N_CH))
    ax.set_yticklabels(config.EMOTIV_CH_NAMES)
    ax.set_title("Relative band power heatmap (mean over epochs)")
    fig.colorbar(im, ax=ax, fraction=0.046, label="relative power")
    fig.tight_layout()
    return fig_to_png_bytes(fig)


def plain_language_report(
    pred: int,
    p_high: float,
    band_profile: Dict[str, float],
    n_epochs: int,
) -> List[str]:
    """Short user-facing bullets explaining the screen output."""
    high = pred == 1
    lines = [
        f"**Output:** model says **{'HIGH' if high else 'LOW'} cognitive workload** "
        f"with P(high) = **{p_high:.0%}** over **{n_epochs}** epochs.",
    ]
    if high:
        lines.append(
            "**UI effect:** interface is **simplified** (fewer controls) so you can focus under load."
        )
        lines.append(
            "**Tip:** take a short break, reduce multitasking, or keep AUTO on so the UI stays light."
        )
    else:
        lines.append(
            "**UI effect:** interface shows **full detail** (tabs, breakdowns, maps)."
        )
        lines.append(
            "**Tip:** good time for deeper review — explore band charts and channel map."
        )

    # Spectral note (descriptive, not causal claim)
    top_band = max(band_profile, key=band_profile.get)
    lines.append(
        f"**EEG snapshot:** strongest average relative band here is **{top_band}** "
        f"({band_profile[top_band]:.2f}). θ={band_profile.get('theta', 0):.2f}, "
        f"α={band_profile.get('alpha', 0):.2f} (descriptive only)."
    )
    lines.append(
        "**Honest note:** STEW LOSO was null — treat this as a **demo report**, not a medical/diagnostic result."
    )
    return lines


def build_report_images(
    X: np.ndarray,
    pred: int,
    p_high: float,
    epoch_proba: np.ndarray,
    classes: np.ndarray,
    n_epochs: int,
    source: str,
    y_true: Optional[int] = None,
    map_band: str = "theta",
) -> Dict[str, bytes]:
    return {
        "summary": plot_output_summary(pred, p_high, n_epochs, source, y_true),
        "bands": plot_band_bars(X),
        "timeline": plot_epoch_timeline(epoch_proba, classes, p_high),
        "heatmap": plot_band_channel_heat(X),
        "chan_map": plot_channel_map(X, band=map_band),
    }
