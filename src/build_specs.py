"""Build conversation specs: the full cross product and a stratified pilot sample."""
from __future__ import annotations

import itertools

from prompts.prompts import CONDITIONS, PERSONAS
from src.schema import ConvSpec, Scenario


def all_specs(scenarios: list[Scenario]) -> list[ConvSpec]:
    """Every scenario x persona x condition (50 x 4 x 3 = 600 for the full dataset)."""
    return [ConvSpec(s.id, p, c) for s, p, c in itertools.product(scenarios, PERSONAS, CONDITIONS)]


def pilot_specs(scenarios: list[Scenario], n: int = 10) -> list[ConvSpec]:
    """Up to n scenarios across product lines, anxious persona, all conditions.

    Matches TRD M4: ten selected scenarios produce thirty conversations.
    A partial scenario collection produces a smaller, explicitly reported pilot.
    """
    if n < 1:
        raise ValueError("Pilot scenario count must be positive")
    if not scenarios:
        return []
    by_domain: dict[str, list[Scenario]] = {}
    for s in sorted(scenarios, key=lambda s: s.id):
        by_domain.setdefault(s.domain, []).append(s)
    queues = list(by_domain.values())
    ordered = [q[i] for i in range(max(map(len, queues))) for q in queues if i < len(q)]
    return [
        ConvSpec(s.id, "anxious", condition)
        for s in ordered[:n] for condition in CONDITIONS
    ]
