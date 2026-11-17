"""
Extensions that must NOT live in config.py (STEW protocol_hash includes config.py bytes).

Newdataset paths, montage honesty notes, units disclaimer.
"""
from __future__ import annotations

from typing import Optional

import config

# Second dataset (Control vs Stress xlsx). Nested folder from user copy.
# Dataset: "An EEG-ECG Dataset of Stress and Mental Workload during Cognitive Tasks"
# (Mendeley Data s87jk3p5ws / DataMed). EEG 2000 Hz, ECG 1000 Hz; EO/AC ≈ 5 min blocks.
NEWDATASET_DIR = config.RAW_DIR / "newdataset" / "newdataset"
NEWDATASET_CH_NAMES = ["Fp1", "Fp2", "F3", "F4", "T3", "T4", "P3", "P4"]
NEWDATASET_SFREQ: Optional[float] = 2000.0
NEWDATASET_ECG_SFREQ = 1000.0
# Analysis rate after cache (anti-alias resample from NEWDATASET_SFREQ)
NEWDATASET_RESAMPLE_HZ = 250.0
NEWDATASET_CACHE_DIR = config.ROOT / "data" / "cache" / "newdataset"
NEWDATASET_CITATION = (
    "Atiwiwat & Hemakom, An EEG-ECG Dataset of Stress and Mental Workload "
    "during Cognitive Tasks (Mendeley Data s87jk3p5ws). EEG sfreq=2000 Hz."
)

MONTAGE_ASSUMED = True
MONTAGE_NOTE = (
    "STEW channel names absent from .mat; Emotiv-14 order in config.EMOTIV_CH_NAMES is an "
    "assumption for Variant A / topo maps only. Primary 84-D features are channel-index "
    "band powers and do not require names. Units in .mat are undocumented — use relative power. "
    "See data/MONTAGE_AND_UNITS.md."
)
