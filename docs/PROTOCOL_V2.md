# Protocol v2 — denser labels / nested CV (does not overwrite frozen v1)

v1 STEW numbers in `RESULTS.md` stay locked. Anything below is a **new** protocol; logs go to `logs/v2/` and `RESULTS_v2.md`.

## Motivation

v1 limitation: one coarse `rating≥7` label per subject → null LOSO.  
v2 addresses label density and evaluation hygiene without leaking test subjects into tuning.

## Track A — STEW multi-threshold (same data, honest sensitivity)

- Targets: binary `rating ≥ t` for `t ∈ {6,7,8}` (descriptive; still one label/subject).
- Same preprocess/features/RF as v1; **separate** LOSO + perm logs per threshold.
- Nested subject CV only if hyperparams change: outer LeaveOneGroupOut, inner GroupKFold on train subjects.

## Track B — Newdataset Control vs Stress (primary v2 research path)

Source: `data/raw/newdataset/newdataset/` — see [`NEWDATASET_SUMMARY.md`](NEWDATASET_SUMMARY.md).

| Item | Value |
|------|--------|
| Channels | Fp1 Fp2 F3 F4 T3 T4 P3 P4 (named in sheets) |
| Subjects | 65 IDs (gaps in 001–077) |
| PRIMARY label | Stress/Experiment=1 vs Mental-workload/Control=0 |
| Factor | Condition EO, AC1–AC4 (within-subject pairs) |
| Split | Leave-one-**subject**-out (never random epochs) |
| sfreq | **2000 Hz** (documented; `config_ext.NEWDATASET_SFREQ`); cache resample **250 Hz** |

Loader: `src/load_newdataset.py` / `python -m src.cache_newdataset`. First LOSO (AC1): see `RESULTS_v2.md`.

### Proposed freeze (once sfreq set)

1. Bandpass 1–40 Hz, notch 50 Hz, average ref, 4.0 s epochs (same spirit as v1; re-hash cache).
2. Relative δθαβγ + θ/α per channel (8 ch → 48-D + optional θ/α).
3. Pipeline: StandardScaler + RF(300, balanced, seed=`config.SEED`).
4. Subject decision = mean epoch probability.
5. Permutation n=200 on subject labels; α×8 positive control.
6. No retuning after seeing outer LOSO.

### Nested CV (if any hyperparameter search)

```
for subject in subjects:          # outer LOSO
  train = all other subjects
  pick hyperparams with GroupKFold(k=5) on train only
  refit on full train → score left-out subject
```

Never tune on the outer test subject.

## Track C — Product honesty (independent of decoding lift)

- API modes: `demo_all_subject` vs `loso_held_out` (see `src/predict.py` / API).
- UI banners: null v1 LOSO; DEMO lifestyle; Hz proxies.
- Live path: STEW replay stream (`/api/live/replay`) before real headset.

## Runbook

```bash
# Inspect newdataset metadata
python -m src.inspect_newdataset

# After setting NEWDATASET_SFREQ in config_ext.py:
# python -m src.cache_newdataset --condition AC1 --max-subjects 3   # when added
# python -m src.train_v2 --help

# STEW multi-threshold (v1 stack, new logs only)
python -m src.train_v2_stew_thresholds --thresholds 6,7,8 --log-dir logs/v2
```

## Out of scope for v2

- Overwriting `RESULTS.md` v1 table  
- Random epoch splits  
- Claiming clinical decoding from DEMO UI  
