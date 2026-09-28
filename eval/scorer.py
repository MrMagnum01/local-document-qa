"""Rule-based scorer, written before any final answers were generated.

Deliberately NOT an LLM judge. Keyword/alias matching on gold atomic facts is
a proxy for correctness, not full semantic verification — this module is
named accordingly ("rule-scored answer agreement") rather than "accuracy".
An unsupported additional claim is not checked here beyond forbidden-term
matches; this is a known limitation, stated in MANIFEST.md and README.md.
"""


def _contains_any(text: str, aliases: list) -> bool:
    t = text.lower()
    return any(alias.lower() in t for alias in aliases)


def _forbidden_hits(text: str, forbidden_terms: list) -> list:
    t = text.lower()
    return [term for term in forbidden_terms if term.lower() in t]


def score_question(gold: dict, answer: dict) -> dict:
    """gold: one row from eval/questions.jsonl.
    answer: {"action": "ANSWER"|"ABSTAIN", "text": str, "cited_ids": [...],
             "invalid_cited_ids": [...], "retrieved": [{"id":...}, ...]}
    """
    gold_action = gold["gold_action"]
    system_abstained = answer["action"] == "ABSTAIN"
    retrieved_ids = {p["id"] for p in answer["retrieved"]}
    retrieved_doc_ids = {pid.split("#")[0] for pid in retrieved_ids}

    result = {
        "id": gold["id"],
        "category": gold["category"],
        "gold_action": gold_action,
        "system_action": answer["action"],
        "system_abstained": system_abstained,
    }

    if gold_action == "ABSTAIN":
        result["correct_abstention"] = system_abstained
        result["is_unanswerable_gold"] = True
        return result

    result["is_unanswerable_gold"] = False
    gold_ids = set(gold.get("gold_passage_ids", []))
    gold_doc_ids = {pid.split("#")[0] for pid in gold_ids}

    result["retrieval_recall_at_k"] = gold_ids.issubset(retrieved_ids) if gold_ids else None
    result["retrieval_all_sources_at_k"] = (
        gold_doc_ids.issubset(retrieved_doc_ids) if gold_doc_ids else None
    )

    if system_abstained:
        result.update({
            "false_abstention": True,
            "facts_total": len(gold.get("gold_atomic_facts", [])),
            "facts_matched": 0,
            "all_facts_matched": False,
            "contains_forbidden": False,
            "citation_validity": None,
            "citation_precision": None,
            "citation_recall": None,
            "all_required_sources_cited": False,
            "correct": False,
        })
        return result

    facts = gold.get("gold_atomic_facts", [])
    matched = [f for f in facts if _contains_any(answer["text"], f["aliases"])]
    forbidden_hits = _forbidden_hits(answer["text"], gold.get("forbidden_terms", []))
    all_matched = len(facts) > 0 and len(matched) == len(facts)

    cited = set(answer["cited_ids"])
    citation_validity = cited.issubset(retrieved_ids)  # qa.py already enforces this
    citation_precision = (len(cited & gold_ids) / len(cited)) if cited else 0.0
    citation_recall = (len(cited & gold_ids) / len(gold_ids)) if gold_ids else None
    cited_doc_ids = {pid.split("#")[0] for pid in cited}
    all_required_sources_cited = gold_doc_ids.issubset(cited_doc_ids) if gold_doc_ids else True

    correct = all_matched and not forbidden_hits and bool(cited) and all_required_sources_cited

    result.update({
        "false_abstention": False,
        "facts_total": len(facts),
        "facts_matched": len(matched),
        "all_facts_matched": all_matched,
        "contains_forbidden": bool(forbidden_hits),
        "forbidden_hits": forbidden_hits,
        "citation_validity": citation_validity,
        "citation_precision": citation_precision,
        "citation_recall": citation_recall,
        "all_required_sources_cited": all_required_sources_cited,
        "correct": correct,
    })
    return result


def _safe_rate(numer, denom):
    if denom == 0:
        return {"value": None, "note": "N/A (zero denominator)", "numerator": numer, "denominator": denom}
    return {"value": numer / denom, "numerator": numer, "denominator": denom}


def aggregate(results: list) -> dict:
    answerable = [r for r in results if not r["is_unanswerable_gold"]]
    unanswerable = [r for r in results if r["is_unanswerable_gold"]]

    recall_hits = [r for r in answerable if r["retrieval_recall_at_k"] is not None]
    recall_at_k = _safe_rate(
        sum(1 for r in recall_hits if r["retrieval_recall_at_k"]), len(recall_hits)
    )

    multi = [r for r in answerable if r["category"] == "answerable_multi"]
    multi_all_sources = _safe_rate(
        sum(1 for r in multi if r.get("retrieval_all_sources_at_k")), len(multi)
    )

    answered = [r for r in answerable if not r["false_abstention"]]
    cite_prec_vals = [r["citation_precision"] for r in answered if r["citation_precision"] is not None]
    citation_precision = _safe_rate(sum(cite_prec_vals), len(cite_prec_vals)) if cite_prec_vals else {"value": None, "note": "N/A", "numerator": 0, "denominator": 0}
    cite_rec_vals = [r["citation_recall"] for r in answered if r["citation_recall"] is not None]
    citation_recall = _safe_rate(sum(cite_rec_vals), len(cite_rec_vals)) if cite_rec_vals else {"value": None, "note": "N/A", "numerator": 0, "denominator": 0}

    rule_scored_agreement = _safe_rate(sum(1 for r in answerable if r["correct"]), len(answerable))

    false_abstentions = _safe_rate(
        sum(1 for r in answerable if r["false_abstention"]), len(answerable)
    )

    system_abstained_all = [r for r in results if r["system_abstained"]]
    abstention_precision = _safe_rate(
        sum(1 for r in system_abstained_all if r["is_unanswerable_gold"]),
        len(system_abstained_all),
    )
    abstention_recall = _safe_rate(
        sum(1 for r in unanswerable if r["system_abstained"]), len(unanswerable)
    )

    return {
        "n_total": len(results),
        "n_answerable": len(answerable),
        "n_unanswerable": len(unanswerable),
        "retrieval_recall_at_k": recall_at_k,
        "multi_doc_all_sources_recall_at_k": multi_all_sources,
        "citation_precision_mean_over_answered": citation_precision,
        "citation_recall_mean_over_answered": citation_recall,
        "rule_scored_answer_agreement": rule_scored_agreement,
        "false_abstention_rate_on_answerable": false_abstentions,
        "abstention_precision": abstention_precision,
        "abstention_recall": abstention_recall,
    }
