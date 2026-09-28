"""Rule-based scorer, written before any final answers were generated.

Deliberately NOT an LLM judge. Keyword/alias matching on gold atomic facts is
a proxy for correctness, not full semantic verification — this module is
named accordingly ("rule-scored answer agreement") rather than "accuracy".
This is a bounded, explicit adjudication protocol, not a universal semantic
scorer: it (1) discounts an alias match that appears inside a negated clause
in the same sentence, so "X is not the default" does not count as support
for "X is the default"; and (2) flags a bounded class of unsupported
additional claims -- numbers, percentages, and monetary amounts asserted in
the answer text that do not appear in the gold facts, aliases, or question
text -- as a failure, even when every required alias is also present. Both
checks are heuristic and pattern-based, not semantic; they narrow, but do not
close, the known limitation that this scorer is a proxy for correctness.
"""
import re

_NEGATION_CUES = (
    "not ", "n't", "never ", "isn't", "doesn't", "wasn't", "weren't",
    "aren't", "won't", "cannot", "can't", "no longer ",
)

_NUMERIC_RE = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d+)?"          # $1,234.56
    r"|\d[\d,]*(?:\.\d+)?\s?(?:%|percent)"  # 12%, 12 percent
    r"|\d[\d,]*(?:\.\d+)?"              # bare number
    r"|\b(?:million|billion|thousand|hundred)\b",
    re.IGNORECASE,
)


def _numeric_tokens(text: str) -> set:
    return {m.group(0).strip().lower() for m in _NUMERIC_RE.finditer(text or "")}


def _sentence_around(t: str, pos: int) -> str:
    start = t.rfind(".", 0, pos)
    end = t.find(".", pos)
    return t[start + 1: end if end != -1 else len(t)]


def _alias_negated(t: str, alias: str) -> bool:
    pos = t.find(alias.lower())
    if pos == -1:
        return False
    sentence = _sentence_around(t, pos)
    return any(cue in sentence for cue in _NEGATION_CUES)


def _contains_any(text: str, aliases: list) -> bool:
    """True if some alias appears in `text` and is not itself negated in the
    same sentence. A negated mention of an alias is not treated as support
    for the fact it names."""
    t = text.lower()
    return any(alias.lower() in t and not _alias_negated(t, alias) for alias in aliases)


def _any_alias_negated(text: str, facts: list) -> bool:
    t = text.lower()
    return any(_alias_negated(t, alias) for f in facts for alias in f["aliases"])


def _forbidden_hits(text: str, forbidden_terms: list) -> list:
    t = text.lower()
    return [term for term in forbidden_terms if term.lower() in t]


def _unsupported_numeric_claims(answer_text: str, gold: dict) -> list:
    """Bounded 'unsupported additional claim' check: any number, percentage,
    or monetary amount in the answer that does not appear anywhere in the
    gold atomic facts, their aliases, or the question text itself. Does not
    catch non-numeric fabrications; documented as a known limitation."""
    allowed = set()
    for fact in gold.get("gold_atomic_facts", []):
        allowed |= _numeric_tokens(fact.get("fact", ""))
        for alias in fact.get("aliases", []):
            allowed |= _numeric_tokens(alias)
    allowed |= _numeric_tokens(gold.get("question", ""))
    return sorted(_numeric_tokens(answer_text) - allowed)


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

    # Proportion of answerable questions whose ENTIRE gold passage group was
    # retrieved -- a per-question all-or-nothing hit rate, not fractional
    # passage recall@5 (a question retrieving 4 of 5 gold passages counts as
    # a miss here, same as retrieving none). See MANIFEST.md.
    result["all_gold_passages_retrieved"] = gold_ids.issubset(retrieved_ids) if gold_ids else None
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
            "contains_negated_gold_fact": False,
            "unsupported_claims": [],
            "citation_validity": None,
            "citation_precision": None,
            "citation_recall": None,
            "all_required_sources_cited": False,
            "correct": False,
        })
        return result

    facts = gold.get("gold_atomic_facts", [])
    answer_text = answer["text"]
    matched = [f for f in facts if _contains_any(answer_text, f["aliases"])]
    forbidden_hits = _forbidden_hits(answer_text, gold.get("forbidden_terms", []))
    negated = _any_alias_negated(answer_text, facts)
    unsupported_claims = _unsupported_numeric_claims(answer_text, gold)
    all_matched = len(facts) > 0 and len(matched) == len(facts)

    cited = set(answer["cited_ids"])
    has_invalid_citation = bool(answer.get("invalid_cited_ids"))
    citation_validity = cited.issubset(retrieved_ids)  # qa.py already enforces this
    citation_precision = (len(cited & gold_ids) / len(cited)) if cited else 0.0
    citation_recall = (len(cited & gold_ids) / len(gold_ids)) if gold_ids else None
    cited_doc_ids = {pid.split("#")[0] for pid in cited}
    all_required_sources_cited = gold_doc_ids.issubset(cited_doc_ids) if gold_doc_ids else True
    # Doc-level subset is not enough on its own (a citation to the wrong
    # passage within the right document still passes it); correctness also
    # requires the exact cited gold passages, not merely their documents.
    gold_passages_cited = gold_ids.issubset(cited) if gold_ids else True

    correct = (
        all_matched
        and not forbidden_hits
        and not unsupported_claims
        and citation_validity
        and not has_invalid_citation
        and bool(cited)
        and gold_passages_cited
    )

    result.update({
        "false_abstention": False,
        "facts_total": len(facts),
        "facts_matched": len(matched),
        "all_facts_matched": all_matched,
        "contains_forbidden": bool(forbidden_hits),
        "forbidden_hits": forbidden_hits,
        "contains_negated_gold_fact": negated,
        "unsupported_claims": unsupported_claims,
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

    recall_hits = [r for r in answerable if r["all_gold_passages_retrieved"] is not None]
    all_gold_passages_retrieved_rate = _safe_rate(
        sum(1 for r in recall_hits if r["all_gold_passages_retrieved"]), len(recall_hits)
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
        "all_gold_passages_retrieved_rate": all_gold_passages_retrieved_rate,
        "multi_doc_all_sources_recall_at_k": multi_all_sources,
        "citation_precision_mean_over_answered": citation_precision,
        "citation_recall_mean_over_answered": citation_recall,
        "rule_scored_answer_agreement": rule_scored_agreement,
        "false_abstention_rate_on_answerable": false_abstentions,
        "abstention_precision": abstention_precision,
        "abstention_recall": abstention_recall,
    }
