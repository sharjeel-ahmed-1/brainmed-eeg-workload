# RESULTS — STEW EEG cognitive workload

Frozen protocol; no LOSO retuning after seeing numbers. Full spec: `PROJECT.md`.

## Dataset

| Item | Value |
|------|--------|
| Source | STEW (Kaggle `.mat`) |
| Shape | 14 ch × 19200 samples × 45 subjects |
| sfreq | 128 Hz (Kaggle PDF; 150 s / subject) |
| Primary label | `rating ≥ 7` → high (2-class) |
| Secondary | `class_012` (3-class; reported, not tuned) |
| Channel names | Not in `.mat`; Emotiv-14 order only as assumption (variant A / maps) |

## Methods (frozen)

- Preprocess: bandpass 1–40 Hz, notch 50 Hz, average ref, 4.0 s epochs
- Reject: raw flat/zero (≥128 identical or any zero); filtered amp MAD z=5
- Features: relative δθαλγ + θ/α per channel → 84-D
- Model: `StandardScaler` + RF(300, balanced, seed=42) in Pipeline
- Split: **Leave-one-subject-out**; subject decision = mean epoch probability
- Sanity: permutation n=200 (subject labels); α-boost positive control + sensitivity
- Variants (pre-specified): A = LR frontal θ + θ/α; B = subject-mean RF

## Primary results

| Eval | Acc | Bal-acc | Notes |
|------|-----|---------|-------|
| PRIMARY 2-class LOSO | **0.356** | 0.340 | Majority 0.556; Wilson [0.232, 0.502] |
| SECONDARY 3-class | 0.422 | 0.398 | ~majority 0.400 |
| Posctrl α×8 | **1.000** | 1.000 | PASSED |
| Sensitivity +10/+25/+50/+100% | 0.422 / 0.622 / 0.933 / 0.978 | — | Clear lift ~+25% |
| Permutation p (acc / bal) | — | — | **0.980 / 0.975** |
| Variant A | 0.400 | 0.395 | ≤ majority |
| Variant B | 0.311 | 0.285 | ≤ majority |

Sources: `logs/sanity_frozen_parallel.log`, `logs/perm_variants.log`, `data/SANITY_REPORT.md`.

**Verdict:** No LOSO-detectable `rating≥7` signal under this frozen feature/model stack. Pipeline can detect injected spectral change (posctrl); natural labels do not separate above chance/majority.

## Interpretation (descriptive)

`python -m src.interpret` → `figures/` + `data/INTERPRETATION.md`.

All-subject RF importances (not held-out) ranked several γ/β channel features highest; Variant A LR coefs were small (θ −0.21, θ/α +0.17). Do not over-read maps given the null LOSO result and montage assumption.

## Demo

```bash
source .venv/bin/activate
python -c "from src.predict import save_primary_model; save_primary_model()"
streamlit run app.py
```

Demo model is fit on **all** subjects. UI simplifies when predicted class = high. Banner states the null LOSO finding.

## Limitations

- Consumer / Emotiv-class EEG; units undocumented in `.mat`
- One rating label per subject (coarse, possible noise)
- Channel montage assumed for regional features / maps only
- No live acquisition; no LOSO hyperparameter search (by design)
- Null primary accuracy is a methods result, not a product claim

### Remediation (does not change the table above)

See `PROTOCOL_V2.md`, `RESULTS_v2.md`, `data/MONTAGE_AND_UNITS.md`, `data/NEWDATASET_SUMMARY.md`.
Product paths: API `model_mode=loso_held_out`, `/api/live/replay`, methods banner.

## Internship / portfolio takeaways

1. Subject-wise evaluation + permutation + positive control beat a flashy but leaky accuracy.
2. Reporting failures (variants A/B, null LOSO) is part of rigorous computational neuroscience / BCI practice.
3. Neuroadaptive UI can still be prototyped honestly when the classifier is weak — as a demo of the *interaction* concept, not as proof of decoding.
