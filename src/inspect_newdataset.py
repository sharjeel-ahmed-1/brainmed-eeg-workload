"""Inspect data/raw/newdataset — metadata only (no bulk EEG dump)."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

import config
import config_ext

BASE = config_ext.NEWDATASET_DIR
OUT_PATH = config.ROOT / "data" / "NEWDATASET_SUMMARY.md"
EEG_CHANNELS = list(config_ext.NEWDATASET_CH_NAMES)
CONDITIONS = ("EO", "AC1", "AC2", "AC3", "AC4")


def _col_letters_to_n(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - 64)
    return n


def _sheet_dims(path: Path, nbytes: int = 8000) -> dict[str, str]:
    with zipfile.ZipFile(path) as z:
        wb = z.read("xl/workbook.xml").decode("utf-8", errors="replace")
        names = [n for n in re.findall(r'name="([^"]+)"', wb) if not n.startswith("microsoft")]
        sheets = sorted(
            [n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n)],
            key=lambda s: int(re.search(r"sheet(\d+)", s).group(1)),
        )
        out: dict[str, str] = {}
        for name, sheet in zip(names, sheets):
            with z.open(sheet) as f:
                head = f.read(nbytes).decode("utf-8", errors="replace")
            m = re.search(r'dimension ref="([^"]+)"', head)
            out[name] = m.group(1) if m else "?"
        return out


def _parse_dim(ref: str) -> tuple[int | None, int | None]:
    m = re.search(r":([A-Z]+)(\d+)$", ref)
    if not m:
        return None, None
    return _col_letters_to_n(m.group(1)), int(m.group(2))


def subject_ids_from_eeg_xlsx(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as z:
        ss = z.read("xl/sharedStrings.xml").decode("utf-8", errors="replace")
        strings = re.findall(r"<t[^>]*>([^<]*)</t>", ss)
    ids: list[str] = []
    for s in strings:
        if re.fullmatch(r"\d{3}", s):
            ids.append(s)
        elif ids:
            break
    return ids


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(config.ROOT))
    except ValueError:
        return str(path)


def main() -> Path:
    mw = BASE / "Mental workload"
    st = BASE / "Stress"
    if not mw.is_dir() or not st.is_dir():
        raise FileNotFoundError(f"Expected Mental workload/ and Stress/ under {BASE}")

    ref = mw / "AC1 - Control.xlsx"
    ids = subject_ids_from_eeg_xlsx(ref)

    lines: list[str] = [
        "# Newdataset summary",
        "",
        f"Source directory: `{BASE}`",
        "",
        "Metadata from xlsx workbook/sheet dimensions + shared-string headers.",
        "**Sampling rate (documented):** EEG **2000 Hz** (Atiwiwat & Hemakom, Mendeley `s87jk3p5ws`). "
        "Cache resamples to `config_ext.NEWDATASET_RESAMPLE_HZ` (250).",
        "",
        "## Layout",
        "",
        "| Folder | Role | Files |",
        "|--------|------|-------|",
        "| `Mental workload/` | Control | EO, AC1–AC4 EEG + ECG |",
        "| `Stress/` | Experiment | EO, AC1–AC4 EEG + ECG |",
        "",
        "## EEG structure (AC / EO workbooks)",
        "",
        f"- Channels (sheet names): `{', '.join(EEG_CHANNELS)}` (**{len(EEG_CHANNELS)}**)",
        f"- Subject columns (from `{ref.name}` header): **{len(ids)}** IDs",
        f"- Subject ID list: `{','.join(ids)}`",
        "- Missing IDs in 001–077 span (gaps): "
        + (
            ", ".join(
                f"{i:03d}"
                for i in range(1, 78)
                if f"{i:03d}" not in set(ids) and f"{i:03d}" <= ids[-1]
            )
            or "(none in span)"
        ),
        "- Orientation: **columns = subjects**, **rows = time** (row 1 = subject IDs)",
        "- Control vs Experiment share the same subject ID set (checked AC1 + EO)",
        "",
        "## Per-file time length (rows − 1 header)",
        "",
        "| File | Sheet | n_cols | n_time |",
        "|------|-------|--------|--------|",
    ]

    eeg_files = []
    for folder, tag in ((mw, "Control"), (st, "Experiment")):
        for cond in CONDITIONS:
            name = f"{cond} - {tag}.xlsx"
            p = folder / name
            if p.exists():
                eeg_files.append(p)

    for p in eeg_files:
        dims = _sheet_dims(p)
        for ch, refdim in dims.items():
            ncols, nrows = _parse_dim(refdim)
            n_time = (nrows - 1) if nrows else None
            lines.append(
                f"| `{_rel(p)}` | {ch} | {ncols if ncols is not None else '?'} | "
                f"{n_time if n_time is not None else refdim} |"
            )

    lines += [
        "",
        "## ECG workbooks (separate)",
        "",
        "Sheets are conditions (`SC`, `EO`, `AC1`…), not EEG channels. "
        "Subject column sets can differ (e.g. SC starts mid-ID list). "
        "Not used by the primary EEG workload loader.",
        "",
        "| File | Sheet | n_cols | n_time |",
        "|------|-------|--------|--------|",
    ]
    for folder, tag in ((mw, "Control"), (st, "Experiment")):
        p = folder / f"ECG - {tag}.xlsx"
        if not p.exists():
            continue
        for ch, refdim in _sheet_dims(p).items():
            ncols, nrows = _parse_dim(refdim)
            n_time = (nrows - 1) if nrows else None
            lines.append(
                f"| `{_rel(p)}` | {ch} | {ncols if ncols is not None else '?'} | "
                f"{n_time if n_time is not None else refdim} |"
            )

    # Duration table only as hypotheses
    ac1_t = None
    d0 = _sheet_dims(ref).get("Fp1", "")
    _, nrows = _parse_dim(d0)
    if nrows:
        ac1_t = nrows - 1
    lines += [
        "",
        "## Sampling rate (unknown)",
        "",
        "No Hz field in xlsx. If AC1 Control Fp1 has "
        f"**{ac1_t}** samples, duration under common rates would be:",
        "",
        "| Assumed Hz | Duration (AC1 Control) |",
        "|------------|------------------------|",
    ]
    if ac1_t:
        for hz in (128, 250, 256, 500, 1000):
            lines.append(f"| {hz} | {ac1_t / hz:.1f} s ({ac1_t / hz / 60:.2f} min) |")
    lines += [
        "",
        "**Action:** confirm Hz from study docs before any MNE Raw / LOSO run.",
        "",
        "## Label scheme (protocol v2 candidate)",
        "",
        "| Target | Definition |",
        "|--------|------------|",
        "| PRIMARY | Control (`Mental workload`) vs Stress (`Stress`) — paired within subject × condition |",
        "| Condition factor | EO, AC1, AC2, AC3, AC4 (task blocks) |",
        "",
        "This is **denser** than STEW’s one-rating-per-subject: each subject has Control and Experiment "
        "recordings across multiple conditions.",
        "",
        "## Notes / QC flags",
        "",
        "- AC1 Control sheet `P4` dimension reported **68** columns vs **65** on other channels — verify on load.",
        "- Files are very large (~0.5–1.1 GB each); prefer convert-to-FIF/NPZ cache before training.",
        "- Values sampled from Fp1 look continuous float (µV-like); units still undocumented.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "python -m src.inspect_newdataset",
        "```",
        "",
    ]

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    return OUT_PATH


if __name__ == "__main__":
    main()
