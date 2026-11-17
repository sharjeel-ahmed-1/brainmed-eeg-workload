from pathlib import Path

ROOT = Path(__file__).parent
RAW_DIR = ROOT / "data" / "raw"
STEW_DIR = RAW_DIR / "stew"
DATASET_MAT = STEW_DIR / "dataset.mat"
CLASS012_MAT = STEW_DIR / "class_012.mat"
RATING_MAT = STEW_DIR / "rating.mat"
# Primary MVP target is 2-class (rating >= 7); 3-class remains secondary.
LABEL_MAT = RATING_MAT
LABELS_CSV = ROOT / "data" / "labels.csv"  # optional mirror; train loads .mat directly
MODEL_PATH = ROOT / "models" / "workload_model.joblib"

# From data/DATA_SUMMARY.md (dataset.mat) + Kaggle STEW PDF
N_CHANNELS = 14
N_TIMES = 19200
N_SUBJECTS = 45

# From Kaggle STEW PDF: 128 Hz, 14 ch, 19200 samples/subject (150 s). Not stored in .mat.
SFREQ = 128.0

SEED = 42
RESAMPLE_HZ = 128
BANDPASS = (1.0, 40.0)
NOTCH_HZ = 50.0
EPOCH_SEC = 4.0
BANDS = {"delta": (1, 4), "theta": (4, 8), "alpha": (8, 13), "beta": (13, 30), "gamma": (30, 40)}

# Binary threshold for PRIMARY target
RATING_HIGH_THRESHOLD = 7

# Epoch rejection on FILTERED epochs (post 1–40 Hz + notch + avg-ref), not raw.
# Drop if max_ch_ptp > median(ptp) + z * 1.4826 * MAD(ptp) within subject.
# z=5: chosen as a conventional robust ≈5σ MAD rule when the reject code was
# written — BEFORE any LOSO that used amplitude rejection (not tuned on acc).
# Units: .mat numeric scale (µV-like); no conversion to volts.
EPOCH_REJECT_Z = 5.0

# Flat/zero epoch reject (data-quality only; NOT tuned on accuracy).
# Applied on RAW (pre-filter) fixed-length epoch segments, index-aligned to filtered epochs.
# Drop epoch if any channel has >= EPOCH_FLAT_RUN_MIN identical consecutive samples
# OR any exact-zero sample in that epoch.
EPOCH_FLAT_RUN_MIN = 128  # 1.0 s at 128 Hz

# Sanity checks
N_PERMUTATIONS = 200
# Multiplicative gain on alpha-band component: data += (gain-1)*alpha
# gain=8.0 → 8× alpha (+700%). Used for the primary positive-control check.
POSCTRL_ALPHA_GAIN = 8.0
# Sensitivity sweep: +10%, +25%, +50%, +100% → gains 1.1, 1.25, 1.5, 2.0
POSCTRL_SENSITIVITY_GAINS = (1.1, 1.25, 1.5, 2.0)
FEATURE_CACHE_DIR = ROOT / "data" / "cache"
# Path resolved at runtime via protocol_hash() — see src/train.py
FEATURE_CACHE = FEATURE_CACHE_DIR / "epoch_features.npz"

# PRE-SPECIFIED Emotiv-14 order for STEW regional features (not in .mat; assumption for variant A only)
# AF3 F7 F3 FC5 T7 P7 O1 O2 P8 T8 FC6 F4 F8 AF4
EMOTIV_CH_NAMES = [
    "AF3", "F7", "F3", "FC5", "T7", "P7", "O1",
    "O2", "P8", "T8", "FC6", "F4", "F8", "AF4",
]
FRONTAL_IDX = (0, 1, 2, 3, 10, 11, 12, 13)  # AF3 F7 F3 FC5 FC6 F4 F8 AF4
