"""
Riemannian covariance features for protocol v2 (newdataset).

Pre-specified (not tuned on outer LOSO):
  Covariances(oas) → TangentSpace(riemann) → StandardScaler → LogisticRegression
"""
from __future__ import annotations

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from pyriemann.estimation import Covariances
from pyriemann.tangentspace import TangentSpace

import config


def make_riemann_lr_pipeline() -> Pipeline:
    """Epoch tensors (n, ch, time) → SPD cov → tangent → balanced LR."""
    return Pipeline(
        [
            ("cov", Covariances(estimator="oas")),
            ("ts", TangentSpace(metric="riemann")),
            ("scale", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    random_state=config.SEED,
                    solver="lbfgs",
                ),
            ),
        ]
    )
