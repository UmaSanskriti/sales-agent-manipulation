"""Synthetic scenario sets for tests, built from the first real scenario."""
import dataclasses

from src.scenarios import load_scenarios
from src.schema import DOMAINS


def fake_scenarios(per_domain: int = 10):
    """per_domain copies of scenario 0 in every product line (10 -> the full 50)."""
    base = load_scenarios()[0]
    return [dataclasses.replace(base, id=f"{d}_{k + 1:02d}", domain=d) for d in DOMAINS for k in range(per_domain)]
