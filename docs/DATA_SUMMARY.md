# STEW data summary

Source directory: `/Users/abc/Downloads/eeg-workload/data/raw/stew`

Metadata only (no EEG sample values).

## PDF timing check (Kaggle STEW summary)

- sfreq (PDF): 128.0 Hz
- channels (PDF): 14
- samples/subject (PDF): 19200
- assert `19200/128 = 150 s` → **passed** (150 s)
- channel names: not confirmed in PDF/mats; keep generic `EEG001`… (no montage yet)

## `dataset.mat`

- loader: `scipy.io.loadmat`

### variable `dataset`
- shape: `(14, 19200, 45)`
- dtype: `float64`
- NaNs: any NaN=False
- axis order:
  - axis 0: size 14 → channels
  - axis 1: size 19200 → time
  - axis 2: size 45 → subjects
- orientation: matches expected (14, 19200, 45) = channels × time × subjects (not transposed).
- time axis length 19200 matches PDF samples/subject
- channel count 14 matches PDF

## `class_012.mat`

- loader: `scipy.io.loadmat`

### variable `class_012`
- shape: `(45, 1)`
- dtype: `uint8`
- NaNs: any NaN=False
- class / value counts: {0: 13, 1: 18, 2: 14}

## `rating.mat`

- loader: `scipy.io.loadmat`

### variable `rating`
- shape: `(45, 1)`
- dtype: `uint8`
- NaNs: any NaN=False
- class / value counts: {4: 3, 5: 10, 6: 7, 7: 11, 8: 11, 9: 3}
- binary preview (rating>=7 → 1): {0: 20, 1: 25} (n_pos=25, n_neg=20)

## `three_class_one_hot.mat`

- loader: `scipy.io.loadmat`

### variable `three_class_one_hot`
- shape: `(45, 3)`
- dtype: `uint8`
- NaNs: any NaN=False
- class counts (argmax): {0: 13, 1: 18, 2: 14}
