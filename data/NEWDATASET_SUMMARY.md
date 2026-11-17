# Newdataset summary

Source directory: `/Users/abc/Downloads/eeg-workload/data/raw/newdataset/newdataset`

Metadata from xlsx workbook/sheet dimensions + shared-string headers.
**Sampling rate (documented):** EEG **2000 Hz**, ECG **1000 Hz** — Atiwiwat & Hemakom, *An EEG-ECG Dataset of Stress and Mental Workload during Cognitive Tasks* (Mendeley Data `s87jk3p5ws` / DataMed). Set in `config_ext.NEWDATASET_SFREQ`. Analysis cache resamples to **250 Hz**.

Duration check: EO Control Fp1 has 588000 samples → 588000/2000 = **294 s ≈ 5 min** (matches described EO block).

## Layout

| Folder | Role | Files |
|--------|------|-------|
| `Mental workload/` | Control | EO, AC1–AC4 EEG + ECG |
| `Stress/` | Experiment | EO, AC1–AC4 EEG + ECG |

## EEG structure (AC / EO workbooks)

- Channels (sheet names): `Fp1, Fp2, F3, F4, T3, T4, P3, P4` (**8**)
- Subject columns (from `AC1 - Control.xlsx` header): **65** IDs
- Subject ID list: `001,002,003,004,005,006,007,008,009,010,011,012,014,015,016,017,018,019,020,021,024,025,026,027,028,029,030,033,034,035,036,037,038,039,040,042,043,045,046,047,048,049,050,051,052,053,054,055,056,057,058,060,061,062,065,066,067,068,069,071,072,073,074,075,077`
- Missing IDs in 001–077 span (gaps): 013, 022, 023, 031, 032, 041, 044, 059, 063, 064, 070, 076
- Orientation: **columns = subjects**, **rows = time** (row 1 = subject IDs)
- Control vs Experiment share the same subject ID set (checked AC1 + EO)

## Per-file time length (rows − 1 header)

| File | Sheet | n_cols | n_time |
|------|-------|--------|--------|
| `data/raw/newdataset/newdataset/Mental workload/EO - Control.xlsx` | Fp1 | 65 | 588000 |
| `data/raw/newdataset/newdataset/Mental workload/EO - Control.xlsx` | Fp2 | 65 | 588000 |
| `data/raw/newdataset/newdataset/Mental workload/EO - Control.xlsx` | F3 | 65 | 588000 |
| `data/raw/newdataset/newdataset/Mental workload/EO - Control.xlsx` | F4 | 65 | 588000 |
| `data/raw/newdataset/newdataset/Mental workload/EO - Control.xlsx` | T3 | 65 | 588000 |
| `data/raw/newdataset/newdataset/Mental workload/EO - Control.xlsx` | T4 | 65 | 588000 |
| `data/raw/newdataset/newdataset/Mental workload/EO - Control.xlsx` | P3 | 65 | 588000 |
| `data/raw/newdataset/newdataset/Mental workload/EO - Control.xlsx` | P4 | 65 | 588000 |
| `data/raw/newdataset/newdataset/Mental workload/AC1 - Control.xlsx` | Fp1 | 65 | 592000 |
| `data/raw/newdataset/newdataset/Mental workload/AC1 - Control.xlsx` | Fp2 | 65 | 592000 |
| `data/raw/newdataset/newdataset/Mental workload/AC1 - Control.xlsx` | F3 | 65 | 592000 |
| `data/raw/newdataset/newdataset/Mental workload/AC1 - Control.xlsx` | F4 | 65 | 592000 |
| `data/raw/newdataset/newdataset/Mental workload/AC1 - Control.xlsx` | T3 | 65 | 592000 |
| `data/raw/newdataset/newdataset/Mental workload/AC1 - Control.xlsx` | T4 | 65 | 592000 |
| `data/raw/newdataset/newdataset/Mental workload/AC1 - Control.xlsx` | P3 | 65 | 592000 |
| `data/raw/newdataset/newdataset/Mental workload/AC1 - Control.xlsx` | P4 | 68 | 592006 |
| `data/raw/newdataset/newdataset/Mental workload/AC2 - Control.xlsx` | Fp1 | 65 | 544000 |
| `data/raw/newdataset/newdataset/Mental workload/AC2 - Control.xlsx` | Fp2 | 65 | 544000 |
| `data/raw/newdataset/newdataset/Mental workload/AC2 - Control.xlsx` | F3 | 65 | 544000 |
| `data/raw/newdataset/newdataset/Mental workload/AC2 - Control.xlsx` | F4 | 65 | 544000 |
| `data/raw/newdataset/newdataset/Mental workload/AC2 - Control.xlsx` | T3 | 65 | 544000 |
| `data/raw/newdataset/newdataset/Mental workload/AC2 - Control.xlsx` | T4 | 65 | 544000 |
| `data/raw/newdataset/newdataset/Mental workload/AC2 - Control.xlsx` | P3 | 65 | 544000 |
| `data/raw/newdataset/newdataset/Mental workload/AC2 - Control.xlsx` | P4 | 65 | 544000 |
| `data/raw/newdataset/newdataset/Mental workload/AC3 - Control.xlsx` | Fp1 | 65 | 476000 |
| `data/raw/newdataset/newdataset/Mental workload/AC3 - Control.xlsx` | Fp2 | 65 | 476000 |
| `data/raw/newdataset/newdataset/Mental workload/AC3 - Control.xlsx` | F3 | 65 | 476000 |
| `data/raw/newdataset/newdataset/Mental workload/AC3 - Control.xlsx` | F4 | 65 | 476000 |
| `data/raw/newdataset/newdataset/Mental workload/AC3 - Control.xlsx` | T3 | 65 | 476000 |
| `data/raw/newdataset/newdataset/Mental workload/AC3 - Control.xlsx` | T4 | 65 | 476000 |
| `data/raw/newdataset/newdataset/Mental workload/AC3 - Control.xlsx` | P3 | 65 | 476000 |
| `data/raw/newdataset/newdataset/Mental workload/AC3 - Control.xlsx` | P4 | 65 | 476000 |
| `data/raw/newdataset/newdataset/Mental workload/AC4 - Control.xlsx` | Fp1 | 65 | 492000 |
| `data/raw/newdataset/newdataset/Mental workload/AC4 - Control.xlsx` | Fp2 | 65 | 492000 |
| `data/raw/newdataset/newdataset/Mental workload/AC4 - Control.xlsx` | F3 | 65 | 492000 |
| `data/raw/newdataset/newdataset/Mental workload/AC4 - Control.xlsx` | F4 | 65 | 492000 |
| `data/raw/newdataset/newdataset/Mental workload/AC4 - Control.xlsx` | T3 | 65 | 492000 |
| `data/raw/newdataset/newdataset/Mental workload/AC4 - Control.xlsx` | T4 | 65 | 492000 |
| `data/raw/newdataset/newdataset/Mental workload/AC4 - Control.xlsx` | P3 | 65 | 492000 |
| `data/raw/newdataset/newdataset/Mental workload/AC4 - Control.xlsx` | P4 | 65 | 492000 |
| `data/raw/newdataset/newdataset/Stress/EO - Experiment.xlsx` | Fp1 | 65 | 636000 |
| `data/raw/newdataset/newdataset/Stress/EO - Experiment.xlsx` | Fp2 | 65 | 636000 |
| `data/raw/newdataset/newdataset/Stress/EO - Experiment.xlsx` | F3 | 65 | 636000 |
| `data/raw/newdataset/newdataset/Stress/EO - Experiment.xlsx` | F4 | 65 | 636000 |
| `data/raw/newdataset/newdataset/Stress/EO - Experiment.xlsx` | T3 | 65 | 636000 |
| `data/raw/newdataset/newdataset/Stress/EO - Experiment.xlsx` | T4 | 65 | 636000 |
| `data/raw/newdataset/newdataset/Stress/EO - Experiment.xlsx` | P3 | 65 | 636000 |
| `data/raw/newdataset/newdataset/Stress/EO - Experiment.xlsx` | P4 | 65 | 636000 |
| `data/raw/newdataset/newdataset/Stress/AC1 - Experiment.xlsx` | Fp1 | 65 | 568000 |
| `data/raw/newdataset/newdataset/Stress/AC1 - Experiment.xlsx` | Fp2 | 65 | 568000 |
| `data/raw/newdataset/newdataset/Stress/AC1 - Experiment.xlsx` | F3 | 65 | 568000 |
| `data/raw/newdataset/newdataset/Stress/AC1 - Experiment.xlsx` | F4 | 65 | 568000 |
| `data/raw/newdataset/newdataset/Stress/AC1 - Experiment.xlsx` | T3 | 65 | 568000 |
| `data/raw/newdataset/newdataset/Stress/AC1 - Experiment.xlsx` | T4 | 65 | 568000 |
| `data/raw/newdataset/newdataset/Stress/AC1 - Experiment.xlsx` | P3 | 65 | 568000 |
| `data/raw/newdataset/newdataset/Stress/AC1 - Experiment.xlsx` | P4 | 65 | 568000 |
| `data/raw/newdataset/newdataset/Stress/AC2 - Experiment.xlsx` | Fp1 | 65 | 456000 |
| `data/raw/newdataset/newdataset/Stress/AC2 - Experiment.xlsx` | Fp2 | 65 | 456000 |
| `data/raw/newdataset/newdataset/Stress/AC2 - Experiment.xlsx` | F3 | 65 | 456000 |
| `data/raw/newdataset/newdataset/Stress/AC2 - Experiment.xlsx` | F4 | 65 | 456000 |
| `data/raw/newdataset/newdataset/Stress/AC2 - Experiment.xlsx` | T3 | 65 | 456000 |
| `data/raw/newdataset/newdataset/Stress/AC2 - Experiment.xlsx` | T4 | 65 | 456000 |
| `data/raw/newdataset/newdataset/Stress/AC2 - Experiment.xlsx` | P3 | 65 | 456000 |
| `data/raw/newdataset/newdataset/Stress/AC2 - Experiment.xlsx` | P4 | 65 | 456000 |
| `data/raw/newdataset/newdataset/Stress/AC3 - Experiment.xlsx` | Fp1 | 65 | 536000 |
| `data/raw/newdataset/newdataset/Stress/AC3 - Experiment.xlsx` | Fp2 | 65 | 536000 |
| `data/raw/newdataset/newdataset/Stress/AC3 - Experiment.xlsx` | F3 | 65 | 536000 |
| `data/raw/newdataset/newdataset/Stress/AC3 - Experiment.xlsx` | F4 | 65 | 536000 |
| `data/raw/newdataset/newdataset/Stress/AC3 - Experiment.xlsx` | T3 | 65 | 536000 |
| `data/raw/newdataset/newdataset/Stress/AC3 - Experiment.xlsx` | T4 | 65 | 536000 |
| `data/raw/newdataset/newdataset/Stress/AC3 - Experiment.xlsx` | P3 | 65 | 536000 |
| `data/raw/newdataset/newdataset/Stress/AC3 - Experiment.xlsx` | P4 | 65 | 536000 |
| `data/raw/newdataset/newdataset/Stress/AC4 - Experiment.xlsx` | Fp1 | 65 | 448000 |
| `data/raw/newdataset/newdataset/Stress/AC4 - Experiment.xlsx` | Fp2 | 65 | 448000 |
| `data/raw/newdataset/newdataset/Stress/AC4 - Experiment.xlsx` | F3 | 65 | 448000 |
| `data/raw/newdataset/newdataset/Stress/AC4 - Experiment.xlsx` | F4 | 65 | 448000 |
| `data/raw/newdataset/newdataset/Stress/AC4 - Experiment.xlsx` | T3 | 65 | 448000 |
| `data/raw/newdataset/newdataset/Stress/AC4 - Experiment.xlsx` | T4 | 65 | 448000 |
| `data/raw/newdataset/newdataset/Stress/AC4 - Experiment.xlsx` | P3 | 65 | 448000 |
| `data/raw/newdataset/newdataset/Stress/AC4 - Experiment.xlsx` | P4 | 65 | 448000 |

## ECG workbooks (separate)

Sheets are conditions (`SC`, `EO`, `AC1`…), not EEG channels. Subject column sets can differ (e.g. SC starts mid-ID list). Not used by the primary EEG workload loader.

| File | Sheet | n_cols | n_time |
|------|-------|--------|--------|
| `data/raw/newdataset/newdataset/Mental workload/ECG - Control.xlsx` | SC | 53 | 315000 |
| `data/raw/newdataset/newdataset/Mental workload/ECG - Control.xlsx` | EO | 65 | 374000 |
| `data/raw/newdataset/newdataset/Mental workload/ECG - Control.xlsx` | AC1 | 65 | 355500 |
| `data/raw/newdataset/newdataset/Mental workload/ECG - Control.xlsx` | AC2 | 65 | 427500 |
| `data/raw/newdataset/newdataset/Mental workload/ECG - Control.xlsx` | AC3 | 65 | 461000 |
| `data/raw/newdataset/newdataset/Mental workload/ECG - Control.xlsx` | AC4 | 65 | 368000 |
| `data/raw/newdataset/newdataset/Stress/ECG - Experiment.xlsx` | SC | 53 | 328200 |
| `data/raw/newdataset/newdataset/Stress/ECG - Experiment.xlsx` | EO | 65 | 373050 |
| `data/raw/newdataset/newdataset/Stress/ECG - Experiment.xlsx` | AC1 | 65 | 404000 |
| `data/raw/newdataset/newdataset/Stress/ECG - Experiment.xlsx` | AC2 | 65 | 415500 |
| `data/raw/newdataset/newdataset/Stress/ECG - Experiment.xlsx` | AC3 | 65 | 386500 |
| `data/raw/newdataset/newdataset/Stress/ECG - Experiment.xlsx` | AC4 | 65 | 409500 |

## Sampling rate (unknown)

No Hz field in xlsx. If AC1 Control Fp1 has **592000** samples, duration under common rates would be:

| Assumed Hz | Duration (AC1 Control) |
|------------|------------------------|
| 128 | 4625.0 s (77.08 min) |
| 250 | 2368.0 s (39.47 min) |
| 256 | 2312.5 s (38.54 min) |
| 500 | 1184.0 s (19.73 min) |
| 1000 | 592.0 s (9.87 min) |

**Action:** confirm Hz from study docs before any MNE Raw / LOSO run.

## Label scheme (protocol v2 candidate)

| Target | Definition |
|--------|------------|
| PRIMARY | Control (`Mental workload`) vs Stress (`Stress`) — paired within subject × condition |
| Condition factor | EO, AC1, AC2, AC3, AC4 (task blocks) |

This is **denser** than STEW’s one-rating-per-subject: each subject has Control and Experiment recordings across multiple conditions.

## Notes / QC flags

- AC1 Control sheet `P4` dimension reported **68** columns vs **65** on other channels — verify on load.
- Files are very large (~0.5–1.1 GB each); prefer convert-to-FIF/NPZ cache before training.
- Values sampled from Fp1 look continuous float (µV-like); units still undocumented.

## Reproduce

```bash
python -m src.inspect_newdataset
```
