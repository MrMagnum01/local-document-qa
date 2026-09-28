"""Corpus loading and chunking.

Frozen chunking scheme (see MANIFEST.md): one passage per level-2 markdown
section ("## Heading"), no overlap. Passage id = "{doc_id}#{section-slug}".

Access is restricted to files that resolve inside the declared corpus
directory: no path escapes, and symlinks pointing outside the corpus root
are rejected.
"""
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
SECTION_RE = re.compile(r"^##\s+(.+)$")


class CorpusError(ValueError):
    pass


@dataclass
class Passage:
    id: str
    doc_id: str
    section_title: str
    text: str
    company: str
    doc_type: str
    title: str
    version: str
    effective_date: str
    status: str
    supersedes: str = None
    superseded_by: str = None
    content_hash: str = field(default="")

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.text.encode("utf-8")).hexdigest()[:16]


def _slug(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _parse_frontmatter(raw: str) -> dict:
    meta = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip().strip('"')
        if value.lower() == "null" or value == "":
            value = None
        meta[key.strip()] = value
    return meta


def parse_document(path: Path) -> tuple:
    raw = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(raw)
    if not m:
        raise CorpusError(f"{path}: missing YAML-style frontmatter block")
    meta = _parse_frontmatter(m.group(1))
    body = m.group(2)
    required = ["id", "company", "doc_type", "title", "version", "effective_date", "status"]
    missing = [k for k in required if not meta.get(k)]
    if missing:
        raise CorpusError(f"{path}: frontmatter missing required fields {missing}")

    sections = []
    current_title = None
    current_lines = []
    for line in body.splitlines():
        sec = SECTION_RE.match(line)
        if sec:
            if current_title is not None:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = sec.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_title is not None:
        sections.append((current_title, "\n".join(current_lines).strip()))

    if not sections:
        raise CorpusError(f"{path}: no '## ' sections found — zero-chunk document")

    return meta, sections


def _resolve_within(root: Path, path: Path) -> Path:
    root_r = root.resolve()
    path_r = path.resolve()
    if root_r not in path_r.parents and path_r != root_r:
        raise CorpusError(f"Path escapes declared corpus root: {path}")
    return path_r


def load_corpus(corpus_dir: str) -> list:
    root = Path(corpus_dir)
    if not root.is_dir():
        raise CorpusError(f"Corpus directory does not exist: {corpus_dir}")

    passages = []
    seen_ids = set()
    for path in sorted(root.glob("*.md")):
        _resolve_within(root, path)
        if path.stat().st_size == 0:
            raise CorpusError(f"{path}: zero-byte document")
        meta, sections = parse_document(path)
        doc_id = meta["id"]
        for title, text in sections:
            if not text:
                continue
            pid = f"{doc_id}#{_slug(title)}"
            if pid in seen_ids:
                raise CorpusError(f"Duplicate passage id: {pid}")
            seen_ids.add(pid)
            passages.append(
                Passage(
                    id=pid,
                    doc_id=doc_id,
                    section_title=title,
                    text=text[: 4000],
                    company=meta["company"],
                    doc_type=meta["doc_type"],
                    title=meta["title"],
                    version=meta["version"],
                    effective_date=meta["effective_date"],
                    status=meta["status"],
                    supersedes=meta.get("supersedes"),
                    superseded_by=meta.get("superseded_by"),
                )
            )
    if not passages:
        raise CorpusError(f"No passages loaded from {corpus_dir} — empty corpus")
    return passages
