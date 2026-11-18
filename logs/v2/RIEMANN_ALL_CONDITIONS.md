# Riemannian newdataset Control vs Stress — all conditions

Pipeline: `Covariances(oas) → TangentSpace(riemann) → StandardScaler → LogisticRegression`
Split: leave-one-subject-out; recording = mean epoch probability.

| condition | n_subjects | n_rec | majority | LOSO acc | LOSO bal-acc | macro-F1 |
|-----------|------------|-------|----------|----------|--------------|----------|
| AC1 | 65 | 125 | 0.504 | **0.544** | 0.544 | 0.543 |
| EO | 65 | 130 | 0.500 | **0.531** | 0.531 | 0.526 |
| AC2 | 65 | 126 | 0.508 | **0.579** | 0.581 | 0.577 |
| AC3 | 65 | 125 | 0.512 | **0.496** | 0.496 | 0.496 |
| AC4 | 65 | 123 | 0.504 | **0.512** | 0.513 | 0.511 |
