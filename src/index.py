"""Embedding index: build, persist, and retrieve.

The persisted index is hash-bound to the corpus bytes, the embedding model,
and the chunking scheme (`src.corpus.CHUNK_VERSION`) at build time. Every
retrieval call re-validates this binding against the live corpus directory
and the index's own internal structure (`_validate_index_integrity` below),
so a stale, edited, or corrupted index errors explicitly instead of being
used silently -- including when the index dict is held in memory and never
round-tripped through `load_index`.
"""
import hashlib
import json
import math
from pathlib import Path

from . import config
from .corpus import CHUNK_VERSION, corpus_fingerprint, load_corpus, passage_binding_hash
from .ollama_client import embed

REQUIRED_INDEX_FIELDS = {
    "corpus_dir", "embed_model", "chunk_version", "corpus_fingerprint",
    "passage_count", "passages",
}
REQUIRED_PASSAGE_FIELDS = {
    "id", "doc_id", "section_title", "text", "company", "doc_type", "title",
    "version", "effective_date", "status", "content_hash", "embedding",
}


class IndexIntegrityError(RuntimeError):
    """The index is missing, stale, structurally malformed, or was built
    from a different corpus/model/chunking-config than what is live now."""


def build_index(corpus_dir: str, embed_model: str = None) -> dict:
    embed_model = embed_model or config.EMBED_MODEL
    passages = load_corpus(corpus_dir)
    entries = []
    for p in passages:
        vec = embed(p.text, model=embed_model)
        entries.append(
            {
                "id": p.id,
                "doc_id": p.doc_id,
                "section_title": p.section_title,
                "text": p.text,
                "company": p.company,
                "doc_type": p.doc_type,
                "title": p.title,
                "version": p.version,
                "effective_date": p.effective_date,
                "status": p.status,
                "supersedes": p.supersedes,
                "superseded_by": p.superseded_by,
                "content_hash": p.content_hash,
                "truncated_at_index": p.truncated_at_index,
                "embedding": vec,
            }
        )
    return {
        "corpus_dir": corpus_dir,
        "embed_model": embed_model,
        "chunk_version": CHUNK_VERSION,
        "corpus_fingerprint": corpus_fingerprint(corpus_dir),
        "passage_count": len(entries),
        "passages": entries,
    }


def save_index(index: dict, path: str) -> None:
    Path(path).write_text(json.dumps(index), encoding="utf-8")


def _validate_index_integrity(index: dict) -> int:
    """Raise `IndexIntegrityError` on any structural, staleness, or binding
    problem; otherwise return the index's passage embedding dimension (0 if
    the index has no passages) so callers that already paid for this
    validation (`retrieve`) can reuse it for query-vector dimension
    checking instead of re-deriving it."""
    missing = REQUIRED_INDEX_FIELDS - index.keys()
    if missing:
        raise IndexIntegrityError(f"Index is missing required field(s): {sorted(missing)}")

    if index["chunk_version"] != CHUNK_VERSION:
        raise IndexIntegrityError(
            f"Index chunking version {index['chunk_version']!r} does not match the "
            f"current chunking scheme {CHUNK_VERSION!r}; rebuild the index."
        )

    if index["embed_model"] != config.EMBED_MODEL:
        raise IndexIntegrityError(
            f"Index was built with embedding model {index['embed_model']!r}, but the "
            f"configured model is {config.EMBED_MODEL!r} (model drift); rebuild the index."
        )

    try:
        live_fingerprint = corpus_fingerprint(index["corpus_dir"])
    except Exception as exc:
        raise IndexIntegrityError(
            f"Cannot verify corpus at {index['corpus_dir']!r}: {exc}"
        ) from exc
    if live_fingerprint != index["corpus_fingerprint"]:
        raise IndexIntegrityError(
            f"Index corpus fingerprint does not match the live corpus directory "
            f"({index['corpus_dir']!r}); the corpus changed since the index was built. "
            "Rebuild the index."
        )

    passages = index["passages"]
    if len(passages) != index["passage_count"]:
        raise IndexIntegrityError(
            f"Index passage_count ({index['passage_count']}) does not match the number "
            f"of stored passages ({len(passages)})."
        )

    dim = None
    for entry in passages:
        pid = entry.get("id", "<unknown>")
        missing_fields = REQUIRED_PASSAGE_FIELDS - entry.keys()
        if missing_fields:
            raise IndexIntegrityError(f"Passage {pid!r} is missing field(s): {sorted(missing_fields)}")

        expected_hash = passage_binding_hash(
            doc_id=entry["doc_id"], section_title=entry["section_title"], text=entry["text"],
            company=entry["company"], doc_type=entry["doc_type"], title=entry["title"],
            version=entry["version"], effective_date=entry["effective_date"], status=entry["status"],
            supersedes=entry.get("supersedes"), superseded_by=entry.get("superseded_by"),
        )
        if entry["content_hash"] != expected_hash:
            raise IndexIntegrityError(
                f"Passage {pid!r} content hash does not match its stored text/metadata "
                "(edited or corrupted index): company, status, supersedes/superseded_by, "
                "version, effective_date, and text are all bound to this hash."
            )

        emb = entry["embedding"]
        if not isinstance(emb, list) or not emb:
            raise IndexIntegrityError(f"Passage {pid!r} has an empty or malformed embedding.")
        if dim is None:
            dim = len(emb)
        elif len(emb) != dim:
            raise IndexIntegrityError(
                f"Passage {pid!r} embedding dimension {len(emb)} does not match the "
                f"index's dimension {dim}."
            )
        if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in emb):
            raise IndexIntegrityError(f"Passage {pid!r} embedding contains non-finite or non-numeric values.")

    return dim or 0


def load_index(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Index not found at {path}. Run `python -m src.build_index` first."
        )
    index = json.loads(p.read_text(encoding="utf-8"))
    _validate_index_integrity(index)
    return index


def _cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def retrieve(question: str, index: dict, k: int = None, embed_model: str = None) -> list:
    dim = _validate_index_integrity(index)
    k = k or config.RETRIEVAL_K

    if embed_model is not None and embed_model != index["embed_model"]:
        raise IndexIntegrityError(
            f"Refusing embed_model override {embed_model!r} at query time; this index is "
            f"bound to {index['embed_model']!r}. A different query-time model would score "
            "against embeddings it did not produce. Rebuild the index to change models."
        )
    embed_model = index["embed_model"]

    qvec = embed(question, model=embed_model)
    if (
        not isinstance(qvec, list)
        or not qvec
        or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in qvec)
    ):
        raise IndexIntegrityError(
            "Query embedding is empty, malformed, or contains non-finite/non-numeric values; "
            "refusing to score it against the index."
        )
    if dim and len(qvec) != dim:
        raise IndexIntegrityError(
            f"Query embedding dimension ({len(qvec)}) does not match the index's passage "
            f"embedding dimension ({dim}); refusing to score a dimension-mismatched vector."
        )

    scored = [
        (_cosine(qvec, entry["embedding"]), entry) for entry in index["passages"]
    ]
    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:k]
    return [{"score": score, **{k2: v for k2, v in entry.items() if k2 != "embedding"}} for score, entry in top]
