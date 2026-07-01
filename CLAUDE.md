# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

**This repository currently contains data only — there is no application code, build system, tests, or git repository yet.** The name `Akasha_GIS_RAG` indicates the intended goal: a Retrieval-Augmented Generation (RAG) system that answers questions over a corpus of Remote Sensing / GIS textbooks.

Do not document build/lint/test commands or a code architecture until they actually exist. When code is added, update this file with the real commands and structure.

## The corpus

All source material lives under [Data/](Data/) — ~1.2 GB across 10 PDF textbooks, split into two syllabus-oriented folders:

- [Data/Bsc Agri/](Data/Bsc%20Agri/) — 6 PDFs (~1.05 GB)
- [Data/BTech Agri/](Data/BTech%20Agri/) — 4 PDFs (~145 MB)

Characteristics that matter for ingestion:

- **Several files are very large and likely scanned/image-heavy** (e.g. Basudev Bhatta ~390 MB, Anji Reddy ~254 MB, Lillesand & Kiefer ~161 MB). Expect that plain text extraction will fail or return garbage on some pages, so an **OCR fallback** will be needed. Verify extractable text per-document before assuming a single pipeline works for all.
- **The corpus overlaps / duplicates.** There are two Lillesand & Kiefer "7th edition" files and two different Reddy textbooks. Deduplicate or track provenance so retrieval does not return near-identical chunks.
- **Folder names encode audience** (`Bsc Agri` vs `BTech Agri`), not distinct topics — both are Remote Sensing & GIS. Preserve the source filename/folder as retrieval metadata for citations.

## Working constraints

- **Never commit the PDFs.** At 1.2 GB they exceed normal git limits. When git is initialized, add `Data/` (and any generated index/vector-store artifacts) to `.gitignore`.
- Paths and filenames contain **spaces**; always quote them in shell commands.
- The environment is **Windows / PowerShell**. Prefer cross-platform (Python `pathlib`) path handling over hardcoded separators.

## Intended direction (not yet built)

A typical pipeline for this project, to be implemented: PDF text/OCR extraction → chunking with source metadata → embeddings → vector store → retrieval + LLM answer synthesis with citations. Treat this as a proposal; confirm specifics before scaffolding.
