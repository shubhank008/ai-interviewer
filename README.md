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

Phase 7 adds provider-independent persistence in `src/interviewer_domain/persistence.py`. `FirebaseAuthAdapter`, `FirestoreDataStore`, `LocalFilesystemStorage`, and `S3CompatibleStorage` use injected backends, while deterministic local services enforce owner isolation, 14-day retention metadata, complete interview deletion, PDF upload bounds, and fixed-window rate limits. Because this repository has no frontend source tree, setup, active interview, history, replay, transcript, and results are represented as stable UI-independent resource contracts rather than an invented React application. See [`docs/specs/007-persistence-user-identity/`](docs/specs/007-persistence-user-identity/) for the specification, plan, and marker contract.

Phase 8 adds `DeterministicEvaluator` and `PostInterviewEvaluationService` in `src/interviewer_domain/evaluation.py`. The evaluator runs only after completion, scores recruiter and technical rubrics from final candidate transcript segments, preserves role, seniority, job-description, resume, and mode context, and emits versioned evidence-linked feedback with confidence and a bounded score. Results are saved and exposed through the existing owned persistence resource. The evaluator protocol is replaceable by future providers, while current tests remain offline, credential-free, and deterministic. See [`docs/specs/008-post-interview-evaluation/`](docs/specs/008-post-interview-evaluation/) for the specification, plan, and marker contract.

Candidate provider implementations include local Faster-Whisper, hosted Groq Whisper, local Kokoro or Piper, and OpenRouter or self-hosted LLMs. These are comparison candidates, not final production decisions. Local development is Docker-first and CPU-only, with an approximate 4 GB RAM and 250 GB storage target.

Resume input is PDF-only with a 5 MB limit, while job descriptions are supplied as text. The Phase 3 local ingestion slice extracts text-based PDFs, preserves source-linked chunks, provides deterministic topic retrieval, and marks instruction-like document text as untrusted data. OCR and external research remain integration work; Phase 7 now provides persistent retention metadata and enforcement boundaries. Uploaded and generated content is treated as untrusted input and must pass prompt-injection and output-safety guardrails. Interview data is retained for 14 days by default and can be completely deleted per interview.

## Project status

The repository has completed the domain and capability foundation, the Phase 2 voice-first session engine, the Phase 3 local document ingestion and retrieval slice, the Phase 4 provider-neutral adapter and benchmark harness, the Phase 5 browser transport and session events slice, the Phase 6 live voice orchestration loop, the Phase 7 provider-independent persistence and user-identity layer, the Phase 8 deterministic post-interview evaluation, the Phase 9 production runtime and API/frontend shell, the Phase 10 test integrity and CI gates, and the Phase 11 runtime configuration and provider readiness. The provider-independent Python package is under `src/interviewer_domain/`, with deterministic providers, a mock voice-shaped turn, recruiter or technical session state-machine coverage, local PDF/text parsing with topic retrieval, provider-neutral STT/TTS/LLM adapters with fallback routing and benchmarking, versioned REST/WebSocket/WebRTC transport seams, cancellable streaming live-voice orchestration with digest-guarded prefetch, ordered TTS scheduling, and timestamped artifacts, owner-checked persistence with retention and deletion, and a deterministic evaluator with mode-specific rubrics and evidence-linked feedback in `tests/`. Run `python -m unittest discover -s tests -v` for the local test gate. Read [`SPEC.md`](SPEC.md) for the product specification and [`PLAN.md`](PLAN.md) for the SDD implementation roadmap. The first implementation will build the voice loop directly rather than creating a separate text-only interview mode.

Each feature will be developed through the repository's SDD workflow:

1. Feature specification
2. Implementation plan
3. Marker contract
4. Capability-first implementation
5. Unit and mock end-to-end tests
6. Evidence and documentation
7. Landmine review and roadmap update

## Phase 9 production runtime

The repository includes a runnable FastAPI composition root at `src/interviewer_api/app.py` and a Vite React frontend under `frontend/`. The API exposes `GET /healthz`, versioned health/version routes, authenticated session creation, history, setup, active, replay, transcript, results, and completion resources. The frontend provides setup, active interview, history/replay/transcript, and results views and is API-backed rather than a static placeholder.

### Prerequisites and installation

Use Python 3.12+, Node.js 20+, npm, and optionally Docker Compose. No credentials are needed for the deterministic local path.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
npm install --prefix frontend
export PYTHONPATH=src
```

The local `Bearer dev-token` is a development-only fixture. Never use it in deployment. Inject real owner-checked identity, durable data/storage providers, HTTPS, and secrets through deployment configuration. Provider adapters use injected transports and must not place credentials in source or frontend bundles.

### Development, tests, and checks

```bash
PYTHONPATH=src uvicorn interviewer_api.app:app --reload --port 8000
npm run dev --prefix frontend
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m compileall -q src tests
npm run build --prefix frontend
```

`tests/test_phase9_production.py` calls real ASGI routes and public domain interfaces across ingestion, retrieval, provider routing, live voice, transport, persistence, evaluation, failure, reconnect, cancellation, partial audio, authorization, retention, rate limits, benchmarks, and privacy boundaries. It does not grep source strings or depend on credentials, network, browser automation, or heavyweight models.

## Phase 11 runtime configuration and provider readiness

Copy `.env.example` to the deployment environment and set `APP_PROFILE=local` for the credential-free deterministic path. `RuntimeSettings` validates environment values and preserves the existing 5 MB PDF and 14-day retention decisions. `APP_PROFILE=production` requires explicit Firebase, Firestore, storage, and provider configuration instead of silently selecting in-memory providers. The API's `/api/v1/readiness` endpoint reports redacted profile, capability, and health information.

Production-shaped STT, TTS, and LLM adapters are `FasterWhisperSTT`, `PiperKokoroTTS`, and `OpenRouterLLM`, selected through existing capability interfaces and injected backend or transport seams. `FallbackRouter` tries configured providers in order. The default tests never download models or call networks. See [`docs/provider-readiness.md`](docs/provider-readiness.md) for provider data sharing, retention, cost, latency, and failure characteristics. Run `./scripts/test_phase11.sh` to verify all Phase 11 markers and forbidden-pattern guards. This evidence does not claim real provider, Firebase, browser, or WebRTC readiness.


For the strict Phase 10 gate, install the pinned development tools and run:

```bash
pip install -r requirements-dev.txt
./scripts/lint_and_typecheck.sh
./scripts/test_backend.sh
npm ci --prefix frontend
./scripts/test_frontend.sh
```

The backend gate runs 50 offline unittest cases, the mock interview evidence path, and an enforced 80% aggregate coverage floor. The frontend gate runs ESLint, Node tests with an 80% line/function/statement and 70% branch coverage floor, and a production Vite build. These gates are credential-free and do not claim provider, browser, or production readiness. Generated coverage and frontend build output are ignored by Git. GitHub Actions runs the same scripts and uploads coverage reports.

### Docker, deployment, and architecture

```bash
docker compose up --build
# API health: http://localhost:8000/healthz
```

The Dockerfile runs the API. Build the frontend with `npm run build --prefix frontend`, then serve `frontend/dist` through a static host or HTTPS reverse proxy. Before production traffic, add a durable database and object store, real identity, retention scheduling, structured logs, metrics/traces, rate-limit policy, provider health checks, and deployment-specific benchmark evidence. No cloud provider is selected by this phase.

### Provider configuration and troubleshooting

The domain remains provider-neutral: configure optional STT, TTS, and LLM adapters only through injected capability implementations and environment-backed secrets. If imports fail, set `PYTHONPATH=src`. API resource calls need `Authorization: Bearer dev-token` locally. Empty, expired, and cross-owner resources fail safely. The local parser supports text PDFs only; scanned or encrypted PDFs must fail safely until an OCR adapter is intentionally added. Frontend `/api` calls require a reverse-proxy or Vite dev proxy to the API.
