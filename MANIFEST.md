# Frozen manifest

Frozen 2026-09-28, before the frozen evaluation run in `eval/results/`. Any
change to an item below after that run requires a new labelled evaluation
(new `eval/results-<date>/` directory), preserving prior outputs — never a
quiet overwrite.

## Corpus
- Main corpus: `data/corpus/` — 12 documents, 60 passages. Per-file SHA-256:
  `data/corpus.sha256`.
- Dev corpus (tuning only, never scored): `data/dev_corpus/` — 2 documents.
  Hashes: `data/dev_corpus.sha256`.
- Safety fixtures (not part of the scored eval): `data/fixtures/injection/`,
  `data/fixtures/conflicting_current/`. Hashes: `data/fixtures.sha256`.
- Corpus precedence metadata: each document's frontmatter carries `status`
  (`current`/`superseded`), `effective_date`, `supersedes`,
  `superseded_by`. Version authority is read from this committed metadata,
  never inferred from document prose.
- Chunking: one passage per level-2 markdown section (`## Heading`), no
  overlap. Passage id = `{doc_id}#{slugified-section-title}`. Implemented in
  `src/corpus.py`.

## Models
- Engine: Ollama 0.34.4, local daemon at `127.0.0.1:11434`, no other network
  access at inference time.
- Generator: `qwen2.5:1.5b-instruct` (Ollama tag), Ollama model ID
  `65ec06548149`, 986 MB. Upstream weights: Qwen/Qwen2.5-1.5B-Instruct.
  Weights + tokenizer + repo license: **Apache License 2.0**, verified from
  `https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/blob/main/LICENSE`
  (checked 2026-09-28; the 1.5B size is explicitly Apache-2.0, unlike the 3B
  and 72B Qwen2.5 sizes, which use the separate Qwen license — do not infer
  license from family name alone).
- Embeddings: `all-minilm:33m` (Ollama tag), Ollama model ID `4f5da3bd944d`,
  67 MB. Upstream weights: sentence-transformers/all-MiniLM-L6-v2, license
  **Apache-2.0** per the HuggingFace model card tags (checked 2026-09-28).
- Runtime license: Ollama itself is MIT-licensed. Model-weight licenses
  (above) are recorded separately from this runtime license — see
  LICENSES.md.
- Total downloaded model artifacts: 986 MB + 67 MB ≈ 1.05 GB, under the 5 GB
  cap.
- Both models were pulled once at setup time via `ollama pull` (network
  activity against the Ollama registry). All later inference in this repo is
  local only: no browsing, no tool calls, no code execution, no other
  remote model code.

## Retrieval and generation config (`src/config.py`)
- `RETRIEVAL_K = 5`
- `MAX_CONTEXT_PASSAGES = 5`, `MAX_PASSAGE_CHARS = 2000`
- Decoding: `temperature = 0.0`, `seed = 42`, `num_predict = 400`
- System prompt: frozen text in `src/qa.py::SYSTEM_PROMPT`
- Safety layer applied before every generation call, in this order:
  1. `src/sanitize.py::sanitize_for_prompt` — heuristic redaction of
     instruction-like lines in retrieved passage text (defense in depth;
     the original, unredacted passage text is still what is stored/shown in
     retrieval results and audit output).
  2. `src/qa.py::_detect_unresolved_current_conflict` — metadata-driven
     check: if two retrieved passages are both `status: current`, from
     different documents, share company + effective_date + section title,
     and neither is linked to the other via `supersedes`/`superseded_by`,
     the system abstains deterministically without calling the generator.
  3. Citation enforcement: an "answer" that cites no passage id actually
     present in the retrieved set is forced to `ABSTAIN` in code
     (`src/qa.py::_parse_output`), regardless of what the raw model output
     claims.

## Dependency and runtime versions
- Python 3.13.5 (stdlib only for the pipeline: `json`, `urllib`, `hashlib`,
  `re`, `dataclasses`, `unittest`, `pathlib`, `math`). No third-party Python
  packages are installed; see `requirements.txt` and LICENSES.md.
- OS: Linux 6.12.107+deb13-amd64.

## Prompts
- `src/qa.py::SYSTEM_PROMPT` (frozen verbatim in source).
- Per-question prompt template: `src/qa.py::_build_prompt`.

## Scoring code
- `eval/scorer.py`, written and unit-tested (`tests/test_scorer.py`) before
  any final answers were generated. Metric: keyword/alias matching against
  committed gold atomic facts plus a forbidden-term check, reported as
  **rule-scored answer agreement** — a proxy for correctness, not full
  semantic verification.

## Frozen evaluation set
- `eval/questions.jsonl`: 40 unique questions — 20 ordinary single-document
  answerable, 8 multi-document answerable, 4 version-sensitive answerable, 8
  unanswerable. Built once by `eval/_build_questions.py` (dev tooling, not
  part of the runtime pipeline) before any answers were generated. Not
  modified after generation began.
- Multi-document questions require citing passages whose `doc_id`s span 2+
  distinct source documents (`gold_passage_ids` in each question row).
- Version-sensitive questions have a `forbidden_terms` entry equal to the
  superseded version's answer, so citing/answering from the stale version
  scores as incorrect even if a gold keyword happens to also appear.

## Known dev-time leak (disclosed, not corrected retroactively)
One diagnostic query was run against the main corpus (not one of the 40
frozen questions) using an earlier draft of the system prompt, before the
prompt-citation-format fix. That fix was designed and validated afterward
against the separate `data/dev_corpus/` fixture, not against the main
corpus or any frozen question. No corpus, question, or gold-data change was
made in response to that query's output. Recorded here for honesty per the
no-quiet-tuning rule.

## Reproduction
```
ollama pull qwen2.5:1.5b-instruct
ollama pull all-minilm:33m
python3 -m src.build_index data/corpus data/index.json
python3 -m eval.run_eval
```
