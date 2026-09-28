"""CLI: build and persist the embedding index for the main corpus.

Usage: python -m src.build_index [corpus_dir] [index_path]
"""
import sys

from . import config
from .index import build_index, save_index

DEFAULT_CORPUS = "data/corpus"
DEFAULT_INDEX = "data/index.json"


def main():
    corpus_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CORPUS
    index_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_INDEX
    index = build_index(corpus_dir, embed_model=config.EMBED_MODEL)
    save_index(index, index_path)
    print(f"Indexed {index['passage_count']} passages from {corpus_dir} -> {index_path}")


if __name__ == "__main__":
    main()
