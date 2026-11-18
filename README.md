# BrainMed+ — EEG Cognitive Workload

Professional research prototype for **subject-wise EEG cognitive-workload estimation**, with an honest LOSO evaluation protocol and the **BrainMed+** clinical-style dashboard.

| Layer | Stack |
|-------|--------|
| Research ML | Python 3.10+, MNE, scikit-learn, LOSO / Group splits |
| API | FastAPI (`src/api_server.py`) |
| Dashboard | React + Vite + Three.js (`frontend/`) |
| Legacy demo | Streamlit (`app.py`) |

**GitHub:** [sharjeel-ahmed-1/brainmed-eeg-workload](https://github.com/sharjeel-ahmed-1/brainmed-eeg-workload)

---

## Repository structure

```text
brainmed-eeg-workload/
├── README.md                 # This file
├── requirements.txt
├── config.py                 # STEW protocol constants (hashed with preprocess)
├── config_ext.py             # Newdataset / montage notes (outside protocol hash)
├── app.py                    # Streamlit demo
├── docs/                     # Research documentation (methods, results, protocols)
├── src/                      # Importable Python package (train, predict, API helpers)
├── frontend/                 # BrainMed+ React application
├── figures/                  # Interpretation plots
├── logs/                     # Evaluation logs (v1 / v2)
├── data/                     # Runtime data only (raw/cache/exports gitignored)
├── models/                   # Trained joblib artifacts (gitignored)
└── .gitignore
```

---

## Quick start — BrainMed+ UI

```bash
# Terminal 1 — API
cd brainmed-eeg-workload
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.api_server:app --reload --port 8000

# Terminal 2 — dashboard
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173**

| Page | Purpose |
|------|---------|
| Overview | 3D brain, band proxies, DEMO lifestyle widgets |
| Reports | Upload / STEW score (`demo_all_subject` or `loso_held_out`) + **within-subject calibration** |
| My History | Cloud-synced session history (free SQLite / optional Postgres `DATABASE_URL`) |

**Within-subject calibration** (best product angle while cross-subject LOSO is null): fit a personal baseline-vs-task model on one session, then score held-out epochs / new uploads. STEW uses a simulated first/last epoch split; real use is baseline+task file upload.

```bash
# STEW demo split (middle epochs scored)
curl -X POST "http://127.0.0.1:8000/api/calibrate/stew/0?n_baseline=10&n_task=10"
```

Demo upload files (local): `data/exports/demo_upload_S00_raw.fif` (generate via `src.predict.export_stew_subject_fif`).

---

## Key results (logged)

| Evaluation | Acc | Notes |
|------------|-----|--------|
| STEW primary LOSO (`rating ≥ 7`) | **0.356** | Below majority 0.556; null under frozen protocol |
| Newdataset AC1 Control vs Stress | **0.576** | Majority ~0.50; denser labels |

Full tables and limitations: [`docs/RESULTS.md`](docs/RESULTS.md), [`docs/RESULTS_v2.md`](docs/RESULTS_v2.md).

Honesty endpoints: `GET /api/methods`, `?model_mode=loso_held_out`, `GET /api/live/replay/{id}`.

---

## Public demo (single URL)

### Temporary (this Mac + Cloudflare quick tunnel)

```bash
cd frontend && npm run build && cd ..
source .venv/bin/activate
uvicorn src.api_server:app --host 127.0.0.1 --port 8000
# other terminal:
cloudflared tunnel --url http://127.0.0.1:8000
```

### Permanent (Docker → Render)

`runtime_assets/` ships STEW cache + model + `.mat` for the live demo. Deploy with the included [`render.yaml`](render.yaml) / [`Dockerfile`](Dockerfile):

1. Push this repo to GitHub.
2. [Render](https://render.com) → **New** → **Blueprint** → select the repo (or Web Service + Docker).
3. Free web service URL looks like `https://brainmed-eeg-workload.onrender.com` (sleeps when idle; first request may take ~30–60s).

Local Docker smoke test:

```bash
docker build -t brainmed .
docker run --rm -p 8000:8000 brainmed
```

Same-origin `/api/*` + SPA from `frontend/dist`.

---

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/PROJECT.md`](docs/PROJECT.md) | Frozen STEW protocol |
| [`docs/RESULTS.md`](docs/RESULTS.md) | Primary LOSO write-up |
| [`docs/RESULTS_v2.md`](docs/RESULTS_v2.md) | Multi-threshold + Control/Stress |
| [`docs/PROTOCOL_V2.md`](docs/PROTOCOL_V2.md) | v2 research track |
| [`docs/PROJECT_REPORT.md`](docs/PROJECT_REPORT.md) | Full project report |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Phase checklist |
| [`docs/NEWDATASET_SUMMARY.md`](docs/NEWDATASET_SUMMARY.md) | Second dataset inventory |
| [`docs/MONTAGE_AND_UNITS.md`](docs/MONTAGE_AND_UNITS.md) | Montage assumption + units |

---

## Design principles

1. **Split by subject** — never random-split epochs.  
2. **Frozen protocol** — no LOSO retuning after seeing numbers.  
3. **Honest UI** — DEMO lifestyle labels; null LOSO stated in-product.  
4. **Raw data not in git** — place STEW / newdataset under `data/raw/` locally.

---

## License / data

Code is provided for portfolio and research reproduction. Datasets (STEW, Atiwiwat & Hemakom EEG-ECG) remain under their original licenses — download separately into `data/raw/`.
