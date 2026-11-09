"""Train/val/test split by scenario, stratified by domain (product line).

All conversations of a scenario (every persona and condition) share a split,
as required by the assignment. Each domain contributes ~60/20/20 of its
scenarios to train/val/test, except `ood_domain`, which goes entirely to
test_ood (the generalization check) and appears nowhere else.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from src.schema import Scenario

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "splits" / "splits.json"


def split_scenarios(scenarios: list[Scenario], ratios=(0.6, 0.2, 0.2), seed: int = 0,
                    ood_domain: str | None = None) -> dict[str, str]:
    """Return {scenario_id: 'train'|'val'|'test'|'test_ood'}."""
    rng = random.Random(seed)
    out: dict[str, str] = {}
    by_domain: dict[str, list[str]] = {}
    for s in scenarios:
        by_domain.setdefault(s.domain, []).append(s.id)
    for domain, ids in by_domain.items():
        if domain == ood_domain:
            out.update({sid: "test_ood" for sid in ids})
            continue
        ids = sorted(ids)
        rng.shuffle(ids)
        n_train = round(ratios[0] * len(ids))
        n_val = round(ratios[1] * len(ids))
        for i, sid in enumerate(ids):
            out[sid] = "train" if i < n_train else "val" if i < n_train + n_val else "test"
    return out


def save_splits(splits: dict[str, str], path: Path | str = DEFAULT_PATH, overwrite: bool = False) -> None:
    """Freeze the split. Refuses to overwrite so the test set can't silently change."""
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists; splits are frozen (pass overwrite=True to replace)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(splits, indent=2, sort_keys=True))


def human_label_sample(specs, splits: dict[str, str], frac: float = 0.05, seed: int = 0):
    """Conversations to hand-label while building the judge (~5% of the dataset).

    Drawn ONLY from train/val scenarios so the test sets stay untouched until the
    judge is frozen, and balanced across conditions.
    """
    rng = random.Random(seed)
    n = max(1, round(frac * len(specs)))
    pools: dict[str, list] = {}
    for s in specs:
        if splits[s.scenario_id] in ("train", "val"):
            pools.setdefault(s.condition, []).append(s)
    for pool in pools.values():
        rng.shuffle(pool)
    conds, out, i = sorted(pools), [], 0
    while len(out) < n and any(pools.values()):
        pool = pools[conds[i % len(conds)]]
        i += 1
        if pool:
            out.append(pool.pop())
    return out
