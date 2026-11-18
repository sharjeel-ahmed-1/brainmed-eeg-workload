# Project Report — BrainMed+ / EEG Workload Evaluation Toolkit

**Title:** BrainMed+ — EEG Workload Evaluation Toolkit (research prototype)  
**Type:** Research / internship portfolio prototype  
**Primary claim:** Subject-wise LOSO + transparent under-majority STEW result; UI demos interaction design, not clinical decoding.

---

## 1. Executive summary

This project evaluates cognitive-workload labels from EEG using the **STEW** dataset, with **leave-one-subject-out (LOSO)** only (no random epoch splits), and ships a **BrainMed+** React + FastAPI dashboard (research prototype) plus a legacy Streamlit demo.

Under a **frozen** preprocess → band-power → Random Forest protocol, primary 2-class LOSO accuracy was **0.356** (majority baseline **0.556**). With **one label per subject**, effective n = **45** subject-level decisions — an **under-powered** cross-subject setup with high variance. Permutation p_acc ≈ 0.98. A positive control (α×8) **passed**, showing the pipeline can detect injected spectral change. The UI labels lifestyle charts as **DEMO** and states the STEW LOSO finding in-product.

---

## 2. Problem & goals

| Goal | Description |
|------|-------------|
| Research | Estimate high vs low cognitive workload from EEG with subject-generalization |
| Methods | Freeze protocol; report failures; permutation + positive control |
| Product | Dashboard UI (BrainMed+) for reports, bands, 3D brain — research prototype |
| Honesty | No inflated accuracy claims; demo model ≠ held-out LOSO model |

---

## 3. Dataset

| Item | Value |
|------|--------|
| Name | STEW (Kaggle `.mat`) |
| Path | `data/raw/stew/` |
| Shape | **14 channels × 19200 samples × 45 subjects** |
| Sampling rate | **128 Hz** (Kaggle PDF; 150 s / subject) |
| Primary label | `rating ≥ 7` → high (2-class) |
| Secondary label | `class_012` (3-class; reported, not tuned) |
| Channel names | Not in `.mat`; Emotiv-14 order assumed only for regional / Variant A maps |

**Limitations:** Consumer / Emotiv-class EEG; units undocumented; one rating per subject (coarse).

---

## 4. Machine learning pipeline

### 4.1 Stack (Python)

| Library | Role |
|---------|------|
| **Python 3.10+** | Runtime |
| **MNE** | EEG filter, reference, epochs |
| **NumPy / SciPy / pandas** | Arrays, signal math, tables |
| **h5py** | `.mat` / HDF-style reads as needed |
| **scikit-learn** | `Pipeline`, `StandardScaler`, `RandomForestClassifier`, `LogisticRegression`, LOSO |
| **joblib** | Model persistence, parallel workers |
| **matplotlib** | Interpretation figures |
| **Streamlit** | Legacy adaptive demo (`app.py`) |
| **FastAPI + Uvicorn** | BrainMed+ API (`src/api_server.py`) |

Config: `config.py` (paths, `SEED`, bands, reject thresholds). No hardcoded data paths in modules.

### 4.2 Modules (`src/`)

| Module | Purpose |
|--------|---------|
| `inspect_data.py` | Dataset inspection → `data/DATA_SUMMARY.md` |
| `load.py` | One-record-per-subject STEW load + labels |
| `preprocess.py` | Bandpass, notch, average ref, epochs |
| `raw_qc.py` | Flat/zero + amplitude rejection |
| `features.py` | Relative band power + θ/α |
| `train.py` | LOSO training, permutation, posctrl, sensitivity |
| `metrics.py` | Acc, balanced acc, recall, Wilson CI, baselines |
| `interpret.py` | RF importances / maps → `figures/`, `data/INTERPRETATION.md` |
| `predict.py` | All-subject demo model save/load; STEW / upload score |
| `report_viz.py` | Band profiles for UI |
| `api_server.py` | REST API for React frontend |

### 4.3 Frozen protocol

**Preprocess**

- Bandpass **1–40 Hz**, notch **50 Hz**, average reference  
- Epochs **4.0 s** @ 128 Hz (~37 epochs/subject before rejects)

**Rejection (not tuned on accuracy)**

1. Raw flat/zero (≥128 identical samples or any zero)  
2. Filtered amplitude: max-ch PTP > median + 5×MAD (z≈5)  
3. Non-finite features → assert (fail loud)

**Features (84-D)**

- Relative **δ, θ, α, β, γ** per channel + **θ/α** per channel

**Classifier**

- `StandardScaler` + `RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=42)` inside **sklearn Pipeline** (scaler fit on train folds only)

**Split**

- **Leave-one-subject-out**; subject decision = **mean epoch probability**  
- Never random-split epochs for the primary claim

**Sanity**

- Permutation **n=200** (shuffle subject labels)  
- Positive control: α gain ×8  
- Sensitivity: +10 / +25 / +50 / +100% spectral injection

**Pre-specified variants**

- **A:** LogisticRegression on frontal mean θ + θ/α (montage assumption)  
- **B:** Subject-mean features (45 samples) + same RF  

**Cache**

- Protocol-hash feature cache under `data/cache/`

---

## 5. Results (frozen — from actual runs)

Sources: `logs/sanity_frozen_parallel.log`, `logs/perm_variants.log`, `data/SANITY_REPORT.md`, `RESULTS.md`.

| Evaluation | Accuracy | Balanced acc | Notes |
|------------|----------|--------------|--------|
| PRIMARY 2-class LOSO | **0.356** | 0.340 | Majority 0.556; Wilson [0.232, 0.502] |
| SECONDARY 3-class | 0.422 | 0.398 | ~majority 0.400 |
| Posctrl α×8 | **1.000** | 1.000 | PASSED |
| Sensitivity +10/+25/+50/+100% | 0.422 / 0.622 / 0.933 / 0.978 | — | Clear lift ~+25% |
| Permutation p (acc / bal) | — | — | **0.980 / 0.975** |
| Variant A | 0.400 | 0.395 | ≤ majority |
| Variant B | 0.311 | 0.285 | ≤ majority |

**Verdict:** No LOSO-detectable `rating≥7` signal under this frozen stack. Pipeline detects injected α change; natural labels do not beat chance/majority.

**Interpretation (descriptive only):** All-subject RF importances ranked several γ/β features high; Variant A LR coefs small. Do not over-read maps given under-majority LOSO + assumed montage.

---

## 6. Applications & UI

### 6.1 BrainMed+ (primary UI)

| Layer | Tech |
|-------|------|
| Build | **Vite**, **TypeScript**, **React 19** |
| Routing | **react-router-dom** |
| Charts | **Recharts** |
| 3D | **Three.js**, **@react-three/fiber**, **@react-three/drei** |
| Font | **Michroma** |
| API client | `frontend/src/api/client.ts` → FastAPI |

**Pages**

1. **Overview** — 3D glass brain (`brain.glb`), neural plexus field, concentration widget, activity/productivity band waves, frequency cards, DEMO lifestyle / timeline widgets  
2. **Reports** — upload EEG or score STEW subject via real `predict` pipeline; verdict + band report  
3. **My History** — local scored sessions (`historyStore`)

**Visual design**

- Medical glass aesthetic: deep navy base + light cyan / amber / mint accent combo  
- Smooth SVG sine waves for band/concentration UI (relative-power Hz **proxies**, not live meters)  
- Lifestyle / diary charts labeled **DEMO** (STEW has no activity diary)

**Run**

```bash
# API
uvicorn src.api_server:app --reload --port 8000
# UI
cd frontend && npm install && npm run dev
# → http://127.0.0.1:5173
```

### 6.2 Legacy Streamlit

- `app.py` + `src/predict.py`  
- STEW subject picker, optional upload, adaptive UI when predicted high  
- Banner: under-powered STEW LOSO + all-subject demo model caveat  

```bash
streamlit run app.py
```

---

## 7. Architecture (high level)

```
STEW .mat ──► load → preprocess → QC → band-power features
                      │
                      ├─► train (LOSO / perm / posctrl) ──► RESULTS.md
                      ├─► interpret ──► figures/
                      └─► predict (all-subject demo model)
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
              Streamlit app          FastAPI api_server
                                              │
                                              ▼
                                    BrainMed+ React (Vite)
```

---

## 8. Documentation map

| File | Content |
|------|---------|
| `PROJECT.md` | Frozen protocol + locked numbers |
| `RESULTS.md` | Methods write-up, limitations, takeaways |
| `ROADMAP.md` | Phase 0–5 checklist (all done) |
| `data/DATA_SUMMARY.md` | Raw data inspection |
| `data/SANITY_REPORT.md` | Permutation / variants |
| `data/INTERPRETATION.md` | Honest under-powered LOSO framing + maps note |
| `PROJECT_REPORT.md` | This summary |

---

## 9. What we deliberately did *not* do

- Hyperparameter search / retuning after seeing LOSO numbers  
- Random epoch train/test splits  
- Claiming product-grade decoding from under-majority STEW LOSO
- Real-time headset acquisition (file replay only)
- Dropping subjects to inflate accuracy  

---

## 10. Internship / portfolio takeaways

1. **Subject-wise evaluation + permutation + positive control** beats a leaky high accuracy.  
2. **Reporting an under-powered / under-majority LOSO result** is valid computational neuroscience / BCI practice.  
3. **Neuroadaptive UI** can still be prototyped honestly — as interaction design, not as proof of decoding.  
4. End-to-end stack: research ML (MNE/sklearn) + API (FastAPI) + premium React/Three.js dashboard.

---

## 11. Quick reference — tools & tech used

**Research / ML:** Python, MNE, scikit-learn, NumPy, SciPy, pandas, h5py, joblib, matplotlib, LeaveOneGroupOut / subject LOSO, StandardScaler, RandomForest, LogisticRegression, Wilson CI, permutation test, positive control.

**Backend / demos:** FastAPI, Uvicorn, Streamlit, python-multipart.

**Frontend:** React 19, TypeScript, Vite, React Router, Recharts, Three.js, React Three Fiber, Drei, Michroma, glass UI theme, GLB brain model.

**Eval ethics:** Frozen protocol, subject splits only, honest DEMO labels, documented under-powered primary result (acc **0.356**, n=45).

---

*Numbers in this report match `RESULTS.md` / frozen logs only. Do not cite other accuracies without a new logged run.*
