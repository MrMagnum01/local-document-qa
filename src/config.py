"""Frozen runtime configuration. Changing these values after the eval freeze
requires a new manifest entry and a new labelled evaluation (see MANIFEST.md)."""

OLLAMA_URL = "http://127.0.0.1:11434"

EMBED_MODEL = "all-minilm:33m"
GEN_MODEL = "qwen2.5:1.5b-instruct"

RETRIEVAL_K = 5
INDEX_MAX_PASSAGE_CHARS = 4000  # bound on section text kept at indexing time
MAX_PASSAGE_CHARS = 2000       # bound on context size per passage placed in a prompt
MAX_CONTEXT_PASSAGES = 5       # bound on total passages placed in the prompt

# MAX_PASSAGE_CHARS is intentionally smaller than INDEX_MAX_PASSAGE_CHARS: every
# generation call re-truncates already-indexed text. This is a second, explicit
# cut, not silent data loss on top of the index-time bound (see MANIFEST.md).
assert MAX_PASSAGE_CHARS <= INDEX_MAX_PASSAGE_CHARS

GEN_OPTIONS = {
    "temperature": 0.0,
    "seed": 42,
    "num_predict": 400,
}

# HTTP timeouts (seconds) for local Ollama calls only. No other network access
# is performed at inference time.
HTTP_TIMEOUT = 120

# Local-boundary and response-size bounds enforced in src/ollama_client.py.
OLLAMA_ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}
MAX_OLLAMA_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MB bound per HTTP response

# Corpus loading bounds enforced in src/corpus.py.
MAX_CORPUS_FILE_BYTES = 2_000_000   # bound on a single source document
MAX_CORPUS_PASSAGES = 500           # bound on total passages loaded from one corpus dir

ABSTAIN_TOKEN = "ABSTAIN"
