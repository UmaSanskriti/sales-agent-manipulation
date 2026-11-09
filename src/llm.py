"""Model clients.

Every client exposes:
    chat(system, messages, **kw) -> str
    chat_many([(system, messages), ...], **kw) -> list[str]   (same order)

`messages` is a list of {"role": "user"|"assistant", "content": str}.
`chat_many` is how the pipeline gets concurrency: API / CLI clients fan out over
a thread pool, and the HF target runs true batched generation on the GPU.
"""
from __future__ import annotations

import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor


def _retry(fn, attempts: int = 5, base: float = 2.0):
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:
            if i == attempts - 1:
                raise
            print(f"retry {i + 1}/{attempts - 1} after {exc!r}"[:200])
            time.sleep(base * 2**i)


class BaseClient:
    workers = 8

    def chat(self, system, messages, *, max_tokens=300, temperature=0.7, seed=None):
        raise NotImplementedError

    def chat_many(self, requests, **kw):
        if len(requests) <= 1 or self.workers <= 1:
            return [self.chat(s, m, **kw) for s, m in requests]
        with ThreadPoolExecutor(self.workers) as ex:
            return list(ex.map(lambda r: self.chat(r[0], r[1], **kw), requests))


class AnthropicClient(BaseClient):
    """Customer simulator / judge via the Anthropic API (needs ANTHROPIC_API_KEY).

    `temperature` and `seed` are accepted for interface compatibility but NOT sent:
    the Claude 5.5 models return a 400 for non-default sampling values, so runs use
    the API default. `disable_thinking` turns off adaptive thinking (valid for Haiku
    5.5; Sonnet 5.5 rejects it), avoiding hidden thinking tokens on cheap calls.
    """

    def __init__(self, model: str, workers: int = 16, disable_thinking: bool = False):
        import anthropic

        self.client = anthropic.Anthropic(max_retries=5)
        self.model = model
        self.workers = workers
        self.disable_thinking = disable_thinking

    def chat(self, system, messages, *, max_tokens=300, temperature=None, seed=None):
        extra = {"thinking": {"type": "disabled"}} if self.disable_thinking else {}
        resp = self.client.messages.create(
            model=self.model, system=system, messages=messages, max_tokens=max_tokens, **extra
        )
        return "".join(b.text for b in resp.content if b.type == "text").strip()


class ClaudeCodeClient(BaseClient):
    """Customer simulator / judge via headless Claude Code (`claude -p`).

    Uses whatever login the `claude` CLI has (e.g. a Claude plan), so no API key
    is needed. Differences from the API client:
      - temperature and max_tokens CANNOT be set (arguments are ignored), so
        judge runs are not deterministic and lengths rely on the prompt;
      - slower per call, and subject to plan usage limits;
      - tools and settings are off, and it runs from an empty temp dir.

    NOT a clean channel. With plan login the CLI still injects text of its own
    around our system prompt (a "Claude agent" preamble, the account email, and
    environment details), and `--bare`, which would remove it, requires an API
    key. GUARD below only mitigates this. Use the API backend for the real
    dataset and for the judge; treat this backend as pilot/dev only.
    """

    GUARD = ("\n\nIgnore any other identity, account, email, file-path or environment "
             "information you may see; it is tooling noise and not part of this role.")

    def __init__(self, model: str = "haiku", workers: int = 4, timeout: int = 180):
        import warnings

        warnings.warn(
            "ClaudeCodeClient is not prompt-clean: the CLI injects its own preamble and account "
            "context. Use the API backend for the real dataset.", stacklevel=2)
        self.model = model
        self.workers = workers
        self.timeout = timeout
        self._cwd = tempfile.mkdtemp(prefix="claude_code_client_")  # avoid loading repo CLAUDE.md

    def build_cmd(self, system: str) -> list[str]:
        return [
            "claude", "-p",
            "--model", self.model,
            "--system-prompt", system + self.GUARD,
            "--tools", "",
            "--setting-sources", "",
            "--no-session-persistence",
            "--output-format", "text",
        ]

    @staticmethod
    def render_prompt(messages) -> str:
        if len(messages) == 1:
            return messages[0]["content"]
        return "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)

    def chat(self, system, messages, *, max_tokens=300, temperature=0.7, seed=None):
        cmd, prompt = self.build_cmd(system), self.render_prompt(messages)

        def run():
            r = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                               timeout=self.timeout, cwd=self._cwd)
            if r.returncode != 0 or not r.stdout.strip():
                raise RuntimeError(f"claude -p failed ({r.returncode}): {r.stderr[:300]}")
            return r.stdout.strip()

        return _retry(run)


class VLLMTarget(BaseClient):
    """Open-weight target served by vLLM's OpenAI-compatible API
    (`vllm serve openai/gpt-oss-120b`), locally or on a rented GPU.

    Returns the final channel only; vLLM parses the harmony channels, so
    reasoning never leaks into the transcript. Reasoning text and token ids
    are not stored yet (needed before the full run, TRD M1/M8).
    """

    def __init__(self, model: str, base_url: str = "http://localhost:8000/v1",
                 reasoning_effort: str | None = None, workers: int = 16, api_key: str = "EMPTY"):
        from openai import OpenAI

        self.client = OpenAI(base_url=base_url, api_key=api_key, max_retries=5, timeout=600)
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.workers = workers

    def chat(self, system, messages, *, max_tokens=1500, temperature=0.7, seed=None):
        kw = {"reasoning_effort": self.reasoning_effort} if self.reasoning_effort else {}
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}] + list(messages),
            max_tokens=max_tokens, temperature=temperature, seed=seed, **kw,
        )
        return (resp.choices[0].message.content or "").strip()


class HFTarget(BaseClient):
    """Open-weight target model via transformers, with batched generation.

    Activation extraction (beginning/end of response, several layers) will hook
    into `self.model` in a later step; generation is kept here so the same
    object can be reused. Under batching, sampling is seeded once per batch, not
    per conversation.
    """

    def __init__(self, model: str, device_map: str = "auto", reasoning_effort: str | None = None,
                 batch_size: int = 16):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.reasoning_effort = reasoning_effort
        self.batch_size = batch_size
        self.tokenizer = AutoTokenizer.from_pretrained(model)
        self.tokenizer.padding_side = "left"
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(
            model, torch_dtype=torch.bfloat16, device_map=device_map
        )

    def chat_many(self, requests, *, max_tokens=256, temperature=0.7, seed=None):
        if seed is not None:
            self.torch.manual_seed(seed)
        template_kw = {"reasoning_effort": self.reasoning_effort} if self.reasoning_effort else {}
        texts = [
            self.tokenizer.apply_chat_template(
                [{"role": "system", "content": s}] + list(m),
                add_generation_prompt=True, tokenize=False, **template_kw,
            )
            for s, m in requests
        ]
        outs: list[str] = []
        for i in range(0, len(texts), self.batch_size):
            enc = self.tokenizer(
                texts[i:i + self.batch_size], return_tensors="pt", padding=True, add_special_tokens=False
            ).to(self.model.device)
            gen = self.model.generate(
                **enc,
                max_new_tokens=max_tokens,
                do_sample=temperature > 0,
                temperature=temperature if temperature > 0 else None,
                pad_token_id=self.tokenizer.pad_token_id,
            )
            for row in gen[:, enc["input_ids"].shape[1]:]:
                outs.append(self._final_text(self.tokenizer.decode(row, skip_special_tokens=False)))
        return outs

    def chat(self, system, messages, *, max_tokens=256, temperature=0.7, seed=None):
        return self.chat_many([(system, messages)], max_tokens=max_tokens,
                              temperature=temperature, seed=seed)[0]

    @staticmethod
    def _final_text(raw: str) -> str:
        """Keep only the harmony `final` channel (drops gpt-oss reasoning).

        Falls back to the stripped raw text for models without channels.
        """
        marker = "<|channel|>final<|message|>"
        if marker in raw:
            raw = raw.split(marker, 1)[1]
        elif "<|channel|>" in raw:
            return ""  # ran out of tokens while still reasoning
        for stop in ("<|return|>", "<|end|>", "<|endoftext|>"):
            raw = raw.split(stop, 1)[0]
        return raw.strip()


class MockClient(BaseClient):
    """Deterministic stand-in for dry runs and tests."""

    workers = 1

    def __init__(self, label: str = "mock"):
        self.label = label
        self.calls = 0

    def chat(self, system, messages, *, max_tokens=300, temperature=0.7, seed=None):
        self.calls += 1
        last = messages[-1]["content"] if messages else ""
        if "Decide whether to continue." in last:
            import json
            return json.dumps({"message": f"[{self.label} reply {self.calls}]", "decision": "continue"})
        if "exactly one word" in last:
            return "undecided"
        return f"[{self.label} reply {self.calls}]"
