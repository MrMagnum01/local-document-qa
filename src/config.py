"""Frozen runtime configuration. Changing these values after the eval freeze
requires a new manifest entry and a new labelled evaluation (see MANIFEST.md)."""

OLLAMA_URL = "http://127.0.0.1:11434"

EMBED_MODEL = "all-minilm:33m"
GEN_MODEL = "qwen2.5:1.5b-instruct"

RETRIEVAL_K = 5
MAX_PASSAGE_CHARS = 2000       # bound on context size per passage
MAX_CONTEXT_PASSAGES = 5       # bound on total passages placed in the prompt

GEN_OPTIONS = {
    "temperature": 0.0,
    "seed": 42,
    "num_predict": 400,
}

# HTTP timeouts (seconds) for local Ollama calls only. No other network access
# is performed at inference time.
HTTP_TIMEOUT = 120

ABSTAIN_TOKEN = "ABSTAIN"
