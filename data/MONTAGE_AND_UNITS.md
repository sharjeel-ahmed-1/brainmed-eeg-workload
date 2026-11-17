# Montage & units (STEW)

## Units

- STEW `.mat` values have **no documented physical scale** in-repo.
- Training / scoring use **relative band power** (and θ/α ratios) — scale-free within epoch.
- Do not convert to volts unless a vendor/paper scale is confirmed.

## Channel montage

- Names are **not** in `dataset.mat`.
- Loader uses generic `EEG001`…`EEG014` for Raw.
- `config.EMOTIV_CH_NAMES` + `FRONTAL_IDX` are a **locked assumption** for Variant A frontal features and descriptive topo maps only (`MONTAGE_ASSUMED=True`).
- Primary LOSO features are **per-channel-index** band powers — they do not depend on 10–20 names.
- Maps / interpretation figures must be read with the watermark: assumed montage + null LOSO.

## Newdataset

- Channels are **named in xlsx sheets** (Fp1…P4) — see `NEWDATASET_SUMMARY.md`.
- Sampling rate still **unknown** until set in `config_ext.NEWDATASET_SFREQ`.
