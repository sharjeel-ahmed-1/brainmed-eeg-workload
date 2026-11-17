"""
Neuroadaptive UI demo — upload / STEW EEG → visual report + adaptive workspace.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

import config
from src.load import load_stew_labels
from src.predict import (
    export_stew_subject_fif,
    load_model,
    predict_stew_subject,
    predict_upload,
    save_primary_model,
)
from src.report_viz import build_report_images, mean_band_profile, plain_language_report

st.set_page_config(page_title="EEG Workload Demo", layout="wide")

st.title("EEG cognitive workload — adaptive demo")

st.warning(
    "**Honest limits:** No live headset / not medical advice. "
    f"Frozen PRIMARY LOSO was **null** (acc 0.356 < majority 0.556; perm p≈0.98). "
    "Demo model fit on **all subjects**. "
    f"Upload: **{config.N_CHANNELS} EEG channels**. See `RESULTS.md`."
)

# ---- Helpful options (sidebar) ----
st.sidebar.header("User options")
show_tips = st.sidebar.checkbox("Show tips & plain-language report", value=True)
show_maps = st.sidebar.checkbox("Show channel map + heatmap", value=True)
show_project_figs = st.sidebar.checkbox("Show project interpretation figures", value=False)
map_band = st.sidebar.selectbox(
    "Channel map metric",
    ("theta", "alpha", "beta", "gamma", "delta", "theta_alpha"),
    index=0,
)
lang = st.sidebar.radio("Tips language", ("English", "Roman Urdu"), index=0)
st.sidebar.caption(f"Model: `{config.MODEL_PATH.name}` · seed={config.SEED}")

if not config.MODEL_PATH.exists():
    with st.spinner("Saving demo model…"):
        try:
            save_primary_model()
        except Exception as e:
            st.error(f"Could not save model: {e}")
            st.stop()

model = load_model()
y_all = load_stew_labels("2class")

# ---- 1) Input ----
st.subheader("1) EEG input")
tab_up, tab_stew = st.tabs(["Upload EEG report / recording", "STEW sample subject"])

up = None
sid = 0
with tab_up:
    st.caption(
        f"`.edf` `.fif` `.bdf` `.set` · **{config.N_CHANNELS} channels** · "
        "file → preprocess → score → **images explain the output**."
    )
    up = st.file_uploader("Upload EEG file", type=["edf", "fif", "bdf", "set"])
    with st.expander("No file? Download STEW sample to test upload"):
        sample_sid = st.selectbox(
            "Export subject",
            options=list(range(config.N_SUBJECTS)),
            format_func=lambda i: f"S{i:02d} (label={int(y_all[i])})",
            key="export_sid",
        )
        if st.button("Prepare sample .fif"):
            try:
                path = export_stew_subject_fif(int(sample_sid))
                st.session_state["sample_fif"] = str(path)
            except Exception as e:
                st.error(str(e))
        sample_path = st.session_state.get("sample_fif")
        if sample_path and Path(sample_path).exists():
            st.download_button(
                "Download sample EEG (.fif)",
                data=Path(sample_path).read_bytes(),
                file_name=Path(sample_path).name,
                mime="application/octet-stream",
            )

with tab_stew:
    sid = st.selectbox(
        "Subject",
        options=list(range(config.N_SUBJECTS)),
        format_func=lambda i: f"S{i:02d} (true label={int(y_all[i])})",
        key="stew_sid",
    )
    st.caption("Used when no file is uploaded.")

result = None
error = None
if up is not None:
    try:
        with st.spinner("Reading EEG + building report…"):
            with tempfile.NamedTemporaryFile(suffix=Path(up.name).suffix, delete=False) as tmp:
                tmp.write(up.getbuffer())
                tmp_path = Path(tmp.name)
            result = predict_upload(tmp_path, model)
            result["file_name"] = up.name
            st.session_state["ui_mode"] = "auto"
    except Exception as e:
        error = str(e)
else:
    try:
        result = predict_stew_subject(int(sid), model)
    except Exception as e:
        error = str(e)

if error:
    st.error(error)
    st.stop()
if result is None:
    st.stop()

pred = int(result["pred"])
p_high = float(result["p_high"])
model_txt = "HIGH" if pred == 1 else "LOW"
X = result["X"]
band_profile = mean_band_profile(X)

# ---- 2) Visual OUTPUT REPORT (images) ----
st.markdown("---")
st.subheader("2) Output report (images)")
st.markdown("Yahan **clear dikhaya** hai ke model ne kya decide kiya — pehle badi image, phir bands / timeline.")

with st.spinner("Rendering report images…"):
    imgs = build_report_images(
        X=X,
        pred=pred,
        p_high=p_high,
        epoch_proba=result["epoch_proba"],
        classes=result["classes"],
        n_epochs=int(result["n_epochs"]),
        source=str(result.get("source", "")),
        y_true=result.get("y_true"),
        map_band=map_band,
    )

st.image(imgs["summary"], caption="OUTPUT — HIGH/LOW decision + confidence bar", use_container_width=True)

cA, cB = st.columns(2)
with cA:
    st.image(imgs["bands"], caption="Band power snapshot (δ θ α β γ)", use_container_width=True)
with cB:
    st.image(imgs["timeline"], caption="Per-epoch P(high) timeline", use_container_width=True)

if show_maps:
    cC, cD = st.columns(2)
    with cC:
        st.image(imgs["heatmap"], caption="Channel × band heatmap", use_container_width=True)
    with cD:
        st.image(imgs["chan_map"], caption=f"Head map — {map_band}", use_container_width=True)

# Downloads
d1, d2, d3 = st.columns(3)
d1.download_button("Download summary PNG", imgs["summary"], "eeg_output_summary.png", "image/png")
d2.download_button("Download bands PNG", imgs["bands"], "eeg_bands.png", "image/png")
d3.download_button("Download timeline PNG", imgs["timeline"], "eeg_timeline.png", "image/png")

if show_tips:
    st.markdown("#### Plain-language explanation")
    bullets = plain_language_report(pred, p_high, band_profile, int(result["n_epochs"]))
    if lang == "Roman Urdu":
        ur = [
            f"**Output:** model kehta hai workload **{'ZYADA (HIGH)' if pred == 1 else 'KAM (LOW)'}** hai "
            f"(P(high)={p_high:.0%}, {result['n_epochs']} epochs).",
            "**UI:** HIGH pe screen simple; LOW pe full detail." if True else "",
            f"**EEG snapshot:** sab se strong average band **{max(band_profile, key=band_profile.get)}** hai.",
            "**Yaad rakho:** yeh demo report hai — medical diagnosis nahi; STEW LOSO null tha.",
        ]
        for b in ur:
            st.markdown(f"- {b}")
    else:
        for b in bullets:
            st.markdown(f"- {b}")

if result.get("source") == "upload":
    st.caption(f"Source: upload `{result.get('file_name')}`")
elif result.get("y_true") is not None:
    match = "match" if int(result["y_true"]) == pred else "mismatch"
    st.caption(
        f"S{int(result['subject_idx']):02d} · true={int(result['y_true'])} · "
        f"pred={pred} ({match}) · {result['source']}"
    )

# ---- 3) Adaptive workspace ----
st.markdown("---")
st.subheader("3) Adaptive workspace (UI manage)")
st.caption("AUTO = EEG ke mutabiq layout. LOW/HIGH = sirf demo override.")
b1, b2, b3 = st.columns(3)
if b1.button("LOW UI", use_container_width=True):
    st.session_state["ui_mode"] = "low"
    st.rerun()
if b2.button("HIGH UI", use_container_width=True, type="primary"):
    st.session_state["ui_mode"] = "high"
    st.rerun()
if b3.button("AUTO from EEG", use_container_width=True):
    st.session_state["ui_mode"] = "auto"
    st.rerun()

ui_mode = st.session_state.get("ui_mode", "auto")
if ui_mode == "high":
    high = True
    ui_note = "forced HIGH"
elif ui_mode == "low":
    high = False
    ui_note = "forced LOW"
else:
    high = pred == 1
    ui_note = "AUTO from EEG"

if high:
    st.markdown(
        f"""
        <div style="padding:1.1rem 1.3rem;background:#1a2332;color:#f5f5f0;
                    border-left:6px solid #c45c26;margin:0.5rem 0 1rem 0;">
          <div style="font-size:1.45rem;font-weight:700;">Focus mode (HIGH)</div>
          <div style="opacity:0.85;">P(high)={p_high:.2f} · {ui_note} · kam widgets</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info(
        "Suggested actions: 1) one task only  2) short break  3) keep AUTO on. "
        "Report images upar reh gayi hain taake output clear rahe."
    )
else:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Decision", model_txt)
    m2.metric("P(high)", f"{p_high:.0%}")
    m3.metric("Epochs", result["n_epochs"])
    m4.metric("Top band", max(band_profile, key=band_profile.get))
    st.success("Explore mode (LOW): full tools available below.")
    with st.expander("Band numbers", expanded=False):
        st.json({k: round(v, 4) for k, v in band_profile.items()})
    with st.expander("Class probabilities", expanded=False):
        st.json(
            {
                int(c): round(float(p), 4)
                for c, p in zip(result["classes"], result["mean_proba"])
            }
        )

# ---- 4) Extra helpful features ----
st.markdown("---")
st.subheader("4) Extra helpful features")
f1, f2, f3 = st.columns(3)
with f1:
    st.markdown("**Quick guide**")
    st.markdown(
        """
        1. Upload / pick subject  
        2. Read **Output report** images  
        3. Let **AUTO** manage UI  
        4. Download PNGs for portfolio/slides  
        """
    )
with f2:
    st.markdown("**What HIGH vs LOW means here**")
    st.markdown(
        """
        - **HIGH** → simplify screen (less clutter)  
        - **LOW** → show maps, tabs, numbers  
        - Not a clinical diagnosis  
        """
    )
with f3:
    st.markdown("**Data checklist**")
    st.markdown(
        f"""
        - {config.N_CHANNELS} EEG channels  
        - Continuous recording (seconds+)  
        - Formats: edf / fif / bdf / set  
        """
    )

if show_project_figs:
    st.markdown("#### Project interpretation figures (training-time)")
    fig_dir = config.ROOT / "figures"
    for name in (
        "rf_top_features.png",
        "rf_band_channel_heat.png",
        "rf_channel_importance_map.png",
        "variant_a_lr_coefs.png",
    ):
        p = fig_dir / name
        if p.exists():
            st.image(str(p), caption=name, use_container_width=True)
