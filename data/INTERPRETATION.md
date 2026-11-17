# Interpretation note (Phase 3)

## Framing

Primary LOSO accuracy was **below majority** (acc 0.356 vs majority 0.556) with
permutation p≈0.98. Figures below are **descriptive** (RF / LR fit on all subjects)
and must not be read as evidence of a reliable held-out workload classifier.

Channel labels use the **Emotiv-14 order assumption** in `config.EMOTIV_CH_NAMES`
(names are not stored in STEW `.mat`).

## What literature often reports

Cognitive-workload EEG reviews commonly associate **increased frontal/midline theta**
and **decreased posterior alpha** (or elevated θ/α) with higher mental effort
(e.g. n-back / multitasking paradigms; consumer-headset studies on STEW-like tasks).
Those effects are typically modest, session- and subject-dependent, and weaker under
noisy dry-electrode / consumer hardware than lab wet systems.

## What we see here

- Top RF features (all-subject fit): F4_gamma, F3_gamma, T8_gamma, O1_gamma, AF4_beta, T8_beta, O2_gamma, FC6_beta…
- Variant A LR coefs: frontal_mean_theta=-0.210,
  frontal_mean_theta_alpha=+0.172
  (sign/magnitude are exploratory; LOSO for A was also ≤ majority).

Honest read: feature ranks may echo band/channel variance more than a true
workload label association. Positive-control (α boost) proved the pipeline can
detect injected spectral change; the **natural STEW `rating≥7` label did not**.

## Takeaway for portfolio

Methods rigor (LOSO, perm, posctrl, frozen protocol) > cherry-picked accuracy.
Null primary result is still a valid computational-neuroscience / BCI methods story
when framed with limitations (label coarseness, consumer EEG, montage assumption).
