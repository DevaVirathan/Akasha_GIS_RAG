# 5. Security

[← Backend APIs](04-backend-apis.md) · [Index](README.md) · Next: [Deployment →](06-deployment.md)

Security spans four concerns specific to a RAG over licensed books calling an
external LLM: **access control** (only `@thaarei.com` employees may use the
system), **secrets/data handling** (the OpenAI key and what leaves the
building), **content trust** (prompt injection from PDFs), and **governance**
(licensing, audit).

## 5.1 Authentication — the `@thaarei.com` gate

Access is one rule: **you must be a current `@thaarei.com` employee.** No role
hierarchy ([03 §3.3](03-vector-db-and-data-stores.md#33-access-model--thaareicom-employees-only)).
Enforced in three layers (defense in depth):

- **IdP tenant restriction** — OIDC/SSO limited to the thaarei.com workspace
  (e.g. Google `hd=thaarei.com` / single-tenant Microsoft 365), so no external
  account can obtain a token. Primary gate.
- **Per-request JWT check** — reject any short-lived token whose `email` is not
  a **verified** `@thaarei.com` address.
- **DB constraint** — the `users_thaarei_domain` CHECK makes a non-domain
  account physically un-insertable.

Accounts are provisioned just-in-time on first SSO login; offboarding sets
`is_active = FALSE`. Workers use scoped internal credentials, not user tokens;
no anonymous access to any endpoint.

## 5.2 Authorization — no roles, `is_admin` only

There is **no role hierarchy and no per-document ACL.** Every active
`@thaarei.com` employee has identical, full read access to the entire
RAG-approved corpus. Authorization reduces to two checks:

1. **Authenticated employee** — enforced by [§5.1](#51-authentication--the-thaareicom-gate);
   this alone grants full query/read access.
2. **`is_admin` flag** — a single boolean
   ([03 §3.3](03-vector-db-and-data-stores.md#33-access-model--thaareicom-employees-only))
   gates corpus administration (upload / ingest / govern / deactivate users).
   It is a capability flag, not a role tier.

Retrieval therefore filters only on **corpus governance** (published + active +
`allowed_for_rag`), never on the caller — see
[03 §3.7](03-vector-db-and-data-stores.md#37-retrieval-query-governance-filter-no-per-user-acl).

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
- Governance fields (owner, edition, `license_status`, `allowed_for_rag`)
  captured at upload ([appendix §2](appendix-domain-reference.md#2-critical-legal-and-data-governance-note)).
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

- AuthZ on upload (`is_admin` only); validate content-type is PDF; enforce
  `MAX_UPLOAD_SIZE_MB`; verify magic bytes, not just extension.
- Malware scan uploads before processing; store raw PDFs in a **private**
  bucket, never publicly served.
- Validate/normalize all query inputs; parameterized SQL only.

## 5.7 Rate limiting & abuse

Per-user (and per-service) token-bucket limits on `/chat` and `/search` to
contain cost and abuse; separate, higher limits for internal eval jobs. Return
`429` with `Retry-After`.

## 5.8 Audit, PII & tenancy

- **Audit log** (append-only `audit_log` table,
  [03 §3.4](03-vector-db-and-data-stores.md#34-schema)) for uploads, ingestion,
  deletes, user (de)activation, `is_admin` changes, and every query (who asked
  what, which chunks were returned).
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
