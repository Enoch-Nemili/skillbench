"""
Model providers for evals. Standard library HTTP only, so the harness has no SDK dependencies.

- gemini:  Google's Gemini API (key from GEMINI_API_KEY or GOOGLE_API_KEY, or a .env file)
- ollama:  a local Ollama server (free, unlimited, runs on your machine)
- keyword: an offline word-overlap baseline (no model at all; what a dumb router would do)

Every provider turns (system prompt, user prompt) into the model's text reply.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta"
OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
if not OLLAMA_URL.startswith("http"):
    OLLAMA_URL = f"http://{OLLAMA_URL}"


class ProviderError(RuntimeError):
    """The provider failed in a way retrying now won't fix (bad key, quota spent, no server)."""


def load_dotenv(path: str | Path = ".env") -> None:
    """Read KEY=value lines from .env into the environment, without overriding real env vars."""
    path = Path(path)
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        os.environ.setdefault(key, value.strip().strip("'\""))


def _post_json(url: str, body: dict, headers: dict, timeout: float) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json", **headers},
    )
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        return json.loads(resp.read())


def _get_json(url: str, headers: dict, timeout: float) -> dict:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        return json.loads(resp.read())


def _retry_delay(err: urllib.error.HTTPError, body: str) -> float | None:
    """Seconds the server asked us to wait, from Retry-After or Gemini's RetryInfo."""
    header = err.headers.get("Retry-After") if err.headers else None
    if header and header.replace(".", "", 1).isdigit():
        return float(header)
    match = re.search(r'"retryDelay":\s*"(\d+(?:\.\d+)?)s"', body)
    return float(match.group(1)) if match else None


class Provider:
    name = "base"

    def __init__(self, model: str, temperature: float = 0.0, rpm: float | None = None):
        self.model = model
        self.temperature = temperature
        self.min_interval = 60.0 / rpm if rpm else 0.0
        self._last_call = 0.0

    def complete(self, system: str, user: str) -> str:
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()
        return self._complete(system, user)

    def _complete(self, system: str, user: str) -> str:  # pragma: no cover - interface
        raise NotImplementedError

    def list_models(self) -> list[str]:
        return []


class GeminiProvider(Provider):
    name = "gemini"
    MAX_RETRIES = 4
    MAX_WAIT = 90.0  # longer than this usually means the daily quota is spent

    def __init__(
        self, model: str, temperature: float = 0.0, rpm: float | None = 5, timeout: float = 60.0
    ):
        super().__init__(model, temperature, rpm)
        load_dotenv()
        self.key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.key:
            raise ProviderError("set GEMINI_API_KEY (or GOOGLE_API_KEY) in the environment or .env")
        self.timeout = timeout

    @property
    def _headers(self) -> dict:
        return {"x-goog-api-key": self.key}

    def _complete(self, system: str, user: str) -> str:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "responseMimeType": "application/json",
            },
        }
        url = f"{GEMINI_URL}/models/{self.model}:generateContent"
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                data = _post_json(url, body, self._headers, self.timeout)
                break
            except urllib.error.HTTPError as err:
                text = err.read().decode(errors="replace")
                if err.code in (429, 500, 503) and attempt < self.MAX_RETRIES:
                    delay = _retry_delay(err, text) or 2 ** (attempt + 2)
                    if delay > self.MAX_WAIT:
                        raise ProviderError(
                            f"quota exhausted (server asks to wait {delay:.0f}s); rerun later "
                            "and the eval resumes where it stopped"
                        ) from err
                    time.sleep(delay)
                    continue
                if err.code == 404:
                    raise ProviderError(
                        f"model {self.model!r} not found; run `skillbench models --provider gemini`"
                    ) from err
                raise ProviderError(f"Gemini API error {err.code}: {text[:300]}") from err
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts if not p.get("thought"))

    def list_models(self) -> list[str]:
        data = _get_json(f"{GEMINI_URL}/models?pageSize=1000", self._headers, self.timeout)
        return sorted(
            m["name"].removeprefix("models/")
            for m in data.get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])
        )


class OllamaProvider(Provider):
    name = "ollama"

    def __init__(
        self, model: str, temperature: float = 0.0, rpm: float | None = None, timeout: float = 180.0
    ):
        super().__init__(model, temperature, rpm)
        self.timeout = timeout

    def _complete(self, system: str, user: str) -> str:
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "format": "json",
            "options": {"temperature": self.temperature},
        }
        try:
            data = _post_json(f"{OLLAMA_URL}/api/chat", body, {}, self.timeout)
        except urllib.error.HTTPError as err:
            raise ProviderError(f"Ollama error {err.code}: {err.read()[:300]!r}") from err
        except (urllib.error.URLError, OSError) as err:
            raise ProviderError(
                f"can't reach Ollama at {OLLAMA_URL}; is `ollama serve` running?"
            ) from err
        return data.get("message", {}).get("content", "")

    def list_models(self) -> list[str]:
        try:
            data = _get_json(f"{OLLAMA_URL}/api/tags", {}, 10)
        except (urllib.error.URLError, OSError) as err:
            raise ProviderError(f"can't reach Ollama at {OLLAMA_URL}") from err
        return sorted(m["name"] for m in data.get("models", []))


_WORD = re.compile(r"[a-z0-9]+")
_STOP_WORDS = (
    "a an and are as at be but by can do does for from how i if in into is it its me my of on "
    "or our should so that the their them then there this to us use user users want we what "
    "when which who why will with you your asks ask wants need needs before after"
)
_STOP = frozenset(_STOP_WORDS.split())


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def keywords(text: str) -> set[str]:
    return {_stem(w) for w in _WORD.findall(text.lower()) if w not in _STOP}


class KeywordProvider(Provider):
    """Offline baseline: pick the skill whose name and description share the most content words
    with the request, if they share at least MIN_OVERLAP. No model, fully deterministic. The
    threshold is fixed, not tuned on the eval set."""

    name = "keyword"
    MIN_OVERLAP = 2

    def __init__(self, model: str = "overlap", temperature: float = 0.0, rpm: float | None = None):
        super().__init__(model, temperature, rpm)
        self.catalog: dict[str, set[str]] = {}

    def set_catalog(self, catalog: list[tuple[str, str]]) -> None:
        self.catalog = {
            name: keywords(f"{name.replace('-', ' ')} {desc}") for name, desc in catalog
        }

    def _complete(self, system: str, user: str) -> str:
        request = keywords(user)
        scored = sorted(
            ((len(request & words), name) for name, words in self.catalog.items()),
            key=lambda pair: (-pair[0], pair[1]),
        )
        chosen = [scored[0][1]] if scored and scored[0][0] >= self.MIN_OVERLAP else []
        return json.dumps({"skills": chosen})


PROVIDERS = {"gemini": GeminiProvider, "ollama": OllamaProvider, "keyword": KeywordProvider}


def make_provider(
    name: str, model: str | None, temperature: float = 0.0, rpm: float | None = None
) -> Provider:
    if name not in PROVIDERS:
        raise ProviderError(f"unknown provider {name!r}; choose from {', '.join(PROVIDERS)}")
    if name != "keyword" and not model:
        raise ProviderError(f"--model is required for {name}; list them with `skillbench models`")
    kwargs = {"temperature": temperature}
    if rpm is not None:
        kwargs["rpm"] = rpm
    return PROVIDERS[name](model or "overlap", **kwargs)
