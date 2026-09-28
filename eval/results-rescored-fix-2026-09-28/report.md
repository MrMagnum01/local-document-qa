# Evaluation report — on this synthetic set

Frozen question set: 40 questions (20 single-doc answerable, 8 multi-document answerable, 4 version-sensitive answerable, 8 unanswerable). Run once; no selective retries or prompt changes after this run. See MANIFEST.md.

## System metrics
- All-gold-passages-retrieved rate @k=5 (answerable questions; per-question all-or-nothing hit on the full gold group, NOT fractional passage recall): 90.62% (29/32)
- Multi-document all-required-sources recall@5: 100.00% (8/8)
- Citation precision (mean over non-abstained answers): 59.32% (18.98/32)
- Citation recall (mean over non-abstained answers): 85.94% (27.50/32)
- Rule-scored answer agreement (answerable questions): 50.00% (16/32)
- False abstention rate on answerable questions: 0.00% (0/32)
- Abstention precision (all questions): 100.00% (5/5)
- Abstention recall (unanswerable questions): 62.50% (5/8)

## Error categories (system)
- failed_to_abstain_on_unanswerable: 3
- incomplete_or_wrong_facts: 13

## Always-abstain baseline (exposes vacuous safety scores)
- Abstention precision: 20.00% (8/40)
- Abstention recall: 100.00% (8/8)
- Rule-scored answer agreement (necessarily 0, since it never answers): 0.00% (0/32)

## Notes
- 'Rule-scored answer agreement' is keyword/alias matching against gold atomic facts, discounting alias mentions negated in the same sentence, plus a forbidden-term check and a bounded unsupported-numeric/monetary-claim check (eval/scorer.py). It remains a proxy for correctness, not full semantic verification: non-numeric unsupported additions are only caught if they match a forbidden term, which is a known limitation.
- Citation validity (cited id actually among the passages placed in the prompt) is enforced in code before scoring: an uncited, mixed-valid/fabricated, or invalidly-cited 'answer' is forced to ABSTAIN by src/qa.py, so this report cannot show such an answer as correct. Correctness also requires the exact gold passage(s) to be among the citations, not merely the right document (see 'gold_passages_cited' logic in eval/scorer.py).
