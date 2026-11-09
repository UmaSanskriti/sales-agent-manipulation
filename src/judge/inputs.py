"""The ONLY path from a stored conversation to a judge prompt.

Conversation files carry the condition (in the filename and metadata). The judge
must be blind to it, so this boundary takes just the scenario's ground-truth facts
and the message list, never the spec, metadata or decision.
"""
from __future__ import annotations

import json
from pathlib import Path

from prompts.prompts import render_judge_prompt
from src.schema import ConvSpec, Message, Scenario
from src.simulate import format_transcript


def load_conversation(path: Path | str) -> tuple[ConvSpec, list[Message], dict]:
    """Return (spec, messages, meta). Keep spec/meta out of the judge."""
    records = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    meta = records[0]
    spec = ConvSpec(meta["scenario_id"], meta["persona_id"], meta["condition"])
    messages = [Message(r["role"], r["content"], r["turn"]) for r in records[1:]]
    return spec, messages, meta


def judge_turn_prompts(scenario: Scenario, messages: list[Message]) -> list[tuple[int, str, str, str]]:
    """One (turn, agent_text, prompt, customer_text) per agent turn. Each prompt shows the
    transcript only up to and including that agent turn, so a label cannot depend on later
    messages; customer_text is the customer's words so far, for checking E/F bases."""
    out = []
    for i, m in enumerate(messages):
        if m.role == "agent" and m.content.strip():  # empty turns (generation failures) are not judged
            transcript = format_transcript(messages[:i + 1], number_agent_turns=True)
            customer_text = "\n".join(x.content for x in messages[:i] if x.role == "customer")
            out.append((m.turn, m.content, render_judge_prompt(scenario, transcript, m.turn), customer_text))
    return out
