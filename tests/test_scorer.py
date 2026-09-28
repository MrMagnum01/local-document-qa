import unittest

from eval.scorer import score_question, aggregate

GOLD_ANSWERABLE = {
    "id": "t1",
    "category": "answerable_single",
    "gold_action": "ANSWER",
    "gold_passage_ids": ["doc-a#sec1"],
    "gold_atomic_facts": [{"fact": "x is 5", "aliases": ["is 5", "equals 5"]}],
    "forbidden_terms": ["is 10"],
}

# Mirrors the review's WireGuard example (2026-09-28 review, group 2).
GOLD_WIREGUARD = {
    "id": "q001",
    "category": "answerable_single",
    "gold_action": "ANSWER",
    "gold_passage_ids": ["solstice-vpn-manual#overview"],
    "gold_atomic_facts": [{"fact": "default protocol is WireGuard", "aliases": ["wireguard"]}],
    "forbidden_terms": ["openvpn is the default"],
    "question": "What VPN protocol does SecureLink use by default?",
}

GOLD_MULTI = {
    "id": "t2",
    "category": "answerable_multi",
    "gold_action": "ANSWER",
    "gold_passage_ids": ["doc-a#sec1", "doc-b#sec1"],
    "gold_atomic_facts": [{"fact": "fact one", "aliases": ["fact one"]}],
    "forbidden_terms": [],
}

GOLD_UNANSWERABLE = {
    "id": "t3",
    "category": "unanswerable",
    "gold_action": "ABSTAIN",
    "gold_passage_ids": [],
    "gold_atomic_facts": [],
    "forbidden_terms": [],
}


def make_answer(action="ANSWER", text="", cited_ids=None, retrieved_ids=None):
    return {
        "action": action,
        "text": text,
        "cited_ids": cited_ids or [],
        "retrieved": [{"id": i} for i in (retrieved_ids or [])],
    }


class TestScorer(unittest.TestCase):
    def test_correct_answer_with_valid_citation(self):
        ans = make_answer(text="x is 5.", cited_ids=["doc-a#sec1"], retrieved_ids=["doc-a#sec1"])
        r = score_question(GOLD_ANSWERABLE, ans)
        self.assertTrue(r["correct"])
        self.assertTrue(r["all_facts_matched"])
        self.assertFalse(r["contains_forbidden"])

    def test_forbidden_term_fails_even_if_keyword_present(self):
        ans = make_answer(text="x is 5, or maybe x is 10.", cited_ids=["doc-a#sec1"], retrieved_ids=["doc-a#sec1"])
        r = score_question(GOLD_ANSWERABLE, ans)
        self.assertTrue(r["contains_forbidden"])
        self.assertFalse(r["correct"])

    def test_uncited_answer_is_not_correct(self):
        # Even if qa.py failed to force-abstain for some reason, an answer with
        # no citation must not score as correct.
        ans = make_answer(text="x is 5.", cited_ids=[], retrieved_ids=["doc-a#sec1"])
        r = score_question(GOLD_ANSWERABLE, ans)
        self.assertFalse(r["correct"])

    def test_abstain_on_answerable_is_false_abstention(self):
        ans = make_answer(action="ABSTAIN", text="ABSTAIN", retrieved_ids=["doc-a#sec1"])
        r = score_question(GOLD_ANSWERABLE, ans)
        self.assertTrue(r["false_abstention"])
        self.assertFalse(r["correct"])

    def test_correct_abstention_on_unanswerable(self):
        ans = make_answer(action="ABSTAIN", text="ABSTAIN")
        r = score_question(GOLD_UNANSWERABLE, ans)
        self.assertTrue(r["correct_abstention"])

    def test_incorrect_non_abstention_on_unanswerable(self):
        ans = make_answer(text="here is an answer", cited_ids=["doc-a#sec1"], retrieved_ids=["doc-a#sec1"])
        r = score_question(GOLD_UNANSWERABLE, ans)
        self.assertFalse(r["correct_abstention"])

    def test_multi_doc_requires_all_sources_cited(self):
        ans = make_answer(text="fact one", cited_ids=["doc-a#sec1"], retrieved_ids=["doc-a#sec1", "doc-b#sec1"])
        r = score_question(GOLD_MULTI, ans)
        self.assertFalse(r["all_required_sources_cited"])
        self.assertFalse(r["correct"])

        ans2 = make_answer(text="fact one", cited_ids=["doc-a#sec1", "doc-b#sec1"],
                            retrieved_ids=["doc-a#sec1", "doc-b#sec1"])
        r2 = score_question(GOLD_MULTI, ans2)
        self.assertTrue(r2["all_required_sources_cited"])
        self.assertTrue(r2["correct"])

    def test_negated_answer_does_not_pass(self):
        # "WireGuard is not the default protocol" must not score as correct
        # just because the alias "wireguard" appears (2026-09-28 review,
        # group 2: negation).
        ans = make_answer(text="WireGuard is not the default protocol.",
                           cited_ids=["solstice-vpn-manual#overview"],
                           retrieved_ids=["solstice-vpn-manual#overview"])
        r = score_question(GOLD_WIREGUARD, ans)
        self.assertFalse(r["all_facts_matched"])
        self.assertTrue(r["contains_negated_gold_fact"])
        self.assertFalse(r["correct"])

    def test_unsupported_additional_claim_does_not_pass(self):
        # A true gold fact plus a fabricated, unrelated monetary claim must
        # not score as correct (2026-09-28 review, group 2: unsupported
        # additions).
        ans = make_answer(text="WireGuard is the default. All customers receive a free million dollars.",
                           cited_ids=["solstice-vpn-manual#overview"],
                           retrieved_ids=["solstice-vpn-manual#overview"])
        r = score_question(GOLD_WIREGUARD, ans)
        self.assertTrue(r["all_facts_matched"])
        self.assertTrue(r["unsupported_claims"])
        self.assertFalse(r["correct"])

    def test_citation_to_wrong_passage_in_right_document_does_not_pass(self):
        # A citation to a different section of the *correct* document must
        # not pass correctness just because the document-level check is
        # satisfied; citation precision/recall are effectively zero
        # (2026-09-28 review, group 2: wrong-passage citation).
        ans = make_answer(text="WireGuard", cited_ids=["solstice-vpn-manual#troubleshooting"],
                           retrieved_ids=["solstice-vpn-manual#overview", "solstice-vpn-manual#troubleshooting"])
        r = score_question(GOLD_WIREGUARD, ans)
        self.assertEqual(r["citation_precision"], 0.0)
        self.assertEqual(r["citation_recall"], 0.0)
        self.assertFalse(r["correct"])

    def test_invalid_cited_ids_prevent_correctness_even_if_dropped(self):
        # Defense in depth: if an answer dict somehow carries invalid_cited_ids
        # alongside valid cited_ids, correctness must not silently ignore it
        # (src/qa.py itself now forces such answers to ABSTAIN before they
        # ever reach the scorer; this guards the scorer independently).
        ans = make_answer(text="x is 5.", cited_ids=["doc-a#sec1"], retrieved_ids=["doc-a#sec1"])
        ans["invalid_cited_ids"] = ["doc-a#fabricated"]
        r = score_question(GOLD_ANSWERABLE, ans)
        self.assertFalse(r["correct"])

    def test_aggregate_zero_denominator_reports_na(self):
        results = [score_question(GOLD_ANSWERABLE, make_answer(text="x is 5.", cited_ids=["doc-a#sec1"],
                                                                 retrieved_ids=["doc-a#sec1"]))]
        agg = aggregate(results)
        self.assertIsNone(agg["abstention_recall"]["value"])
        self.assertEqual(agg["abstention_recall"]["denominator"], 0)

    def test_retrieval_metric_is_all_or_nothing_not_fractional(self):
        # Renamed per the review: the aggregate key and its per-question
        # source must reflect "all gold passages retrieved", not fractional
        # recall@5 (2026-09-28 review, group 2).
        partial = make_answer(text="fact one", cited_ids=["doc-a#sec1", "doc-b#sec1"],
                               retrieved_ids=["doc-a#sec1"])  # only 1 of 2 gold passages retrieved
        r = score_question(GOLD_MULTI, partial)
        self.assertFalse(r["all_gold_passages_retrieved"])
        agg = aggregate([r])
        self.assertIn("all_gold_passages_retrieved_rate", agg)
        self.assertNotIn("retrieval_recall_at_k", agg)


if __name__ == "__main__":
    unittest.main()
