# Diagnosis (2026-11-17) — amp=nan / drop=0 / baseline drift

## 1. Raw `dataset.mat`
- Shape `(14, 19200, 45)`, dtype float64
- Global: **nan=0, inf=0**, min=0, max=8401.54
- Per-subject: all finite; values mostly ~1e3–8e3 (subject 30 reaches 0)
- **Units not stored in .mat.** Magnitudes look like µV-scale Emotiv counts. We load into `mne.io.RawArray` **without** converting to volts (MNE’s default unit assumption). Relative band-power features are scale-invariant to a global constant, but absolute amp stats are in whatever unit the file uses.

## 2. Where `amp=[nan,nan]` came from
- Function: `load_feature_cache()` in `src/train.py`
- Cause: `--reuse-cache` loaded an old `epoch_features.npz` that only had `X` and `groups`. The loader **invented** `amp_min/amp_max = nan` and `dropped = 0` instead of failing.
- **Fix:** cache now stores audit arrays; missing keys → `RuntimeError`. `print_audit` **asserts** finite amps. Non-finite features → `AssertionError` (no silent drop).

## 3. Why `kept<37` with `drop=0` (under reused cache)
Steps that can remove epochs:
1. **`make_fixed_length_epochs`**: `floor(150/4) = 37` always; leftover 2 s discarded (same for every subject).
2. **`reject_epochs_amplitude`**: only step that varies per subject (174 drops in first real audit → kept 25–37).
3. **Non-finite features**: now **assert** (never silent).

Under `--reuse-cache` with the old loader, `kept` came from real cached rows (already amplitude-filtered) while `drop` was hard-coded 0 — inconsistent fake audit. Fixed by persisting `dropped_amp` / `epochs_fixed` / `epochs_kept`.

## 4. Baseline 0.378 → 0.311
| Run | Acc | Feature set |
|-----|-----|-------------|
| First `python -m src.train` | 0.378 | **No** amplitude rejection (~37×45 epochs) |
| Sanity run (`SANITY_RUN.log`) | 0.311 | **With** amplitude rejection (1665→1491 epochs, 10.5% dropped) |

Code changes that affect features/labels between those runs:
1. **Added `reject_epochs_amplitude`** (MAD/ptp) — changes which epochs enter features.
2. **`preprocess`**: skip `resample` when already at 128 Hz (was always calling resample; should be near-no-op at 128).
3. Labels: **unchanged** (`rating>=7` 2-class).
4. Model: same RF (300 trees, balanced, seed=42); reporting metrics expanded but accuracy definition unchanged.

## Amplitude rejection
- Rule: `max_ch_ptp > median(ptp) + 5 * 1.4826 * MAD(ptp)` within subject (`EPOCH_REJECT_Z=5`)
- Domain: **FILTERED** epochs (1–40 Hz, notch, avg-ref) — DC already removed
- Units: .mat numeric scale (µV-like); not converted to volts
- Choice: pre-specified robust rule; **not** tuned on LOSO
- Pooled filtered PTP: median≈223, p95≈2707, max≈9286; drops 174/1665 at z=5

## Raw zeros / flats
- Exact zeros: only subject 30 has 6 zero samples (0.002%); others 0
- Flats (identical run ≥8 samples): several subjects; heavy in s=23,30,31,40
- Handling: flagged in audit via `src/raw_qc.py`; **no dedicated flat reject** yet

## Positive control / permutation
- Passing check used **gain=8.0×** (+700% on alpha component)
- Sensitivity sweep coded: gains 1.1, 1.25, 1.5, 2.0 (+10/+25/+50/+100%)
- Label shuffles: `default_rng(SEED)` stream (matches serial order)
- RF seeds: `SEED+k` per perm (serial used fixed SEED → null accs will not match prior 50)

## Command (do not auto-start from agent shell)
```bash
cd /Users/abc/Downloads/eeg-workload
source .venv/bin/activate
python -m src.train --n-perm 200 --log logs/sanity_parallel_manual.log
```
