# 8. Team Workflow

[← Evaluation](07-evaluation.md) · [Index](README.md)

How the team builds, reviews, ships, and operates Akasha RAG. This is the pillar
the original draft omitted; it turns the architecture into a repeatable practice.

## 8.1 Roles & RACI

Built from the [target users in appendix §4](appendix-domain-reference.md#4-target-users).

| Activity | Backend | GIS analyst / curator | DevOps | QA | Product |
|----------|:------:|:---------------------:|:------:|:--:|:------:|
| Ingestion & chunking code | **R** | C | C | I | I |
| Document approval & licensing | I | **R/A** | I | I | C |
| Retrieval/prompt tuning | **R** | C | I | C | I |
| Golden set curation | C | **R** | I | C | A |
| Deploy & infra | C | I | **R/A** | I | I |
| Eval gate sign-off | C | **R** | I | C | A |
| Security review | **R** | I | **R** | I | I |

R = responsible, A = accountable, C = consulted, I = informed.

## 8.2 Repository

Single monorepo (`apps/api`, `apps/web`, `infra`, `scripts`, `docs`, `Plan`) —
layout in [appendix §22](appendix-domain-reference.md#22-folder-structure).
`CODEOWNERS` maps each area to an owner: `ingestion/` + `rag/` → backend/GIS;
`infra/` → DevOps; `evals/` → GIS/QA; `Plan/` → tech lead.

## 8.3 Branching, review, Definition of Done

- **Trunk-based**: short-lived feature branches → PR → `main`; `main` always
  deployable. Tags/releases for prod promotions.
- **PR review:** ≥1 code-owner approval; CI green ([06 §6.5](06-deployment.md#65-ci-on-pull-request));
  retrieval evals non-regressing for retrieval-affecting PRs.
- **Definition of Ready:** licensing cleared for any new source; acceptance
  criteria + eval impact noted.
- **Definition of Done:** tests + docs updated; evals pass; observability in
  place (logs/metrics for new paths); security checklist done if auth/ingestion
  touched. Production DoD: [appendix §30](appendix-domain-reference.md#30-definition-of-done-for-production).

## 8.4 Ingestion runbook

Standard operating procedure for adding a book (governance is a **gate**, not a
formality):

1. **Verify licensing** — confirm the org may use this PDF; set `license_status`
   + `allowed_for_rag` ([05 §5.4](05-security.md#54-data-governance--licensing)).
   No license → stop.
2. Upload via admin API; capture metadata (title, author, edition, year, source).
3. Enqueue ingestion; monitor job + OCR ratio.
4. Review the **QA report** ([02 §2.6](02-ingestion-pipeline.md#26-ingestion-qa-gate));
   quarantined versions get manual spot-check.
5. Spot-check retrieval on a few known questions from that book.
6. Publish the version; record in the change log.
7. Add/refresh a few golden-set questions covering the new material.

## 8.5 Model & version change management

OpenAI models and prompts are **pinned config**, changed deliberately:

- Model ids live in env/config only ([04 §4.6](04-backend-apis.md#46-openai-client-wrapper));
  never hardcoded.
- Any change to model id, embedding model, prompt template, or chunking is a PR
  that **re-runs the eval suite** and is compared to the pinned baseline
  ([07 §7.6](07-evaluation.md#76-cicd-gates)).
- **Embedding-model change ⇒ full re-embed + reindex** (dimensions/space differ)
  — plan it as a migration, not a config tweak
  ([03 §3.9](03-vector-db-and-data-stores.md#39-sizing-backups-migrations)).
- This is the pathway for the pending
  [OpenAI validation](README.md#validate-before-locking): confirm ids → PR →
  evals → promote.

## 8.6 Eval-gated releases

- Retrieval evals on every retrieval-affecting PR; full suite before prod.
- GIS/QA owns thresholds and sign-off; Product is accountable for the gate.
- Promotion to prod is blocked on a failing gate — no manual override without
  tech-lead + Product sign-off recorded.

## 8.7 Incident response & on-call

- **Sev levels:** Sev1 outage / wrong-permission data exposure; Sev2 degraded
  quality or latency; Sev3 minor.
- **Wrong-answer / hallucination reports** are first-class: capture
  `query_log_id`, triage, add to golden set, fix retrieval/prompt, verify via evals.
- Runbooks for: OpenAI outage/rate-limit (degrade gracefully, surface status),
  DB restore ([06 §6.8](06-deployment.md#68-backups--dr)), ingestion backlog,
  cost spike.

## 8.8 Documentation & decisions

- This `Plan/` set is the source of truth; keep it current as reality diverges.
- **ADRs** in `docs/` for significant choices (e.g. "pgvector over Qdrant",
  "OpenAI model X after validation") with context + consequences.
- The [appendix](appendix-domain-reference.md) holds domain reference material
  (glossary backlog, answer modes, sample questions) — curators keep it current.

## 8.9 Cadence

- Work tracked as issues mapped to the [phased roadmap](appendix-domain-reference.md#26-implementation-phases).
- Regular corpus/eval review: inspect low-feedback and empty-retrieval queries,
  refresh the golden set, reprioritize ingestion.
- Security + dependency review on a fixed cadence ([05 §5.10](05-security.md#510-security-review-gates)).
