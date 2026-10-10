"""Gemini and Ollama providers against fake local HTTP servers: no network, no keys."""

import json
import os
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from skillbench import providers
from skillbench.providers import GeminiProvider, OllamaProvider, ProviderError


@contextmanager
def fake_server(routes):
    """routes: {(method, path_prefix): handler(request_json, headers) -> (status, body, headers)}"""
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def _handle(self, method):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else None
            seen.append((method, self.path, body, {k.lower(): v for k, v in self.headers.items()}))
            for (m, prefix), fn in routes.items():
                if m == method and self.path.startswith(prefix):
                    status, payload, extra = fn(body, self.headers)
                    break
            else:
                status, payload, extra = 404, {"error": "no route"}, {}
            data = json.dumps(payload).encode()
            self.send_response(status)
            for key, value in extra.items():
                self.send_header(key, value)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):  # noqa: N802
            self._handle("POST")

        def do_GET(self):  # noqa: N802
            self._handle("GET")

        def log_message(self, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}", seen
    finally:
        httpd.shutdown()
        httpd.server_close()


@pytest.fixture
def gemini_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(providers.time, "sleep", lambda s: None)


def reply(text, thought=None):
    parts = ([{"text": thought, "thought": True}] if thought else []) + [{"text": text}]
    return 200, {"candidates": [{"content": {"parts": parts}}]}, {}


def test_gemini_request_and_reply(monkeypatch, gemini_env):
    routes = {("POST", "/models/m1:generateContent"): lambda b, h: reply('{"skills": []}', "hmm")}
    with fake_server(routes) as (url, seen):
        monkeypatch.setattr(providers, "GEMINI_URL", url)
        text = GeminiProvider("m1", rpm=None).complete("system text", "user text")
    assert text == '{"skills": []}'  # thought parts are dropped
    _, _, body, headers = seen[0]
    assert headers["x-goog-api-key"] == "test-key"
    assert body["systemInstruction"]["parts"][0]["text"] == "system text"
    assert body["contents"][0]["parts"][0]["text"] == "user text"
    assert body["generationConfig"]["responseMimeType"] == "application/json"


def test_gemini_retries_short_rate_limits(monkeypatch, gemini_env):
    calls = {"n": 0}

    def flaky(body, headers):
        calls["n"] += 1
        if calls["n"] == 1:
            return 429, {"error": {"details": [{"retryDelay": "3s"}]}}, {}
        return reply('{"skills": ["a"]}')

    with fake_server({("POST", "/models/"): flaky}) as (url, _):
        monkeypatch.setattr(providers, "GEMINI_URL", url)
        assert GeminiProvider("m1", rpm=None).complete("s", "u") == '{"skills": ["a"]}'
    assert calls["n"] == 2


def test_gemini_stops_when_quota_is_spent(monkeypatch, gemini_env):
    spent = {("POST", "/models/"): lambda b, h: (429, {}, {"Retry-After": "3600"})}
    with fake_server(spent) as (url, _):
        monkeypatch.setattr(providers, "GEMINI_URL", url)
        with pytest.raises(ProviderError, match="quota exhausted"):
            GeminiProvider("m1", rpm=None).complete("s", "u")


def test_gemini_unknown_model(monkeypatch, gemini_env):
    with fake_server({}) as (url, _):
        monkeypatch.setattr(providers, "GEMINI_URL", url)
        with pytest.raises(ProviderError, match="not found"):
            GeminiProvider("nope", rpm=None).complete("s", "u")


def test_gemini_lists_only_generate_content_models(monkeypatch, gemini_env):
    models = {
        "models": [
            {"name": "models/flash-x", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/embed-y", "supportedGenerationMethods": ["embedContent"]},
        ]
    }
    with fake_server({("GET", "/models"): lambda b, h: (200, models, {})}) as (url, _):
        monkeypatch.setattr(providers, "GEMINI_URL", url)
        assert GeminiProvider("m1", rpm=None).list_models() == ["flash-x"]


def test_gemini_needs_a_key(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ProviderError, match="GEMINI_API_KEY"):
        GeminiProvider("m1")


def test_dotenv_does_not_override_real_env(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("# comment\nSB_A=from-file\nexport SB_B='quoted'\nSB_C=file\n")
    monkeypatch.setenv("SB_C", "from-env")
    monkeypatch.delenv("SB_A", raising=False)
    monkeypatch.delenv("SB_B", raising=False)
    providers.load_dotenv(tmp_path / ".env")
    assert (os.environ["SB_A"], os.environ["SB_B"], os.environ["SB_C"]) == (
        "from-file",
        "quoted",
        "from-env",
    )


def test_ollama_request_and_models(monkeypatch):
    routes = {
        ("POST", "/api/chat"): lambda b, h: (200, {"message": {"content": '{"skills": []}'}}, {}),
        ("GET", "/api/tags"): lambda b, h: (200, {"models": [{"name": "qwen3:8b"}]}, {}),
    }
    with fake_server(routes) as (url, seen):
        monkeypatch.setattr(providers, "OLLAMA_URL", url)
        provider = OllamaProvider("qwen3:8b")
        assert provider.complete("sys", "user") == '{"skills": []}'
        assert provider.list_models() == ["qwen3:8b"]
    body = seen[0][2]
    assert body["format"] == "json" and body["stream"] is False
    assert [m["role"] for m in body["messages"]] == ["system", "user"]


def test_ollama_not_running(monkeypatch):
    monkeypatch.setattr(providers, "OLLAMA_URL", "http://127.0.0.1:9")
    with pytest.raises(ProviderError, match="can't reach Ollama"):
        OllamaProvider("x").complete("s", "u")


def test_rate_limit_spaces_calls(monkeypatch):
    sleeps = []
    monkeypatch.setattr(providers.time, "sleep", sleeps.append)

    class Echo(providers.Provider):
        def _complete(self, system, user):
            return user

    provider = Echo("m", rpm=60)
    provider.complete("s", "1")
    provider.complete("s", "2")
    assert sleeps and 0.9 < sleeps[0] <= 1.0


def slow_then(reply_after, delay=0.5):
    """A route that stalls past the client timeout for the first `reply_after` calls."""
    calls = {"n": 0}

    def route(body, headers):
        calls["n"] += 1
        if calls["n"] <= reply_after:
            # Event.wait, not time.sleep: the gemini_env fixture stubs out time.sleep.
            threading.Event().wait(delay)
        return reply('{"skills": []}')

    return route, calls


def test_gemini_retries_a_read_timeout(monkeypatch, gemini_env):
    """Regression: a slow reply raised a bare TimeoutError and crashed the whole run."""
    route, calls = slow_then(reply_after=1)
    with fake_server({("POST", "/models/"): route}) as (url, _):
        monkeypatch.setattr(providers, "GEMINI_URL", url)
        provider = GeminiProvider("m1", rpm=None, timeout=0.2)
        assert provider.complete("s", "u") == '{"skills": []}'
    assert calls["n"] == 2


def test_gemini_gives_up_cleanly_when_the_network_keeps_failing(monkeypatch, gemini_env):
    route, _ = slow_then(reply_after=99)
    with fake_server({("POST", "/models/"): route}) as (url, _):
        monkeypatch.setattr(providers, "GEMINI_URL", url)
        with pytest.raises(ProviderError, match="network"):
            GeminiProvider("m1", rpm=None, timeout=0.2).complete("s", "u")


def test_latency_excludes_rate_limit_waiting(monkeypatch):
    """Regression: answer latency included the rate limiter's sleep, so fast models all
    looked like they took exactly 60/rpm seconds."""
    clock = {"t": 0.0}
    monkeypatch.setattr(providers.time, "monotonic", lambda: clock["t"])
    monkeypatch.setattr(providers.time, "perf_counter", lambda: clock["t"])
    monkeypatch.setattr(providers.time, "sleep", lambda s: clock.__setitem__("t", clock["t"] + s))

    class TwoSecondModel(providers.Provider):
        def _complete(self, system, user):
            clock["t"] += 2.0
            return user

    provider = TwoSecondModel("m", rpm=5)  # 12 s between calls
    provider.complete("s", "first")
    provider.complete("s", "second")  # waits ~10 s for the limiter, then 2 s of model time
    assert provider.last_seconds == 2.0
