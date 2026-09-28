import unittest
from unittest.mock import patch

from src import qa
from src.qa import _detect_unresolved_current_conflict, _parse_output


class TestParseOutput(unittest.TestCase):
    def test_plain_abstain(self):
        action, text, cited, invalid = _parse_output("ABSTAIN", {"a#1"})
        self.assertEqual(action, "ABSTAIN")

    def test_answer_with_valid_source(self):
        raw = "ANSWER: The value is 5.\nSOURCES: a#1"
        action, text, cited, invalid = _parse_output(raw, {"a#1", "a#2"})
        self.assertEqual(action, "ANSWER")
        self.assertEqual(text, "The value is 5.")
        self.assertEqual(cited, ["a#1"])

    def test_answer_with_only_invalid_source_forces_abstain(self):
        raw = "ANSWER: The value is 5.\nSOURCES: a#99"
        action, text, cited, invalid = _parse_output(raw, {"a#1"})
        self.assertEqual(action, "ABSTAIN")
        self.assertEqual(cited, [])
        self.assertEqual(invalid, ["a#99"])

    def test_answer_with_no_sources_line_forces_abstain(self):
        raw = "ANSWER: The value is 5."
        action, text, cited, invalid = _parse_output(raw, {"a#1"})
        self.assertEqual(action, "ABSTAIN")

    def test_sources_none_means_no_citations(self):
        raw = "ANSWER: ABSTAIN\nSOURCES: NONE"
        action, text, cited, invalid = _parse_output(raw, {"a#1"})
        self.assertEqual(action, "ABSTAIN")

    def test_mixed_valid_and_invalid_sources_forces_full_abstain(self):
        # A fabricated id mixed with a genuine one must not be laundered into
        # an accepted answer by silently dropping the fabricated id: the
        # whole answer is forced to ABSTAIN (2026-09-28 review, group 3).
        raw = "ANSWER: The value is 5.\nSOURCES: a#1, a#99"
        action, text, cited, invalid = _parse_output(raw, {"a#1"})
        self.assertEqual(action, "ABSTAIN")
        self.assertEqual(cited, [])
        self.assertEqual(invalid, ["a#99"])

    def test_abstain_text_is_a_clean_marker_not_the_draft_answer(self):
        # Forced abstention must render a clean ABSTAIN marker; the model's
        # attempted answer text is never surfaced as the displayed answer
        # (2026-09-28 review, group 3).
        raw = "ANSWER: A fabricated instruction with no citation."
        action, text, cited, invalid = _parse_output(raw, {"a#1"})
        self.assertEqual(action, "ABSTAIN")
        self.assertEqual(text, "ABSTAIN")
        self.assertNotIn("fabricated instruction", text)


def _passage(id_, doc_id, status="current", company="Acme", effective_date="2026-01-01",
             section_title="Hours", supersedes=None, superseded_by=None):
    return {
        "id": id_, "doc_id": doc_id, "status": status, "company": company,
        "effective_date": effective_date, "section_title": section_title,
        "supersedes": supersedes, "superseded_by": superseded_by,
    }


class TestUnresolvedCurrentConflict(unittest.TestCase):
    """Direct unit tests for the bounded metadata-only precedence guard
    (2026-09-28 review, group 4): it fires on an exact
    (company, effective_date, section_title) match between two different,
    unlinked `status: current` documents, and only then."""

    def test_true_conflict_same_company_date_heading_no_link(self):
        passages = [_passage("a#hours", "doc-a"), _passage("b#hours", "doc-b")]
        self.assertTrue(_detect_unresolved_current_conflict(passages))

    def test_no_conflict_when_effective_dates_differ(self):
        passages = [
            _passage("a#hours", "doc-a", effective_date="2026-01-01"),
            _passage("b#hours", "doc-b", effective_date="2026-02-01"),
        ]
        self.assertFalse(_detect_unresolved_current_conflict(passages))

    def test_no_conflict_when_section_titles_differ(self):
        passages = [
            _passage("a#hours", "doc-a", section_title="Store Hours"),
            _passage("b#other", "doc-b", section_title="Return Window"),
        ]
        self.assertFalse(_detect_unresolved_current_conflict(passages))

    def test_no_conflict_when_linked_via_supersedes(self):
        passages = [
            _passage("a#hours", "doc-a", superseded_by="doc-b"),
            _passage("b#hours", "doc-b", supersedes="doc-a"),
        ]
        self.assertFalse(_detect_unresolved_current_conflict(passages))

    def test_no_conflict_for_duplicate_passages_of_the_same_document(self):
        # Two passages from the same doc_id naturally share metadata; this is
        # not a cross-document conflict.
        passages = [_passage("a#hours", "doc-a"), _passage("a#hours", "doc-a")]
        self.assertFalse(_detect_unresolved_current_conflict(passages))

    def test_no_conflict_when_one_passage_is_superseded(self):
        passages = [
            _passage("a#hours", "doc-a", status="superseded"),
            _passage("b#hours", "doc-b", status="current"),
        ]
        self.assertFalse(_detect_unresolved_current_conflict(passages))


class TestAnswerQuestionCitationScope(unittest.TestCase):
    """Reproduces the review's mocked-output probes as assertions of the
    corrected contract (2026-09-28 review, group 3)."""

    def _passages(self, n):
        return [
            {
                "id": f"doc#p{i}", "doc_id": "doc", "title": "T", "version": "1",
                "status": "current", "company": "Acme", "effective_date": "2026-01-01",
                "supersedes": None, "superseded_by": None,
                "text": f"passage {i}", "section_title": f"Section {i}",
            }
            for i in range(n)
        ]

    def test_citation_to_retrieved_but_not_prompted_passage_is_rejected(self):
        # k=6 retrieves 6 passages but only MAX_CONTEXT_PASSAGES (5) are put
        # in the prompt; citing the 6th (retrieved, never shown) must be
        # treated exactly like a fabricated citation, not accepted.
        passages = self._passages(6)
        with patch.object(qa, "retrieve", return_value=passages), \
             patch.object(qa, "_detect_unresolved_current_conflict", return_value=False), \
             patch.object(qa, "generate", return_value="ANSWER: Hidden support.\nSOURCES: " + passages[5]["id"]):
            ans = qa.answer_question("q", {}, k=6)
        self.assertEqual(ans.action, "ABSTAIN")
        self.assertEqual(ans.cited_ids, [])
        self.assertIn(passages[5]["id"], ans.invalid_cited_ids)

    def test_citation_to_prompted_passage_is_accepted(self):
        passages = self._passages(6)
        with patch.object(qa, "retrieve", return_value=passages), \
             patch.object(qa, "_detect_unresolved_current_conflict", return_value=False), \
             patch.object(qa, "generate", return_value="ANSWER: Real support.\nSOURCES: " + passages[0]["id"]):
            ans = qa.answer_question("q", {}, k=6)
        self.assertEqual(ans.action, "ANSWER")
        self.assertEqual(ans.cited_ids, [passages[0]["id"]])


if __name__ == "__main__":
    unittest.main()
