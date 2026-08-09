# Plan 003 - Job Description and Resume RAG

## Global Constraints

- Preserve capability-based architecture and keep vendor integrations out of domain logic.
- Implement abstract contracts before deterministic or production provider implementations.
- Treat job descriptions, resumes, and retrieved research as untrusted user data, never as instructions.
- Keep sensitive document data bounded by the 5 MB resume limit and retain source and deletion metadata.
- Keep feature work traceable through focused semantic commits and run the no-mistakes pipeline before publication.
- Maintain deterministic local providers and real code-path tests without mocks.
- Avoid adding browser, transport, persistence, authentication, or external service dependencies in this slice.

## Marker contract

Written in `contracts/log-markers.md` before implementation. The evidence run must print:

- `[RAG] job-description-ok`
- `[RAG] resume-pdf-ok`
- `[RAG] source-chunks-ok`
- `[RAG] retrieval-ok`
- `[RAG] safety-boundary-ok`
- `[RAG] mock-ingestion-ok`

Forbidden patterns include `Traceback`, `AssertionError`, `Script Error`, `TypeError`, and `TimeoutError`.

## Work order

1. `src/interviewer_domain/contracts.py` and `models.py` - extend normalized document, embedding, and retrieval contracts.
2. `src/interviewer_domain/documents.py` - implement validation, text and limited PDF parsing, section normalization, chunking, and safety boundaries.
3. `src/interviewer_domain/retrieval.py` - implement deterministic embeddings, in-memory vector storage, and topic-aware retrieval.
4. `src/interviewer_domain/__init__.py` - expose the stable domain API.
5. `tests/test_document_rag.py` - cover pure logic, provider behavior, safety, and mock ingestion.
6. `PLAN.md` and `README.md` - record the completed Phase 3 slice and its boundaries.

## Test plan

- Unit: validate text and PDF input, section extraction, chunk source references, injection isolation, deterministic embeddings, and vector ranking.
- E2E: ingest a job description and PDF-like resume through the real pipeline, retrieve topic context, and print every RAG marker.
- Frames: none, this feature has no visual surface.
