# Sanity / LOSO report (perm + variants)

Earlier stages (audit/baseline/posctrl/sensitivity): `logs/sanity_frozen_parallel.log`

```
=== BASELINE RF | PRIMARY 2class (refresh) ===
Baselines: majority-class acc=0.556 (label=1) | chance=0.500
Pooled confusion (rows=true, cols=pred, labels=[0, 1]):
[[ 4 16]
 [13 12]]
Accuracy 0.356 | balanced accuracy 0.340 | Wilson 95% CI [0.232, 0.502] (k=16/45)
Per-class recall: 0=0.200, 1=0.480

=== PERMUTATION TEST (n=200, subject-mean features, Parallel n_jobs=-1, RF n_jobs=1, rf_seed=SEED+k) ===
Observed (epoch-LOSO, for reference): acc=0.356 bal=0.340
Observed (subject-mean LOSO, matched null): acc=0.311 bal=0.285
Null accuracy: mean=0.477 std=0.092 min=0.200 max=0.667
Null balanced accuracy: mean=0.458 std=0.094 min=0.185 max=0.655
p-value (acc, right-tailed): 0.9801
p-value (balanced acc, right-tailed): 0.9751

=== VARIANT A (PRE-SPECIFIED): LR on frontal theta + theta/alpha ===
Assumption: Emotiv-14 channel order ['AF3', 'F7', 'F3', 'FC5', 'T7', 'P7', 'O1', 'O2', 'P8', 'T8', 'FC6', 'F4', 'F8', 'AF4']; frontal idx=(0, 1, 2, 3, 10, 11, 12, 13)
=== VARIANT A LR compact | PRIMARY 2class ===
Baselines: majority-class acc=0.556 (label=1) | chance=0.500
Pooled confusion (rows=true, cols=pred, labels=[0, 1]):
[[ 7 13]
 [14 11]]
Accuracy 0.400 | balanced accuracy 0.395 | Wilson 95% CI [0.270, 0.545] (k=18/45)
Per-class recall: 0=0.350, 1=0.440

=== VARIANT B (PRE-SPECIFIED): subject-mean features (45 samples) + RF ===
=== VARIANT B subject-mean RF | PRIMARY 2class ===
Baselines: majority-class acc=0.556 (label=1) | chance=0.500
Pooled confusion (rows=true, cols=pred, labels=[0, 1]):
[[ 1 19]
 [12 13]]
Accuracy 0.311 | balanced accuracy 0.285 | Wilson 95% CI [0.195, 0.457] (k=14/45)
Per-class recall: 0=0.050, 1=0.520

```
