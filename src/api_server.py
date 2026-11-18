"""
FastAPI adapter for BrainMed+ dashboard.
Wraps existing predict / report_viz — no duplicate ML.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import numpy as np
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import config
import config_ext
from src.calibrate import (
    CALIB_MSG,
    calibrate_from_files,
    calibrate_stew_subject,
    load_calibrator,
    score_with_calibrator,
)
from src.load import load_stew_labels, load_subject_raw
from src.predict import (
    load_model,
    predict_stew_subject,
    predict_stew_subject_loso,
    predict_upload,
    save_primary_model,
)
from src.report_viz import mean_band_profile, split_features

LOSO_NULL_MSG = (
    "PRIMARY LOSO was null (acc 0.356 < majority 0.556; perm p≈0.98). "
    "Pipeline score is not a clinical / LOSO-validated product claim."
)
DEMO_MODEL_MSG = (
    "Model mode demo_all_subject: RF fit on all 45 STEW subjects — not held-out."
)
HELD_OUT_MSG = (
    "Model mode loso_held_out: RF fit on N−1 subjects; scored subject was left out of training."
)
CALIB_MODEL_MSG = CALIB_MSG

BAND_META = {
    "delta": {"label": "Drowsiness", "symbol": "δ", "range_hz": (0.5, 4.0), "center_hz": 2.25},
    "theta": {"label": "Sleep", "symbol": "θ", "range_hz": (4.0, 8.0), "center_hz": 6.0},
    "alpha": {"label": "Reflective", "symbol": "α", "range_hz": (8.0, 13.0), "center_hz": 10.5},
    "beta": {"label": "Active mind", "symbol": "β", "range_hz": (13.0, 30.0), "center_hz": 21.5},
    "gamma": {"label": "Concentration", "symbol": "γ", "range_hz": (30.0, 40.0), "center_hz": 35.0},
}

app = FastAPI(title="BrainMed+ EEG API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"https://.*\.(trycloudflare\.com|onrender\.com|up\.railway\.app|railway\.app)"
        r"|http://(localhost|127\.0\.0\.1)(:\d+)?"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIST = config.ROOT / "frontend" / "dist"

_model = None


def get_model():
    global _model
    if _model is None:
        if not config.MODEL_PATH.exists():
            save_primary_model()
        _model = load_model()
    return _model


def _epoch_band_series(X: np.ndarray) -> Dict[str, List[float]]:
    band, _ = split_features(X)
    # mean across channels per epoch → (n_epochs, n_bands)
    ep = band.mean(axis=1)
    names = list(config.BANDS.keys())
    return {names[i]: [float(v) for v in ep[:, i]] for i in range(len(names))}


def _band_payload(profile: Dict[str, float], series: Dict[str, List[float]]) -> List[Dict[str, Any]]:
    out = []
    for name, meta in BAND_META.items():
        rel = float(profile.get(name, 0.0))
        # Display Hz = band center scaled by relative power (proxy, not hardware Hz)
        hz_proxy = float(meta["center_hz"] * (0.55 + 0.9 * rel))
        out.append(
            {
                "id": name,
                "name": name,
                "label": meta["label"],
                "symbol": meta["symbol"],
                "range_hz": list(meta["range_hz"]),
                "relative_power": rel,
                "hz_proxy": round(hz_proxy, 2),
                "hz_note": "relative-power proxy (not a live hardware Hz meter)",
                "series": series.get(name, []),
            }
        )
    return out


def _report_from_predict(result: Dict[str, Any]) -> Dict[str, Any]:
    X = result["X"]
    profile = mean_band_profile(X)
    series = _epoch_band_series(X)
    classes = [int(c) for c in result["classes"]]
    epoch_proba = np.asarray(result["epoch_proba"])
    if 1 in classes:
        p_high_series = epoch_proba[:, classes.index(1)].tolist()
    else:
        p_high_series = epoch_proba.max(axis=1).tolist()
    return {
        "source": result.get("source"),
        "subject_idx": result.get("subject_idx"),
        "file_name": result.get("file_name"),
        "y_true": result.get("y_true"),
        "pred": int(result["pred"]),
        "pred_label": "HIGH" if int(result["pred"]) == 1 else "LOW",
        "p_high": float(result["p_high"]),
        "n_epochs": int(result["n_epochs"]),
        "mean_proba": {
            int(c): float(p) for c, p in zip(result["classes"], result["mean_proba"])
        },
        "p_high_series": [float(x) for x in p_high_series],
        "bands": _band_payload(profile, series),
        "band_profile": profile,
        "model_type": result.get("model_type", "demo_all_subject"),
        "train_subjects": result.get("train_subjects"),
        "honest": {
            "loso_null": True,
            "loso_acc": 0.356,
            "majority_acc": 0.556,
            "message": LOSO_NULL_MSG
            + " "
            + (
                CALIB_MODEL_MSG
                if result.get("model_type") == "within_subject_calib"
                else HELD_OUT_MSG
                if result.get("model_type") == "loso_held_out"
                else DEMO_MODEL_MSG
            ),
            "hz_proxy_note": "Band Hz values are relative-power proxies, not live hardware meters.",
            "units_note": "STEW .mat units undocumented; features use relative band power only.",
        },
        "calib_id": result.get("calib_id"),
        "calib": result.get("calib"),
    }


@app.on_event("startup")
def _startup():
    try:
        get_model()
    except Exception as e:
        # Allow health to report; first request may retry
        print(f"startup model load: {e}")


@app.get("/api/health")
def health():
    ok = config.MODEL_PATH.exists() or True
    return {
        "ok": True,
        "model_exists": config.MODEL_PATH.exists(),
        "n_subjects": config.N_SUBJECTS,
        "n_channels": config.N_CHANNELS,
        "seed": config.SEED,
    }


@app.get("/api/subjects")
def list_subjects():
    y = load_stew_labels("2class")
    return {
        "source": "stew",
        "subjects": [
            {"id": i, "true_label": int(y[i]), "true_label_name": "HIGH" if int(y[i]) == 1 else "LOW"}
            for i in range(config.N_SUBJECTS)
        ],
    }


ModelMode = Literal["demo_all_subject", "loso_held_out"]


@app.get("/api/subjects/{subject_id}/report")
def subject_report(
    subject_id: int,
    model_mode: ModelMode = Query("demo_all_subject"),
):
    if subject_id < 0 or subject_id >= config.N_SUBJECTS:
        raise HTTPException(404, f"subject_id out of range 0..{config.N_SUBJECTS - 1}")
    try:
        if model_mode == "loso_held_out":
            result = predict_stew_subject_loso(subject_id)
        else:
            result = predict_stew_subject(subject_id, get_model())
        return _report_from_predict(result)
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}") from e


@app.get("/api/methods")
def methods_banner():
    """Persistent honesty payload for Overview / Reports."""
    return {
        "loso_null": True,
        "loso_acc": 0.356,
        "majority_acc": 0.556,
        "perm_p_acc": 0.980,
        "message": LOSO_NULL_MSG,
        "calibration": CALIB_MSG,
        "montage": {
            "assumed": config_ext.MONTAGE_ASSUMED,
            "names": list(config.EMOTIV_CH_NAMES),
            "note": config_ext.MONTAGE_NOTE,
        },
        "units": "arbitrary / undocumented in STEW .mat; relative power only",
        "lifestyle": "DEMO — not STEW diary labels",
    }


@app.post("/api/calibrate/stew/{subject_id}")
def calibrate_stew(
    subject_id: int,
    n_baseline: int = Query(10, ge=2, le=30),
    n_task: int = Query(10, ge=2, le=30),
):
    """
    Within-subject calib on one STEW subject: first epochs=low, last=high;
    score middle held-out epochs when available.
    """
    if subject_id < 0 or subject_id >= config.N_SUBJECTS:
        raise HTTPException(404, f"subject_id out of range 0..{config.N_SUBJECTS - 1}")
    try:
        result = calibrate_stew_subject(subject_id, n_baseline=n_baseline, n_task=n_task)
        return _report_from_predict(result)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}") from e


@app.post("/api/calibrate/upload")
async def calibrate_upload(
    baseline: UploadFile = File(...),
    task: UploadFile = File(...),
):
    """Fit calibrator on baseline (low) + task (high) uploads; score task file."""
    allowed = {".edf", ".fif", ".bdf", ".set"}
    b_suf = Path(baseline.filename or "baseline.fif").suffix.lower()
    t_suf = Path(task.filename or "task.fif").suffix.lower()
    if b_suf not in allowed or t_suf not in allowed:
        raise HTTPException(400, "Supported: .edf .fif .bdf .set for both files")
    try:
        with tempfile.NamedTemporaryFile(suffix=b_suf, delete=False) as tb:
            tb.write(await baseline.read())
            b_path = Path(tb.name)
        with tempfile.NamedTemporaryFile(suffix=t_suf, delete=False) as tt:
            tt.write(await task.read())
            t_path = Path(tt.name)
        result = calibrate_from_files(b_path, t_path)
        result["file_name"] = task.filename
        if result.get("calib"):
            result["calib"]["baseline_file"] = baseline.filename
            result["calib"]["task_file"] = task.filename
        return _report_from_predict(result)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(400, f"{type(e).__name__}: {e}") from e


@app.get("/api/calibrate/{calib_id}")
def get_calibrator(calib_id: str):
    try:
        _, meta = load_calibrator(calib_id)
        return {"calib_id": calib_id, "meta": meta}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@app.post("/api/calibrate/{calib_id}/score")
async def score_calibrated(calib_id: str, file: UploadFile = File(...)):
    """Score a new upload with a saved within-subject calibrator."""
    suffix = Path(file.filename or "upload.fif").suffix.lower()
    if suffix not in {".edf", ".fif", ".bdf", ".set"}:
        raise HTTPException(400, "Supported: .edf .fif .bdf .set")
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(await file.read())
            path = Path(tmp.name)
        result = score_with_calibrator(calib_id, path)
        result["file_name"] = file.filename
        return _report_from_predict(result)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:
        raise HTTPException(400, f"{type(e).__name__}: {e}") from e


@app.get("/api/live/replay/{subject_id}")
def live_replay(
    subject_id: int,
    window_sec: float = Query(4.0, ge=1.0, le=30.0),
    hop_sec: float = Query(2.0, ge=0.5, le=15.0),
    max_windows: int = Query(40, ge=1, le=200),
):
    """
    Fake LIVE path: replay STEW subject as successive windows (no headset).
    """
    if subject_id < 0 or subject_id >= config.N_SUBJECTS:
        raise HTTPException(404, f"subject_id out of range 0..{config.N_SUBJECTS - 1}")
    try:
        import mne

        from src.features import band_power_features
        from src.predict import aggregate_subject

        raw = load_subject_raw(subject_id).copy()
        raw.filter(config.BANDPASS[0], config.BANDPASS[1], verbose="ERROR")
        if config.NOTCH_HZ < raw.info["sfreq"] / 2:
            raw.notch_filter(config.NOTCH_HZ, verbose="ERROR")
        raw.set_eeg_reference("average", verbose="ERROR")
        sfreq = float(raw.info["sfreq"])
        data = raw.get_data()
        n_times = data.shape[1]
        win = int(window_sec * sfreq)
        hop = max(1, int(hop_sec * sfreq))
        model = get_model()
        windows = []
        t0 = 0
        wi = 0
        while t0 + win <= n_times and wi < max_windows:
            seg = data[:, t0 : t0 + win]
            epochs = mne.EpochsArray(seg[np.newaxis, ...], raw.info, tmin=0.0, verbose="ERROR")
            X = band_power_features(epochs)
            profile = mean_band_profile(X)
            score = aggregate_subject(model, X)
            windows.append(
                {
                    "i": wi,
                    "t_start_sec": round(t0 / sfreq, 3),
                    "t_end_sec": round((t0 + win) / sfreq, 3),
                    "p_high": float(score["p_high"]),
                    "pred_label": "HIGH" if int(score["pred"]) == 1 else "LOW",
                    "band_profile": profile,
                }
            )
            t0 += hop
            wi += 1
        return {
            "source": "live_replay",
            "live": True,
            "simulated": True,
            "subject_idx": subject_id,
            "window_sec": window_sec,
            "hop_sec": hop_sec,
            "n_windows": len(windows),
            "windows": windows,
            "honest": {
                "message": "LIVE = STEW file replay, not a headset stream. " + LOSO_NULL_MSG,
            },
        }
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}") from e


@app.post("/api/upload")
async def upload_eeg(file: UploadFile = File(...)):
    suffix = Path(file.filename or "upload.fif").suffix.lower()
    if suffix not in {".edf", ".fif", ".bdf", ".set"}:
        raise HTTPException(400, "Supported: .edf .fif .bdf .set")
    try:
        raw = await file.read()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw)
            path = Path(tmp.name)
        result = predict_upload(path, get_model())
        result["file_name"] = file.filename
        return _report_from_predict(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"{type(e).__name__}: {e}") from e


RangeName = Literal["today", "week", "month"]


@app.get("/api/demo/dashboard")
def demo_dashboard(
    range_name: RangeName = Query("today", alias="range"),
    subject_id: Optional[int] = None,
):
    """
    Lifestyle / time-spend / history widgets. STEW has no diary — always source=demo.
    Optional subject_id shapes waveforms using real band means.
    """
    return _demo_dashboard_body(range_name, subject_id)


def _demo_dashboard_body(range_name: RangeName, subject_id: Optional[int] = None) -> Dict[str, Any]:
    rng = np.random.default_rng(config.SEED + {"today": 0, "week": 1, "month": 2}[range_name])
    profile = {b: 0.2 for b in config.BANDS}
    if subject_id is not None:
        try:
            result = predict_stew_subject(subject_id, get_model())
            profile = mean_band_profile(result["X"])
        except Exception:
            pass

    categories = [
        ("Physical Activity", "#e85d4c"),
        ("Work", "#f0a05a"),
        ("Leisure", "#e8d44c"),
        ("Meal", "#5ecf7a"),
        ("Communication", "#36d9f5"),
        ("Sleep", "#8275ff"),
    ]
    base = {
        "today": [1.2, 4.5, 2.0, 1.0, 1.5, 7.0],
        "week": [5.0, 28.0, 10.0, 7.0, 8.0, 49.0],
        "month": [20.0, 110.0, 40.0, 30.0, 35.0, 200.0],
    }[range_name]
    jitter = rng.normal(0, 0.08, size=len(base))
    time_spend = [
        {
            "category": name,
            "hours": round(max(0.2, float(h * (1 + j))), 2),
            "color": color,
        }
        for (name, color), h, j in zip(categories, base, jitter)
    ]

    n_points = {"today": 24, "week": 7, "month": 30}[range_name]
    gamma = float(profile.get("gamma", 0.2))
    conc = []
    for i in range(n_points):
        v = 0.35 + 0.45 * gamma + 0.15 * np.sin(i / 3.0) + float(rng.normal(0, 0.04))
        conc.append(round(float(np.clip(v, 0.05, 0.98)), 3))

    avg_conc = float(np.mean(conc))
    target = 0.33
    on_target = round(100.0 * min(1.0, avg_conc / max(target, 1e-6)) * 0.587, 1)

    hours = list(range(n_points)) if range_name == "today" else list(range(1, n_points + 1))

    return {
        "source": "demo",
        "range": range_name,
        "disclaimer": (
            "DEMO MODE: Time Spend, targets, and lifestyle history are simulated. "
            "They are not STEW labels or live physiological measurements."
        ),
        "time_spend": time_spend,
        "concentration_series": [{"t": hours[i], "value": conc[i]} for i in range(n_points)],
        "general": {
            "avg_label": "avg concentration (demo)",
            "avg_value": round(avg_conc, 3),
            "avg_hours_per_day": round(6.0 + 4.0 * gamma, 1),
            "progress_pct": round(100 * avg_conc, 1),
            "target_pct": round(100 * target, 1),
            "highest_day": round(float(max(conc)), 3),
        },
        "target": {
            "on_target_pct": on_target,
            "target_pct": round(100 * target, 1),
        },
        "band_profile_used": profile,
    }


# ---- Static BrainMed+ UI (production / tunnel): build with `npm run build` in frontend/
if FRONTEND_DIST.is_dir() and (FRONTEND_DIST / "index.html").exists():
    assets = FRONTEND_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/")
    def spa_root():
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if full_path.startswith("api/") or full_path in {"docs", "openapi.json", "redoc"}:
            raise HTTPException(404, "Not found")
        candidate = FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
