# Feature 003 marker contract

## Required markers

The deterministic evidence test must print each marker exactly once when its behavior passes:

```text
[RAG] job-description-ok
[RAG] resume-pdf-ok
[RAG] source-chunks-ok
[RAG] retrieval-ok
[RAG] safety-boundary-ok
[RAG] mock-ingestion-ok
```

## Forbidden patterns

The evidence output must not contain any of these strings:

```text
Traceback
AssertionError
Script Error
TypeError
TimeoutError
```

## Evidence meaning

- `job-description-ok`: text input is normalized and sectioned.
- `resume-pdf-ok`: bounded PDF input is parsed and oversized input is rejected.
- `source-chunks-ok`: chunks retain source kind, section, location, and trust metadata.
- `retrieval-ok`: topic retrieval returns ranked relevant evidence through interfaces.
- `safety-boundary-ok`: instruction-like document text remains quoted untrusted content.
- `mock-ingestion-ok`: the complete parser, chunker, embedder, store, and retriever path works together.
