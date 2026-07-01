# Akasha GIS & Remote Sensing RAG Model — Production-Ready Implementation Plan

> **⚠️ Reference snapshot — superseded by pillars 01–08 where they differ.**
> This is the original end-to-end draft, kept for its domain detail (glossary,
> answer modes, target users, sample questions, phases). The authoritative
> design lives in [README.md](README.md) and `01`–`08`. Where this document
> conflicts, **the pillar docs win** — notably:
> - **OpenAI-only** for embeddings + generation (no Voyage/Claude). Ignore the
>   unverified `gpt-5.5` in §24.
> - **`@thaarei.com` employees only, no role hierarchy** (single `is_admin`
>   flag) — replaces the RBAC/roles in §19 and the ACL-style schema in §15.
> - **1536-dim embeddings** (pgvector index ceiling) — the `VECTOR(1536)` and
>   full schema live in [03](03-vector-db-and-data-stores.md).

## 1. Executive Summary

Akasha RAG will be an internal domain knowledge assistant for the development team building a crop monitoring / GIS application similar to EOS Crop Monitoring. The goal is to reduce the domain learning gap for software developers, QA engineers, product owners, and GIS analysts by providing citation-backed explanations from approved Remote Sensing and GIS reference PDFs, internal architecture documents, Bhoonidhi API notes, and Akasha application documentation.

The system should not be treated as a generic chatbot. It should be a controlled enterprise knowledge layer with:

- Source-grounded answers
- Page/chapter-level citations
- GIS and Remote Sensing glossary support
- Developer-focused explanations
- Formula-level support for NDVI, NDRE, RECI, MSAVI, NDMI, cloud masking, preprocessing, mosaicking, COG, STAC, AOI, SAR, multispectral bands, and crop monitoring workflows
- Retrieval evaluation before production rollout
- Secure OpenAI API key handling
- Audit logs and feedback loop
- Dockerized deployment suitable for local, staging, and on-prem production environments

---

## 2. Critical Legal and Data Governance Note

Only ingest PDFs and books that your organization legally owns or has permission to use. Do not upload pirated, unauthorized, or license-violating copies into the RAG pipeline. For every PDF, store metadata such as license status, owner, upload date, source, edition, and permitted usage.

Recommended document governance fields:

- `source_title`
- `author`
- `publisher`
- `edition`
- `publication_year`
- `license_status`
- `uploaded_by`
- `allowed_for_rag`
- `allowed_for_team_training`
- `confidentiality_level`
- `version`

---

## 3. Business Problem

Your development team is building Akasha, a GIS / Remote Sensing / Crop Monitoring platform. The team is technically strong but the domain is specialized. Developers are facing difficulty understanding:

- Remote sensing fundamentals
- GIS terminology
- Satellite image processing
- Vegetation index formulas
- Moisture index formulas
- Preprocessing steps
- Sensor bands
- Indian satellite data workflows
- Bhoonidhi / STAC-style catalog search
- EOS-like crop monitoring feature design
- How scientific concepts map to backend APIs, databases, frontend maps, and raster processing services

Akasha RAG solves this by acting as a domain knowledge engine for the team.

---

## 4. Target Users

| User Type | Main Need | Example Question |
|---|---|---|
| Backend Developer | Understand domain logic and API requirements | “How should I calculate NDVI from Red and NIR bands?” |
| Frontend Developer | Understand map layers and color legends | “How should NDVI values be displayed on a Leaflet/Mapbox map?” |
| QA Engineer | Understand expected output and test scenarios | “What is a valid NDVI range and what edge cases should be tested?” |
| Product Manager | Understand business workflows | “How does crop stress detection help agriculture users?” |
| GIS Analyst | Validate scientific correctness | “Which preprocessing step should happen before index calculation?” |
| DevOps Engineer | Deploy and monitor the RAG system | “How should ingestion jobs and chat API be scaled?” |

---

## 5. Knowledge Sources

### 5.1 Primary PDF Sources

Use only legally approved PDF copies of the following books:

1. Fundamentals of Remote Sensing — George Joseph, C. Jeganathan
2. Jensen, J. R. 2013. Remote Sensing of the Environment: An Earth Resource Perspective
3. Reddy, A. M. 2006. Textbook of Remote Sensing and Geographical Information Systems
4. Shultz, G. A. and Engman, E. T. 2000. Remote Sensing in Hydrology and Water Management
5. Advances in Geoinformatics: Remote Sensing and GIS — Bhunia, Gouri Sankar; Uday Chatterjee; Gopal Krishna Panda
6. Basudev Bhatta — Remote Sensing and GIS, Second Edition
7. Cirsan J. Paul. 1985. Principles of Remote Sensing
8. Remote Sensing and Image Interpretation, Seventh Edition — Lillesand, Kiefer, Chipman
9. Remote Sensing and Image Interpretation, 7th Edition, Wiley Student Edition
10. Textbook of Remote Sensing and Geographical Information Systems — M. Anji Reddy

### 5.2 Internal Sources to Add Later

- Akasha product requirements
- EOS Crop Monitoring feature analysis notes
- Bhoonidhi API documentation
- Satellite download workflow docs
- NDVI / NDRE / RECI / MSAVI / NDMI implementation notes
- Backend API documentation
- Frontend map layer documentation
- DevOps deployment guides
- QA test cases
- Codebase explanation markdown files
- Architecture diagrams

---

## 6. Product Scope

### 6.1 MVP Scope

The MVP should answer team questions from approved PDFs with citations.

MVP capabilities:

- Upload PDF
- Extract text page-wise
- Chunk text
- Generate embeddings
- Store chunks in vector DB
- Ask question
- Retrieve top relevant chunks
- Generate answer using OpenAI model
- Show cited sources with page number
- Capture thumbs up/down feedback

### 6.2 Production Scope

Production capabilities:

- Role-based login
- Admin upload dashboard
- Ingestion queue
- PDF versioning
- OCR fallback for scanned pages
- Hybrid retrieval: vector + keyword
- Metadata filters by book, chapter, year, domain, topic
- Reranking
- Citation validation
- Glossary builder
- Evaluation dashboard
- Cost tracking
- Rate limiting
- Audit logs
- Prometheus/Grafana monitoring
- Dockerized deployment
- CI/CD pipeline

---

## 7. Recommended Architecture

```mermaid
flowchart TD
    U[Team User] --> FE[React / Next.js Chat UI]
    FE --> API[FastAPI Gateway]

    API --> AUTH[Auth & RBAC]
    API --> RAG[RAG Orchestrator]
    API --> DOC[Document Service]
    API --> FB[Feedback Service]

    DOC --> OBJ[Object Storage: MinIO / GCS]
    DOC --> Q[Worker Queue: Redis + Celery/RQ]
    Q --> ING[Ingestion Worker]

    ING --> EXT[PDF Text Extraction]
    EXT --> OCR[OCR Fallback for Scanned PDFs]
    EXT --> CHUNK[Semantic Chunking]
    CHUNK --> EMB[OpenAI Embeddings]
    EMB --> VDB[Vector DB: PostgreSQL + pgvector]

    RAG --> RET[Hybrid Retriever]
    RET --> VDB
    RET --> PG[(PostgreSQL Metadata DB)]
    RET --> RERANK[Reranker]
    RERANK --> LLM[OpenAI Response Model]
    LLM --> API

    API --> LOG[Query Logs + Audit Logs]
    API --> METRICS[Prometheus Metrics]
    METRICS --> GRAF[Grafana Dashboard]
```

---

## 8. Recommended Tech Stack

| Layer | Recommended Tool | Why |
|---|---|---|
| Backend API | FastAPI | Your team already uses Python/FastAPI; good for async APIs |
| LLM Provider | OpenAI API | You already have API key; production-grade model access |
| Embeddings | `text-embedding-3-small` initially | Strong cost/performance balance |
| High-accuracy Embeddings | `text-embedding-3-large` after evaluation | Better retrieval quality when needed |
| Vector DB | PostgreSQL + pgvector | Simple because your stack already uses PostgreSQL |
| Alternative Vector DB | Qdrant | Better if vector traffic becomes high-scale |
| Metadata DB | PostgreSQL | Document, user, feedback, logs, evaluation storage |
| Object Storage | MinIO locally / GCS in cloud | Store raw PDFs and extracted files |
| Queue | Redis + Celery or RQ | Background ingestion pipeline |
| PDF Extraction | PyMuPDF, pdfplumber, unstructured, Docling | Extract text, layout, tables |
| OCR Fallback | Tesseract / PaddleOCR | For scanned PDFs only |
| Frontend | React / Next.js | Chat UI, admin dashboard, citations panel |
| Auth | JWT / OAuth / Keycloak | Internal team access control |
| Monitoring | Prometheus + Grafana | Your team already uses this direction |
| Deployment | Docker + Docker Compose | Good for on-prem and staging |
| CI/CD | GitHub Actions + self-hosted runner | Fits your existing deployment model |

---

## 9. Why RAG, Not Fine-Tuning First?

For this use case, RAG should be the primary approach.

Fine-tuning is not the right first step because your team needs source-grounded, page-cited answers from reference books and internal documents. Fine-tuning is useful later for tone, classification, routing, or domain-specific response style, but it should not replace retrieval from the approved knowledge base.

Recommended strategy:

1. Start with RAG.
2. Build a clean source corpus.
3. Add evaluations.
4. Improve retrieval quality.
5. Only then consider fine-tuning for narrow tasks such as question classification, intent routing, glossary extraction, or response formatting.

---

## 10. Knowledge Model Design

Akasha RAG should have three knowledge layers.

### 10.1 Layer 1 — Source Corpus

Raw extracted content from books and internal PDFs.

Examples:

- Chapter text
- Tables
- Formula explanations
- Figure captions
- Definitions
- Examples
- Case studies

### 10.2 Layer 2 — Domain Glossary

Curated GIS / Remote Sensing glossary generated from sources and validated by GIS experts.

Example glossary terms:

- AOI
- Raster
- Vector
- CRS
- Projection
- GeoTIFF
- COG
- STAC
- Multispectral imagery
- Hyperspectral imagery
- SAR
- Red band
- NIR band
- SWIR band
- Red Edge band
- NDVI
- NDRE
- RECI
- MSAVI
- NDMI
- Atmospheric correction
- Radiometric correction
- Geometric correction
- Cloud masking
- Mosaicking
- Subsetting

### 10.3 Layer 3 — Akasha Implementation Knowledge

Internal engineering knowledge that maps theory to the product.

Examples:

- “How NDVI is implemented in Akasha backend”
- “How Bhoonidhi data is downloaded”
- “How raster tiles are stored”
- “How map layers are rendered”
- “How field boundary clipping works”
- “How API should return index layer metadata”

---

## 11. Document Ingestion Pipeline

### 11.1 Ingestion Flow

```mermaid
flowchart LR
    A[Upload PDF] --> B[Register Document Metadata]
    B --> C[Store Raw PDF]
    C --> D[Extract Text Page-wise]
    D --> E{Is Page Scanned?}
    E -- Yes --> F[OCR]
    E -- No --> G[Use Extracted Text]
    F --> H[Clean Text]
    G --> H
    H --> I[Detect Chapters / Sections]
    I --> J[Chunk Content]
    J --> K[Generate Embeddings]
    K --> L[Store in Vector DB]
    L --> M[Run Ingestion QA]
    M --> N[Ready for Search]
```

### 11.2 Extraction Rules

For every PDF:

- Preserve page number
- Preserve chapter title
- Preserve section title
- Preserve table title if available
- Preserve formula text
- Preserve figure caption
- Avoid merging unrelated pages
- Remove repeated headers/footers where possible
- Keep source metadata attached to every chunk

### 11.3 Chunking Rules

Recommended initial chunking:

- Chunk size: 500–800 tokens
- Overlap: 80–120 tokens
- Split by section first, then paragraph
- Never split formulas from their explanation
- Never split table title from table content
- Add heading context to every chunk

Example chunk payload:

```json
{
  "document_id": "book_jensen_2013",
  "source_title": "Remote Sensing of the Environment",
  "chapter": "Vegetation Applications",
  "section": "Vegetation Indices",
  "page_start": 342,
  "page_end": 343,
  "chunk_index": 128,
  "text": "NDVI is calculated using NIR and Red reflectance...",
  "tags": ["NDVI", "vegetation index", "NIR", "Red band"],
  "domain": "remote_sensing",
  "difficulty": "beginner"
}
```

---

## 12. Retrieval Strategy

### 12.1 Retrieval Pipeline

```mermaid
flowchart TD
    Q[User Question] --> QR[Query Rewrite]
    QR --> INTENT[Intent Detection]
    INTENT --> FILTER[Metadata Filter]
    FILTER --> VS[Vector Search]
    FILTER --> KS[Keyword/BM25 Search]
    VS --> MERGE[Merge Results]
    KS --> MERGE
    MERGE --> RERANK[Rerank Top Results]
    RERANK --> PACK[Context Packing]
    PACK --> GEN[Generate Answer]
    GEN --> CIT[Citation Validation]
    CIT --> OUT[Final Answer]
```

### 12.2 Retrieval Types

| Query Type | Retrieval Method |
|---|---|
| Definition question | Glossary + vector search |
| Formula question | Keyword + vector search with formula filter |
| Comparison question | Multi-source retrieval |
| Developer implementation question | Internal docs + source corpus |
| EOS-like feature question | Internal product docs + remote sensing theory |
| Satellite/Bhoonidhi question | Internal satellite docs + API docs |
| Debugging question | Internal code docs + glossary |

### 12.3 Hybrid Search Recommendation

Use both semantic search and keyword search because GIS terms are often short and technical.

Examples where keyword search matters:

- `NDVI`
- `NDRE`
- `RECI`
- `COG`
- `STAC`
- `LISS-III`
- `AWiFS`
- `SAR`
- `NIR`
- `SWIR`

Semantic search alone may miss exact acronym matches. Hybrid search improves reliability.

---

## 13. Answer Generation Rules

The assistant must follow these rules:

1. Answer only from retrieved sources when the question is domain-specific.
2. Always show source citations with book name and page number.
3. If the answer is not available in sources, say that the knowledge base does not contain enough evidence.
4. Explain concepts in beginner-friendly language first.
5. Then explain the developer implementation angle.
6. Do not provide unsupported scientific claims.
7. Do not quote long copyrighted passages.
8. Prefer concise, structured output.
9. For formulas, show variables and expected data types.
10. For Akasha implementation questions, map concept → backend → database → frontend → QA.

---

## 14. Prompt Architecture

### 14.1 System Prompt

```text
You are Akasha GIS RAG Assistant, an internal technical assistant for a crop monitoring and GIS development team.

Your job is to answer questions using only the retrieved context from approved knowledge sources and internal Akasha documentation.

Response rules:
- Give a direct answer first.
- Explain in beginner-friendly terms.
- Add developer implementation guidance when relevant.
- Cite every factual claim using source title, chapter/section, and page number.
- If the answer is not present in the retrieved context, say: "The current knowledge base does not contain enough evidence for this answer."
- Do not invent formulas, satellite specifications, API parameters, or book references.
- Do not quote long copyrighted passages.
- For crop monitoring topics, connect the explanation to Akasha application workflows.
```

### 14.2 Developer-Focused Answer Template

```text
## Direct Answer
...

## Simple Explanation
...

## Developer POV
- Input:
- Processing:
- Output:
- Backend impact:
- Frontend impact:
- QA checks:

## Akasha Application Mapping
...

## Sources
- Source title, page number
```

---

## 15. Database Design

### 15.1 Core Tables

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    publisher TEXT,
    edition TEXT,
    publication_year INT,
    source_type TEXT NOT NULL,
    license_status TEXT NOT NULL,
    file_path TEXT NOT NULL,
    checksum TEXT NOT NULL,
    uploaded_by UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE document_versions (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    version_no INT NOT NULL,
    file_path TEXT NOT NULL,
    checksum TEXT NOT NULL,
    ingestion_status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    document_version_id UUID REFERENCES document_versions(id),
    chunk_index INT NOT NULL,
    page_start INT,
    page_end INT,
    chapter TEXT,
    section TEXT,
    heading_path TEXT,
    text TEXT NOT NULL,
    token_count INT,
    domain TEXT,
    difficulty TEXT,
    tags TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE chunk_embeddings (
    id UUID PRIMARY KEY,
    chunk_id UUID REFERENCES chunks(id),
    embedding_model TEXT NOT NULL,
    embedding_dimension INT NOT NULL,
    embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE glossary_terms (
    id UUID PRIMARY KEY,
    term TEXT NOT NULL,
    acronym TEXT,
    definition TEXT NOT NULL,
    simple_explanation TEXT,
    developer_explanation TEXT,
    related_terms TEXT[],
    validated_by_expert BOOLEAN DEFAULT FALSE,
    source_chunk_ids UUID[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE query_logs (
    id UUID PRIMARY KEY,
    user_id UUID,
    question TEXT NOT NULL,
    rewritten_query TEXT,
    intent TEXT,
    retrieved_chunk_ids UUID[],
    answer TEXT,
    model_name TEXT,
    prompt_tokens INT,
    completion_tokens INT,
    latency_ms INT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE feedback (
    id UUID PRIMARY KEY,
    query_log_id UUID REFERENCES query_logs(id),
    user_id UUID,
    rating INT,
    comment TEXT,
    issue_type TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE eval_questions (
    id UUID PRIMARY KEY,
    question TEXT NOT NULL,
    expected_answer TEXT,
    expected_source_titles TEXT[],
    expected_terms TEXT[],
    difficulty TEXT,
    category TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 15.2 Metadata Filters

Every chunk should support filters:

- Book title
- Author
- Chapter
- Section
- Page range
- Topic tag
- Difficulty level
- Domain
- Source type
- License status
- Internal/external document

---

## 16. API Design

### 16.1 Document APIs

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/documents/upload` | Upload PDF |
| GET | `/api/v1/documents` | List documents |
| GET | `/api/v1/documents/{id}` | Get document details |
| POST | `/api/v1/documents/{id}/ingest` | Start ingestion job |
| GET | `/api/v1/documents/{id}/chunks` | View extracted chunks |
| DELETE | `/api/v1/documents/{id}` | Disable/remove document |

### 16.2 Chat/RAG APIs

> Superseded by the resource-oriented model in [04 §4.2](04-backend-apis.md#42-api-surface):
> chat is **messages inside a conversation**, and streaming is negotiated with
> `Accept: text/event-stream` on one endpoint (not a separate `/chat/stream`).

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/conversations` | Start a conversation |
| GET | `/api/v1/conversations` | List the caller's conversations |
| GET | `/api/v1/conversations/{id}` | Conversation with its messages |
| POST | `/api/v1/conversations/{id}/messages` | Ask a question (SSE stream or JSON) |
| POST | `/api/v1/search` | Search chunks without answer generation |

### 16.3 Glossary APIs

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/glossary` | List terms |
| GET | `/api/v1/glossary/{term}` | Get term explanation |
| POST | `/api/v1/glossary/generate` | Generate candidate terms from corpus |
| PATCH | `/api/v1/glossary/{id}/validate` | GIS expert validation |

### 16.4 Feedback and Evaluation APIs

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/messages/{id}/feedback` | Feedback on a specific answer |
| POST | `/api/v1/evals/run` | Run RAG evaluation set |
| GET | `/api/v1/evals/results` | View quality metrics |
| GET | `/api/v1/analytics/usage` | Usage and cost summary |

---

## 17. Example Chat Request / Response

### Request

```json
{
  "question": "What is NDVI and how do we implement it in Akasha?",
  "filters": {
    "domain": "remote_sensing",
    "tags": ["NDVI", "vegetation_index"]
  },
  "answer_style": "developer_friendly"
}
```

### Response

```json
{
  "answer": "NDVI is a vegetation index calculated from NIR and Red reflectance...",
  "developer_pov": {
    "input": "NIR band and Red band raster",
    "formula": "(NIR - Red) / (NIR + Red)",
    "output": "GeoTIFF + PNG tile layer + legend metadata",
    "qa_checks": [
      "NDVI range should be between -1 and +1",
      "Handle division by zero",
      "Preserve CRS and transform",
      "Mask cloud/no-data pixels"
    ]
  },
  "sources": [
    {
      "title": "Remote Sensing and Image Interpretation",
      "page": 412,
      "chunk_id": "..."
    }
  ]
}
```

---

## 18. Frontend UX Plan

### 18.1 Main Screens

1. Login page
2. Chat page
3. Source citation side panel
4. Document library page
5. Upload document page
6. Ingestion status page
7. Glossary page
8. Evaluation dashboard
9. Admin settings page

### 18.2 Chat UX

Chat answer should show:

- Final answer
- Simple explanation
- Developer POV
- Akasha mapping
- Sources
- Confidence level
- Feedback buttons
- “Open source page” action if PDF viewer is available

### 18.3 Source Viewer

When user clicks a citation:

- Open PDF viewer
- Jump to page
- Highlight retrieved chunk if possible
- Show metadata: book, chapter, page, section

---

## 19. Production Security Plan

### 19.1 API Key Security

- Never hardcode OpenAI API key in source code
- Store key in `.env` locally
- Use secret manager in staging/production
- Restrict server access
- Rotate keys periodically
- Use separate OpenAI project keys for dev/staging/prod
- Monitor usage and spending

### 19.2 Application Security

- JWT authentication
- Role-based access control
- Admin-only document uploads
- User-level audit logs
- Rate limiting per user
- Input validation
- File type validation
- PDF size limits
- Malware scanning if exposed to external uploads
- No public access to raw PDFs unless authorized

### 19.3 RAG Safety

- Prevent prompt injection from PDF content
- Treat retrieved text as untrusted context
- Do not follow instructions inside retrieved documents
- Do not reveal system prompts
- Do not reveal API keys or internal secrets
- Add answer refusal rule when evidence is insufficient

---

## 20. Observability and Monitoring

Track these metrics:

| Metric | Why It Matters |
|---|---|
| Request count | Usage tracking |
| Average latency | User experience |
| Retrieval latency | Vector DB performance |
| LLM latency | OpenAI response performance |
| Token usage | Cost control |
| Error rate | Reliability |
| Ingestion failures | Data pipeline quality |
| Empty retrieval rate | Knowledge gap detection |
| Low feedback rate | Answer quality signal |
| Hallucination reports | Production risk |

Recommended tools:

- Prometheus for metrics
- Grafana dashboards
- Structured JSON logs
- Sentry for exceptions
- PostgreSQL query logs
- OpenAI usage dashboard

---

## 21. Evaluation Strategy

### 21.1 Build Golden Question Set

Create 200–500 validation questions before production.

Categories:

- GIS fundamentals
- Remote sensing basics
- Satellite sensors
- Multispectral bands
- Vegetation indices
- Moisture indices
- Image preprocessing
- SAR/RADAR
- Bhoonidhi workflow
- EOS-like crop monitoring features
- Akasha implementation questions

### 21.2 Metrics

| Metric | Target |
|---|---|
| Retrieval Recall@5 | >= 85% |
| Citation accuracy | >= 90% |
| Answer correctness | >= 85% |
| Hallucination rate | < 5% |
| Average answer latency | < 6 seconds for normal answers |
| User helpful feedback | >= 80% positive |

### 21.3 Example Eval Questions

1. What is AOI in GIS?
2. What is the difference between raster and vector data?
3. What is NDVI?
4. Which bands are needed for NDVI?
5. Why do we need atmospheric correction?
6. What is cloud masking?
7. What is mosaicking?
8. What is COG?
9. What is STAC?
10. How does NDMI differ from NDVI?
11. What is Red Edge band?
12. What is SAR and why is it useful during cloudy conditions?
13. How should Akasha generate an index layer after satellite download?
14. What QA checks are needed for NDVI output?
15. What should the frontend show for vegetation index legends?

---

## 22. Folder Structure

```text
akasha-rag/
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/
│   │   │   │   ├── config.py
│   │   │   │   ├── security.py
│   │   │   │   └── logging.py
│   │   │   ├── db/
│   │   │   │   ├── session.py
│   │   │   │   ├── models.py
│   │   │   │   └── migrations/
│   │   │   ├── documents/
│   │   │   │   ├── router.py
│   │   │   │   ├── service.py
│   │   │   │   └── schemas.py
│   │   │   ├── ingestion/
│   │   │   │   ├── extractor.py
│   │   │   │   ├── cleaner.py
│   │   │   │   ├── chunker.py
│   │   │   │   ├── embedder.py
│   │   │   │   └── pipeline.py
│   │   │   ├── rag/
│   │   │   │   ├── router.py
│   │   │   │   ├── orchestrator.py
│   │   │   │   ├── retriever.py
│   │   │   │   ├── reranker.py
│   │   │   │   ├── prompts.py
│   │   │   │   └── citation_validator.py
│   │   │   ├── glossary/
│   │   │   │   ├── router.py
│   │   │   │   └── service.py
│   │   │   ├── evals/
│   │   │   │   ├── router.py
│   │   │   │   ├── runner.py
│   │   │   │   └── metrics.py
│   │   │   └── feedback/
│   │   │       ├── router.py
│   │   │       └── service.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   └── web/
│       ├── src/
│       │   ├── app/
│       │   ├── components/
│       │   ├── features/chat/
│       │   ├── features/documents/
│       │   ├── features/glossary/
│       │   └── features/evals/
│       ├── Dockerfile
│       └── package.json
├── infra/
│   ├── docker-compose.yml
│   ├── nginx/
│   ├── prometheus/
│   └── grafana/
├── scripts/
│   ├── ingest_document.py
│   ├── build_glossary.py
│   └── run_evals.py
├── docs/
│   ├── architecture.md
│   ├── ingestion.md
│   ├── rag-quality.md
│   └── deployment.md
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
├── .env.example
└── README.md
```

---

## 23. Docker Compose Services

```yaml
services:
  api:
    build: ./apps/api
    env_file: .env
    depends_on:
      - postgres
      - redis
      - minio

  worker:
    build: ./apps/api
    command: celery -A app.ingestion.worker worker --loglevel=info
    env_file: .env
    depends_on:
      - postgres
      - redis
      - minio

  web:
    build: ./apps/web
    env_file: .env
    depends_on:
      - api

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: akasha_rag
      POSTGRES_USER: akasha
      POSTGRES_PASSWORD: akasha_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7

  minio:
    image: minio/minio
    command: server /data --console-address ':9001'
    environment:
      MINIO_ROOT_USER: minio
      MINIO_ROOT_PASSWORD: minio_password
    volumes:
      - minio_data:/data

  nginx:
    image: nginx:alpine
    volumes:
      - ./infra/nginx:/etc/nginx/conf.d
    depends_on:
      - api
      - web

volumes:
  postgres_data:
  minio_data:
```

---

## 24. Environment Variables

```env
APP_ENV=development
APP_NAME=akasha-rag

DATABASE_URL=postgresql+psycopg://akasha:akasha_password@postgres:5432/akasha_rag
REDIS_URL=redis://redis:6379/0

OPENAI_API_KEY=replace_with_secret
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_RESPONSE_MODEL=gpt-5.5

MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minio
MINIO_SECRET_KEY=minio_password
MINIO_BUCKET=akasha-documents

JWT_SECRET=replace_with_secret
MAX_UPLOAD_SIZE_MB=200
DEFAULT_TOP_K=12
RERANK_TOP_K=6
```

---

## 25. CI/CD Plan

### 25.1 CI Pipeline

On pull request:

1. Install dependencies
2. Run lint
3. Run type checks
4. Run unit tests
5. Run ingestion pipeline tests
6. Run RAG prompt tests
7. Build Docker images

### 25.2 Deployment Pipeline

On merge to main:

1. Build Docker images
2. Push images to registry
3. SSH/self-hosted runner deploys on server
4. Run database migrations
5. Restart services
6. Health check API
7. Smoke test chat endpoint

---

## 26. Implementation Phases

## Phase 0 — Governance and Data Preparation

### Goals

- Confirm legal use of all PDFs
- Prepare metadata sheet
- Classify source priority
- Decide MVP corpus

### Tasks

- Create document inventory
- Add license status
- Add edition and author metadata
- Mark scanned vs text PDF
- Select first 2–3 books for MVP
- Create 50 initial test questions

### Acceptance Criteria

- Approved source list completed
- First corpus selected
- Legal/licensing flag available for every PDF

---

## Phase 1 — Local MVP RAG

### Goals

Build basic PDF-to-answer workflow.

### Tasks

- FastAPI project setup
- PostgreSQL + pgvector setup
- PDF upload endpoint
- PyMuPDF text extraction
- Basic chunking
- OpenAI embedding generation
- Vector search endpoint
- Basic chat endpoint
- Return answer with source title and page number

### Acceptance Criteria

- Upload one PDF
- Ask “What is remote sensing?”
- Get citation-backed answer
- Query logs stored

---

## Phase 2 — Production Ingestion Pipeline

### Goals

Make ingestion reliable and asynchronous.

### Tasks

- Add Redis + Celery/RQ worker
- Store PDF in MinIO
- Add document versioning
- Add ingestion status
- Add OCR fallback
- Add text cleaning
- Add section-aware chunking
- Add ingestion QA report

### Acceptance Criteria

- Admin can upload multiple PDFs
- Ingestion runs in background
- Failed pages are logged
- Chunks are visible from API

---

## Phase 3 — High-Quality Retrieval

### Goals

Improve answer accuracy.

### Tasks

- Add hybrid search
- Add metadata filters
- Add acronym-aware keyword search
- Add reranking
- Add context packing
- Add citation validation

### Acceptance Criteria

- Retrieval works for acronyms like NDVI, COG, SAR, STAC
- User can filter by book/topic
- Citations include page numbers

---

## Phase 4 — Chat UI and Admin Dashboard

### Goals

Make the system usable by the team.

### Tasks

- Build React chat UI
- Build document upload UI
- Build citation side panel
- Build PDF source viewer
- Add feedback buttons
- Add chat history

### Acceptance Criteria

- Developer can ask question from browser
- Answer shows citations
- Admin can upload and ingest PDF
- Feedback is stored

---

## Phase 5 — Glossary and Learning Mode

### Goals

Help beginners learn GIS/Remote Sensing terms.

### Tasks

- Generate glossary candidates
- Add GIS expert validation flow
- Build glossary UI
- Add “Explain like beginner” mode
- Add “Developer POV” mode
- Add related terms graph

### Acceptance Criteria

- User can search “AOI” and get validated definition
- Related terms are shown
- Answer includes Akasha implementation mapping

---

## Phase 6 — Evaluation and Quality Gate

### Goals

Prevent hallucination and weak retrieval.

### Tasks

- Build golden question set
- Add eval runner
- Track Recall@5
- Track citation accuracy
- Track hallucination reports
- Add manual review dashboard

### Acceptance Criteria

- 200+ eval questions available
- Retrieval Recall@5 >= 85%
- Citation accuracy >= 90%
- Quality report generated before deployment

---

## Phase 7 — Production Hardening

### Goals

Make it production-ready.

### Tasks

- JWT/RBAC
- Rate limiting
- Streaming responses
- Retry and timeout handling
- Cost tracking
- Prometheus metrics
- Grafana dashboards
- Structured logs
- Backup strategy
- CI/CD deployment

### Acceptance Criteria

- Staging and production environments separated
- Secrets are not in code
- API health checks pass
- Dashboard shows usage and errors

---

## Phase 8 — Akasha Domain Integration

### Goals

Connect RAG to actual Akasha product development.

### Tasks

- Add Akasha architecture docs
- Add Bhoonidhi API docs
- Add satellite ingestion docs
- Add NDVI microservice docs
- Add field analytics code explanations
- Add “Implementation Answer Mode”
- Add “QA Test Scenario Mode”

### Acceptance Criteria

- Developer can ask: “How do I implement NDRE in Akasha?”
- RAG returns formula, required bands, backend steps, DB storage, map output, and QA checks
- Answer cites source theory and internal implementation docs

---

## 27. Akasha-Specific Answer Modes

### 27.1 Domain Explanation Mode

For learning GIS concepts.

Example:

> “What is atmospheric correction?”

Output:

- Simple definition
- Why it matters
- Crop monitoring example
- Source citation

### 27.2 Developer Implementation Mode

For backend/frontend tasks.

Example:

> “How do I implement NDVI after satellite download?”

Output:

- Required input bands
- Formula
- Preprocessing dependency
- Raster processing steps
- API response design
- Frontend layer behavior
- QA checks

### 27.3 QA Mode

For testers.

Example:

> “What test cases are needed for NDVI?”

Output:

- Functional cases
- Edge cases
- No-data cases
- Cloud mask cases
- Range validation
- Visual validation

### 27.4 Product Mode

For PM/client discussions.

Example:

> “Why is NDVI useful for agriculture users?”

Output:

- Business value
- User workflow
- Crop health interpretation
- Limitation notes

---

## 28. Initial Domain Glossary Backlog

Start with these high-priority terms:

### GIS Basics

- GIS
- AOI
- Raster
- Vector
- Layer
- CRS
- Projection
- Coordinate system
- Shapefile
- GeoJSON
- GeoTIFF
- COG
- Tile
- Bounding box

### Remote Sensing Basics

- Remote sensing
- Passive sensor
- Active sensor
- Spatial resolution
- Spectral resolution
- Temporal resolution
- Radiometric resolution
- Reflectance
- DN value
- Multispectral imagery
- Hyperspectral imagery

### Satellite and Sensor Terms

- Sentinel-2
- Resourcesat
- LISS-III
- LISS-IV
- AWiFS
- SAR
- RISAT
- NISAR
- Optical satellite
- Radar satellite

### Band Terms

- Blue band
- Green band
- Red band
- Red Edge band
- NIR band
- SWIR band

### Vegetation and Moisture Indices

- NDVI
- NDRE
- RECI
- MSAVI
- NDMI
- EVI
- SAVI

### Processing Terms

- Radiometric correction
- Atmospheric correction
- Geometric correction
- Orthorectification
- Cloud masking
- Mosaicking
- Subsetting
- Resampling
- Reprojection
- Clipping

### Data Catalog Terms

- STAC
- STAC item
- STAC collection
- Asset
- COG asset
- Metadata
- Search filter

---

## 29. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Unauthorized PDF usage | Legal/compliance issue | Ingest only approved/licensed documents |
| Poor PDF extraction | Bad answers | Page-wise QA, OCR fallback, manual review |
| Hallucinated answers | Team may implement wrong logic | Citation validation, evals, refusal rule |
| Weak acronym retrieval | Misses GIS terms | Hybrid search + keyword boosting |
| High OpenAI cost | Budget issue | Cache, smaller models, token limits, usage monitoring |
| Slow responses | Poor UX | Streaming, top-k tuning, caching, reranking limits |
| Outdated internal docs | Wrong implementation guidance | Versioning and doc ownership |
| Prompt injection from documents | Security issue | Treat source text as untrusted context |
| No domain expert validation | Scientific mistakes | GIS expert review queue |

---

## 30. Definition of Done for Production

Akasha RAG is production-ready when:

- Auth and RBAC are enabled
- PDFs are legally approved and versioned
- Upload/ingestion pipeline is stable
- Source citations are shown for every factual answer
- Eval metrics meet target thresholds
- Logs and metrics are monitored
- OpenAI key is stored securely
- Costs are tracked
- Feedback loop is active
- Backup and restore process is documented
- CI/CD pipeline deploys without manual steps
- Team can use it for daily development questions

---

## 31. Recommended MVP Build Order

1. PostgreSQL + pgvector setup
2. FastAPI base project
3. PDF upload
4. PDF text extraction
5. Chunking
6. OpenAI embeddings
7. Vector search
8. Basic chat API
9. Citation output
10. Query logs
11. React chat UI
12. Feedback buttons
13. Admin upload UI
14. Evaluation question set
15. Production hardening

---

## 32. First 20 Questions to Validate MVP

1. What is remote sensing?
2. What is GIS?
3. What is AOI?
4. What is raster data?
5. What is vector data?
6. What is NDVI?
7. Which bands are required for NDVI?
8. What is NIR?
9. What is Red Edge band?
10. What is NDRE?
11. What is NDMI?
12. What is cloud masking?
13. What is atmospheric correction?
14. What is geometric correction?
15. What is mosaicking?
16. What is COG?
17. What is STAC?
18. What is SAR?
19. Why is SAR useful during cloud cover?
20. How does a vegetation index help crop monitoring?

---

## 33. Final Recommendation

Build Akasha RAG as a production-grade internal knowledge platform, not just a chatbot. Start with a controlled MVP using 2–3 legally approved PDFs, PostgreSQL + pgvector, FastAPI, OpenAI embeddings, and citation-backed chat. After the MVP works, add hybrid retrieval, glossary validation, evaluation, and production hardening.

For your Akasha crop monitoring team, the most valuable feature will be “Developer Implementation Mode,” where the RAG system explains GIS/Remote Sensing concepts and directly maps them to backend APIs, raster processing, database design, frontend map layers, and QA test cases.
