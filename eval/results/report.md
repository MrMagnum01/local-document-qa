# Evaluation report — on this synthetic set

Frozen question set: 40 questions (20 single-doc answerable, 8 multi-document answerable, 4 version-sensitive answerable, 8 unanswerable). Run once; no selective retries or prompt changes after this run. See MANIFEST.md.

## System metrics
- Retrieval recall@5 (gold passages, answerable questions): 90.62% (29/32)
- Multi-document all-required-sources recall@5: 100.00% (8/8)
- Citation precision (mean over non-abstained answers): 59.32% (18.98/32)
- Citation recall (mean over non-abstained answers): 85.94% (27.50/32)
- Rule-scored answer agreement (answerable questions): 62.50% (20/32)
- False abstention rate on answerable questions: 0.00% (0/32)
- Abstention precision (all questions): 100.00% (5/5)
- Abstention recall (unanswerable questions): 62.50% (5/8)

## Error categories (system)
- failed_to_abstain_on_unanswerable: 3
- incomplete_or_wrong_facts: 12

## Always-abstain baseline (exposes vacuous safety scores)
- Abstention precision: 20.00% (8/40)
- Abstention recall: 100.00% (8/8)
- Rule-scored answer agreement (necessarily 0, since it never answers): 0.00% (0/32)

## Notes
- 'Rule-scored answer agreement' is keyword/alias matching against gold atomic facts plus a forbidden-term check; it is a proxy for correctness, not full semantic verification. An unsupported additional claim beyond the fixed rubric is only caught if it matches a forbidden term, which is a known limitation.
- Citation validity (cited id actually among retrieved passages) is enforced in code before scoring: an uncited or invalidly-cited 'answer' is forced to ABSTAIN by src/qa.py, so this report cannot show an uncited answer as correct.
