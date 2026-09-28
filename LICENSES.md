# Licenses

## Runtime dependencies (installed metadata)
This project has **zero third-party Python packages** (see `requirements.txt`).
The pipeline uses only the Python 3 standard library.

| Component | License | Notes |
|---|---|---|
| Python 3.13 standard library | PSF License 2.0 (OSI-approved) | `json`, `urllib`, `hashlib`, `re`, `dataclasses`, `pathlib`, `math`, `unittest` |
| Ollama (runtime engine, v0.34.4) | MIT | Local inference server; installed separately, not vendored in this repo |

## Model weights (separate from the runtime license above)
| Model | Ollama tag | Upstream | Weights/tokenizer license | Verified |
|---|---|---|---|---|
| Generator | `qwen2.5:1.5b-instruct` | Qwen/Qwen2.5-1.5B-Instruct | **Apache License 2.0** | `https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/blob/main/LICENSE`, checked 2026-09-28. The 1.5B size is explicitly Apache-2.0; the 3B and 72B Qwen2.5 sizes use a different, non-OSI Qwen license — license was not inferred from the model family name. |
| Embeddings | `all-minilm:33m` | sentence-transformers/all-MiniLM-L6-v2 | **Apache-2.0** | HuggingFace model card tags (`license: apache-2.0`), checked 2026-09-28. |

No Llama or Gemma community-licensed models are used anywhere in this repo.

## Data
All corpus documents under `data/corpus/`, `data/dev_corpus/`, and
`data/fixtures/` are synthetic, written for this demo. No real company,
customer, or employee data.
