# EEG Workload Evaluation Toolkit *(research prototype)*

Subject-wise EEG cognitive-workload **evaluation toolkit** with a dashboard UI.  
Not a clinical or consumer medical product — research / portfolio prototype only.

| Layer | Stack |
|-------|--------|
| Research ML | Python 3.10+, MNE, scikit-learn, LOSO / Group splits |
| API | FastAPI (`src/api_server.py`) |
| Dashboard | React + Vite + Three.js (`frontend/`) |
| Legacy demo | Streamlit (`app.py`) |

**GitHub:** [sharjeel-ahmed-1/brainmed-eeg-workload](https://github.com/sharjeel-ahmed-1/brainmed-eeg-workload)  
**Live demo:** [brainmed-eeg-workload.onrender.com](https://brainmed-eeg-workload.onrender.com) — free Render host; **first load after idle ~30–60 s** (cold start / wake).

---

## Evaluation practices (what the protocol actually does)

- Split by **subject** (LeaveOneGroupOut / GroupKFold) — never random-split epochs for the primary claim  
- Scaler / encoder / feature steps inside an **sklearn Pipeline** (fit on train folds only)  
- Report accuracy, baselines (majority), and (where logged) bal-acc / macro-F1 / confusion  
- Fixed seed from `config.SEED`; permutation test + α-boost positive control on STEW  
- Frozen protocol: no retuning on outer LOSO after seeing primary numbers  

---

## Repository structure

```text
brainmed-eeg-workload/
├── README.md
├── docs/                     # Methods, results, protocols
├── src/                      # Train / predict / API / DB
├── frontend/                 # Dashboard UI
├── runtime_assets/           # STEW cache + model for Docker demo
├── logs/                     # Evaluation logs (v1 / v2)
└── …
```

---

## Quick start — UI

```bash
# Terminal 1 — API
cd brainmed-eeg-workload
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.api_server:app --reload --port 8000

# Terminal 2 — dashboard
cd frontend && npm install && npm run dev
```

Open **http://127.0.0.1:5173**

| Page | Purpose |
|------|---------|
| Overview | 3D brain, band proxies, DEMO lifestyle widgets, **file replay (simulated live)** |
| Reports | Upload / STEW score (`demo_all_subject` or `loso_held_out`) + within-subject calibration |
| My History | Session history (SQLite by default; optional Postgres `DATABASE_URL`) |

Within-subject calibration: fit baseline-vs-task on one session (STEW first/last epoch split is simulated; or upload real baseline+task files).

---

## Results summary (logged)

| Track | Dataset | Label | LOSO acc | Majority |
|-------|---------|-------|----------|----------|
| v1 primary | STEW | rating ≥ 7 (2-class) | **0.356** | 0.556 |
| v2-A | STEW | rating ≥ 6 | 0.711 | 0.711 |
| v2-A | STEW | rating ≥ 7 | 0.356 | 0.556 |
| v2-A | STEW | rating ≥ 8 | 0.689 | 0.689 |
| v2-B RF | Newdataset AC1 | Control vs Stress | **0.576** | ~0.504 |
| v2-B RF | Newdataset EO | Control vs Stress | 0.538 | 0.500 |
| v2-B RF | Newdataset AC2 | Control vs Stress | 0.556 | ~0.508 |
| v2-B RF | Newdataset AC3 | Control vs Stress | 0.544 | ~0.512 |
| v2-B RF | Newdataset AC4 | Control vs Stress | 0.504 | ~0.504 |
| v2-D Riemann | Newdataset AC1 | Control vs Stress | 0.544 | ~0.504 |
| v2-D Riemann | Newdataset AC2 | Control vs Stress | **0.579** | ~0.508 |

Full write-ups: [`docs/RESULTS.md`](docs/RESULTS.md), [`docs/RESULTS_v2.md`](docs/RESULTS_v2.md).

**STEW v1 read:** LOSO **below majority** (0.356 vs 0.556). With **one label per subject**, the effective sample size is **n = 45** subject-level decisions — high variance; treat as an **under-powered subject-level protocol**, not a polished “model failure” story. Permutation p_acc ≈ 0.98. Positive control (α×8) passed.

Product honesty paths: `GET /api/methods`, `?model_mode=loso_held_out`, `GET /api/live/replay/{id}` (**file replay / simulated live**, not a headset stream).

---

## Public demo (Render)

```bash
docker build -t brainmed .
docker run --rm -p 8000:8000 brainmed
```

Hosted: https://brainmed-eeg-workload.onrender.com  
**First load after idle ~30–60 s.** Free tier may sleep; SQLite history can reset on cold instances unless you set a persistent `DATABASE_URL`.

---

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/PROJECT.md`](docs/PROJECT.md) | Frozen STEW protocol |
| [`docs/RESULTS.md`](docs/RESULTS.md) | Primary LOSO write-up + limitations |
| [`docs/RESULTS_v2.md`](docs/RESULTS_v2.md) | Multi-threshold + Control/Stress + Riemann |
| [`docs/PROTOCOL_V2.md`](docs/PROTOCOL_V2.md) | v2 research tracks |
| [`docs/PROJECT_REPORT.md`](docs/PROJECT_REPORT.md) | Longer project report |
| [`docs/MONTAGE_AND_UNITS.md`](docs/MONTAGE_AND_UNITS.md) | Montage assumption + units |

---

## Design choices

1. Subject splits only for primary claims.  
2. Frozen STEW v1 table — later work logged separately under v2.  
3. UI labels DEMO lifestyle charts; states LOSO findings in-product.  
4. Raw datasets stay out of git — place under `data/raw/` locally.

---

## License / data

Code is for portfolio and research reproduction. STEW and Atiwiwat & Hemakom EEG-ECG remain under their original licenses — download separately into `data/raw/`.
