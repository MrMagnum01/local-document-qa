"""Thin stdlib-only HTTP client for the local Ollama daemon.

No third-party dependencies: uses urllib from the standard library. The only
network calls this module makes are to OLLAMA_URL (127.0.0.1), which must
already have the required models pulled (setup-time step, see README).
"""
import json
import urllib.request
import urllib.error

from . import config


class OllamaError(RuntimeError):
    pass


def _post(path: str, payload: dict) -> dict:
    url = config.OLLAMA_URL.rstrip("/") + path
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise OllamaError(
            f"Could not reach Ollama at {url}. Is `ollama serve` running and the "
            f"model pulled? ({exc})"
        ) from exc


def embed(text: str, model: str = None) -> list:
    model = model or config.EMBED_MODEL
    resp = _post("/api/embeddings", {"model": model, "prompt": text})
    if "embedding" not in resp:
        raise OllamaError(f"No embedding in response: {resp}")
    return resp["embedding"]


def generate(prompt: str, model: str = None, system: str = None, options: dict = None) -> str:
    model = model or config.GEN_MODEL
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": options or config.GEN_OPTIONS,
    }
    if system:
        payload["system"] = system
    resp = _post("/api/generate", payload)
    if "response" not in resp:
        raise OllamaError(f"No response field in generation output: {resp}")
    return resp["response"]
