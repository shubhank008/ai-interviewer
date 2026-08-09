# AI Mock Interview Platform

A browser-based, voice-native mock interview platform for practicing realistic recruiter and technical interviews with an adaptive LLM interviewer.

## Product direction

Candidates provide a job description and optionally a resume. The platform uses that context to conduct a role-, seniority-, location-, and company-aware interview with either:

- A recruiter-screen persona
- A technical or hiring-manager persona

The interview is designed to be dynamic and conversational. It uses streaming speech-to-text, LLM responses, and text-to-speech, then provides a replayable audio recording, timestamped transcript, summary, structured feedback, and a score out of 100.

## Architecture direction

The project uses capability-based interfaces rather than vendor-specific business logic. Local, hosted, open-source, and experimental providers can be swapped and A/B tested behind common interfaces for:

- LLM generation
- Speech-to-text
- Text-to-speech
- Document parsing and resume RAG
- Optional external company and culture research
- Authentication and data storage
- Audio transport and event delivery
- Storage and observability

The initial application stack is React with Tailwind v4 and shadcn/ui for a minimal, clean, mobile-friendly frontend, and FastAPI for the backend. The system is split into frontend, API, audio, and worker services.

The planned browser communication model is:

- WebRTC for live microphone and agent audio
- WebSocket for interview state, transcript events, interruptions, and playback control
- HTTP REST APIs for setup, uploads, history, recordings, transcripts, and results
- Optional backend Pub/Sub or event-bus workflows for asynchronous processing and fan-out

Candidate provider implementations include local Faster-Whisper, hosted Groq Whisper, local Kokoro or Piper, and OpenRouter or self-hosted LLMs. These are comparison candidates, not final production decisions. Local development is Docker-first and CPU-only, with an approximate 4 GB RAM and 250 GB storage target.

Resume input is PDF-only with a 5 MB limit, while job descriptions are supplied as text. The Phase 3 local ingestion slice extracts text-based PDFs, preserves source-linked chunks, provides deterministic topic retrieval, and marks instruction-like document text as untrusted data. OCR, external research, and persistent retention enforcement remain integration work. Uploaded and generated content is treated as untrusted input and must pass prompt-injection and output-safety guardrails. Interview data is retained for 14 days by default and can be completely deleted per interview.

## Project status

The repository has completed the domain and capability foundation, the Phase 2 voice-first session engine, and the Phase 3 local document ingestion and retrieval slice. The provider-independent Python package is under `src/interviewer_domain/`, with deterministic providers, a mock voice-shaped turn, recruiter or technical session state-machine coverage, and local PDF/text parsing with topic retrieval in `tests/`. Run `python -m unittest discover -s tests -v` for the local test gate. Read [`SPEC.md`](SPEC.md) for the product specification and [`PLAN.md`](PLAN.md) for the SDD implementation roadmap. The first implementation will build the voice loop directly rather than creating a separate text-only interview mode.

Each feature will be developed through the repository's SDD workflow:

1. Feature specification
2. Implementation plan
3. Marker contract
4. Capability-first implementation
5. Unit and mock end-to-end tests
6. Evidence and documentation
7. Landmine review and roadmap update
