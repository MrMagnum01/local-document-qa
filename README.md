# Local Document Q&A

Retrieval-augmented question answering over a synthetic document corpus
(company policies, product manuals, FAQs), running entirely on local
models via [Ollama](https://ollama.com). Answers cite the passage id(s)
they used, or explicitly abstain — an uncited "answer" is never presented
as a success.

**Role:** Synthetic portfolio demonstration, implemented with AI coding
agents.  No client data or client work.

**Independent review:** cleared by the company’s separate AI reviewer at commit 65ac5a4 (scope: bounded synthetic demo; local models, no real documents or production use). Later commits are not covered by that review.

Relevant Upwork job types: "RAG chatbot over company documents", "AI
document Q&A", "local/private LLM assistant".

## What this is
- A 12-document synthetic corpus across 3 fictional companies (an IT
  products company, a healthcare-adjacent HR department, and a retailer),
  including two policies with a superseded and a current version each.
- A retrieval pipeline (embedding + cosine similarity, k=5) and a local
  generator (Qwen2.5-1.5B-Instruct via Ollama) that answers only from
  retrieved passages, cites passage ids, and abstains when it should.
- A frozen 40-question evaluation set (`eval/questions.jsonl`), committed
  before any answers were generated, with a rule-based scorer
  (`eval/scorer.py`, no LLM-as-judge) and a full frozen manifest
  (`MANIFEST.md`).
- Safety tests for prompt injection and for contradictory current documents
  with no defined precedence (`tests/test_safety.py`).

## What this is not / out of scope
- Not a hosted chat UI — this is a CLI pipeline over synthetic files.
- Not tested against real customer documents.
- No fine-tuning of any model.
- No guarantee of answer accuracy for arbitrary questions or corpora —
  measured numbers below are reported "on this synthetic set" only.

## Setup
Requires [Ollama](https://ollama.com) installed and running locally
(`ollama serve`, or the systemd service). The first run of the commands
below pulls the two models from the Ollama model registry — this is the
only network activity in this project; all inference afterward is local.

```bash
ollama pull qwen2.5:1.5b-instruct   # ~986 MB, Apache-2.0 weights
ollama pull all-minilm:33m          # ~67 MB, Apache-2.0 weights
```

No Python packages are required — the pipeline uses only the standard
library (see `requirements.txt`, `LICENSES.md`).

## Quickstart
```bash
python3 -m src.build_index          # builds data/index.json from data/corpus/
./run_demo.sh                       # answers one sample question
```

## Running the tests
```bash
python3 -m unittest tests.test_corpus tests.test_scorer tests.test_qa \
                     tests.test_index tests.test_local_bounds tests.test_run_eval  # fast, no network
python3 -m unittest tests.test_safety                                              # needs Ollama, ~30-60s on CPU
```

## Running the frozen evaluation
Already run once; `eval/results/` holds the original 40-answer run and is
retained as evidence. **New generation-evaluation runs are currently
disabled** (2026-09-28 round-2 review, group 6): the pre-run freeze
`eval/run_eval.py` wrote at generation time bound tags/questions/scorer,
not a true pre-run binding of exact model/tokenizer/artifact identity,
runtime, and sources/prompts/config before generation starts, and a
labelled run directory could still be overwritten by re-running the same
`--label`. `main()` now refuses immediately, on both the default and
`--label` paths, until a reviewed successor adds that freeze:
```bash
python3 -m eval.run_eval                            # DISABLED: refuses with a clear message
python3 -m eval.run_eval --label <name>              # DISABLED: refuses with a clear message
python3 -m eval.run_eval --rescore-retained <name>   # NOT disabled: re-score eval/results/ with the
                                                      # current scorer, no model call, no regeneration
```
Per `MANIFEST.md`, a scorer fix gets a labelled re-score of the retained
answers (above), never a silent overwrite of committed numbers; a genuinely
new generation pass is not available through this entry point at all right
now.

## Results, on this synthetic set
See `eval/results/report.md` / `eval/results/scores.json` for the original
committed 40-question run, and
`eval/results-rescored-fix-2026-09-28/report.md` for the same retained
answers re-scored against the corrected `eval/scorer.py` (2026-09-28 review
fixes: negation and unsupported-claim rejection, exact gold-passage citation
match instead of doc-level only). Both are preserved; neither was
regenerated. Headline numbers, original vs. re-scored:

| Metric | Original | Re-scored |
|---|---|---|
| All-gold-passages-retrieved rate @k=5 (per-question all-or-nothing on the full gold group, not fractional recall) | 90.6% (29/32) | 90.6% (29/32) |
| Multi-document all-required-sources recall@5 | 100% (8/8) | 100% (8/8) |
| Rule-scored answer agreement (answerable questions) | 62.5% (20/32) | 50.0% (16/32) |
| False abstention rate on answerable questions | 0% | 0% |
| Abstention precision / recall | 100% (5/5) / 62.5% (5/8) | 100% (5/5) / 62.5% (5/8) |
| Always-abstain baseline: abstention precision / recall | 20% (8/40) / 100% (8/8) | 20% (8/40) / 100% (8/8) |

The re-scored agreement is lower because the corrected scorer now rejects
negated alias matches, a bounded class of unsupported numeric/monetary
claims, and citations to the wrong passage within an otherwise-correct
document — cases the original scorer counted as correct. Retrieval and
citation precision/recall are unchanged because the underlying retained
answers were not regenerated; only the scoring rule changed. The
always-abstain baseline is reported alongside these numbers specifically to
expose that a trivial "never answer" system would score 100% abstention
recall but only 20% abstention precision — the real system's split is not a
vacuous safety score.

"Rule-scored answer agreement" is keyword/alias matching against committed
gold atomic facts — discounting a negated alias mention — plus a
forbidden-term check and a bounded unsupported-numeric/monetary-claim check.
**This is pattern matching, not a semantic judge of whether an answer's
claims are actually supported by its cited passages** — no automatic
scorer in this repo evaluates support; the AI-builder adjudication below is a separate check by the AI agent that built the demo, not a human or independent validation.
The rule check both over- and under-fires: it misses paraphrases (e.g. "not
counted against" for the gold alias "not deducted"), misses forbidden
claims split by an inserted word (e.g. "no per-person cap" vs. the
forbidden term "no cap"), and penalizes verbatim-sourced text that happens
to contain a bare number not present in the gold aliases. See
`eval/scorer.py` for the code.

**AI-builder adjudication of the retained 40 answers** (not human, not independent validation)
(`eval/adjudication-2026-09-28.csv`, 2026-09-28 round-2 review, group 2): a
the AI coding agent that built this demo read every retained answer against its gold facts and citations and
labelled it supported / partial / unsupported / contradictory /
correctly-abstained, with a reason, independent of the rule scorer.
Adjudicated agreement on the 32 answerable questions — an answer counted
correct only if its content is supported **and** grounded in a cited gold
passage — is **62.5% (20/32)**, alongside the rule score's 50.0% (16/32).
These numbers diverge for different reasons in both directions: the rule
scorer both over-penalizes (paraphrases, verbatim-but-flagged numbers) and
under-catches (q014, q015 directly contradict the source cap/approval
amounts but dodge the exact-substring forbidden-term check by one inserted
word). The full reasoning for all 40 rows, including 5 of 8 unanswerable
questions correctly abstained and 3 where the system should have abstained
but fabricated or misattributed an answer instead, is in the CSV. This
adjudication is a bounded, one-time AI-builder review of these specific 40
retained outputs, not a repeatable automatic judge — a future evaluation
run has no equivalent unless it is re-adjudicated. No human has reviewed these labels; the separate AI reviewer spot-checked the arithmetic (20/32) and two rows (q014, q015) only.

No positive accuracy threshold was required for this demo to ship: the
generator is a small (1.5B parameter) CPU-only model, and its answer
quality is exactly what is reported above — the retrieval,
citation-enforcement, and abstention-safety pipeline is the part of this
demo with the stronger claim.

## Safety design
- **Documents are data, not instructions.** Retrieved passage text is
  heuristically scanned for instruction-injection markers and redacted
  before it reaches the generator (`src/sanitize.py`), on top of an explicit
  system-prompt instruction never to follow in-document instructions, visit
  URLs, or call tools. Tested against injected "ignore previous
  instructions" / "reveal your system prompt" / fake system-override blocks
  in `tests/test_safety.py`. This proves observed behavior on these specific
  fixtures, not universal prompt-injection resistance.
- **Every answer cites a real passage id from its own prompt, or abstains.**
  Citation ids are validated against exactly the passages placed in that
  prompt's context — not the broader retrieved set — in code. Any citation
  outside that context (fabricated, or a retrieved-but-unshown id) forces
  the whole answer to `ABSTAIN`, even when mixed with otherwise-valid
  citations (`src/qa.py::_parse_output`); the rendered text on that path is
  always a clean abstention marker, and the model's raw attempt is kept
  only as diagnostic evidence — the renderer cannot turn an uncited or
  partially-fabricated answer into a success.
- **Version authority comes from committed metadata**, not document prose:
  each document's frontmatter states `status`, `effective_date`,
  `supersedes`/`superseded_by`, and this metadata (including company) is
  shown to the model in every prompt. A bounded, metadata-only guard scoped
  to this synthetic corpus's fixed schema — not a general contradiction
  detector — deterministically abstains when two different, unlinked
  `status: current` documents share an identical (company, section_title)
  topic/authority key (`src/qa.py::_detect_unresolved_current_conflict`).
  `effective_date` is deliberately **not** part of that key: a later date
  on an otherwise-identical, unlinked document is operator-supplied prose,
  not a verified precedence signal, so it never breaks the tie on its own —
  only an explicit `supersedes`/`superseded_by` link does (2026-09-28
  round-2 review, group 4). This guard does not compare the passages'
  actual claims and says nothing about a corpus with a different metadata
  schema.
- **The index is hash-bound to the corpus, embedding model, chunking
  scheme, and query-time embedding shape.** Every `retrieve()` call —
  including on an index already held in memory — re-validates the live
  corpus bytes, embedding-model identity, chunking version, passage count,
  and per-passage embedding dimension/finiteness. The per-passage binding
  hash covers the passage's **text and its bound metadata together**
  (company, status, supersedes/superseded_by, version, effective_date, ...)
  so editing metadata independently of text is caught the same way as
  editing text (`src/corpus.py::passage_binding_hash`); a caller-supplied
  `embed_model` that differs from the index's bound model is refused rather
  than silently scoring against embeddings it did not produce; and the
  query embedding itself is validated (non-empty, finite, dimension-matched
  to the index) before scoring, rather than silently truncated by `zip()`.
  Any mismatch raises `IndexIntegrityError` instead of retrieving against a
  stale, edited, corrupted, or model/dimension-mismatched index
  (`src/index.py`).
- **Inference stays on loopback, and responses are shape-validated.**
  `src/ollama_client.py` refuses any URL whose host is not
  `127.0.0.1`/`localhost`/`::1`, ignores inherited `HTTP_PROXY`/
  `HTTPS_PROXY`, refuses to follow HTTP redirects, bounds every response to
  10 MB, and requires the parsed JSON body to be an object (not e.g. a bare
  array) before reading a field out of it; embedding vectors are rejected
  if any element is non-finite (NaN/±inf), not just non-numeric.
- **Corpus access and size are bounded**: files must resolve inside the
  declared corpus directory (no path escapes or symlinks pointing outside
  it), zero-byte/duplicate-id/missing-frontmatter/oversized documents and
  oversized corpora fail as categorized errors rather than being silently
  skipped or read unbounded, and passage/context sizes are capped
  (`src/config.py`, `src/corpus.py`). `corpus_fingerprint` — called on every
  retrieval — enforces the same per-file byte bound as corpus loading,
  rather than hashing an oversized file whole.
- **New generation-evaluation runs are disabled.** `eval/run_eval.py`'s
  `main()` refuses immediately, on both the default and `--label` paths,
  until a reviewed successor implements a genuine pre-run freeze of exact
  model/tokenizer/artifact identity, runtime, and sources/prompts/config
  (2026-09-28 round-2 review, group 6). `--rescore-retained` is unaffected.

## Repository layout
```
data/corpus/          frozen main corpus (12 docs, 60 passages)
data/dev_corpus/       small corpus used only for prompt tuning, never scored
data/fixtures/         injection + no-precedence-conflict safety fixtures
src/                   corpus loading, embedding/retrieval, QA pipeline, sanitization
eval/                  frozen questions, scorer, eval runner, results/ (retained),
                       results-rescored-*/ (re-scored retained answers),
                       adjudication-2026-09-28.csv (AI-builder adjudication of the
                       retained 40 answers, see "Results" above)
tests/                 unit + safety tests
MANIFEST.md            frozen corpus/model/config/prompt manifest
LICENSES.md            dependency and model-weight licenses
```
