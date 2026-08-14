# AI Interviewer

AI Interviewer is a browser-based, voice-native mock interview platform. A candidate provides a job description, optionally uploads a PDF resume, selects a mode, and practices a conversational interview with an adaptive interviewer persona.

Supported interview modes:

- **Recruiter screen:** background, motivation, role fit, communication, logistics, availability, location, and work authorization where relevant.
- **Technical or hiring-manager interview:** technical depth, problem solving, system design, domain knowledge, projects, behavioral signals, and role-specific follow-up questions.

The intended post-interview experience includes replayable audio, a timestamped speaker-labeled transcript, a score out of 100, a summary, strengths, missed opportunities, role-specific feedback, and concrete improvements.

> **Current status:** deterministic local domain and acceptance paths are implemented, and Phase 15 added opt-in concrete provider transports. The latest Phase 15 run skipped every real integration because safe credentials, model paths, and a browser integration URL were absent. This repository must not yet claim live production interview readiness.

## Contents

- [Status](#status)
- [How it works](#how-it-works)
- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Local development](#local-development)
- [API and browser boundaries](#api-and-browser-boundaries)
- [Provider integrations](#provider-integrations)
- [Configuration](#configuration)
- [Testing and evidence](#testing-and-evidence)
- [Production deployment](#production-deployment)
- [Security and privacy](#security-and-privacy)
- [Roadmap and readiness](#roadmap-and-readiness)

## Status

| Capability | Local path | Configured path | Evidence |
|---|---|---|---|
| Setup, modes, PDF parsing, retrieval | Implemented | Needs application verification | Phase 14 offline |
| Live voice orchestration | In-memory STT, LLM, TTS | Provider adapters exist | Live run pending |
| STT | Contract fixture only | WhisperX small on CPU | Live execution pending |
| TTS | Contract fixture only | Kokoro Python, English, randomized voice | Live execution pending |
| LLM | Contract fixture only | OpenRouter through `LLM_API_KEY` | Live execution pending |
| Auth and data | Development fixtures only | Firebase Auth, Firestore, local/NFS storage | Live execution pending |
| Browser media | Timestamped chunk contract | Browser microphone chunk transport | Live execution pending |
| Evaluation | Contract evaluator only | OpenRouter post-interview evaluator | Live execution pending |

Requirements are in [`SPEC.md`](SPEC.md), implementation status is in [`PLAN.md`](PLAN.md), and provider operations are in [`docs/provider-readiness.md`](docs/provider-readiness.md).

## How it works

1. The candidate authenticates, enters a text job description, selects a mode, and optionally selects a PDF resume.
2. Text PDF ingestion validates, parses, normalizes, chunks, and retrieves relevant evidence. Documents are untrusted data, never system instructions.
3. A session is created through the versioned API and authorized for the current user.
4. HTTP handles setup and resources, WebSocket handles ordered control and transcript/status events, and the selected browser audio transport handles microphone and agent audio. Media frames never enter WebSocket control messages.
5. `LiveVoiceOrchestrator` coordinates STT, interview state, LLM generation, TTS scheduling, interruption, cancellation, fallback, and timestamped artifacts.
6. Completion persists transcript, recording metadata, events, and evaluation artifacts. Evaluation runs only after completion from final transcript evidence.
7. History, replay, transcript, results, retention, and deletion use owner-checked boundaries.

The local profile exercises these contracts without credentials or external network calls. It does not prove speech quality, model quality, Firebase behavior, or production browser-audio connectivity.

## Architecture

Business logic is provider-neutral. Capability interfaces define normalized payloads, cancellation, timeouts, errors, health, and discovery. Vendor formats, SDK imports, credentials, retries, and provider failures remain in adapters.

```text
React browser UI
    | HTTP REST: setup, sessions, history, transcript, results
    | WebSocket: control, signaling, transcript, status, replay
    | Selected browser audio transport: microphone and agent audio
    v
FastAPI composition root
    | AuthProvider
    | DocumentParser + retrieval
    | Interview state machine + question planning
    | LiveVoiceOrchestrator
    |   STTProvider -> LLMProvider -> TTSProvider
    | PersistenceService -> DataStore + StorageProvider
    | PostInterviewEvaluationService
    v
Local, self-hosted, and hosted provider adapters
```

Provider paths currently include `OpenRouterHTTPTransport`, `FasterWhisperLocalBackend`, `KokoroTTS`, `FirebaseAdminAuthBackend`, `FirestoreGoogleBackend`, and `FirebaseStorageBackend`. In-memory providers remain available for deterministic tests. Optional SDKs are imported lazily, model weights are never downloaded automatically, and configured providers must not silently fall back to memory.

## Repository layout

```text
src/interviewer_domain/       Domain models, contracts, routing, orchestration
  capabilities/               Protocols, normalized DTOs, provider errors
  adapters/                   Firebase, Firestore, storage, OpenRouter, STT, TTS, browser-audio adapters
  providers/in_memory/        Deterministic local implementations
src/interviewer_api/          FastAPI REST, WebSocket, and composition root
frontend/src/                 React UI, API clients, auth, media, transport
scripts/                      Quality gates and phase evidence runners
tests/                        Offline, contract, acceptance, provider tests
docs/specs/                   SDD specifications, plans, marker contracts
SPEC.md                       Product specification
PLAN.md                       Phase roadmap
.env.example                  Safe environment template
Dockerfile                    API image
docker-compose.yml            Local API container definition
```

## Local development

Requirements are exactly Python 3.12, `pip`, Node.js, npm, and optionally Docker. The supported runtime is recorded in [`.python-version`](.python-version), and the API image uses the Python 3.12 slim Bookworm base.

Production Python dependencies in [`requirements.txt`](requirements.txt) are intentionally pinned to exact versions. This prevents an unattended minor or major release from changing the production runtime and protects provider integrations from unreviewed breaking changes. Update them only through a deliberate compatibility test and review. The weekly [major dependency check](.github/workflows/dependency-major-check.yml) reports available major releases by opening or updating a GitHub issue; it never edits requirements or deploys an update.

### Run the deterministic API

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
export PYTHONPATH="$PWD/src"
export APP_PROFILE=local
uvicorn interviewer_api.app:app --host 127.0.0.1 --port 8000 --reload
```

Check it with `curl http://127.0.0.1:8000/healthz`, `curl http://127.0.0.1:8000/api/v1/health`, and `curl http://127.0.0.1:8000/api/v1/readiness`. The local API uses `Authorization: Bearer dev-token`; this is a development fixture and must never be deployed.

### Run the frontend

In another terminal:

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

Open <http://127.0.0.1:5173>. The current frontend uses local identity and a development token. A reverse proxy must route `/api` and WebSocket upgrades to the API. Real microphone/browser-audio use requires HTTPS.

```bash
npm run lint
npm test
npm run test:coverage
npm run build
```

### Run with Docker

The supplied Compose file runs the API only. It does not serve React, provide Firebase, start model workers, or provision durable storage.

```bash
docker compose up --build
curl http://127.0.0.1:8000/healthz
```

Run the frontend separately or serve its built `frontend/dist` through an HTTPS reverse proxy.

## API and browser boundaries

| Method | Path | Purpose |
|---|---|---|
| GET | `/healthz` | Liveness |
| GET | `/api/v1/health` | Versioned health |
| GET | `/api/v1/readiness` | Redacted profile and capability readiness |
| GET | `/api/v1/version` | API version |
| POST | `/api/v1/sessions` | Create an owned session |
| GET | `/api/v1/history` | List owned history |
| GET | `/api/v1/sessions/{id}/{view}` | Retrieve an owned view |
| POST | `/api/v1/sessions/{id}/complete` | Complete a session |
| WS | `/ws/v1/sessions/{id}` | Authenticated control channel |
| WS | `/ws/v1/sessions/{id}/media` | Authenticated microphone frame channel |
| WS | `/ws/v1/sessions/{id}/signaling` | Authenticated signaling channel |

The FastAPI composition root targets the Phase 16 live beta configuration: Firebase email/password and Google Sign-In Auth, Firestore, Firebase Storage with local/NFS checks, WhisperX small on CPU, OpenRouter through `LLM_API_KEY`, and Kokoro. The single Docker container is the initial self-hosted/Railway benchmark target. Offline tests protect contracts only; live composition and agent-to-agent rehearsal are required before beta readiness.

## Provider integrations

Phase 16 is live-first. Live provider runs distinguish `exercised`, `skipped`, and `failed`; missing configuration is a skip, not a readiness pass, and a selected provider failure is a failure. Offline tests may protect contracts but cannot pass beta readiness.

```bash
export PYTHONPATH="$PWD/src"
./scripts/test_phase16.sh
```

The Phase 16 rehearsal runner must execute every selected live operation with real test accounts, fixtures, live providers, and programmatic agent-to-agent audio buffers. It must write only redacted evidence and benchmark metadata.

- **OpenRouter:** set `LLM_API_KEY`, `LLM_MODEL=~deepseek/deepseek-v4-flash-latest`, and `LLM_PROVIDER=openrouter`. Do not use the legacy `OPENROUTER_API_KEY`. Requests use a 60-second timeout and up to three transient retries; permanent errors fail without retry. Record only redacted token, time, model, and cost metrics.
- **WhisperX:** set `STT_PROVIDER=whisperx`, `STT_MODEL=small`, `STT_CPU=true`, and `STT_LANGUAGE=en`. The provider receives a model name; `STT_MODEL_PATH` is obsolete and must not be required. Install and exercise WhisperX in the live environment.
- **Kokoro:** set `TTS_PROVIDER=kokoro`, `TTS_MODEL`, and `TTS_LANGUAGE=en`. The Python adapter resolves its runtime from the model/language configuration. `TTS_MODEL_PATH` and `TTS_COMMAND` are obsolete. Select a supported voice randomly per invocation, normalize browser-compatible audio, and benchmark playback, cancellation, and quality.
- **Firebase and Firestore:** provide `FIREBASE_PROJECT_ID`, protected `FIREBASE_CREDENTIALS_PATH`, Firebase Web Auth configuration, and EU Firestore. Use email/password and Google Sign-In Auth with open signup. Firestore rules remain managed in Firebase; application owner checks remain mandatory.
- **Storage:** the live beta uses `STORAGE_BACKEND=gcs` to select Firebase Storage bucket `gs://the-interviewer-c3a01.firebasestorage.app`. `STORAGE_BACKEND=local` is for development and deterministic checks. FTP and S3 are out of scope. Exercise upload, replay, retention, partial failure, and deletion.
- **Agent audio:** the Phase 16 rehearsal exchanges timestamped in-memory audio buffers between Interviewer and Interviewee Agents. Browser audio and WebRTC/TURN are deferred to the browser transport phase.
- **Fixtures:** use `tests/demo_resume.pdf` and `tests/demo_jobdescription.txt`; enforce 10 MB limits for each job description and resume. Text-only PDF parsing must fail gracefully for scanned or encrypted documents.

## Configuration

```bash
cp .env.example .env
```

| Variable | Purpose |
|---|---|
| `APP_PROFILE` | `production` for the live beta; local is contract/development mode only |
| `STT_PROVIDER`, `STT_MODEL`, `STT_CPU`, `STT_LANGUAGE` | WhisperX selection, model name, CPU mode, and language; beta uses `whisperx` and `small` |
| `TTS_PROVIDER`, `TTS_MODEL`, `TTS_LANGUAGE` | Kokoro selection, provider model setting, and language; beta uses English with random per-call voice selection |
| `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY` | OpenRouter selection, configured model, and unified credential |
| `FIREBASE_PROJECT_ID`, `FIREBASE_CREDENTIALS_PATH`, Firebase Web Auth settings | Beta Firebase Admin/Web Auth and EU Firestore |
| `STORAGE_BACKEND`, `STORAGE_PATH`, `STORAGE_BUCKET` | `gcs` selects locked Firebase Storage for beta; `local` is development/deterministic only |
| `WEBRTC_ICE_SERVERS` | Optional benchmark transport configuration; timestamped browser chunks are the initial beta transport |
| `RETENTION_DAYS` | Resume and default artifact retention, 14 days |
| `AUDIO_RETENTION_DAYS` | Combined interview recording retention, 7 days |
| `AUDIT_RETENTION_DAYS` | Audit/access record retention, 30 days |
| `RATE_LIMIT`, `RATE_WINDOW_SECONDS` | Rate limiting |
| `CORS_ORIGINS` | Allowed browser origins |

Never put credentials in `.env.example`, source, Git history, screenshots, logs, evidence, or frontend bundles.

## Testing and evidence

Offline checks protect contracts only. They are not Phase 16 release evidence. The release gate is the configured live rehearsal runner, which writes redacted evidence under `.agent_tmp/` and distinguishes exercised, skipped, and failed providers.

```bash
export PYTHONPATH="$PWD/src"
./scripts/test_phase16.sh
```

The live runner must use safe beta accounts and fixtures, exercise both recruiter and technical journeys, switch storage adapters, execute negative cases, and emit the required markers without credentials, personal data, raw provider payloads, transcript text, resume text, or audio bytes.

## Production deployment

Production is not yet a supported one-command deployment. Before accepting real candidate data:

1. Implement Firebase email/password and Google Sign-In signup/login, open signup, session restoration, server-side ID-token verification, and remove `dev-token` from the production path.
2. Compose Firebase Auth, EU Firestore, Firebase Storage plus local/NFS, WhisperX small, OpenRouter, and Kokoro in one Docker container for the beta benchmark.
3. Implement 10 MB input limits, protected-PDF UI errors, scanned-PDF extraction, consent, 14-day resume retention, 7-day combined-audio retention, 30-day audit/access retention, and complete account deletion.
4. Benchmark the selected browser microphone transport and STT/TTS/LLM behavior for latency, CPU, memory, interruption, cancellation, retries, cost, and quality. Do not impose a latency or concurrency target until measured.
5. Add redacted logs, metrics, traces, alerts, readiness probes, abuse controls, patching, rollback, and incident procedures.
6. Build the frontend with `npm run build`, serve it over HTTPS, and route API and WebSocket traffic to the single container.
7. Run the full live Phase 16 rehearsal with both agent-to-agent journeys, storage switching, negative cases, retention, deletion, and all required markers.

After the single-container benchmark, split frontend, API, model/audio worker, and asynchronous evaluation services into separate Docker containers if resource measurements require it. Railway profiles and self-hosted Docker are the initial deployment targets.

## Security and privacy

Resumes, job descriptions, voice recordings, transcripts, and evaluations may contain personal data.

- Treat documents and provider responses as untrusted input and never allow them to override system instructions.
- Send only the minimum permitted context to external providers.
- Review provider training, retention, region, and deletion policies before enabling them.
- Use separate test projects, buckets, credentials, and model configurations.
- Redact credentials, prompts, transcript text, audio, and personal data from logs and evidence.
- Enforce owner checks on sessions, transcripts, recordings, evaluations, and deletion.
- Use HTTPS and secure WebSocket origins in production.
- Retain resumes for 14 days, combined interview recordings for 7 days, and audit/access records for 30 days.
- Show placeholder consent before collection. Disclose that resume, transcript, audio-derived content, and evaluation context are sent to OpenRouter or the selected LLM provider.
- Beta users are real candidates. Only the account owner and system administrator may access recordings and evaluations; the administration surface is out of scope for this repository.
- Account deletion must remove all user-owned data from every selected durable store and external provider that received it.

## Roadmap and readiness

Phases 1 through 15 establish product specifications, capability contracts, local PDF/RAG, live voice orchestration, persistence/evaluation boundaries, browser transport, offline acceptance, and concrete opt-in provider transports.

Phase 15 is merged, but its real-provider execution checkbox remains incomplete. The latest evidence says OpenRouter, Faster-Whisper, Piper/Kokoro, Firebase, Firestore, storage, and browser audio were skipped because required configuration was absent. The project is therefore **not ready to claim a live production interview**.

Phase 16 must not be closed until it has backend/provider coverage, a clean Docker release candidate, the configured live provider turns, durable artifact and deletion verification, operations procedures, and a scripted live agent-to-agent rehearsal recording provider/model, latency, cost, quality, and limitations.

## Known limitations

- Full live provider execution and agent-to-agent journeys remain to be exercised with configured deployment accounts.
- Password-protected, scanned, or encrypted PDFs require a graceful text-only parser error in Phase 16; OCR is deferred.
- The initial deployment is a single Docker container; separate worker containers are a roadmap item.
- Browser audio transport remains selected by the Phase 16 deployment configuration; benchmark evidence must document latency, quality, and limitations.
- The repository contains no model weights, Firebase credentials, FTP credentials, or production secrets.
- Phase 15 evidence is not live readiness. A profile must produce an `exercised` result from a deliberate real run.

## Contributing

Use the SDD workflow for every feature or fix: specification, plan, marker contract, capability-first implementation, behavior tests, evidence, documentation, quality gates, and `/no-mistakes` before pushing or opening a pull request. Keep commits focused and never commit secrets or generated evidence.

## License

No license has been declared in this repository yet.
