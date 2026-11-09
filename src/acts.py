"""Visible-text replay of conversations through the target model, and the token positions we read.

For every judged agent turn we store three vectors per layer:
  pre   last prompt token (the `<|start|>assistant` header), before any reply text
  last  last reply token (the final token of the reply text, before the channel-end token)
  mean  mean over the reply's text tokens

The model is causal, so one pass over a whole conversation yields the same vectors for every turn
as a separate pass per turn would. Hidden reasoning was never saved, so the replay has NO analysis
channel: the reply sits in the `final` channel directly (see docs/trace_format.md).
"""
from __future__ import annotations

POSITIONS = ("pre", "last", "mean")
FINAL_MARKER = "<|channel|>final<|message|>"


def agent_turn_indices(messages) -> list[int]:
    """Indices of the agent messages that get a row: same rule as the judge (non-empty replies)."""
    return [i for i, m in enumerate(messages) if m.role == "agent" and m.content.strip()]


def to_chat(system: str, messages) -> list[dict]:
    """customer -> user, agent -> assistant. Empty agent messages are dropped (they were never judged)."""
    out = [{"role": "system", "content": system}]
    for m in messages:
        if m.role == "agent" and not m.content.strip():
            continue
        out.append({"role": "user" if m.role == "customer" else "assistant", "content": m.content})
    return out


def locate_turns(tokenizer, system: str, messages, reasoning_effort: str | None = None):
    """Tokenize a conversation once and find each judged turn's positions.

    Returns (input_ids, spans) where spans is a list of dicts
    {turn, pre, start, end}: `pre` is the index of the last prompt token, and [start, end) are the
    reply's text tokens. Raises if the tokenization of the whole conversation does not contain the
    prefix tokenizations (which would make the indices wrong).
    """
    kw = {"reasoning_effort": reasoning_effort} if reasoning_effort else {}
    keep = [m for m in messages if not (m.role == "agent" and not m.content.strip())]
    last_agent = max((i for i, m in enumerate(keep) if m.role == "agent"), default=-1)
    keep = keep[: last_agent + 1]  # the closing customer remark comes after every reply; drop it
    chat = to_chat(system, keep)
    full_text = tokenizer.apply_chat_template(chat, add_generation_prompt=False, tokenize=False, **kw)
    full_ids = tokenizer(full_text, add_special_tokens=False)["input_ids"]

    spans = []
    for i, m in enumerate(keep):
        if m.role != "agent":
            continue
        prefix_chat = to_chat(system, keep[:i])
        prompt = tokenizer.apply_chat_template(prefix_chat, add_generation_prompt=True, tokenize=False, **kw)
        n_prompt = len(tokenizer(prompt, add_special_tokens=False)["input_ids"])
        n_start = len(tokenizer(prompt + FINAL_MARKER, add_special_tokens=False)["input_ids"])
        n_end = len(tokenizer(prompt + FINAL_MARKER + m.content, add_special_tokens=False)["input_ids"])
        if n_end <= n_start:
            raise ValueError(f"turn {m.turn}: reply produced no tokens")
        for n, name in ((n_prompt, "prompt"), (n_end, "reply")):
            part = tokenizer(prompt + FINAL_MARKER + m.content, add_special_tokens=False)["input_ids"][:n]
            if full_ids[:n] != part:
                raise ValueError(f"turn {m.turn}: {name} tokens are not a prefix of the full conversation")
        spans.append({"turn": m.turn, "pre": n_prompt - 1, "start": n_start, "end": n_end})
    return full_ids, spans


def gather_vectors(hidden_states, spans):
    """hidden_states: sequence of [1, T, D] tensors (embedding output + each block). Returns a float16
    numpy array [n_turns, n_layers, 3, D] in POSITIONS order."""
    import numpy as np
    import torch

    per_layer = []
    for h in hidden_states:
        h = h[0].float()
        rows = []
        for s in spans:
            rows.append(torch.stack([h[s["pre"]], h[s["end"] - 1], h[s["start"]:s["end"]].mean(0)]))
        per_layer.append(torch.stack(rows))  # [n_turns, 3, D]
    out = torch.stack(per_layer, dim=1)  # [n_turns, n_layers, 3, D]
    return out.cpu().numpy().astype(np.float16)
