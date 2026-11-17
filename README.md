# BrainMed+ / STEW EEG workload

Premium **BrainMed+** React dashboard + Python STEW ML pipeline (subject-wise LOSO research prototype).

## Primary UI (BrainMed+)

```bash
# Terminal 1 — API (wraps existing src/predict)
cd /Users/abc/Downloads/eeg-workload
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.api_server:app --reload --port 8000

# Terminal 2 — dashboard
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173

- **Overview** — 3D brain, band waves, frequency cards, DEMO lifestyle widgets
- **Reports** — upload EEG / score STEW subject (real pipeline)
- **My History** — local scored sessions

Lifestyle charts are labeled **DEMO** (STEW has no activity diary). Band Hz values are **relative-power proxies**, not live hardware meters.

## Legacy Streamlit demo

```bash
source .venv/bin/activate
streamlit run app.py
```

## Research docs

| Doc | What |
|-----|------|
| `RESULTS.md` | Frozen LOSO numbers + limitations |
| `RESULTS_v2.md` | v2 tracks (multi-threshold / newdataset) — does not overwrite v1 |
| `PROTOCOL_V2.md` | Nested CV + Control/Stress plan |
| `data/NEWDATASET_SUMMARY.md` | Second dataset inventory |
| `data/MONTAGE_AND_UNITS.md` | Assumed Emotiv montage + relative units |
| `PROJECT.md` | Protocol freeze |
| `ROADMAP.md` | Phase checklist |

**Primary STEW LOSO:** acc 0.356 (majority 0.556); perm p≈0.98. Posctrl α×8 passed.

**Newdataset (Control vs Stress, AC1):** LOSO recording acc **0.576** (majority ~0.50). Full condition table: `RESULTS_v2.md`.

API honesty: `GET /api/methods`, `?model_mode=loso_held_out`, `GET /api/live/replay/{id}`.
