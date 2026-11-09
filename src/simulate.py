"""Run multi-turn conversations between the target (sales agent) and the simulated customer.

`run_batch` advances many conversations in lockstep: each turn is one batched
target call plus one concurrent simulator call per conversation.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from prompts.prompts import (
    CUSTOMER_DECISION_CORE,
    CUSTOMER_SIMULATOR_PROMPT,
    CUSTOMER_SITUATION,
    CUSTOMER_TURN_REQUEST,
    DECISION_PROMPT,
    OBJECTIONS,
    PERSONAS,
    render_customer_needs,
    render_system_prompt,
)
from src.schema import ConvSpec, Conversation, Message, Scenario

VALID_DECISIONS = ("buy", "no", "undecided")
CUSTOMER_DECISIONS = {"buy": "buy", "decline": "no", "leave_undecided": "undecided"}


def parse_customer_reply(raw: str) -> tuple[str, str]:
    """Reject malformed replies rather than silently feeding JSON to the agent."""
    text = raw.strip()
    if text.startswith("```") and text.endswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    value = json.loads(text)
    if not isinstance(value, dict) or set(value) != {"message", "decision"}:
        raise ValueError("Customer must return message and decision fields")
    message, decision = value["message"], value["decision"]
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Customer message must be non-empty text")
    if not isinstance(decision, str) or decision not in ("continue", *CUSTOMER_DECISIONS):
        raise ValueError("Unknown customer decision")
    return clean_customer_message(message), decision


def _h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def format_transcript(messages: list[Message], number_agent_turns: bool = False) -> str:
    """Plain transcript for the simulator; `number_agent_turns=True` for the judge,
    so it can be told which "Agent (turn N)" to label."""
    def label(m: Message) -> str:
        if m.role == "customer":
            return "Customer"
        return f"Agent (turn {m.turn})" if number_agent_turns else "Agent"

    return "\n".join(f"{label(m)}: {m.content}" for m in messages)


_ROLE_PREFIXES = ("customer:", "**customer:**", "user:", "me:")


def clean_customer_message(text: str) -> str:
    """Strip role prefixes / wrapping quotes the simulator sometimes adds, so the
    agent only ever sees the customer's words."""
    t = text.strip()
    if t.lower().startswith(_ROLE_PREFIXES):
        t = t.split(":", 1)[1].lstrip("* ").strip()
    if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'":
        t = t[1:-1].strip()
    return t


def customer_system_prompt(scenario: Scenario, persona_id: str) -> str:
    p = PERSONAS[persona_id]
    return CUSTOMER_SIMULATOR_PROMPT.format(
        persona_description=p["description"],
        customer_situation=CUSTOMER_SITUATION,
        customer_needs=render_customer_needs(),
        decision_core=CUSTOMER_DECISION_CORE,
        persona_behavior=p["behavior"],
    )


def _agent_view(messages: list[Message]) -> list[dict]:
    """Target model sees the customer as `user` and itself as `assistant`."""
    return [{"role": "user" if m.role == "customer" else "assistant", "content": m.content} for m in messages]


@dataclass
class _State:
    spec: ConvSpec
    scenario: Scenario
    agent_system: str
    customer_system: str
    messages: list[Message] = field(default_factory=list)
    decision: str | None = None
    stop_reason: str | None = None


def run_batch(items, target, simulator, *, n_turns: int = 10, target_kwargs=None,
              simulator_kwargs=None, seed: int | None = None,
              meta: dict | None = None) -> list[Conversation]:
    """items: list of (ConvSpec, Scenario, first_customer_message).

    n_turns is a maximum number of exchanges. A terminal customer remark is
    stored after the final agent reply but is never sent back to the agent.
    Customer messages 1 and 2 are fixed (first message, persona objection), so the
    first two agent turns are matched across conditions; the simulator writes the rest.
    The simulator never sees the condition or the agent's system prompt.
    """
    target_kwargs = target_kwargs or {}
    simulator_kwargs = simulator_kwargs or {}
    if n_turns < 1:
        raise ValueError("n_turns must be at least one")
    states = [
        _State(spec, sc, render_system_prompt(sc, spec.condition),
               customer_system_prompt(sc, spec.persona_id), [Message("customer", first, 1)])
        for spec, sc, first in items
    ]

    for turn in range(1, n_turns + 1):
        active = [s for s in states if s.decision is None]
        if not active:
            break
        replies = target.chat_many(
            [(s.agent_system, _agent_view(s.messages)) for s in active], seed=seed, **target_kwargs
        )
        if len(replies) != len(active):
            raise ValueError("Target response count does not match active conversations")
        for s, reply in zip(active, replies):
            s.messages.append(Message("agent", reply, turn))
        if turn == 1 and n_turns > 1:
            for s in active:
                objection = OBJECTIONS[s.spec.persona_id].format(product=s.scenario.product)
                s.messages.append(Message("customer", objection, 2))
        elif turn < n_turns:
            reqs = [
                (s.customer_system,
                 [{"role": "user", "content": CUSTOMER_TURN_REQUEST.format(transcript=format_transcript(s.messages))}])
                for s in active
            ]
            nexts = simulator.chat_many(reqs, **simulator_kwargs)
            if len(nexts) != len(active):
                raise ValueError("Simulator response count does not match active conversations")
            for s, nxt in zip(active, nexts):
                try:
                    message, decision = parse_customer_reply(nxt)
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"Invalid simulator reply for {s.spec.conv_id} after turn {turn}") from exc
                s.messages.append(Message("customer", message, turn + 1))
                if decision != "continue":
                    s.decision = CUSTOMER_DECISIONS[decision]
                    s.stop_reason = "customer_decision"

    capped = [s for s in states if s.decision is None]
    decision_reqs = [
        (s.customer_system,
         [{"role": "user", "content": DECISION_PROMPT.format(transcript=format_transcript(s.messages))}])
        for s in capped
    ]
    raws = simulator.chat_many(decision_reqs, max_tokens=5, temperature=0.0) if capped else []
    if len(raws) != len(capped):
        raise ValueError("Final decision count does not match capped conversations")
    for s, raw in zip(capped, raws):
        word = raw.strip().lower().strip(".")
        s.decision = word if word in VALID_DECISIONS else "undecided"
        s.stop_reason = "turn_limit" if word in VALID_DECISIONS else "invalid_final_decision"

    convs = []
    for s in states:
        convs.append(Conversation(
            spec=s.spec,
            messages=s.messages,
            decision=s.decision,
            metadata={
                "n_turns": n_turns,
                "seed": seed,
                "domain": s.scenario.domain,
                # >0 means the agent ran out of tokens mid-reasoning; inspect or regenerate
                "empty_agent_turns": sum(1 for m in s.messages if m.role == "agent" and not m.content),
                "agent_system_prompt_hash": _h(s.agent_system),
                "agent_system_prompt": s.agent_system,
                "customer_system_prompt_hash": _h(s.customer_system),
                **(meta or {}),
                "protocol_version": "customer_stopping_v1",
                "actual_agent_turns": sum(m.role == "agent" for m in s.messages),
                "stop_reason": s.stop_reason,
            },
        ))
    return convs


def run_conversation(spec: ConvSpec, scenario: Scenario, first_message: str, target, simulator,
                     **kw) -> Conversation:
    """Single-conversation convenience wrapper around run_batch."""
    return run_batch([(spec, scenario, first_message)], target, simulator, **kw)[0]
