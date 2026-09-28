import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.corpus import load_corpus, corpus_fingerprint, CorpusError

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestCorpusLoading(unittest.TestCase):
    def test_loads_main_corpus_without_error(self):
        passages = load_corpus(str(REPO_ROOT / "data" / "corpus"))
        self.assertEqual(len(passages), 60)
        ids = [p.id for p in passages]
        self.assertEqual(len(ids), len(set(ids)), "passage ids must be unique")

    def test_version_metadata_present(self):
        passages = load_corpus(str(REPO_ROOT / "data" / "corpus"))
        by_doc = {p.doc_id: p for p in passages}
        self.assertEqual(by_doc["meridian-remote-work-v1"].status, "superseded")
        self.assertEqual(by_doc["meridian-remote-work-v1"].superseded_by, "meridian-remote-work-v2")
        self.assertEqual(by_doc["meridian-remote-work-v2"].status, "current")
        self.assertEqual(by_doc["meridian-remote-work-v2"].supersedes, "meridian-remote-work-v1")

    def test_missing_directory_raises(self):
        with self.assertRaises(CorpusError):
            load_corpus(str(REPO_ROOT / "data" / "does-not-exist"))

    def test_zero_byte_document_fails_categorised(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "empty.md").write_text("")
            with self.assertRaises(CorpusError):
                load_corpus(tmp)

    def test_missing_frontmatter_field_fails_categorised(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "bad.md").write_text(
                "---\nid: bad-doc\ncompany: X\n---\n## Section\nsome text\n"
            )
            with self.assertRaises(CorpusError):
                load_corpus(tmp)

    def test_no_sections_fails_categorised(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "nosections.md").write_text(
                "---\nid: x\ncompany: X\ndoc_type: faq\ntitle: T\nversion: \"1\"\n"
                "effective_date: 2025-01-01\nstatus: current\n---\nplain text, no headers\n"
            )
            with self.assertRaises(CorpusError):
                load_corpus(tmp)

    def test_fingerprint_enforces_per_file_bound(self):
        # 2026-09-28 review round 2, group 5: corpus_fingerprint is called
        # on every retrieval and must not read a whole file unbounded just
        # because it's only hashing, not loading, that file.
        with patch("src.corpus.config.MAX_CORPUS_FILE_BYTES", 1):
            with self.assertRaises(CorpusError):
                corpus_fingerprint(str(REPO_ROOT / "data" / "corpus"))

    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "corpus"
            root.mkdir()
            outside = Path(tmp) / "outside.md"
            outside.write_text(
                "---\nid: x\ncompany: X\ndoc_type: faq\ntitle: T\nversion: \"1\"\n"
                "effective_date: 2025-01-01\nstatus: current\n---\n## S\ntext\n"
            )
            link = root / "escape.md"
            try:
                link.symlink_to(outside)
            except OSError:
                self.skipTest("symlinks not supported in this environment")
            with self.assertRaises(CorpusError):
                load_corpus(str(root))


if __name__ == "__main__":
    unittest.main()
