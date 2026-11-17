"""Run Control vs Stress LOSO for multiple cached conditions; update logs/v2 table."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import config
from src.train_v2_newdataset import run


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--conditions", default="EO,AC1,AC2,AC3,AC4")
    p.add_argument("--log-dir", type=Path, default=config.ROOT / "logs" / "v2")
    args = p.parse_args()
    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    rows = []
    for cond in conditions:
        print(f"\n######## {cond} ########\n", flush=True)
        try:
            summary = run(cond, args.log_dir)  # type: ignore[arg-type]
            rows.append(summary)
        except Exception as e:
            print(f"FAILED {cond}: {type(e).__name__}: {e}", flush=True)
            rows.append({"condition": cond, "error": f"{type(e).__name__}: {e}"})

    table = args.log_dir / "NEWDATASET_ALL_CONDITIONS.md"
    lines = [
        "# Newdataset Control vs Stress LOSO — all conditions",
        "",
        "| condition | n_subjects | n_rec | majority | LOSO acc | LOSO bal-acc |",
        "|-----------|------------|-------|----------|----------|--------------|",
    ]
    for s in rows:
        if "error" in s:
            lines.append(f"| {s.get('condition')} | — | — | — | ERROR | {s['error'][:40]} |")
        else:
            lines.append(
                f"| {s['condition']} | {s['n_subjects']} | {s['n_recordings_scored']} | "
                f"{s['majority_acc']:.3f} | **{s['loso_recording_acc']:.3f}** | "
                f"{s['loso_recording_bal_acc']:.3f} |"
            )
    lines.append("")
    table.write_text("\n".join(lines), encoding="utf-8")
    (args.log_dir / "newdataset_all_conditions.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )
    print(f"Wrote {table}", flush=True)


if __name__ == "__main__":
    main()
