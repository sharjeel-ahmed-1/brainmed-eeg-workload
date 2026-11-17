# ROADMAP — STEW EEG workload (frozen protocol)

Portfolio research prototype. Report results as obtained; **no LOSO tuning**.

Legend: `[x]` done · `[~]` in progress · `[ ]` todo

---

## Status at a glance

| # | Phase | Status |
|---|--------|--------|
| 0 | Foundations (data, load, freeze) | **DONE** |
| 1 | Frozen sanity evaluation run | **DONE** |
| 2 | Lock numbers into docs | **DONE** |
| 3 | Interpretation (importance / maps / lit) | **DONE** |
| 4 | Streamlit adaptive demo | **DONE** |
| 5 | RESULTS.md write-up | **DONE** |

**MVP presentable when:** Phase 1–2 + Phase 4 minimal + Phase 5.  
**Portfolio “comp neuro” bar:** also Phase 3.

---

## Phase 0 — Foundations — DONE

- [x] STEW `.mat` inspect (`src/inspect_data.py` → `data/DATA_SUMMARY.md`)
- [x] One-record-per-subject load (`src/load.py`)
- [x] Preprocess + band-power features
- [x] Flat/zero + amp rejection + finite asserts
- [x] Protocol-hash feature cache
- [x] LOSO-by-subject + subject mean-proba aggregation
- [x] Metrics: acc, bal-acc, recall, Wilson CI, baselines
- [x] Parallel LOSO folds / perm workers (all cores)
- [x] Frozen protocol written in `PROJECT.md`
- [x] `ROADMAP.md` created

---

## Phase 1 — Frozen evaluation run — DONE

- [x] Audit / baselines / posctrl / sensitivity (`logs/sanity_frozen_parallel.log`)
- [x] Permutation n=200 — p_acc=**0.980**, p_bal=**0.975** (`logs/perm_variants.log`)
- [x] Variant A acc **0.400**; Variant B acc **0.311**
- [x] `ALL STAGES done` + `data/SANITY_REPORT.md`

---

## Phase 2 — Lock results — DONE

- [x] Numbers in `PROJECT.md`
- [x] `data/SANITY_REPORT.md` for perm/variants
- [x] No retuning after results

---

## Phase 3 — Interpretation — DONE

- [x] `src/interpret.py` — RF importances + variant A LR coefs
- [x] Figures under `figures/` (`rf_top_features`, heat, channel/θ maps, `variant_a_lr_coefs`)
- [x] Short lit note: `data/INTERPRETATION.md` (honest null framing; Emotiv-14 assumption)

**Verify:** `python -m src.interpret` ✓

---

## Phase 4 — Streamlit adaptive demo — DONE

- [x] `src/predict.py` — save all-subject demo model + STEW/upload scoring
- [x] `app.py` — STEW subject picker, optional upload, adaptive UI when high
- [x] Honest banner: recorded data only; null LOSO; all-subject model caveat

**Verify:** `streamlit run app.py`

---

## Phase 5 — Write-up — DONE

- [x] `RESULTS.md`: methods, table, posctrl/perm/sensitivity, variants, limitations
- [x] Internship takeaways (methods rigor > cherry-picked accuracy)

---

## Ordered next actions

1. ~~Phase 0–5~~ done — portfolio MVP complete
2. Optional: polish figures / README link to `RESULTS.md` / run Streamlit locally

## Out of scope (frozen)

- Extra model search / hyperparameter tuning on LOSO  
- Live headset  
- Subject drops based on accuracy  
