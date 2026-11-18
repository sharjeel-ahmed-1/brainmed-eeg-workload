# RESULTS v2 — logged runs (does not replace RESULTS.md)

Frozen v1 primary stays in [`RESULTS.md`](RESULTS.md). Numbers below are from `logs/v2/` only.

> Paths are under `docs/` in the repository root.

## Combined results table

| Track | Dataset | Label | LOSO acc | Majority |
|-------|---------|-------|----------|----------|
| v1 (see RESULTS.md) | STEW | rating ≥ 7 | **0.356** | 0.556 |
| v2-A | STEW | rating ≥ 6 | 0.711 | 0.711 |
| v2-A | STEW | rating ≥ 7 | 0.356 | 0.556 |
| v2-A | STEW | rating ≥ 8 | 0.689 | 0.689 |
| v2-B (band-power RF) | Newdataset EO | Control vs Stress | 0.538 | 0.500 |
| v2-B | Newdataset AC1 | Control vs Stress | **0.576** | ~0.504 |
| v2-B | Newdataset AC2 | Control vs Stress | 0.556 | ~0.508 |
| v2-B | Newdataset AC3 | Control vs Stress | 0.544 | ~0.512 |
| v2-B | Newdataset AC4 | Control vs Stress | 0.504 | ~0.504 |
| v2-D (Riemann OAS→tangent→LR) | Newdataset EO | Control vs Stress | 0.531 | 0.500 |
| v2-D | Newdataset AC1 | Control vs Stress | 0.544 | ~0.504 |
| v2-D | Newdataset AC2 | Control vs Stress | **0.579** | ~0.508 |
| v2-D | Newdataset AC3 | Control vs Stress | 0.496 | ~0.512 |
| v2-D | Newdataset AC4 | Control vs Stress | 0.512 | ~0.504 |
| v2-C | — | Product honesty / UI | — | — |

Sources: `logs/v2/STEW_MULTI_THRESHOLD.md`, `NEWDATASET_ALL_CONDITIONS.md`, `RIEMANN_ALL_CONDITIONS.md`.

**Notes:** STEW subject-level LOSO has **n = 45** (one label/subject) → **under-powered** for strong cross-subject claims; primary 0.356 vs majority 0.556. Newdataset denser labels; best RF cell AC1 0.576, best Riemann AC2 0.579 — still near majority. Not a clinical claim. Newdataset QC: empty-padded columns → variable trimmed durations.

Citation (newdataset): Atiwiwat & Hemakom, Mendeley Data `s87jk3p5ws` (EEG **2000 Hz**; analysis cache **250 Hz**). Recording-level LOSO (mean epoch proba per arm); subject held out.

### Reproduce

```bash
python -m src.train_v2_stew_thresholds --thresholds 6,7,8 --log-dir logs/v2
python -m src.cache_newdataset --conditions EO,AC1,AC2,AC3,AC4 --arms control,stress
python -m src.train_v2_newdataset_all --conditions EO,AC1,AC2,AC3,AC4 --log-dir logs/v2
python -m src.train_v2_riemann --conditions AC1,EO,AC2,AC3,AC4 --log-dir logs/v2
```

## v2-C — Product honesty / file replay (simulated live)

| Endpoint / UI | Purpose |
|---------------|---------|
| `GET /api/methods` | STEW LOSO finding + montage/units |
| `?model_mode=loso_held_out` | N−1 held-out score |
| `GET /api/live/replay/{id}` | STEW **file replay (simulated live)** — not a headset stream |

## Montage / units

See [`MONTAGE_AND_UNITS.md`](MONTAGE_AND_UNITS.md) and `config_ext.MONTAGE_NOTE`.
