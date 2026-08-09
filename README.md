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

Phase 4 adds provider-neutral adapters in `src/interviewer_domain/provider_adapters.py` for Faster-Whisper-compatible STT, Piper/Kokoro-compatible TTS, and OpenRouter-compatible LLM transports. These adapters are optional: tests inject deterministic backends, do not access the network, and do not require credentials or model downloads. `FallbackRouter` and `ProviderFlags` provide configuration seams without placing vendor names in interview business logic. `ProviderBenchmark` records first-byte and end-to-end latency, fixture quality, estimated cost, failures, and CPU time. See `docs/specs/004-provider-benchmark-harness/` for the contract and limitations.

The browser communication model is:

- WebRTC for live microphone and agent audio. Media frames never enter the control channel.
- WebSocket for ordered interview state, transcript events, interruptions, playback control, and WebRTC signaling.
- Versioned HTTP REST resources under `/api/v1` for setup and session bootstrap; later phases add uploads, history, recordings, transcripts, and results.
- Optional backend Pub/Sub or event-bus workflows for asynchronous processing and fan-out.

Phase 5 implements these provider-independent seams in `src/interviewer_domain/transport.py`. `LocalSessionEventChannel` supports strictly ordered, correlated, idempotent events and replay after an acknowledged cursor. `LocalWebRTCMediaTransport` and `LocalBrowserControlTransport` make the media/control boundary executable offline. See [`docs/specs/005-browser-transport-session-events/`](docs/specs/005-browser-transport-session-events/) for the schemas, marker contract, and test plan.

Phase 6 adds `LiveVoiceOrchestrator` in `src/interviewer_domain/live_voice.py`. It connects incremental STT, cancellable LLM and secondary responses, digest-guarded prefetch, ordered TTS scheduling, interruption handling, timestamped artifacts, latency telemetry, and fallback routing through protocols. Deterministic streaming fixtures in `providers.py` exercise the complete loop without browsers, credentials, network access, or heavyweight models. See [`docs/specs/006-live-voice-loop/`](docs/specs/006-live-voice-loop/) for the specification, plan, and marker contract.

Candidate provider implementations include local Faster-Whisper, hosted Groq Whisper, local Kokoro or Piper, and OpenRouter or self-hosted LLMs. These are comparison candidates, not final production decisions. Local development is Docker-first and CPU-only, with an approximate 4 GB RAM and 250 GB storage target.

Resume input is PDF-only with a 5 MB limit, while job descriptions are supplied as text. The Phase 3 local ingestion slice extracts text-based PDFs, preserves source-linked chunks, provides deterministic topic retrieval, and marks instruction-like document text as untrusted data. OCR, external research, and persistent retention enforcement remain integration work. Uploaded and generated content is treated as untrusted input and must pass prompt-injection and output-safety guardrails. Interview data is retained for 14 days by default and can be completely deleted per interview.

## Project status

The repository has completed the domain and capability foundation, the Phase 2 voice-first session engine, the Phase 3 local document ingestion and retrieval slice, the Phase 4 provider-neutral adapter and benchmark harness, and the Phase 5 browser transport and session events slice. The provider-independent Python package is under `src/interviewer_domain/`, with deterministic providers, a mock voice-shaped turn, recruiter or technical session state-machine coverage, local PDF/text parsing with topic retrieval, provider-neutral STT/TTS/LLM adapters with fallback routing and benchmarking, and versioned REST/WebSocket/WebRTC transport seams in `tests/`. Run `python -m unittest discover -s tests -v` for the local test gate. Read [`SPEC.md`](SPEC.md) for the product specification and [`PLAN.md`](PLAN.md) for the SDD implementation roadmap. The first implementation will build the voice loop directly rather than creating a separate text-only interview mode.

Each feature will be developed through the repository's SDD workflow:

1. Feature specification
2. Implementation plan
3. Marker contract
4. Capability-first implementation
5. Unit and mock end-to-end tests
6. Evidence and documentation
7. Landmine review and roadmap update
