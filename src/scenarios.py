"""Load and validate scenarios."""
from __future__ import annotations

import json
from pathlib import Path

from src.schema import DOMAINS, Scenario

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "scenarios" / "scenarios.json"


def load_scenarios(path: Path | str = DEFAULT_PATH) -> list[Scenario]:
    scenarios = [Scenario(**s) for s in json.loads(Path(path).read_text())]
    ids = [s.id for s in scenarios]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate scenario ids")
    for s in scenarios:
        if s.domain not in DOMAINS:
            raise ValueError(f"{s.id}: unknown domain {s.domain!r}")
        if not s.facts or not s.limitations:
            raise ValueError(f"{s.id}: facts and limitations must be non-empty")
    return scenarios
