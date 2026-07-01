# 5. Security

[← Backend APIs](04-backend-apis.md) · [Index](README.md) · Next: [Deployment →](06-deployment.md)

Security spans four concerns specific to a RAG over licensed books calling an
external LLM: **access control** (who sees which book), **secrets/data
handling** (the OpenAI key and what leaves the building), **content trust**
(prompt injection from PDFs), and **governance** (licensing, audit).

## 5.1 Authentication

- OIDC / SSO against the org IdP; short-lived **JWT** access tokens + refresh.
- Service-to-service (workers) use scoped internal credentials, not user tokens.
- No anonymous access to any content endpoint.

## 5.2 Authorization (RBAC + row-level ACL)

Roles: **admin** (everything), **curator** (upload/ingest/govern), **developer**
(query all approved corpora), **viewer** (query a restricted subset).

Authorization is enforced in **two layers**:

1. **Endpoint RBAC** — e.g. only curator/admin may upload or ingest.
2. **Row-level ACL at retrieval** — the retriever intersects the caller's roles
   with `document_acl` / `confidentiality_level` **before ranking**
   ([03 §3.5](03-vector-db-and-data-stores.md#35-permission-filtering-at-query-time)),
   so a forbidden book's chunks are never scored, retrieved, or cited.

This is the "permission filters" capability, and it must live in the retrieval
query — never as a post-filter on generated text.

## 5.3 Secrets & OpenAI key handling

- **Never** in source, images, or logs. Local dev via `.env` (gitignored);
  staging/prod via a secret manager (Vault / cloud secrets).
- **Separate OpenAI project keys per environment** so spend and blast radius are
  isolated; scope/limit each key and set usage alerts.
- Rotate on a schedule and on any suspected exposure; keys injected at runtime.

## 5.4 Data governance & licensing

**The highest-severity non-technical risk.** Only ingest PDFs the org is
licensed to use. Enforced structurally:

- `license_status` + `allowed_for_rag` on every document; ingestion **refuses**
  to run unless `allowed_for_rag = true` ([02 §2.2](02-ingestion-pipeline.md#22-stage-by-stage)).
- Governance fields (owner, edition, license, confidentiality) captured at
  upload ([appendix §2](appendix-domain-reference.md#2-critical-legal-and-data-governance-note)).
- Generation rule: **do not emit long verbatim copyrighted passages** — answer
  in synthesized form with citations ([appendix §13](appendix-domain-reference.md#13-answer-generation-rules)).

## 5.5 Prompt-injection defense

Retrieved PDF text is **untrusted input**. A scanned book could contain
"ignore previous instructions." Mitigations:

- System prompt instructs the model to **treat retrieved context as data, never
  as instructions**, and never to reveal the system prompt or secrets.
- Retrieved content is clearly delimited from instructions in the prompt.
- Enforce the citation/refusal contract so off-context "answers" are caught by
  [citation validation](04-backend-apis.md#44-rag-orchestrator).
- Never let retrieved content trigger tool calls or code execution.

## 5.6 Input & upload safety

- AuthZ on upload (curator/admin only); validate content-type is PDF; enforce
  `MAX_UPLOAD_SIZE_MB`; verify magic bytes, not just extension.
- Malware scan uploads before processing; store raw PDFs in a **private**
  bucket, never publicly served.
- Validate/normalize all query inputs; parameterized SQL only.

## 5.7 Rate limiting & abuse

Per-user and per-role token-bucket limits on `/chat` and `/search` to contain
cost and abuse; separate, higher limits for internal eval jobs. Return `429`
with `Retry-After`.

## 5.8 Audit, PII & tenancy

- **Audit log** (append-only) for uploads, ingestion, deletes, role changes,
  and every query (who asked what, which chunks were returned).
- Corpus is textbook content (low PII), but user identities in logs are
  personal data — restrict access, set retention.
- Environment isolation (dev/staging/prod) doubles as tenant isolation for now.

## 5.9 Transport & at-rest

- TLS everywhere (public and, where feasible, internal).
- Encrypt object storage and DB at rest; encrypted backups.
- Least-privilege network: DB/object store/Redis not internet-exposed.

## 5.10 Security review gates

Referenced in [08-team-workflow.md](08-team-workflow.md): dependency scanning +
secret scanning in CI, a security checklist on PRs touching auth/ingestion, and
a pre-production review against this document.
