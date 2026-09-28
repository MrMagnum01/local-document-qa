#!/usr/bin/env bash
# Quickstart: build the index (if needed) and answer a sample question.
# Requires: ollama running locally with qwen2.5:1.5b-instruct and
# all-minilm:33m already pulled (see README.md "Setup").
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f data/index.json ]; then
  echo "Building embedding index..."
  python3 -m src.build_index
fi

python3 -c "
from src.index import load_index
from src.qa import answer_question

idx = load_index('data/index.json')
question = 'Under the current Meridian remote work policy, how much is the home office stipend?'
a = answer_question(question, idx)
print('Q:', question)
print('Action:', a.action)
print('Answer:', a.text)
print('Cited passage ids:', a.cited_ids)
"
