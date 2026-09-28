"""Embedding index: build, persist, and retrieve.

The persisted index records the corpus directory, each passage's content
hash, and the embedding model name so a stale index (built from an older
corpus) can be detected rather than silently used.
"""
import json
import math
from pathlib import Path

from . import config
from .corpus import load_corpus
from .ollama_client import embed


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
                "embedding": vec,
            }
        )
    return {
        "corpus_dir": corpus_dir,
        "embed_model": embed_model,
        "passage_count": len(entries),
        "passages": entries,
    }


def save_index(index: dict, path: str) -> None:
    Path(path).write_text(json.dumps(index), encoding="utf-8")


def load_index(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Index not found at {path}. Run `python -m src.build_index` first."
        )
    return json.loads(p.read_text(encoding="utf-8"))


def _cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def retrieve(question: str, index: dict, k: int = None, embed_model: str = None) -> list:
    k = k or config.RETRIEVAL_K
    embed_model = embed_model or index.get("embed_model", config.EMBED_MODEL)
    qvec = embed(question, model=embed_model)
    scored = [
        (_cosine(qvec, entry["embedding"]), entry) for entry in index["passages"]
    ]
    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:k]
    return [{"score": score, **{k2: v for k2, v in entry.items() if k2 != "embedding"}} for score, entry in top]
