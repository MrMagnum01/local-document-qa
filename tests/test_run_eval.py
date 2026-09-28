"""Tests for eval/run_eval.py's disabled generation entry point
(2026-09-28 review round 2, group 6): `main()` must refuse before touching
the model, the corpus, or disk -- on both the default `eval/results/` path
and any `--label` path -- until a reviewed successor adds a genuine
pre-run freeze. `--rescore-retained` is a separate path (no generation,
no model call) and must keep working and keep refusing to overwrite an
occupied output directory, including the retained round-1 rescore.
"""
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from eval import run_eval


class TestGenerationDisabled(unittest.TestCase):
    def test_default_run_refuses(self):
        with self.assertRaises(SystemExit):
            run_eval.main()

    def test_labelled_run_refuses(self):
        with self.assertRaises(SystemExit):
            run_eval.main("some-new-label")

    def test_labelled_run_never_touches_an_occupied_target_directory(self):
        # Reproduces the review's label_overwrite probe: a pre-existing
        # labelled results directory must never be overwritten. Trivially
        # true now, since main() refuses before touching disk at all.
        root = pathlib.Path(tempfile.mkdtemp(prefix="test-run-eval-"))
        target = root / "results-existing"
        target.mkdir()
        (target / "answers.jsonl").write_text("DO NOT OVERWRITE")
        with patch.object(run_eval, "RESULTS_DIR", root / "results"):
            with self.assertRaises(SystemExit):
                run_eval.main("existing")
        self.assertEqual((target / "answers.jsonl").read_text(), "DO NOT OVERWRITE")


class TestRescoreRetainedUnaffected(unittest.TestCase):
    def test_refuses_to_overwrite_the_retained_round1_rescore(self):
        # eval/results-rescored-fix-2026-09-28/ is retained evidence from
        # the first review round; rescore_retained must still refuse to
        # touch it, using the real committed eval/results/ and the real
        # committed rescore directory (no mocking needed for this guard).
        with self.assertRaises(SystemExit):
            run_eval.rescore_retained("fix-2026-09-28")


if __name__ == "__main__":
    unittest.main()
