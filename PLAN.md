# AI Mock Interview Platform Roadmap

## Purpose

This document tracks the initial implementation roadmap for the voice-native AI mock interview platform. `SPEC.md` defines the product and architecture requirements. Each implementation slice must receive a focused feature specification and plan under `docs/specs/` before code is written.

## Current status

Phases 0 through 9 provide the provider-independent domain foundation, deterministic offline pipeline, persistence seams, evaluation, and an initial API/frontend shell. The repository is not yet ready for a live demo. The mandatory production-readiness program is phases 10 through 16: real CI, configuration, selected providers, complete frontend identity and setup, browser WebSocket/WebRTC integration, full user E2E acceptance, opt-in provider integrations, enforced coverage, and release rehearsal.

A passing offline test suite proves deterministic code-path behavior only. It does not prove that Firebase, storage, STT, TTS, LLM, WebRTC, browser permissions, deployment configuration, or production observability work together.

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

- [x] Connect streaming or incremental STT to the interview state machine.
- [x] Stream live LLM responses and support cancellation.
- [x] Add the bounded secondary response layer for acknowledgements and fillers.
- [x] Implement guarded prefetching of topic plans and secondary responses.
- [x] Stream TTS audio, schedule chunks, and handle interruptions.
- [x] Record separately persisted audio and timestamped transcript artifacts.
- [x] Measure and expose turn latency and provider fallback events.

The Phase 6 local live voice slice is specified in `docs/specs/006-live-voice-loop/`. `LiveVoiceOrchestrator` composes streaming provider protocols, digest-guards speculative responses, cancels stale generation and playback, and emits deterministic latency and fallback events. The in-memory providers and tests remain CPU-only, offline, credential-free, and vendor-neutral.

### Phase 7: Identity, persistence, and user experience

- [x] Add Firebase Authentication behind `AuthProvider`.
- [x] Add Firestore behind `DataStore`.
- [x] Add local filesystem or Docker-volume storage through `StorageProvider`.
- [x] Add remote or S3-compatible storage implementations for deployment environments.
- [x] Define provider-neutral interview setup, active interview, history, replay, transcript, and results resource contracts. The real browser UI and Firebase flows are intentionally deferred to the post-Phase-9 production-readiness program.
- [x] Enforce access control, 14-day retention, complete dataset deletion, upload validation, and rate limits.

The Phase 7 slice is specified in `docs/specs/007-persistence-user-identity/`. It provides injected Firebase Auth, Firestore, local filesystem, and S3-compatible seams, ownership and retention enforcement, complete deletion, bounded PDF uploads, fixed-window rate limiting, and deterministic UI-independent resource contracts.

### Phase 8: Post-interview evaluation

- [x] Finalize recruiter and technical rubric dimensions and normalized weights.
- [x] Implement versioned structured evaluation output.
- [x] Add transcript evidence references, evidence status, and evaluator confidence.
- [x] Generate summary, strengths, weaknesses, and improvement recommendations.
- [x] Persist and expose the score out of 100 through the results resource.
- [x] Add evaluator regression fixtures, quality checks, and a real offline mock path.

The Phase 8 local evaluation slice is specified in `docs/specs/008-post-interview-evaluation/`. `DeterministicEvaluator` scores only final candidate transcript segments with mode-specific versioned rubrics. `PostInterviewEvaluationService` authorizes completed owned interviews before saving results through the Phase 7 datastore seam. No LLM, network, credentials, or frontend is required.

### Phase 9: Production hardening

- [x] Add end-to-end mock interview coverage for the complete pipeline.
- [x] Add provider failure, reconnect, cancellation, and partial-audio tests.
- [x] Add load, latency, cost, and resource benchmark seams.
- [x] Complete deterministic security and privacy boundary checks.
- [x] Add a FastAPI entrypoint, health/version routes, local runtime, and operational documentation.
- [x] Add a maintainable React frontend for setup, active interview, history/replay/transcript, and results.
- [ ] Add hosted observability dashboards and select production providers from deployment-specific evidence.
- [x] Document Docker/local deployment and hosted component boundaries.

Phase 9 is specified in `docs/specs/009-production-hardening/`. Its deterministic production boundary is intentionally credential-free: FastAPI composes in-memory capabilities locally, while deployment adapters remain replaceable behind existing interfaces. It provides a runnable Vite/API shell and real offline evidence, but not Firebase signup, configured providers, browser WebSocket/WebRTC media, or live-demo readiness. The offline gate executes public methods and ASGI routes instead of inspecting source strings.

## Post-Phase-9 production-readiness program

Phase 9 delivered a runnable local API and frontend shell, but it did not complete a production browser interview. The following phases are mandatory before the first live demo. They are intentionally separated so a green offline test suite cannot be mistaken for provider, browser, or production readiness.

### Phase 10: Test integrity and real CI gates

- [x] Define one reproducible backend test command and one reproducible frontend test command.
- [x] Add pinned development dependencies for test, lint, type checking, and coverage. Browser automation remains a Phase 14 concern.
- [x] Audit the existing test surface and preserve behavior-level tests without source inspection.
- [x] Require tests to assert observable behavior, state, persistence, transport messages, and failure modes.
- [x] Replace the placeholder GitHub Actions workflow with real backend, frontend, lint, type, coverage, build, and artifact steps.
- [x] Add pull-request status gates and fail CI when required tools are missing or skipped.
- [x] Add test reports and coverage artifacts without committing generated output.

Phase 10 is specified in `docs/specs/010-test-integrity-and-ci/`. Its local and CI gates are credential-free and offline. The current baseline is 85% aggregate backend coverage and 100% coverage for the tested frontend API seam; stricter per-surface thresholds and browser automation remain later release work.

### Phase 11: Runtime configuration and provider readiness

- [x] Add `.env.example` with documented, non-secret configuration for Firebase, Firestore, storage, STT, TTS, LLM, WebRTC, CORS, retention, rate limits, and observability.
- [x] Add typed configuration loading, environment validation, safe defaults, and startup diagnostics that never print secrets.
- [x] Add a local development profile using deterministic providers and a production profile requiring explicitly configured providers.
- [x] Add provider capability and health checks with fail-fast behavior for required production capabilities.
- [x] Implement and benchmark at least one usable production-shaped STT, TTS, and LLM path, including fallback behavior through injected seams.
- [x] Document data-sharing, retention, cost, latency, and failure characteristics for every selected provider.

Phase 11 is specified in `docs/specs/011-runtime-configuration-and-provider-readiness/`. The default local profile is offline and deterministic. Production-shaped adapters use injected backend and transport seams, while `/api/v1/readiness` exposes only redacted capability status. Passing local tests does not claim real provider, Firebase, browser, or WebRTC readiness. Run `scripts/test_phase11.sh` for the Phase 11 marker evidence path.

### Phase 12: Production frontend and Firebase identity

- [x] Replace the Phase 9 shell with a maintainable React and Tailwind design system with an abstract component and token layer.
- [x] Implement signup, login, logout, session restoration, protected routes, error states, loading states, and Firebase Authentication integration.
- [x] Implement job-description entry, PDF resume selection/upload/progress/error handling, interview-mode selection, and setup validation.
- [x] Implement active interview controls, microphone permissions, connection state, mute/stop/reconnect controls, live transcript, and interruption feedback.
- [x] Implement history, replay, transcript, evaluation, deletion, retention, and account states using real API resources.
- [x] Add accessible responsive design and visual evidence for the primary user journeys.
- [x] Keep visual code separate from domain/API clients so agents can redesign the UI without changing interview behavior.

### Phase 13: Usable browser WebSocket and WebRTC voice loop

- [x] Implement authenticated WebSocket session connection, event envelopes, sequence cursors, reconnect replay, heartbeat, and close/error handling in the API.
- [x] Implement authenticated WebRTC signaling, ICE exchange, media-track negotiation, microphone capture, agent audio playback, and teardown.
- [ ] Connect browser media to the live voice orchestrator and route control/transcript/status events through WebSocket.
- [x] Implement browser interruption, cancellation, stale-response rejection, partial transcript updates, final transcript updates, and provider fallback UI.
- [ ] Persist final audio, transcript, event, and evaluation artifacts through the configured providers.
- [x] Add a local deterministic browser mode and a real configured-provider mode without mixing their credentials or behavior.

Phase 13 implementation is complete in the feature branch: authenticated WebSocket session ownership and replay, WebRTC signaling/media seams, browser reconnect and live-room state, deterministic negative tests, and local marker/evidence checks. The local path remains credential-free and provider-neutral; real microphone, TURN, Firebase, and hosted-provider readiness require configured integration evidence.

### Phase 14: Full programmatic user E2E acceptance

- [ ] Build a repeatable user-journey test: signup/login, provide job description, upload a valid local PDF resume, select mode, start, conduct turns, interrupt/reconnect, complete, and view results.
- [ ] Simulate the candidate voice using a test candidate LLM plus TTS, feed audio through the same browser/media path, and transcribe it through the configured STT path.
- [ ] Run the interviewer and candidate simulations as separate provider instances; never replace the production pipeline with expected strings.
- [ ] Verify provider routing, RAG context, session state, WebSocket events, WebRTC media, timestamped transcript, persisted recording, evaluation, score, and deletion.
- [ ] Add negative journeys for invalid login, unauthorized access, invalid PDF, provider outage, microphone denial, reconnect, cancellation, timeout, and incomplete interviews.
- [ ] Produce human-readable evidence artifacts and clear pass/fail diagnostics for each journey.

### Phase 15: Opt-in provider integration suite

- [ ] Add separately tagged integration tests for Firebase Auth, Firestore, object storage, STT, TTS, LLM, and WebRTC infrastructure.
- [ ] Run integrations only when the required environment variables and explicit CI secrets are present; never make them part of the default offline suite.
- [ ] Validate real authentication claims, provider payload translation, streaming, cancellation, rate limits, cost, latency, retries, and data deletion.
- [ ] Redact credentials and personal data from logs and test artifacts.
- [ ] Record provider versions, model names, region, timing, cost, quality, and known limitations.

### Phase 16: Coverage and live-demo release gate

- [ ] Enforce separate backend domain, API, frontend, and browser E2E coverage thresholds in CI.
- [ ] Require changed production code to have behavior-level tests and require every concrete provider adapter to have an integration or deterministic contract test.
- [ ] Add coverage trend artifacts and prevent threshold regressions.
- [ ] Run a clean Docker release candidate from documented instructions.
- [ ] Verify production configuration, Firebase auth, storage, provider health, HTTPS, CORS, retention, deletion, monitoring, rollback, and incident procedures.
- [ ] Run a scripted live-demo rehearsal and record the exact selected provider configuration and known limitations.
- [ ] Declare demo readiness only after all mandatory gates pass; offline deterministic tests alone are insufficient.

## SDD feature order

Feature specifications have been completed through `011-runtime-configuration-and-provider-readiness`. New specifications must be created in this order:

1. `012-production-frontend-and-firebase-identity`
2. `013-browser-webrtc-websocket-voice-loop`
3. `014-full-user-e2e-acceptance`
4. `015-provider-integration-suite`
5. `016-coverage-and-live-demo-readiness`

Each phase may contain smaller implementation slices, but no phase may be marked complete using only static fixtures or an offline mock when its acceptance criteria require configured infrastructure.

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
