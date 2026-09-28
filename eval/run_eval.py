"""Run the frozen evaluation set, or re-score retained answers, and write
immutable, labelled outputs.

Usage:
  python -m eval.run_eval                 # first/only run: writes eval/results/
  python -m eval.run_eval --label <name>   # a NEW generation run: eval/results-<name>/
  python -m eval.run_eval --rescore-retained <name>
      # re-score the RETAINED eval/results/answers.jsonl with the CURRENT
      # eval/scorer.py, writing eval/results-rescored-<name>/ alongside both
      # the old and new aggregate numbers. Calls no model and does not touch
      # eval/results/.

Per MANIFEST.md: once `eval/results/` is committed as recorded evidence, this
script refuses to overwrite it. A discovered scorer defect gets a new
labelled re-score (above); a genuinely new generation run gets a new labelled
run directory -- never a silent overwrite of retained evidence.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as src_config
from src.corpus import CHUNK_VERSION, corpus_fingerprint
from src.index import load_index
from src.qa import answer_question
from eval.scorer import score_question, aggregate

REPO_ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = Path(__file__).parent / "questions.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"
INDEX_PATH = REPO_ROOT / "data" / "index.json"
CORPUS_DIR = REPO_ROOT / "data" / "corpus"


def _repo_relative(path: Path) -> str:
    """Repo-relative path string for anything written into a results file:
    the demo is a portfolio artifact and must not embed the builder's local
    absolute filesystem path (owner/host string)."""
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_questions():
    return [json.loads(line) for line in QUESTIONS_PATH.read_text().splitlines() if line.strip()]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _provenance_snapshot() -> dict:
    """Passage/version/config provenance recorded alongside every run or
    re-score, so a results directory carries its own evidence of what
    produced it rather than relying only on prose in MANIFEST.md."""
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "corpus_dir": _repo_relative(CORPUS_DIR),
        "corpus_fingerprint": corpus_fingerprint(str(CORPUS_DIR)),
        "chunk_version": CHUNK_VERSION,
        "embed_model": src_config.EMBED_MODEL,
        "gen_model": src_config.GEN_MODEL,
        "gen_options": src_config.GEN_OPTIONS,
        "retrieval_k": src_config.RETRIEVAL_K,
        "max_context_passages": src_config.MAX_CONTEXT_PASSAGES,
        "questions_sha256": _sha256_bytes(QUESTIONS_PATH.read_bytes()),
        "scorer_sha256": _sha256_bytes((Path(__file__).parent / "scorer.py").read_bytes()),
    }


def to_answer_dict(ans) -> dict:
    return {
        "action": ans.action,
        "text": ans.text,
        "cited_ids": ans.cited_ids,
        "invalid_cited_ids": ans.invalid_cited_ids,
        "retrieved": [{"id": p["id"]} for p in ans.retrieved],
        "raw_model_output": ans.raw_model_output,
        "error_category": ans.error_category,
    }


def run_system(questions, index):
    rows = []
    for q in questions:
        ans = answer_question(q["question"], index)
        rows.append({"id": q["id"], **to_answer_dict(ans)})
    return rows


def run_always_abstain_baseline(questions):
    return [
        {"id": q["id"], "action": "ABSTAIN", "text": "", "cited_ids": [],
         "invalid_cited_ids": [], "retrieved": [], "raw_model_output": "", "error_category": None}
        for q in questions
    ]


def score_all(questions, answers):
    by_id = {a["id"]: a for a in answers}
    results = [score_question(q, by_id[q["id"]]) for q in questions]
    return results, aggregate(results)


def write_report(path, system_agg, baseline_agg, system_results, n_questions):
    def fmt(rate):
        if rate["value"] is None:
            return f"N/A ({rate['note']}; {rate['numerator']}/{rate['denominator']})"
        num = rate["numerator"]
        num_str = f"{num:.2f}" if isinstance(num, float) else str(num)
        return f"{rate['value']:.2%} ({num_str}/{rate['denominator']})"

    error_categories = {}
    for r in system_results:
        cat = None
        if r.get("false_abstention"):
            cat = "false_abstention_on_answerable"
        elif r["is_unanswerable_gold"] and not r["system_abstained"]:
            cat = "failed_to_abstain_on_unanswerable"
        elif not r["is_unanswerable_gold"] and not r.get("all_facts_matched", True) and not r["system_abstained"]:
            cat = "incomplete_or_wrong_facts"
        elif r.get("contains_forbidden"):
            cat = "contradicted_forbidden_answer"
        if cat:
            error_categories[cat] = error_categories.get(cat, 0) + 1

    lines = [
        "# Evaluation report — on this synthetic set",
        "",
        f"Frozen question set: {n_questions} questions (20 single-doc answerable, "
        "8 multi-document answerable, 4 version-sensitive answerable, 8 unanswerable). "
        "Run once; no selective retries or prompt changes after this run. See MANIFEST.md.",
        "",
        "## System metrics",
        f"- All-gold-passages-retrieved rate @k=5 (answerable questions; per-question "
        f"all-or-nothing hit on the full gold group, NOT fractional passage recall): "
        f"{fmt(system_agg['all_gold_passages_retrieved_rate'])}",
        f"- Multi-document all-required-sources recall@5: {fmt(system_agg['multi_doc_all_sources_recall_at_k'])}",
        f"- Citation precision (mean over non-abstained answers): {fmt(system_agg['citation_precision_mean_over_answered'])}",
        f"- Citation recall (mean over non-abstained answers): {fmt(system_agg['citation_recall_mean_over_answered'])}",
        f"- Rule-scored answer agreement (answerable questions): {fmt(system_agg['rule_scored_answer_agreement'])}",
        f"- False abstention rate on answerable questions: {fmt(system_agg['false_abstention_rate_on_answerable'])}",
        f"- Abstention precision (all questions): {fmt(system_agg['abstention_precision'])}",
        f"- Abstention recall (unanswerable questions): {fmt(system_agg['abstention_recall'])}",
        "",
        "## Error categories (system)",
    ]
    if error_categories:
        for cat, n in sorted(error_categories.items()):
            lines.append(f"- {cat}: {n}")
    else:
        lines.append("- none")
    lines += [
        "",
        "## Always-abstain baseline (exposes vacuous safety scores)",
        f"- Abstention precision: {fmt(baseline_agg['abstention_precision'])}",
        f"- Abstention recall: {fmt(baseline_agg['abstention_recall'])}",
        f"- Rule-scored answer agreement (necessarily 0, since it never answers): {fmt(baseline_agg['rule_scored_answer_agreement'])}",
        "",
        "## Notes",
        "- 'Rule-scored answer agreement' is keyword/alias matching against gold atomic facts, "
        "discounting alias mentions negated in the same sentence, plus a forbidden-term check and "
        "a bounded unsupported-numeric/monetary-claim check (eval/scorer.py). It remains a proxy "
        "for correctness, not full semantic verification: non-numeric unsupported additions are "
        "only caught if they match a forbidden term, which is a known limitation.",
        "- Citation validity (cited id actually among the passages placed in the prompt) is enforced "
        "in code before scoring: an uncited, mixed-valid/fabricated, or invalidly-cited 'answer' is "
        "forced to ABSTAIN by src/qa.py, so this report cannot show such an answer as correct. "
        "Correctness also requires the exact gold passage(s) to be among the citations, not merely "
        "the right document (see 'gold_passages_cited' logic in eval/scorer.py).",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_results(target_dir: Path, system_answers, system_results, system_agg,
                    baseline_results, baseline_agg, n_questions, extra_scores_fields=None):
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "answers.jsonl").write_text(
        "\n".join(json.dumps(a) for a in system_answers) + "\n", encoding="utf-8"
    )
    payload = {
        "system": {"per_question": system_results, "aggregate": system_agg},
        "always_abstain_baseline": {"per_question": baseline_results, "aggregate": baseline_agg},
        "provenance": _provenance_snapshot(),
    }
    if extra_scores_fields:
        payload.update(extra_scores_fields)
    (target_dir / "scores.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_report(target_dir / "report.md", system_agg, baseline_agg, system_results, n_questions)


def main(label: str = None):
    """Run the full pipeline (retrieval + local generation) over the frozen
    question set. Refuses to overwrite `eval/results/` once it holds
    retained evidence; pass --label for any new generation run."""
    target_dir = RESULTS_DIR if label is None else RESULTS_DIR.parent / f"results-{label}"
    if target_dir == RESULTS_DIR and RESULTS_DIR.exists() and any(RESULTS_DIR.iterdir()):
        raise SystemExit(
            f"{RESULTS_DIR} already holds retained evidence (committed answers/scores). "
            "Refusing to overwrite it. Pass `--label <name>` to write a new, separately "
            f"labelled run to {RESULTS_DIR.parent / 'results-<name>'} instead, or use "
            "`--rescore-retained <name>` if only the scorer changed and the answers "
            "themselves do not need regenerating."
        )

    questions = load_questions()
    index = load_index(str(INDEX_PATH))

    system_answers = run_system(questions, index)
    baseline_answers = run_always_abstain_baseline(questions)
    system_results, system_agg = score_all(questions, system_answers)
    baseline_results, baseline_agg = score_all(questions, baseline_answers)

    _write_results(target_dir, system_answers, system_results, system_agg,
                    baseline_results, baseline_agg, len(questions))
    print(f"Evaluated {len(questions)} questions. See {target_dir}/report.md")


def rescore_retained(label: str, source_dir: Path = RESULTS_DIR):
    """Re-score the RETAINED answers in `source_dir` (unmodified, not
    regenerated) using the CURRENT eval/scorer.py. Calls no model, touches no
    corpus, and never writes into `source_dir`: writes a new
    eval/results-rescored-<label>/ directory carrying both the old aggregate
    (as committed) and the new one, so a scorer fix is visible as a labelled
    delta rather than a silent overwrite."""
    answers_path = source_dir / "answers.jsonl"
    old_scores_path = source_dir / "scores.json"
    questions = load_questions()
    answers = [json.loads(line) for line in answers_path.read_text().splitlines() if line.strip()]
    old_scores = json.loads(old_scores_path.read_text())

    results, agg = score_all(questions, answers)
    baseline_answers = run_always_abstain_baseline(questions)
    baseline_results, baseline_agg = score_all(questions, baseline_answers)

    out_dir = RESULTS_DIR.parent / f"results-rescored-{label}"
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"{out_dir} already exists and is non-empty; choose a different --label.")
    out_dir.mkdir(parents=True, exist_ok=True)
    answers_path_bytes = answers_path.read_bytes()
    (out_dir / "answers.jsonl").write_bytes(answers_path_bytes)  # retained, copied verbatim

    source_dir_rel = _repo_relative(source_dir)
    extra = {
        "note": (
            f"Re-score of the RETAINED answers in {source_dir_rel} using the current "
            "eval/scorer.py. The answers themselves were NOT regenerated -- only the "
            "scoring rule changed. Compare old_aggregate (as originally committed) "
            "against system.aggregate (this file) for the before/after."
        ),
        "source_answers_dir": source_dir_rel,
        "source_answers_sha256": _sha256_bytes(answers_path_bytes),
        "old_aggregate": old_scores["system"]["aggregate"],
    }
    _write_results(out_dir, answers, results, agg, baseline_results, baseline_agg,
                    len(questions), extra_scores_fields=extra)
    print(f"Re-scored {len(questions)} retained answers from {source_dir} -> {out_dir}/report.md")
    return out_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", help="write a NEW generation run to eval/results-<label>/ instead of eval/results/")
    parser.add_argument("--rescore-retained", metavar="LABEL",
                         help="re-score eval/results/answers.jsonl (retained) with the current scorer "
                              "into eval/results-rescored-LABEL/; no model call, no regeneration")
    args = parser.parse_args()
    if args.rescore_retained:
        rescore_retained(args.rescore_retained)
    else:
        main(label=args.label)
