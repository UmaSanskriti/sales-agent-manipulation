import json
import httpx
import pytest
from src.huit import BASE_URL, HuitBedrockClient


def test_fixed_destination_and_text_only(monkeypatch):
    monkeypatch.setenv("HUIT_API_KEY", "test-key")
    seen = []
    def respond(request):
        seen.append(request)
        return httpx.Response(200, json={"stop_reason": "end_turn", "content": [
            {"type": "thinking", "thinking": "private"}, {"type": "text", "text": "OK"}]})
    client = HuitBedrockClient("us.anthropic.claude-haiku-5-5", transport=httpx.MockTransport(respond))
    try:
        assert client.chat("system", [{"role": "user", "content": "hi"}], max_tokens=32, seed=1, temperature=0) == "OK"
    finally:
        client.close()
    assert str(seen[0].url) == BASE_URL + "/model/us.anthropic.claude-haiku-5-5/invoke"
    assert seen[0].headers["Authorization"] == "Bearer test-key"
    body = json.loads(seen[0].content)
    assert body["max_tokens"] == 32
    assert "seed" not in body and "temperature" not in body


def test_no_personal_key_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("HUIT_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "personal")
    with pytest.raises(ValueError, match="HUIT_API_KEY"):
        HuitBedrockClient("test")
    empty = tmp_path / "empty.env"
    empty.write_text("")
    monkeypatch.setenv("HUIT_API_KEY", "other-project-key")
    with pytest.raises(ValueError, match="HUIT_API_KEY"):
        HuitBedrockClient("test", key_file=empty)


def test_transient_rate_limit_retries_same_request(monkeypatch):
    monkeypatch.setenv("HUIT_API_KEY", "test-key")
    monkeypatch.setattr("src.huit.time.sleep", lambda _: None)
    requests = []
    def respond(request):
        requests.append(request.content)
        if len(requests) == 1:
            return httpx.Response(429)
        return httpx.Response(200, json={"stop_reason": "end_turn", "content": [{"type": "text", "text": "OK"}]})
    client = HuitBedrockClient("test", transport=httpx.MockTransport(respond))
    try:
        assert client.chat("system", [{"role": "user", "content": "hi"}]) == "OK"
    finally:
        client.close()
    assert len(requests) == 2 and requests[0] == requests[1]


def test_persistent_transient_errors_are_bounded(monkeypatch):
    monkeypatch.setenv("HUIT_API_KEY", "test-key")
    monkeypatch.setattr("src.huit.time.sleep", lambda _: None)
    calls = []
    def respond(request):
        calls.append(1)
        return httpx.Response(503)
    client = HuitBedrockClient("test", transport=httpx.MockTransport(respond))
    try:
        with pytest.raises(RuntimeError, match="HTTP 503"):
            client.chat("system", [{"role": "user", "content": "hi"}])
    finally:
        client.close()
    assert len(calls) == 4


@pytest.mark.parametrize("status,payload", [
    (403, {}), (302, {}),
    (200, {"stop_reason": "max_tokens", "content": [{"type": "text", "text": "partial"}]}),
    (200, {"stop_reason": "end_turn", "content": []}),
])
def test_bad_responses_fail_closed(monkeypatch, status, payload):
    monkeypatch.setenv("HUIT_API_KEY", "test-key")
    client = HuitBedrockClient("test", transport=httpx.MockTransport(
        lambda req: httpx.Response(status, json=payload, headers={"Location": "https://example.com"})))
    try:
        with pytest.raises(RuntimeError):
            client.chat("system", [{"role": "user", "content": "hi"}])
    finally:
        client.close()
