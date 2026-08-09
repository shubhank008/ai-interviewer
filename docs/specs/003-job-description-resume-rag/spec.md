# Spec 003 - Job Description and Resume RAG

## What the feature is about and what the user experiences

A candidate can submit a text-only job description and an optional PDF resume during interview setup. The platform validates the inputs, extracts useful sections, removes unsafe instruction-like content, and prepares source-linked evidence for the interview agent.

The interview agent can request context for a topic such as motivation, system design, or project impact. Retrieval returns only the most relevant job-description and resume evidence, with source labels and locations so downstream prompts can distinguish candidate claims from role requirements. Unsupported or malformed documents fail safely without exposing raw secrets or treating uploaded text as system instructions.

This slice uses deterministic local implementations for parsing, chunking, embeddings, and vector search. All business logic depends on capability contracts so production adapters can be added later.

## Numbers

| Value | Number | Source |
|---|---:|---|
| Maximum resume upload size | 5 MB | SPEC.md, section 2.1 |
| Default retrieval result count | 5 | DESIGN-FRESH |
| Minimum chunk characters | 40 | DESIGN-FRESH |
| Maximum chunk characters | 800 | DESIGN-FRESH |
| Default retention period | 14 days | SPEC.md, section 8 |

## Out of scope

- Browser upload endpoints, authentication, Firebase, Firestore, and persistent storage
- External embedding APIs, hosted vector databases, and company research providers
- OCR for scanned PDFs, password-protected PDFs, or arbitrary office formats
- Live voice transport, LLM prompt assembly, evaluation scoring, and UI rendering
- Deletion scheduling and enforcement beyond preserving source and retention metadata

## Acceptance

- [x] Marker contract written before implementation
- [ ] Text job descriptions normalize into source-linked chunks
- [ ] PDF resumes enforce the 5 MB limit and extract supported text with source references
- [ ] Empty, malformed, and unsupported documents fail with normalized errors
- [ ] Chunk embeddings and retrieval are available through capability interfaces
- [ ] Retrieved evidence preserves source kind, section, and trust boundary
- [ ] Instruction-like content is isolated as untrusted data and never returned as executable instructions
- [ ] Unit tests exercise parsers, chunking, retrieval, safety filtering, and a real mock ingestion path
- [ ] All required markers print with no forbidden failure patterns
