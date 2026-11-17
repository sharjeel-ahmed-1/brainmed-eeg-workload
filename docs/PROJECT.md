# EEG Workload Estimation

## Goal
Estimate cognitive workload from EEG; later drive a neuroadaptive interface.

## Data
- Dataset: STEW (Kaggle `.mat` under `data/raw/stew/`)
- Layout (from `data/DATA_SUMMARY.md`): `dataset` shape `(14, 19200, 45)` = channels × time × subjects
- Labels (one per subject): PRIMARY `rating>=7` (2-class); SECONDARY `class_012` (3-class)
- `sfreq`: 128 Hz from Kaggle PDF (19200 / 128 = 150 s); not stored in `.mat`
- Channel names: not in the `.mat` files; loader uses `EEG001`…`EEG014` (Emotiv-14 order assumed only for variant A)

## Frozen protocol
Everything below is frozen. Report results as obtained; no further tuning on LOSO.

### Targets
- **PRIMARY:** 2-class — `rating >= 7` → 1 else 0
- **SECONDARY:** 3-class — `class_012` ∈ {0,1,2} (always reported)

### Preprocess
- Bandpass 1–40 Hz, notch 50 Hz, average reference, fixed-length epochs 4.0 s @ 128 Hz (37 epochs/subject before rejects)

### Epoch rejection (no subject exclusions)
1. **Flat/zero (RAW epochs, data-quality only):** drop if any exact-zero sample **or** any channel has ≥128 consecutive identical samples (1.0 s). Not tuned on accuracy.
2. **Amplitude (FILTERED epochs):** drop if max-ch PTP > `median + 5 × 1.4826 × MAD` within subject (`EPOCH_REJECT_Z=5`). Chosen as a conventional robust ≈5σ rule when the reject code was written, **before any LOSO that used amplitude rejection**; not tuned on accuracy.
3. Non-finite features: assert (fail loudly)

### Features (baseline)
- Relative band power (δ θ α β γ) per channel + θ/α per channel → 84-D
- Subject-level decision: mean predicted probability across epochs (LOSO by subject)

### Classifier (baseline RF)
- `StandardScaler` + `RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=42, n_jobs=-1)` in Pipeline
- Parallel workers (permutation): same RF with `n_jobs=1`, `random_state=SEED+k`

### Sanity
- Permutation: **n_perm=200**; shuffle the **45 subject-level labels**; epoch labels always `y_subject[subject_id]`
- Positive control: alpha gain 8× (+700%); sensitivity +10/+25/+50/+100% (gains 1.1, 1.25, 1.5, 2.0)
- Metrics: pooled accuracy, balanced accuracy, per-class recall, Wilson 95% CI; majority + chance baselines

### Pre-specified variants (max 2; report failures too)
- **A:** LogisticRegression on frontal mean θ + frontal θ/α (Emotiv-14 order assumption)
- **B:** Subject-mean features (45 samples) + same RF

### Cache
- `data/cache/epoch_features_<sha256(config.py|preprocess.py)[:16]>.npz` — invalid if those files change

## Split strategy
Leave-one-subject-out. No random epoch splits.

## Current best result (frozen protocol)

Sources: `logs/sanity_frozen_parallel.log` (baseline/posctrl/sensitivity) + `logs/perm_variants.log` / `data/SANITY_REPORT.md` (perm + variants).

| Eval | Acc | Bal-acc | Notes |
|------|-----|---------|-------|
| PRIMARY 2-class (epoch LOSO + mean proba) | **0.356** | 0.340 | Below majority 0.556; Wilson [0.232, 0.502] |
| SECONDARY 3-class | **0.422** | 0.398 | ~majority 0.400 |
| Posctrl 8× alpha | **1.000** | 1.000 | PASSED |
| Sensitivity +10/+25/+50/+100% | 0.422 / 0.622 / 0.933 / 0.978 | — | Smallest clear lift ~+25% |
| Permutation p (acc / bal-acc) | — | — | **0.980 / 0.975** (not better than null) |
| Variant A (LR frontal) | **0.400** | 0.395 | Still ≤ majority |
| Variant B (subject-mean RF) | **0.311** | 0.285 | Still ≤ majority |

Honest summary: **no LOSO-detectable `rating≥7` signal** with frozen features/models; pipeline sanity (posctrl) OK.

Interpretation (descriptive only): `python -m src.interpret` → `figures/` + `data/INTERPRETATION.md`.

Write-up: `RESULTS.md`. Demo: `streamlit run app.py` (model via `src.predict.save_primary_model`).

## Known issues / decisions
- Saved model via `--save` is fit on all subjects (not held-out)
- `.mat` units not documented; no V scaling applied
- Flat/heavy-artifact subjects stay in LOSO (no exclusions)

## Run
```
cd /Users/abc/Downloads/eeg-workload
source .venv/bin/activate
python -m src.train --n-perm 200 --log logs/sanity_frozen.log
```
