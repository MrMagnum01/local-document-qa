"""Local-network-boundary and bounded-input tests (2026-09-28 review, group
5): Ollama calls must stay on loopback with no inherited proxy and no
redirect, HTTP responses are bounded, and corpus loading rejects oversized
files/corpora rather than reading them whole."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import config
from src.corpus import CorpusError, load_corpus
from src.ollama_client import OllamaError, _require_loopback


DOC_TEMPLATE = """---
id: doc-{n}
company: Acme
doc_type: faq
title: Doc {n}
version: "1"
effective_date: 2026-01-01
status: current
---
## Section
Some content.
"""


class TestLoopbackEnforcement(unittest.TestCase):
    def test_configured_url_is_loopback(self):
        _require_loopback(config.OLLAMA_URL)  # must not raise

    def test_non_loopback_host_rejected(self):
        with self.assertRaises(OllamaError):
            _require_loopback("http://example.com:11434")

    def test_https_scheme_rejected(self):
        # Ollama serves plain HTTP on loopback; a scheme mismatch is refused
        # rather than silently accepted.
        with self.assertRaises(OllamaError):
            _require_loopback("https://127.0.0.1:11434")

    def test_localhost_alias_accepted(self):
        _require_loopback("http://localhost:11434")


class TestNoProxyNoRedirect(unittest.TestCase):
    def test_proxy_env_vars_are_not_honoured(self):
        # The opener is (re)built with an explicit empty ProxyHandler even
        # when HTTP_PROXY/HTTPS_PROXY are set in the environment, so no
        # handler ends up registered to route requests through a proxy.
        import urllib.request

        from src.ollama_client import _build_opener

        with patch.dict("os.environ", {"HTTP_PROXY": "http://attacker.example:8080",
                                        "HTTPS_PROXY": "http://attacker.example:8080"}):
            opener = _build_opener()
        for scheme_handlers in opener.handle_open.values():
            for h in scheme_handlers:
                self.assertNotIsInstance(h, urllib.request.ProxyHandler)

    def test_redirect_handler_refuses_redirects(self):
        from src.ollama_client import _NoRedirectHandler
        handler = _NoRedirectHandler()
        with self.assertRaises(OllamaError):
            handler.redirect_request(None, None, 302, "Found", {}, "http://attacker.example/steal")


class TestCorpusBounds(unittest.TestCase):
    def test_oversized_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            big_body = "## Section\n" + ("x" * (config.MAX_CORPUS_FILE_BYTES + 10))
            (root / "big.md").write_text(
                "---\nid: big\ncompany: X\ndoc_type: faq\ntitle: T\nversion: \"1\"\n"
                "effective_date: 2025-01-01\nstatus: current\n---\n" + big_body
            )
            with self.assertRaises(CorpusError):
                load_corpus(str(root))

    def test_too_many_passages_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sections = "\n".join(f"## S{i}\ntext {i}" for i in range(config.MAX_CORPUS_PASSAGES + 5))
            (root / "many.md").write_text(
                "---\nid: many\ncompany: X\ndoc_type: faq\ntitle: T\nversion: \"1\"\n"
                "effective_date: 2025-01-01\nstatus: current\n---\n" + sections
            )
            with self.assertRaises(CorpusError):
                load_corpus(str(root))

    def test_index_truncation_recorded_and_smaller_than_prompt_bound_is_impossible(self):
        # INDEX_MAX_PASSAGE_CHARS must never be smaller than MAX_PASSAGE_CHARS,
        # or prompt-time truncation could silently no-op against a shorter
        # index-time cut, hiding the two-stage truncation the manifest
        # documents.
        self.assertGreaterEqual(config.INDEX_MAX_PASSAGE_CHARS, config.MAX_PASSAGE_CHARS)

    def test_overlong_section_marked_truncated_at_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            long_text = "y" * (config.INDEX_MAX_PASSAGE_CHARS + 500)
            (root / "long.md").write_text(
                "---\nid: long\ncompany: X\ndoc_type: faq\ntitle: T\nversion: \"1\"\n"
                "effective_date: 2025-01-01\nstatus: current\n---\n## Section\n" + long_text
            )
            passages = load_corpus(str(root))
            self.assertTrue(passages[0].truncated_at_index)
            self.assertEqual(len(passages[0].text), config.INDEX_MAX_PASSAGE_CHARS)


if __name__ == "__main__":
    unittest.main()
