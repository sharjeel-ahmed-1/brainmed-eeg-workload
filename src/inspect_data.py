"""Inspect STEW .mat files; write metadata-only summary (no sample dump)."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np

import config

STEW_DIR = config.RAW_DIR / "stew"
MAT_FILES = (
    "dataset.mat",
    "class_012.mat",
    "rating.mat",
    "three_class_one_hot.mat",
)
LABEL_FILES = {"class_012.mat", "rating.mat", "three_class_one_hot.mat"}
SKIP_KEYS = {"__header__", "__version__", "__globals__"}
OUT_PATH = config.ROOT / "docs" / "DATA_SUMMARY.md"

# From Kaggle STEW PDF: 14 channels, 128 Hz, 19200 samples/subject
PDF_N_CHANNELS = 14
PDF_SFREQ = 128.0
PDF_N_SAMPLES = 19200
PDF_DURATION_SEC = PDF_N_SAMPLES / PDF_SFREQ  # must be 150.0
EXPECTED = (14, 19200, 45)  # channels × time × subjects
AXIS_NAMES = {14: "channels", 19200: "time", 45: "subjects"}


def _load_mat(path: Path) -> tuple[dict[str, np.ndarray], str]:
    """Load .mat via scipy; fall back to h5py on MATLAB v7.3 (HDF5)."""
    try:
        from scipy.io import loadmat

        mat = loadmat(str(path), squeeze_me=False, struct_as_record=False)
        out = {k: np.asarray(v) for k, v in mat.items() if k not in SKIP_KEYS}
        return out, "scipy.io.loadmat"
    except NotImplementedError:
        import h5py

        out: dict[str, np.ndarray] = {}
        with h5py.File(path, "r") as f:
            for key in f.keys():
                out[key] = np.asarray(f[key])
        return out, "h5py (MATLAB v7.3)"


def _is_one_hot(arr: np.ndarray) -> bool:
    """True only for 2D arrays with a class axis of size >= 2 and one-hot rows/cols."""
    if arr.ndim != 2:
        return False
    flat = arr.astype(float)
    for class_axis in (0, 1):
        n_classes = arr.shape[class_axis]
        if n_classes < 2 or n_classes > 10:
            continue
        sample_axis = 1 - class_axis
        if arr.shape[sample_axis] <= n_classes:
            continue
        if not np.all((flat == 0) | (flat == 1)):
            continue
        sums = flat.sum(axis=class_axis)
        if np.allclose(sums, 1.0):
            return True
    return False


def _class_counts(name: str, arr: np.ndarray) -> list[str]:
    lines: list[str] = []
    a = np.asarray(arr)
    use_argmax = name == "three_class_one_hot" or _is_one_hot(a)
    if use_argmax:
        if a.ndim == 2:
            if a.shape[1] <= 10 and a.shape[1] < a.shape[0]:
                class_axis = 1
            elif a.shape[0] <= 10 and a.shape[0] < a.shape[1]:
                class_axis = 0
            else:
                class_axis = 0 if a.shape[0] < a.shape[1] else 1
            labels = np.argmax(a, axis=class_axis)
        else:
            labels = a.ravel()
        counts = Counter(int(x) for x in labels.tolist())
        lines.append(f"- class counts (argmax): {dict(sorted(counts.items()))}")
        return lines

    flat = a.ravel()
    if np.issubdtype(flat.dtype, np.floating) and np.allclose(flat, np.round(flat)):
        flat = np.round(flat).astype(int)
    counts = Counter(flat.tolist())
    lines.append(f"- class / value counts: {dict(sorted(counts.items(), key=lambda x: str(x[0])))}")
    if name == "rating":
        binary = (flat.astype(int) >= 7).astype(int)
        bcounts = Counter(binary.tolist())
        lines.append(
            f"- binary preview (rating>=7 → 1): {dict(sorted(bcounts.items()))} "
            f"(n_pos={bcounts.get(1, 0)}, n_neg={bcounts.get(0, 0)})"
        )
    return lines


def _nan_report(arr: np.ndarray) -> str:
    if not np.issubdtype(arr.dtype, np.number):
        return "n/a (non-numeric)"
    n = int(np.isnan(arr.astype(float)).sum())
    any_nan = n > 0
    return f"any NaN={any_nan}" + (f", count={n}" if any_nan else "")


def _axis_order_lines(shape: tuple[int, ...]) -> list[str]:
    """Report axis order explicitly (index → role)."""
    lines = ["- axis order:"]
    for i, dim in enumerate(shape):
        role = AXIS_NAMES.get(dim, "unknown")
        lines.append(f"  - axis {i}: size {dim} → {role}")
    if shape == EXPECTED:
        lines.append(
            "- orientation: matches expected (14, 19200, 45) = "
            "channels × time × subjects (not transposed)."
        )
    elif len(shape) == 3 and sorted(shape) == sorted(EXPECTED):
        mapping = [AXIS_NAMES.get(d, str(d)) for d in shape]
        lines.append(
            f"- orientation: permutation of (14, 19200, 45): "
            f"{' × '.join(mapping)} (transposed relative to ch×time×subject)."
        )
    else:
        lines.append(
            f"- orientation: shape {shape} does NOT match (14, 19200, 45) "
            "or a permutation — inspect manually."
        )
    return lines


def _pdf_duration_assert(lines: list[str]) -> None:
    """Assert PDF timing: 19200 samples / 128 Hz = 150 s."""
    duration = PDF_N_SAMPLES / PDF_SFREQ
    if duration != PDF_DURATION_SEC or duration != 150.0:
        raise AssertionError(
            f"Duration check failed: {PDF_N_SAMPLES}/{PDF_SFREQ} = {duration}, "
            f"expected 150.0"
        )
    lines.extend(
        [
            "## PDF timing check (Kaggle STEW summary)",
            "",
            f"- sfreq (PDF): {PDF_SFREQ} Hz",
            f"- channels (PDF): {PDF_N_CHANNELS}",
            f"- samples/subject (PDF): {PDF_N_SAMPLES}",
            f"- assert `{PDF_N_SAMPLES}/{int(PDF_SFREQ)} = {duration:g} s` → **passed** (150 s)",
            "- channel names: not confirmed in PDF/mats; keep generic `EEG001`… (no montage yet)",
            "",
        ]
    )


def inspect_mat(path: Path) -> list[str]:
    lines: list[str] = [f"## `{path.name}`", ""]
    arrays, loader = _load_mat(path)
    lines.append(f"- loader: `{loader}`")
    lines.append("")
    if not arrays:
        lines.append("- (no user variables)")
        lines.append("")
        return lines

    for key, arr in arrays.items():
        lines.append(f"### variable `{key}`")
        lines.append(f"- shape: `{arr.shape}`")
        lines.append(f"- dtype: `{arr.dtype}`")
        lines.append(f"- NaNs: {_nan_report(arr)}")
        if path.name in LABEL_FILES:
            count_name = key if key in ("class_012", "rating", "three_class_one_hot") else path.stem
            lines.extend(_class_counts(count_name, arr))
        if path.name == "dataset.mat" and arr.ndim == 3:
            lines.extend(_axis_order_lines(tuple(arr.shape)))
            # Cross-check PDF sample count on time axis if identifiable
            if 19200 in arr.shape:
                lines.append(f"- time axis length 19200 matches PDF samples/subject")
            if arr.shape[0] == PDF_N_CHANNELS or PDF_N_CHANNELS in arr.shape:
                lines.append(f"- channel count 14 matches PDF")
        lines.append("")
    return lines


def main() -> None:
    lines: list[str] = [
        "# STEW data summary",
        "",
        f"Source directory: `{STEW_DIR}`",
        "",
        "Metadata only (no EEG sample values).",
        "",
    ]
    if not STEW_DIR.is_dir():
        raise SystemExit(f"Missing directory: {STEW_DIR}")

    _pdf_duration_assert(lines)

    for name in MAT_FILES:
        path = STEW_DIR / name
        if not path.exists():
            lines.append(f"## `{name}`")
            lines.append("")
            lines.append("- **missing**")
            lines.append("")
            continue
        lines.extend(inspect_mat(path))

    text = "\n".join(lines).rstrip() + "\n"
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(text, encoding="utf-8")
    print(text)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
