"""Index integrity tests (2026-09-28 review, group 1): a stale, edited, or
malformed index must error explicitly rather than being silently used, both
via `load_index` and via `retrieve()` on an index dict already held in
memory. These wire in the review's mocked-output/index probes
(`~/vault/40-sessions/2026-09-28-astra-local-document-qa-probes.py`) as
assertions of the corrected behaviour rather than reproductions of the bug.
"""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import index

FAKE_EMBEDDING = [0.1, 0.2, 0.3]

DOC = """---
id: test-doc
company: Acme
doc_type: faq
title: Test Doc
version: "1"
effective_date: 2026-01-01
status: current
---
## Overview
The default protocol is WireGuard.
"""


class TestIndexIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.corpus_dir = Path(self.tmp.name)
        (self.corpus_dir / "doc.md").write_text(DOC)
        with patch("src.index.embed", return_value=FAKE_EMBEDDING):
            self.idx = index.build_index(str(self.corpus_dir))

    def tearDown(self):
        self.tmp.cleanup()

    def _retrieve(self, idx):
        with patch("src.index.embed", return_value=FAKE_EMBEDDING):
            return index.retrieve("q", idx, k=1)

    def test_fresh_index_validates_and_retrieves(self):
        results = self._retrieve(self.idx)
        self.assertEqual(len(results), 1)

    def test_missing_corpus_directory_raises(self):
        altered = copy.deepcopy(self.idx)
        altered["corpus_dir"] = "/definitely/missing/corpus"
        with self.assertRaises(index.IndexIntegrityError):
            self._retrieve(altered)

    def test_edited_passage_text_with_stale_hash_raises(self):
        altered = copy.deepcopy(self.idx)
        altered["passages"][0]["text"] = "EDITED INDEX CONTENT"  # content_hash now stale
        with self.assertRaises(index.IndexIntegrityError):
            self._retrieve(altered)

    def test_edited_passage_metadata_with_stale_hash_raises(self):
        # 2026-09-28 review round 2, group 1: the index must be bound to
        # metadata, not just text -- editing status/company/supersedes
        # independently of the text must be caught the same way.
        altered = copy.deepcopy(self.idx)
        altered["passages"][0]["status"] = "current"
        altered["passages"][0]["company"] = "FAKE"
        altered["passages"][0]["supersedes"] = "invented"
        with self.assertRaises(index.IndexIntegrityError):
            self._retrieve(altered)

    def test_query_time_embed_model_override_raises(self):
        # A per-call embed_model that differs from the index's bound model
        # must be refused, not silently used to score against embeddings it
        # did not produce (2026-09-28 review round 2, group 1).
        with self.assertRaises(index.IndexIntegrityError):
            with patch("src.index.embed", return_value=FAKE_EMBEDDING):
                index.retrieve("q", self.idx, k=1, embed_model="different-model")

    def test_query_time_embed_model_matching_bound_model_is_allowed(self):
        with patch("src.index.embed", return_value=FAKE_EMBEDDING):
            results = index.retrieve("q", self.idx, k=1, embed_model=self.idx["embed_model"])
        self.assertEqual(len(results), 1)

    def test_wrong_dimension_query_embedding_raises(self):
        # The index's passages are 3-dimensional (FAKE_EMBEDDING); a
        # 1-dimensional query vector must be refused before scoring, not
        # silently truncated by zip() (2026-09-28 review round 2, group 1).
        with self.assertRaises(index.IndexIntegrityError):
            with patch("src.index.embed", return_value=[1.0]):
                index.retrieve("q", self.idx, k=1)

    def test_nonfinite_query_embedding_raises(self):
        with self.assertRaises(index.IndexIntegrityError):
            with patch("src.index.embed", return_value=[0.1, float("nan"), 0.3]):
                index.retrieve("q", self.idx, k=1)

    def test_empty_query_embedding_raises(self):
        with self.assertRaises(index.IndexIntegrityError):
            with patch("src.index.embed", return_value=[]):
                index.retrieve("q", self.idx, k=1)

    def test_changed_corpus_bytes_on_disk_raises(self):
        (self.corpus_dir / "doc.md").write_text(DOC + "\nExtra line.\n")
        with self.assertRaises(index.IndexIntegrityError):
            self._retrieve(self.idx)

    def test_model_drift_raises(self):
        altered = copy.deepcopy(self.idx)
        altered["embed_model"] = "some-other-embedding-model"
        with self.assertRaises(index.IndexIntegrityError):
            self._retrieve(altered)

    def test_stale_chunk_version_raises(self):
        altered = copy.deepcopy(self.idx)
        altered["chunk_version"] = "some-old-chunking-scheme"
        with self.assertRaises(index.IndexIntegrityError):
            self._retrieve(altered)

    def test_malformed_vector_raises(self):
        altered = copy.deepcopy(self.idx)
        altered["passages"][0]["embedding"] = [0.1, float("nan"), 0.3]
        with self.assertRaises(index.IndexIntegrityError):
            self._retrieve(altered)

    def test_mismatched_embedding_dimension_raises(self):
        altered = copy.deepcopy(self.idx)
        dup = copy.deepcopy(altered["passages"][0])
        dup["id"] = "test-doc#overview-2"
        dup["embedding"] = [0.1, 0.2]  # wrong dimension vs. the first passage
        altered["passages"].append(dup)
        altered["passage_count"] = len(altered["passages"])
        with self.assertRaises(index.IndexIntegrityError):
            self._retrieve(altered)

    def test_passage_count_mismatch_raises(self):
        altered = copy.deepcopy(self.idx)
        altered["passage_count"] = 999
        with self.assertRaises(index.IndexIntegrityError):
            self._retrieve(altered)

    def test_missing_required_field_raises(self):
        altered = copy.deepcopy(self.idx)
        del altered["corpus_fingerprint"]
        with self.assertRaises(index.IndexIntegrityError):
            self._retrieve(altered)

    def test_load_index_also_validates(self):
        path = self.corpus_dir / "index.json"
        index.save_index(self.idx, str(path))
        loaded = index.load_index(str(path))
        self.assertEqual(loaded["passage_count"], self.idx["passage_count"])

        stale = copy.deepcopy(self.idx)
        stale["embed_model"] = "different-model"
        index.save_index(stale, str(path))
        with self.assertRaises(index.IndexIntegrityError):
            index.load_index(str(path))


if __name__ == "__main__":
    unittest.main()
