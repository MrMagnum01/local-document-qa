import unittest

from src.qa import _parse_output


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

    def test_mixed_valid_and_invalid_sources_keeps_only_valid(self):
        raw = "ANSWER: The value is 5.\nSOURCES: a#1, a#99"
        action, text, cited, invalid = _parse_output(raw, {"a#1"})
        self.assertEqual(action, "ANSWER")
        self.assertEqual(cited, ["a#1"])
        self.assertEqual(invalid, ["a#99"])


if __name__ == "__main__":
    unittest.main()
