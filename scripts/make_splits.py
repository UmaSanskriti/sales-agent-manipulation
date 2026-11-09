"""Freeze the train/val/test split by scenario (run once, after all 50 scenarios exist).

    python scripts/make_splits.py
"""
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from src.scenarios import load_scenarios  # noqa: E402
from src.splits import DEFAULT_PATH, save_splits, split_scenarios  # noqa: E402


def main():
    cfg = yaml.safe_load((ROOT / "configs" / "experiment.yaml").read_text())
    scenarios = load_scenarios()
    splits = split_scenarios(scenarios, tuple(cfg["split"]["ratios"]), cfg["split"]["seed"],
                             cfg["split"].get("ood_domain"))
    save_splits(splits)  # raises if already frozen
    print(f"wrote {DEFAULT_PATH}: {dict(Counter(splits.values()))} scenarios")
    for d in sorted({s.domain for s in scenarios}):
        print(f"  {d}: {dict(Counter(splits[s.id] for s in scenarios if s.domain == d))}")


if __name__ == "__main__":
    main()
