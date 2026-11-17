# RESULTS v2 — logged runs (does not replace RESULTS.md)

Frozen v1 primary stays in [`RESULTS.md`](RESULTS.md). Numbers below are from `logs/v2/` only.

## Track A — STEW multi-threshold LOSO

| threshold | n_high | majority | LOSO acc | LOSO bal-acc |
|-----------|--------|----------|----------|--------------|
| ≥6 | 32 | 0.711 | **0.711** | 0.523 |
| ≥7 | 25 | 0.556 | **0.356** | 0.340 |
| ≥8 | 14 | 0.689 | **0.689** | 0.500 |

Source: `logs/v2/STEW_MULTI_THRESHOLD.md`.

## Track B — Newdataset Control vs Stress (all conditions)

Citation: Atiwiwat & Hemakom, Mendeley Data `s87jk3p5ws` (EEG **2000 Hz**; analysis cache **250 Hz**).  
Recording-level LOSO (mean epoch proba per arm); subject held out.

| condition | n_subjects | n_rec | majority | LOSO acc | LOSO bal-acc |
|-----------|------------|-------|----------|----------|--------------|
| EO | 65 | 130 | 0.500 | **0.538** | 0.538 |
| AC1 | 65 | 125 | 0.504 | **0.576** | 0.575 |
| AC2 | 65 | 126 | 0.508 | **0.556** | 0.557 |
| AC3 | 65 | 125 | 0.512 | **0.544** | 0.545 |
| AC4 | 65 | 123 | 0.504 | **0.504** | 0.505 |

Source: `logs/v2/NEWDATASET_ALL_CONDITIONS.md`.

### Reproduce

```bash
python -m src.cache_newdataset --conditions EO,AC1,AC2,AC3,AC4 --arms control,stress
python -m src.train_v2_newdataset_all --conditions EO,AC1,AC2,AC3,AC4 --log-dir logs/v2
```

**Read:** Best lift on **AC1** (0.576 vs ~0.50 majority). Performance falls toward chance on harder AC3/AC4. EO pair is near chance (expected weak stress contrast at rest). Modest signal vs STEW null — still not a product/clinical claim. QC caveat: empty-padded columns → variable trimmed durations.

## Track C — Product honesty / live replay

| Endpoint / UI | Purpose |
|---------------|---------|
| `GET /api/methods` | Null LOSO + montage/units |
| `?model_mode=loso_held_out` | N−1 held-out score |
| `GET /api/live/replay/{id}` | STEW file LIVE replay |

## Montage / units

See `data/MONTAGE_AND_UNITS.md` and `config_ext.MONTAGE_NOTE`.
