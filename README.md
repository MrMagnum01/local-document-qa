# Local Document Q&A

Retrieval-augmented question answering over a synthetic document corpus
(company policies, product manuals, FAQs), running entirely on local
models via [Ollama](https://ollama.com). Answers cite the passage id(s)
they used, or explicitly abstain — an uncited "answer" is never presented
as a success.

**Role:** Synthetic portfolio demonstration, implemented with AI coding
agents; independent review pending. No client data or client work.

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
python3 -m unittest tests.test_corpus tests.test_scorer tests.test_qa   # fast, no network
python3 -m unittest tests.test_safety                                   # needs Ollama, ~30-60s on CPU
```

## Running the frozen evaluation
Already run once; outputs are committed under `eval/results/`. To
reproduce:
```bash
python3 -m eval.run_eval
```
This overwrites `eval/results/`. Per `MANIFEST.md`, if a scorer defect is
later found, the fix gets a new labelled evaluation directory that
preserves the old outputs — not a silent overwrite of "final" numbers.

## Results, on this synthetic set
See `eval/results/report.md` for the full report and `eval/results/scores.json`
for per-question detail. Headline numbers from the frozen 40-question run
with a 1.5B local model:

- Retrieval recall@5 (gold passages, answerable questions): 90.6% (29/32)
- Multi-document all-required-sources recall@5: 100% (8/8)
- Rule-scored answer agreement (answerable questions): 62.5% (20/32)
- False abstention rate on answerable questions: 0%
- Abstention precision: 100% (5/5) — abstention recall on unanswerable
  questions: 62.5% (5/8)
- Always-abstain baseline is reported alongside these numbers specifically
  to expose that a trivial "never answer" system would score 100%
  abstention recall but only 20% abstention precision — the real system's
  100%/62.5% split is not a vacuous safety score.

"Rule-scored answer agreement" is keyword/alias matching against committed
gold atomic facts plus a forbidden-term check — a proxy for correctness,
not full semantic verification; see `eval/scorer.py` and the notes at the
bottom of `eval/results/report.md`. No positive accuracy threshold was
required for this demo to ship: the generator is a small (1.5B parameter)
CPU-only model, and its answer quality is exactly what is reported above —
the retrieval, citation-enforcement, and abstention-safety pipeline is the
part of this demo with the stronger claim.

## Safety design
- **Documents are data, not instructions.** Retrieved passage text is
  heuristically scanned for instruction-injection markers and redacted
  before it reaches the generator (`src/sanitize.py`), on top of an explicit
  system-prompt instruction never to follow in-document instructions, visit
  URLs, or call tools. Tested against injected "ignore previous
  instructions" / "reveal your system prompt" / fake system-override blocks
  in `tests/test_safety.py`. This proves observed behavior on these specific
  fixtures, not universal prompt-injection resistance.
- **Every answer cites a real passage id, or abstains.** Citation ids are
  validated against the actually-retrieved passage set in code; an
  uncited or invalidly-cited "answer" is forced to `ABSTAIN`
  (`src/qa.py::_parse_output`) — the renderer cannot turn an uncited answer
  into a success.
- **Version authority comes from committed metadata**, not document prose:
  each document's frontmatter states `status`, `effective_date`,
  `supersedes`/`superseded_by`. Two current documents that conflict on the
  same fact with no defined precedence cause a deterministic abstention
  (`src/qa.py::_detect_unresolved_current_conflict`), not a model guess.
- **Corpus access is bounded**: files must resolve inside the declared
  corpus directory (no path escapes or symlinks pointing outside it),
  zero-byte/duplicate-id/missing-frontmatter documents fail as categorized
  errors rather than being silently skipped, and passage/context sizes are
  capped (`src/config.py`).

## Repository layout
```
data/corpus/          frozen main corpus (12 docs, 60 passages)
data/dev_corpus/       small corpus used only for prompt tuning, never scored
data/fixtures/         injection + no-precedence-conflict safety fixtures
src/                   corpus loading, embedding/retrieval, QA pipeline, sanitization
eval/                  frozen questions, scorer, eval runner, results
tests/                 unit + safety tests
MANIFEST.md            frozen corpus/model/config/prompt manifest
LICENSES.md            dependency and model-weight licenses
```
