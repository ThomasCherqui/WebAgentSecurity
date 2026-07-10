from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class OllamaChatError(RuntimeError):
    """Raised when the Ollama backend cannot return a real response."""


def normalize_ollama_host(host: str | None = None) -> str:
    value = (host or os.getenv("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
    if not (value.startswith("http://") or value.startswith("https://")):
        value = "http://" + value
    return value


def ollama_chat(prompt: str, model: str, host: str | None = None, temperature: float = 0.0, max_tokens: int = 4096) -> str:
    host = normalize_ollama_host(host)
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": "You are a careful privacy adjudicator. Return valid JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    req = urllib.request.Request(
        host + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise OllamaChatError(f"Ollama HTTP {e.code} at {host}: {body}") from e
    except urllib.error.URLError as e:
        raise OllamaChatError(f"Could not reach Ollama at {host}. Is `ollama serve` running?") from e
    return str((data.get("message") or {}).get("content", ""))


def safe_ollama_chat(prompt: str, model: str, host: str | None = None, allow_errors: bool = False) -> str:
    _ = allow_errors
    return ollama_chat(prompt, model, host=host)
