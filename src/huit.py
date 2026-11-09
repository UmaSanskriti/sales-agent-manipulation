"""Claude Messages via Harvard's Bedrock gateway (no direct-provider fallback)."""
from __future__ import annotations

import os
import time
from urllib.parse import quote

import httpx
from dotenv import dotenv_values

from src.llm import BaseClient

BASE_URL = "https://apis.huit.harvard.edu/ais-bedrock-llm/v2"


class HuitBedrockClient(BaseClient):
    def __init__(self, model: str, workers: int = 4, key_file=None, *, transport=None):
        key = (dotenv_values(key_file).get("HUIT_API_KEY") if key_file
               else os.environ.get("HUIT_API_KEY"))
        if not key or not key.strip():
            raise ValueError("HUIT_API_KEY is required for the huit backend")
        self.model = model
        self.workers = workers
        self.client = httpx.Client(
            headers={"Authorization": "Bearer " + key.strip()},
            timeout=90, follow_redirects=False, transport=transport,
        )

    def chat(self, system, messages, *, max_tokens=300, temperature=None, seed=None):
        # Default sampling matches the direct Claude client; never forward seeds.
        body = {"anthropic_version": "bedrock-2023-05-31", "system": system,
                "messages": list(messages), "max_tokens": max_tokens,
                "thinking": {"type": "disabled"}}
        for attempt in range(4):
            try:
                response = self.client.post(
                    BASE_URL + "/model/" + quote(self.model, safe="") + "/invoke", json=body,
                )
            except httpx.TransportError:
                if attempt == 3:
                    raise RuntimeError("HUIT model request failed after transient transport errors") from None
                time.sleep(2 ** attempt)
                continue
            if response.status_code not in (429, 500, 502, 503, 504) or attempt == 3:
                break
            time.sleep(2 ** attempt)
        if response.status_code != 200:
            # Do not include request headers or provider bodies in logs.
            raise RuntimeError(f"HUIT model request failed (HTTP {response.status_code})")
        result = response.json()
        if result.get("stop_reason") == "max_tokens":
            raise RuntimeError("HUIT reply hit max_tokens; increase the simulator token budget")
        text = "".join(b.get("text", "") for b in result.get("content", [])
                       if b.get("type") == "text").strip()
        if not text:
            raise RuntimeError("HUIT returned no visible text")
        return text

    def close(self):
        self.client.close()
