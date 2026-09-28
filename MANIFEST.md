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
- `MAX_CONTEXT_PASSAGES = 5`, `MAX_PASSAGE_CHARS = 2000` (per-passage chars
  placed in the *prompt*), `INDEX_MAX_PASSAGE_CHARS = 4000` (per-passage
  chars kept at *indexing* time). The prompt bound is deliberately smaller
  and re-truncates already-indexed text on every generation call; this is an
  explicit second cut, not silent extra data loss, and each passage records
  `truncated_at_index` for provenance.
- Decoding: `temperature = 0.0`, `seed = 42`, `num_predict = 400`
- System prompt: frozen text in `src/qa.py::SYSTEM_PROMPT`; per-passage
  metadata shown to the model (`src/qa.py::_build_prompt`) includes title,
  version, status, company, effective_date, supersedes, and superseded_by —
  all fields the prompt rules instruct the model to reason over.
- Index integrity: the persisted index is hash-bound to the corpus bytes
  (`src/corpus.py::corpus_fingerprint`), the embedding model, and the
  chunking scheme (`src/corpus.py::CHUNK_VERSION`). Both `load_index` and
  every `retrieve()` call (including on an in-memory index dict) re-validate
  this binding plus internal structure — passage count, per-passage content
  hash, embedding presence/dimension/finiteness — via
  `src/index.py::_validate_index_integrity`, raising `IndexIntegrityError`
  on any mismatch instead of retrieving against stale or corrupted data.
- Safety layer applied before every generation call, in this order:
  1. `src/sanitize.py::sanitize_for_prompt` — heuristic redaction of
     instruction-like lines in retrieved passage text (defense in depth;
     the original, unredacted passage text is still what is stored/shown in
     retrieval results and audit output).
  2. `src/qa.py::_detect_unresolved_current_conflict` — a bounded,
     metadata-only guard scoped to this synthetic corpus's fixed frontmatter
     schema: if two retrieved passages are both `status: current`, from
     different `doc_id`s, and share an identical (company, effective_date,
     section_title) key, with neither linked to the other via
     `supersedes`/`superseded_by`, the system abstains deterministically
     without calling the generator. It does not compare the passages'
     actual claims and does not detect precedence expressed any other way —
     narrowly scoped, not a general contradiction detector.
  3. Citation enforcement: an "answer" is validated against exactly the
     passage ids placed in *that prompt's context* (not the broader
     retrieved set). Any citation outside that context — fabricated, or a
     retrieved-but-not-shown id when `k` exceeds `MAX_CONTEXT_PASSAGES` —
     forces the whole answer to `ABSTAIN` in code
     (`src/qa.py::_parse_output`), even when mixed with otherwise-valid
     citations, regardless of what the raw model output claims. The
     rendered `text` on the abstention path is always a clean `ABSTAIN`
     marker; the model's raw attempt is retained separately in
     `raw_model_output` as diagnostic evidence only, never as the displayed
     answer.
- Local network boundary: `src/ollama_client.py` refuses any URL whose host
  is not `127.0.0.1`/`localhost`/`::1`, ignores inherited
  `HTTP_PROXY`/`HTTPS_PROXY` environment variables, refuses to follow HTTP
  redirects, bounds every response to `MAX_OLLAMA_RESPONSE_BYTES` (10 MB),
  and validates the shape of both the embedding and generation responses
  before use.
- Corpus input bounds: `src/corpus.py` rejects any single source document
  over `MAX_CORPUS_FILE_BYTES` (2 MB) and any corpus directory yielding more
  than `MAX_CORPUS_PASSAGES` (500) passages, in addition to the existing
  zero-byte/duplicate-id/missing-frontmatter/path-escape checks.

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
  committed gold atomic facts — discounting an alias mention that is negated
  in the same sentence (e.g. "X is not the default" does not support "X is
  the default") — plus a forbidden-term check and a bounded
  unsupported-numeric/monetary-claim check (a number, percentage, or
  monetary amount asserted in the answer that appears in none of the gold
  facts/aliases/question text), reported as **rule-scored answer
  agreement** — a bounded, explicit, pattern-based adjudication protocol,
  still a proxy for correctness, not full semantic verification; non-numeric
  unsupported additions are a known residual gap.
- Correctness additionally requires: citation validity against the actual
  prompt context, no invalid/fabricated citations, and the exact gold
  passage id(s) among the citations (not merely the right document — a
  citation to the wrong section of the right document is not correct).
- The retrieval statistic historically reported as "recall@5" is a
  per-question all-or-nothing hit on the full gold passage group
  (`all_gold_passages_retrieved_rate`), not fractional passage recall@5;
  renamed throughout `eval/scorer.py`, `eval/run_eval.py`, and `README.md`
  to avoid that ambiguity.

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

## Frozen evidence and result preservation
- `eval/results/` (40 answers, scores, report) is **retained evidence** of
  the original run against the pre-fix pipeline and scorer. It is not
  deleted, regenerated, or overwritten by the review-response fixes below —
  `eval/run_eval.py`'s default entry point now refuses to overwrite it.
- Independent review (`~/vault/40-sessions/2026-09-28-astra-local-document-qa-review.md`)
  found defects in the pre-fix scorer (negation and unsupported-claim
  blindness, doc-level-only citation checks) and pipeline (index staleness,
  citation scope, non-loopback network defaults, missing precedence
  metadata in the prompt). The code was corrected in place; per the
  no-silent-overwrite rule, the retained answers were **re-scored, not
  regenerated**, with the corrected `eval/scorer.py`:
  `python3 -m eval.run_eval --rescore-retained <label>` writes a new
  `eval/results-rescored-<label>/` directory containing both
  `old_aggregate` (the original committed numbers) and the new
  `system.aggregate`, plus full corpus/model/config provenance
  (`corpus_fingerprint`, `chunk_version`, model tags, question/scorer
  hashes) — see that directory's `scores.json` and `report.md` for the
  actual before/after numbers.
- The manifest and pipeline fixes above were **not** validated by running a
  brand-new generation pass against the frozen 40 questions: doing so would
  not be a new holdout (the questions are already exposed) and would risk
  exactly the silent-regeneration failure mode this section exists to
  avoid. A prospective successor evaluation, on a freshly frozen question
  set, is the correct way to measure the fixed pipeline's end-to-end
  answer quality; that is future work, not claimed here.
- This manifest's own freeze timing relative to the original evaluation
  rests on the single commit history disclosed above (`27e8215`); no
  additional independent pre-evaluation hash evidence beyond that commit is
  available. The original `eval/results/` should be read as **post-development
  evidence from that commit**, not a blind prospective holdout.
- A second review round (`~/vault/40-sessions/2026-09-28-astra-local-document-qa-r2-review.md`)
  found that the round-1 `_provenance_snapshot` recorded tags/questions/
  scorer at write time but did not enforce a true *pre-run* freeze of exact
  model/tokenizer/artifact identity, runtime, and sources/prompts/config
  before generation starts, and that a labelled run directory could still be
  overwritten by re-running the same `--label`. `eval/run_eval.py`'s
  `main()` (both the default and `--label` paths) is now **disabled** —
  it refuses immediately with a clear message — until a reviewed successor
  adds that pre-run freeze; `--rescore-retained` is unaffected; it still
  calls no model and never touches `eval/results/`. This release is scoped
  to the retained `eval/results/` and `eval/results-rescored-*/` evidence,
  not to any new generation pass. The round-2 review's scoring finding
  (numeric-only unsupported-claim filtering does not assess atomic support)
  is addressed by `eval/adjudication-2026-09-28.csv`, a bounded manual
  AI-builder adjudication (not human, not independent validation) of the retained 40 answers, reported alongside —
  not in place of — the rule score; see `README.md`.

## Reproduction
```
ollama pull qwen2.5:1.5b-instruct
ollama pull all-minilm:33m
python3 -m src.build_index data/corpus data/index.json

# Generation runs are DISABLED as of the round-2 review (both of these
# refuse immediately with a clear message; see "Frozen evidence" above):
python3 -m eval.run_eval
python3 -m eval.run_eval --label <name>

# Re-score the retained eval/results/answers.jsonl with the current scorer,
# without calling the model or touching eval/results/ (NOT disabled):
python3 -m eval.run_eval --rescore-retained <name>
```
