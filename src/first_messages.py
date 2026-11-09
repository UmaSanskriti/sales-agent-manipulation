"""Generate each (scenario, persona) first customer message once, then freeze.

The same frozen message is reused in all three conditions. Review the JSON by
hand before running the full experiment.
"""
from __future__ import annotations

import json
from pathlib import Path

from prompts.prompts import CUSTOMER_SITUATION, FIRST_MESSAGE_PERSONA_EXTRA, FIRST_MESSAGE_PROMPT, PERSONAS
from src.schema import Scenario

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "first_messages" / "first_messages.json"
SYSTEM = "You write realistic customer chat messages."


def key(scenario_id: str, persona_id: str) -> str:
    return f"{scenario_id}__{persona_id}"


def render_first_message_prompt(scenario: Scenario, persona_id: str) -> str:
    p = PERSONAS[persona_id]
    return FIRST_MESSAGE_PROMPT.format(
        persona_description=p["description"],
        persona_behavior=p["behavior"],
        customer_situation=CUSTOMER_SITUATION,
        product=scenario.product,
        company=scenario.company,
        persona_extra=FIRST_MESSAGE_PERSONA_EXTRA[persona_id],
    )


def get_first_messages(pairs, scenarios_by_id, client, path: Path | str = DEFAULT_PATH,
                       temperature=0.9, max_tokens=150) -> dict[str, str]:
    """Return {key: message} for the given (scenario_id, persona_id) pairs.

    Existing entries in `path` are never regenerated; missing ones are generated
    concurrently and appended.
    """
    path = Path(path)
    cache = json.loads(path.read_text()) if path.exists() else {}
    missing = sorted({(s, p) for s, p in pairs if key(s, p) not in cache})
    if missing:
        reqs = [(SYSTEM, [{"role": "user", "content": render_first_message_prompt(scenarios_by_id[s], p)}])
                for s, p in missing]
        for (s, p), text in zip(missing, client.chat_many(reqs, temperature=temperature, max_tokens=max_tokens)):
            cache[key(s, p)] = text.strip().strip('"')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache, indent=2, sort_keys=True))
    return {key(s, p): cache[key(s, p)] for s, p in pairs}
