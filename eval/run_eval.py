"""Run the frozen evaluation set once and write frozen outputs.

Usage: python -m eval.run_eval

Writes:
  eval/results/answers.jsonl   -- every system answer, verbatim
  eval/results/scores.json     -- per-question scores + aggregate metrics
  eval/results/report.md       -- human-readable report

Re-running this script overwrites the results files. Per MANIFEST.md, once
results are committed as "final", a discovered scorer defect requires a new
labelled evaluation run (new directory) preserving the old outputs, not a
silent overwrite.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.index import load_index
from src.qa import answer_question
from eval.scorer import score_question, aggregate

QUESTIONS_PATH = Path(__file__).parent / "questions.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"
INDEX_PATH = Path(__file__).resolve().parent.parent / "data" / "index.json"


def load_questions():
    return [json.loads(line) for line in QUESTIONS_PATH.read_text().splitlines() if line.strip()]


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
        f"- Retrieval recall@5 (gold passages, answerable questions): {fmt(system_agg['retrieval_recall_at_k'])}",
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
        "- 'Rule-scored answer agreement' is keyword/alias matching against gold atomic facts plus a "
        "forbidden-term check; it is a proxy for correctness, not full semantic verification. "
        "An unsupported additional claim beyond the fixed rubric is only caught if it matches a "
        "forbidden term, which is a known limitation.",
        "- Citation validity (cited id actually among retrieved passages) is enforced in code before "
        "scoring: an uncited or invalidly-cited 'answer' is forced to ABSTAIN by src/qa.py, so this "
        "report cannot show an uncited answer as correct.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    RESULTS_DIR.mkdir(exist_ok=True)
    questions = load_questions()
    index = load_index(str(INDEX_PATH))

    system_answers = run_system(questions, index)
    (RESULTS_DIR / "answers.jsonl").write_text(
        "\n".join(json.dumps(a) for a in system_answers) + "\n", encoding="utf-8"
    )

    baseline_answers = run_always_abstain_baseline(questions)

    system_results, system_agg = score_all(questions, system_answers)
    baseline_results, baseline_agg = score_all(questions, baseline_answers)

    (RESULTS_DIR / "scores.json").write_text(
        json.dumps({"system": {"per_question": system_results, "aggregate": system_agg},
                    "always_abstain_baseline": {"per_question": baseline_results, "aggregate": baseline_agg}}, indent=2),
        encoding="utf-8",
    )

    write_report(RESULTS_DIR / "report.md", system_agg, baseline_agg, system_results, len(questions))
    print(f"Evaluated {len(questions)} questions. See {RESULTS_DIR}/report.md")


if __name__ == "__main__":
    main()
