# AI Mock Interview Platform Roadmap

## Purpose

This document tracks the initial implementation roadmap for the voice-native AI mock interview platform. `SPEC.md` defines the product and architecture requirements. Each implementation slice must receive a focused feature specification and plan under `docs/specs/` before code is written.

## Current status

Phases 0 through 15 provide the provider-independent domain foundation, deterministic offline pipeline, persistence seams, evaluation, API/frontend shell, browser transport seams, and concrete provider adapters. Phase 16 has produced programmatic live-beta evidence: the agent-to-agent rehearsal exercises WhisperX, OpenRouter, Kokoro, Firebase Auth/Admin, Firestore, Firebase Storage, and the post-interview evaluator with recorded transcripts. Browser authentication owner isolation, browser media, and production operations remain open gates.

A passing offline test suite proves deterministic code-path behavior only. It does not prove that Firebase, storage, STT, TTS, LLM, WebRTC, browser permissions, deployment configuration, or production observability work together.

## Next execution priorities

These are the highest-priority planned moves for the next implementation session. They must be completed before wrapping Phase 16 and moving to the remaining browser/operations launch gates.

- [x] **P0.1: Vision LLM document parsing adapter:** add a `VisionDocumentParser` adapter behind the existing `DocumentParser` interface for resume PDF extraction and structured data extraction. The adapter sends the document to a vision-capable LLM through an injected OpenRouter-compatible transport using the verified file-payload contract, uses a dedicated untrusted-data prompt, validates bounded output, normalizes provider error envelopes, and tolerates one transient malformed response before failing closed. A `RoutedDocumentParser` routes resume PDFs to the vision adapter and job-description text to the local parser; the live rehearsal now uses this routed composition.
- [x] **P0.2: Dedicated document model configuration:** add a separate document-parsing model setting defaulting to `gemma4`, configurable through `.env`/runtime configuration, with redacted diagnostics/readiness metadata and independent OpenRouter request model selection. Secrets remain environment-injected.
- [x] **P0.3: Adaptive interview ending policy:** extend `QuestionPlanner` and the live session state so every completed candidate turn produces an end decision. The LLM must evaluate the candidate response on each turn and return structured `should_end` plus bounded rationale/decision metadata. `should_end=true` has highest priority and ends the interview immediately after the current turn is safely persisted. Otherwise enforce the hard limits of a maximum 30-minute wall-clock interview and a maximum of 10 interviewer turns. Explicit candidate stop, cancellation, provider failure, and timeout remain terminal conditions. Persist the end reason and expose it through lifecycle events/results. Evidence: shared injectable-clock policy, live session integration, 17 focused tests, and full suite pass.
- [x] **P0.4: Rehearsal parity for ending behavior:** update the Phase 16 agent-to-agent rehearsal to use exactly the same adaptive ending policy and limits as the browser session, including injectable clock/time seams for deterministic 30-minute tests, structured `should_end` fixtures, immediate unsuitable-candidate termination, ten-turn protection, and transcript/evidence output showing the end reason and triggering evaluation. Evidence: shared policy in both journeys, redacted transcript metadata, provider-failure fallback, and deterministic Phase 16 checks pass. Configured live provider execution remains environment-blocked after WhisperX/Kokoro startup.

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

- [x] Build a repeatable user-journey test: signup/login, provide job description, upload a valid local PDF resume, select mode, start, conduct turns, interrupt/reconnect, complete, and view results.
- [x] Simulate the candidate voice using a test candidate LLM plus TTS, feed audio through the same browser/media path, and transcribe it through the configured STT path.
- [x] Run the interviewer and candidate simulations as separate provider instances; never replace the production pipeline with expected strings.
- [x] Verify provider routing, RAG context, session state, WebSocket events, WebRTC media, timestamped transcript, persisted recording, evaluation, score, and deletion.
- [x] Add negative journeys for invalid login, unauthorized access, invalid PDF, provider outage, microphone denial, reconnect, cancellation, timeout, and incomplete interviews.
- [x] Produce human-readable evidence artifacts and clear pass/fail diagnostics for each journey.

Phase 14 implementation is complete: `scripts/test_phase14.sh` runs real behavior-level positive and negative journeys, prints the marker contract, and writes timestamped JSON, Markdown, and HTML evidence. The default profile is deterministic and offline; configured integrations are opt-in and report explicit redacted skips when unavailable.

### Phase 15: Opt-in provider integration suite

- [x] Add separately selectable integration profiles and redacted JSON, Markdown, and HTML evidence for Firebase Auth, Firestore, object storage, STT, TTS, LLM, and WebRTC infrastructure.
- [x] Add concrete lazy OpenRouter HTTP, Faster-Whisper local-model, Piper/Kokoro command, Firebase Admin, Firestore, and S3-compatible transports behind existing capability seams.
- [x] Run integrations only when required environment variables and explicit secrets are present; default offline tests remain unchanged.
- [x] Validate configuration gating, model-path validation, credential-safe diagnostics, cancellation and timeout normalization, and deletion boundaries in offline contract tests.
- [x] Redact credentials and personal data from logs and test artifacts; record provider/model/version/region/device/timing/cost/quality/limitations when configured.
- [ ] Exercise real providers and configured browser/TURN infrastructure. This remains opt-in and is skipped when safe credentials, model paths, or infrastructure are absent.

Phase 15 implementation provided the provider execution paths. Phase 16 now has authoritative live-provider evidence for the programmatic beta rehearsal; browser automation, browser media, and operational release evidence remain Phase 17/future gates.

### Phase 16: Live Beta Enablement

Specification, plan, and marker contract: `docs/specs/016-live-beta-enablement/`.

- [ ] Restructure `src/interviewer_domain` into the long-term package layout; compatibility modules remain for the current beta.
- [x] Compose the explicit beta set: Firebase Auth/Admin, Firestore, Firebase Storage selected by `STORAGE_BACKEND=gcs`, OpenRouter, WhisperX small, Kokoro, timestamped agent audio buffers, and an OpenRouter evaluator.
- [x] Implement production startup validation that rejects accidental in-memory providers and exposes active provider health without secrets.
- [ ] Future browser gate: Firebase browser authentication owner isolation, token refresh, protected routes, and server verification. This is explicitly deferred from the programmatic Phase 16 gate.
- [x] Exercise Firestore session, transcript, recording, evaluation, retention, and exact deletion lifecycle through the rehearsal repositories.
- [x] Implement Firebase Storage upload, download, replay, retention, and deletion lifecycle; retain local storage only for development and deterministic checks. Keep FTP and S3 out of scope.
- [x] Exercise real resume PDF parsing, job-description parsing, source-linked context, and live prompt context using the committed fixtures.
- [x] Implement and exercise programmatic timestamped audio-buffer ingress and interviewer egress; browser microphone, WebRTC, and TURN remain deferred.
- [x] Exercise CPU WhisperX small transcription with partial/final timestamped events.
- [x] Exercise OpenRouter interviewer responses and evaluator operation through the configured adapter.
- [x] Exercise Kokoro English synthesis, sequencing, and stored replay audio.
- [x] Exercise final recording, transcript persistence, evaluation, score validation, results, replay, and deletion.
- [x] Run the real programmatic recruiter and technical agent-to-agent journeys against the configured stack, save redacted evidence, and save a readable transcript under `tests/` by default.
- [x] Add flushed opt-in progress markers to identify heavyweight provider initialization or rehearsal stalls.

A deterministic test pass cannot mark Phase 16 complete. The authoritative programmatic gate must produce exercised results for the selected live providers and both journeys; missing configuration is skipped and configured failure is failed. Phase 16 is complete for programmatic beta evidence, while browser media, browser-token owner isolation, and Phase 17 operational release controls remain open.

### Phase 17: Coverage and operational release gate

Specification, plan, and marker contract: `docs/specs/018-phase17-operational-release-gate/`.

- [x] Add a repeatable release-candidate gate with redacted JSON and Markdown evidence.
- [x] Validate the Docker Compose definition, production fail-closed configuration, backend quality/tests/mock turn, and frontend quality/tests/build.
- [x] Record browser identity/media, deployment security, durable operations, observability, rollback, and incident-runbook blockers explicitly.
- [ ] Enforce separate backend domain, API, frontend, provider, and browser E2E coverage thresholds.
- [ ] Run a clean Docker release candidate with frontend, API, CPU workers, durable services, and media infrastructure.
- [ ] Verify HTTPS, CORS, secure WebSocket origins, retention scheduling, deletion, monitoring, rollback, and incident procedures.
- [ ] Run a scripted beta rehearsal with provider/model/version, latency, cost, quality, and limitation evidence.
- [ ] Declare beta readiness only after Phase 16 real execution and all operational gates pass.

Phase 17 currently provides deterministic release evidence only. The gate exits nonzero while the documented live-launch blockers remain open.

### Browser-based live launch gates

These are explicit follow-on targets after the programmatic Phase 16 gate. They define a soft-browser release path without changing the Phase 16 provider evidence boundary.

- [ ] **B1: Firebase browser identity gate:** exercise email/password signup, Google sign-in where enabled, session restoration, logout, ID-token refresh, expired-token rejection, protected routes, API token forwarding, server verification, and cross-user owner isolation with two test accounts.
- [ ] **B2: Browser setup and consent gate:** exercise consent notice, job-description entry, 10 MB validation, PDF selection/upload progress, parser errors for scanned/encrypted PDFs, mode selection, and setup recovery in a real browser.
- [ ] **B3: Browser control-channel gate:** exercise authenticated WebSocket connect, heartbeat, ordered events, reconnect replay, sequence cursors, cancellation, interruption, provider error states, and secure-origin/CORS behavior.
- [ ] **B4: Browser audio gate:** exercise microphone permission, capture, mute, stop, teardown, agent playback, ordered transcript/audio state, and a soft-browser audio turn. WebRTC/TURN must be validated only if selected by deployment configuration; browser tests must not put media bytes in WebSocket events.
- [ ] **B5: Browser completed-interview gate:** complete recruiter and technical soft-browser interviews, verify adaptive continuation/end conditions, final transcript, replay recording, evaluation results, and user-visible failure recovery.
- [ ] **B6: Browser persistence and deletion gate:** verify history, transcript, results, replay, retention display, per-interview deletion, account deletion, and cross-user access denial against Firebase/Firestore/Storage.
- [ ] **B7: Production security gate:** remove development `dev-token` paths from production, enforce HTTPS, secure WebSocket origins, CORS allowlists, Firebase rules, secret injection, redacted logs, rate limits, upload limits, and fail-closed startup/readiness.
- [ ] **B8: Release-candidate operations gate:** run the frontend/API/worker Docker release candidate, verify health/readiness probes, model warm-up, resource limits, monitoring, alerts, backup/restore assumptions, rollback, retention scheduling, deletion retries, and incident runbook.
- [ ] **B9: Soft-browser acceptance gate:** run a scripted real-browser smoke test with the demo fixtures and test account, capture screenshots/logs without sensitive data, record provider/model/version, latency, cost, quality, and limitations, and obtain explicit beta-launch approval.

The browser launch is not ready until B1 through B9 pass. The programmatic Phase 16 gate remains a prerequisite, not a substitute for these browser and operational gates.

## SDD feature order

Feature specifications have been completed through `011-runtime-configuration-and-provider-readiness`. New specifications must be created in this order:

1. `012-production-frontend-and-firebase-identity`
2. `013-browser-webrtc-websocket-voice-loop`
3. `014-full-user-e2e-acceptance`
4. `015-provider-integration-suite`
5. `016-live-beta-enablement`

Each phase may contain smaller implementation slices, but no phase may be marked complete using only static fixtures or an offline mock when its acceptance criteria require configured infrastructure.

## Resolved decisions

- Frontend: React with Tailwind v4 and shadcn/ui; minimal, clean, and mobile friendly.
- Backend: FastAPI.
- Product interaction: voice loop is built directly; there is no separate text or chat interview mode.
- Services: frontend, API, audio, and worker services are separate deployment boundaries.
- Development: Docker-first and CPU-only, targeting approximately 4 GB RAM and 250 GB storage.
- Storage: Firebase Storage and local filesystem adapters are the initial beta choices.
- Deployment: CPU-only beta services with HTTPS, WebRTC/TURN, frontend, API, workers, and durable services.
- Resume input: PDF-only upload, maximum 10 MB for the Phase 16 beta.
- Job description input: text-only message box.
- Retention: 14 days by default, with complete per-interview deletion available to the user.
- Company and culture context: derive it from job-description or resume content and optional model-supported or `ResearchProvider` web research; do not request a separate company-information form.
- Beta providers: Firebase Auth, Firestore, Firebase Storage/local storage, OpenRouter, Faster-Whisper, Kokoro, WebRTC, and an OpenRouter LLM evaluator.
- Workers: CPU-only for the first beta.
- Retention: 14 days by default with complete user deletion.

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
