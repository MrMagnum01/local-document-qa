"""Thin stdlib-only HTTP client for the local Ollama daemon.

No third-party dependencies: uses urllib from the standard library. Every
network call this module makes must resolve to a loopback host
(`config.OLLAMA_ALLOWED_HOSTS`); the opener ignores inherited HTTP(S)_PROXY
environment variables and refuses to follow any HTTP redirect, so a
compromised or misconfigured environment cannot silently redirect inference
traffic off-box. Responses are read up to a fixed byte bound
(`config.MAX_OLLAMA_RESPONSE_BYTES`) rather than as an unbounded whole-file
read, and each response's shape is validated before use. The models must
already have been pulled (setup-time step, see README).
"""
import json
import urllib.error
import urllib.parse
import urllib.request

from . import config


class OllamaError(RuntimeError):
    pass


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise OllamaError(f"Refusing to follow HTTP redirect from local Ollama endpoint to {newurl!r}")


def _build_opener():
    # ProxyHandler({}) (an explicit empty mapping, not the None default) never
    # calls getproxies(), so no inherited HTTP_PROXY/HTTPS_PROXY/NO_PROXY env
    # var is honoured; _NoRedirectHandler refuses every HTTP redirect.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirectHandler())


_opener = _build_opener()


def _require_loopback(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in config.OLLAMA_ALLOWED_HOSTS:
        raise OllamaError(
            f"Refusing non-loopback Ollama URL {url!r}; only http://<{'|'.join(sorted(config.OLLAMA_ALLOWED_HOSTS))}> is permitted."
        )


def _post(path: str, payload: dict) -> dict:
    url = config.OLLAMA_URL.rstrip("/") + path
    _require_loopback(url)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with _opener.open(req, timeout=config.HTTP_TIMEOUT) as resp:
            body = resp.read(config.MAX_OLLAMA_RESPONSE_BYTES + 1)
    except urllib.error.URLError as exc:
        raise OllamaError(
            f"Could not reach Ollama at {url}. Is `ollama serve` running and the "
            f"model pulled? ({exc})"
        ) from exc
    if len(body) > config.MAX_OLLAMA_RESPONSE_BYTES:
        raise OllamaError(
            f"Response from {url} exceeded the {config.MAX_OLLAMA_RESPONSE_BYTES}-byte bound; refusing to load it."
        )
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OllamaError(f"Malformed JSON response from {url}: {exc}") from exc


def embed(text: str, model: str = None) -> list:
    model = model or config.EMBED_MODEL
    resp = _post("/api/embeddings", {"model": model, "prompt": text})
    vec = resp.get("embedding")
    if not isinstance(vec, list) or not vec or not all(isinstance(x, (int, float)) for x in vec):
        raise OllamaError(f"Malformed or missing embedding in response: {resp}")
    return vec


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
    text = resp.get("response")
    if not isinstance(text, str):
        raise OllamaError(f"Malformed or missing 'response' field in generation output: {resp}")
    return text
