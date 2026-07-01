# 7. Evaluation

[← Deployment](06-deployment.md) · [Index](README.md) · Next: [Team workflow →](08-team-workflow.md)

Evaluation is a **release gate**, not an afterthought. A domain RAG that
confidently states a wrong NDVI formula is worse than no assistant, because the
team may implement it. Retrieval and answer quality are measured on a domain
golden set, and regressions block promotion.

## 7.1 Golden question set

Build **200–500** curated, expert-validated Q&A items before production, spanning
the domain categories in [appendix §21.1](appendix-domain-reference.md#211-build-golden-question-set)
(GIS fundamentals, sensors, bands, vegetation/moisture indices, preprocessing,
SAR, Bhoonidhi, EOS-like features, Akasha implementation).

Each item stores: question, expected answer, **expected source titles/pages**,
expected key terms, category, difficulty (schema:
[appendix §15](appendix-domain-reference.md#15-database-design), `eval_questions`).

## 7.2 Retrieval metrics

Measured independently of generation, using expected source/page labels:

| Metric | Meaning | Launch target |
|--------|---------|---------------|
| Recall@k | Is a relevant chunk in top-k? | ≥ 85% @5 |
| MRR | Rank of first relevant chunk | track |
| nDCG@k | Graded ranking quality | track |
| Empty-retrieval rate | Queries returning nothing | minimize; also a live signal |

Retrieval eval is fast/cheap → run on **every PR** touching chunking, embeddings,
or retrieval.

## 7.3 Answer metrics

| Metric | Meaning | Launch target |
|--------|---------|---------------|
| Faithfulness / groundedness | Answer supported by retrieved context | high |
| Citation accuracy | Citations point to chunks that actually support the claim | ≥ 90% |
| Answer correctness | Matches expert-validated answer | ≥ 85% |
| Refusal correctness | Correctly says "insufficient evidence" when it should | high |
| Hallucination rate | Unsupported claims | < 5% |

`query_logs.cited_chunk_ids` vs `retrieved_chunk_ids`
([03 §3.7](03-vector-db-and-data-stores.md#37-citation-tracking)) makes citation
accuracy directly measurable.

## 7.4 Tooling

- **Retrieval:** deterministic scripted metrics against labels (no LLM needed).
- **Answer quality:** an LLM-as-judge (e.g. RAGAS-style faithfulness/relevance)
  plus periodic **human expert** review. Use a **judge model distinct from the
  generator** where possible and keep judged samples for human audit — LLM
  judges are noisy and can share the generator's blind spots.
- Store every eval run (dataset version, model ids, metrics) for trend tracking.

## 7.5 Offline harness + online signals

- **Offline:** the golden set, run in CI and before releases.
- **Online:** production signals that surface drift between formal runs —
  thumbs-up/down [feedback](04-backend-apis.md#42-api-surface), empty-retrieval
  rate, hallucination reports, low-confidence answers — triaged back into the
  golden set.

## 7.6 CI/CD gates

| Stage | Gate |
|-------|------|
| PR (retrieval-affecting) | Retrieval metrics must not regress vs baseline |
| Pre-prod (CD) | Full suite ≥ thresholds ([§7.2](#72-retrieval-metrics)–[§7.3](#73-answer-metrics)) or promotion blocks |
| Model/prompt change | Re-run full suite; compare to pinned baseline before rollout |

This gate is the step that makes **model validation** safe: when the
[OpenAI model ids are confirmed](README.md#validate-before-locking), swapping
them re-runs evals and won't promote on a regression.

## 7.7 Eval data management

- Version the golden set; expert sign-off on additions.
- Guard against leakage (eval questions not fed back as few-shot examples).
- Re-baseline deliberately (record why) when corpus, chunking, or models change.
- Ownership + cadence: [08 §8.6](08-team-workflow.md#86-eval-gated-releases).
