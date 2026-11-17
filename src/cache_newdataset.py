"""Cache newdataset EEG xlsx → resampled NPZ.

Example:
  python -m src.cache_newdataset --conditions AC1 --arms control,stress
  python -m src.cache_newdataset --conditions AC1 --max-subjects 5
"""
from __future__ import annotations

import argparse

from src.load_newdataset import Arm, Condition, cache_condition


def main():
    p = argparse.ArgumentParser(description="Cache newdataset Control/Stress EEG")
    p.add_argument("--conditions", default="AC1", help="Comma list: EO,AC1,AC2,AC3,AC4")
    p.add_argument("--arms", default="control,stress", help="Comma list: control,stress")
    p.add_argument("--max-subjects", type=int, default=None)
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args()
    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    for arm in arms:
        for cond in conditions:
            print(f"=== {arm} / {cond} ===", flush=True)
            paths = cache_condition(
                arm,  # type: ignore[arg-type]
                cond,  # type: ignore[arg-type]
                overwrite=args.overwrite,
                max_subjects=args.max_subjects,
            )
            print(f"done {len(paths)} files", flush=True)


if __name__ == "__main__":
    main()
