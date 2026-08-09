# AI Mock Interview Platform Roadmap

## Purpose

This document tracks the initial implementation roadmap for the voice-native AI mock interview platform. `SPEC.md` defines the product and architecture requirements. Each implementation slice must receive a focused feature specification and plan under `docs/specs/` before code is written.

## Guiding principles

- Build capability interfaces before provider integrations.
- Keep business logic independent of hosted vendors and infrastructure.
- Maintain local providers and deterministic test providers wherever practical.
- Measure latency, quality, cost, reliability, and resource usage before selecting production providers.
- Keep the live interview adaptive. Prefetch plans and secondary responses may be discarded when the conversation changes.
- Evaluate the completed interview after the session using a versioned, structured rubric.
- Treat audio, transcript, resume, and job-description data as sensitive user data.
- Every feature follows the SDD gates: spec, plan, marker contract, implementation, tests, evidence, documentation, and landmine review.

## Roadmap

### Phase 0: Repository and development foundation

- [ ] Establish the application layout and runtime boundaries.
- [x] Choose React, Tailwind v4, shadcn/ui, and FastAPI as initial framework conventions.
- [ ] Add formatting, linting, type checking, unit-test, and mock-turn commands.
- [x] Define separate frontend, API, audio, and worker service boundaries.
- [x] Define Docker-first, CPU-only local development assumptions of approximately 4 GB RAM and 250 GB storage.
- [ ] Define local development configuration without committing secrets.
- [ ] Document the local provider strategy and test fixtures.

### Phase 1: Domain model and capability interfaces

- [x] Define interview, turn, event, transcript, recording, evaluation, and provider measurement models.
- [x] Define `LLMProvider`, `STTProvider`, `TTSProvider`, `DataStore`, and `AuthProvider` interfaces.
- [x] Define `DocumentParser`, `EmbeddingProvider`, `VectorStore`, `AudioTransport`, `EventBus`, `StorageProvider`, `ResearchProvider`, and `ObservabilityProvider` interfaces.
- [x] Define normalized provider errors, cancellation, timeout, health, and capability contracts.
- [x] Add deterministic in-memory providers for tests and a provider-independent mock turn.

### Phase 2: Voice-first interview engine

- [x] Implement the voice-first interview session state machine.
- [x] Implement recruiter and technical interview modes.
- [x] Implement session lifecycle, topic, turn, cancellation, failure, and completion state.
- [x] Implement question planning and guarded follow-up preparation.
- [x] Implement event ordering, correlation IDs, sequence guards, and cancellation.
- [x] Build mock audio-turn coverage using deterministic STT, LLM, and TTS providers.

The Phase 2 vertical slice is implemented in `src/interviewer_domain/session.py` and covered by `tests/test_session_engine.py`. It intentionally stops before browser transport, vendor integrations, and persistence.

### Phase 3: Job-description and resume intelligence

- [x] Parse pasted text-only job descriptions.
- [x] Parse text-based PDF resumes up to 5 MB into structured sections and source-referenced chunks.
- [x] Add deterministic embeddings and vector retrieval behind interfaces.
- [x] Implement topic-aware context retrieval for live turns.
- [x] Add prompt-injection defenses for resume and job-description content.
- [ ] Add optional external company and culture research with source attribution.
- [ ] Add persistent sensitive-data handling, 14-day retention, and deletion enforcement.

The completed local Phase 3 slice is specified in `docs/specs/003-job-description-resume-rag/`. OCR, external research, and persistence remain later integration work.

### Phase 4: Provider implementations and benchmark harness

- [x] Implement a local Faster-Whisper-compatible `STTProvider` adapter with optional injected backend.
- [ ] Implement a hosted Groq Whisper `STTProvider`.
- [x] Implement a provider-neutral local Kokoro/Piper-compatible `TTSProvider` adapter.
- [x] Implement an optional OpenRouter-compatible `LLMProvider` adapter.
- [x] Add normalized provider health, capability discovery, configuration flags, and fallback routing.
- [x] Build a deterministic benchmark for first-byte latency, end-to-end turn latency, fixture quality, estimated cost, failures, and CPU resource use.

The Phase 4 slice is specified in `docs/specs/004-provider-benchmark-harness/`. Optional adapters do not import or download third-party packages at module load, so CPU-only tests remain offline and secret-free. Concrete model transports can be injected by deployment configuration. The deterministic benchmark uses in-memory providers and records fixture quality separately from production speech quality.

### Phase 5: Browser and backend communication

- [x] Define REST resources and versioned request and response schemas.
- [x] Implement WebSocket session events and reconnect behavior.
- [x] Implement WebRTC signaling and browser media transport.
- [x] Keep media on WebRTC and control/state events on WebSocket.
- [ ] Add an optional backend Pub/Sub or event-bus workflow for asynchronous jobs and fan-out.
- [x] Add deterministic transport tests and marker evidence; no visual browser frame is needed for this seam-only slice.

The Phase 5 local transport slice is specified in `docs/specs/005-browser-transport-session-events/`. It provides versioned REST paths, validated schemas, replayable WebSocket-like session events, WebRTC signaling envelopes, and separate media/control protocols without external services.

### Phase 6: Live voice loop

- [ ] Connect streaming or incremental STT to the interview state machine.
- [ ] Stream live LLM responses and support cancellation.
- [ ] Add the secondary response layer for acknowledgements, fillers, and permitted company or culture context.
- [ ] Implement guarded prefetching of topic plans and secondary responses.
- [ ] Stream TTS audio, schedule chunks, and handle interruptions.
- [ ] Record the mixed or separately persisted audio and timestamped transcript.
- [ ] Measure and expose turn latency and provider fallback events.

### Phase 7: Identity, persistence, and user experience

- [ ] Add Firebase Authentication behind `AuthProvider`.
- [ ] Add Firestore behind `DataStore`.
- [ ] Add local filesystem or Docker-volume storage through `StorageProvider`.
- [ ] Add remote or S3-compatible storage implementations for deployment environments.
- [ ] Implement interview setup, active interview, history, replay, transcript, and results views with a minimal mobile-friendly React UI.
- [ ] Enforce access control, 14-day retention, complete dataset deletion, upload validation, and rate limits.

### Phase 8: Post-interview evaluation

- [ ] Finalize recruiter and technical rubric dimensions and weights.
- [ ] Implement versioned structured evaluation output.
- [ ] Add transcript evidence references and evaluator confidence.
- [ ] Generate summary, strengths, weaknesses, and improvement recommendations.
- [ ] Persist and render the score out of 100.
- [ ] Add evaluator regression fixtures and quality checks.

### Phase 9: Production hardening

- [ ] Add end-to-end mock interview coverage for the complete pipeline.
- [ ] Add provider failure, reconnect, cancellation, and partial-audio tests.
- [ ] Add load, latency, cost, and resource benchmarks.
- [ ] Complete security and privacy review.
- [ ] Add observability dashboards and operational runbooks.
- [ ] Select production providers from benchmark evidence.
- [ ] Document deployment options for self-hosted and hosted components.

## SDD feature order

The first feature specifications should be created in this order:

1. `001-domain-capability-foundation`
2. `002-voice-first-interview-engine`
3. `003-job-description-resume-rag`
4. `004-provider-benchmark-harness`
5. `005-browser-transport-session-events`
6. `006-live-voice-loop`
7. `007-persistence-and-user-identity`
8. `008-post-interview-evaluation`
9. `009-production-hardening`

## Resolved decisions

- Frontend: React with Tailwind v4 and shadcn/ui; minimal, clean, and mobile friendly.
- Backend: FastAPI.
- Product interaction: voice loop is built directly; there is no separate text or chat interview mode.
- Services: frontend, API, audio, and worker services are separate deployment boundaries.
- Development: Docker-first and CPU-only, targeting approximately 4 GB RAM and 250 GB storage.
- Storage: local storage first through `StorageProvider`, with cloud or S3-compatible implementations later.
- Deployment: local Docker plus remote deployment adapters for platforms such as Vercel and Railway.
- Resume input: PDF-only upload, maximum 5 MB.
- Job description input: text-only message box.
- Retention: 14 days by default, with complete per-interview deletion available to the user.
- Company and culture context: derive it from job-description or resume content and optional model-supported or `ResearchProvider` web research; do not request a separate company-information form.

## Remaining decisions

- Browser audio codec, recording format, and the best-fit codec per provider.
- Initial local development database and queue or Pub/Sub substitute.
- Candidate hosted LLMs and local LLM feasibility under CPU-only constraints.
- Initial evaluation rubric weights for each interview mode.
- Deployment target for the first end-to-end vertical slice.

## Definition of done for each feature

- Feature spec exists under `docs/specs/`.
- Feature plan lists constraints, work order, and test plan.
- Marker contract exists before implementation.
- Capability interfaces precede concrete providers.
- Unit tests cover pure logic and each concrete provider.
- Mock end-to-end coverage exercises the real code path.
- Visual work has frame evidence.
- Linting and type checking pass.
- Documentation is updated.
- Surprises and durable constraints are recorded in `AGENTS.md`.
