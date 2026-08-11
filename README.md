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
| STT | In-memory fixture | Faster-Whisper local backend | Phase 15 contract; skipped live |
| TTS | In-memory fixture | Piper/Kokoro command backend | Phase 15 contract; skipped live |
| LLM | In-memory fixture | OpenRouter HTTP transport | Phase 15 contract; skipped live |
| Auth and data | Dev token and memory stores | Firebase Admin, Firestore, S3 seams | Skipped live |
| Browser media | Local WebSocket/WebRTC boundary | Real microphone and TURN | Skipped live |
| Evaluation | Deterministic post-interview evaluator | Provider selection is future work | Phase 14 offline |

Requirements are in [`SPEC.md`](SPEC.md), implementation status is in [`PLAN.md`](PLAN.md), and provider operations are in [`docs/provider-readiness.md`](docs/provider-readiness.md).

## How it works

1. The candidate authenticates, enters a text job description, selects a mode, and optionally selects a PDF resume.
2. Text PDF ingestion validates, parses, normalizes, chunks, and retrieves relevant evidence. Documents are untrusted data, never system instructions.
3. A session is created through the versioned API and authorized for the current user.
4. HTTP handles setup and resources, WebSocket handles ordered control and transcript/status events, and WebRTC handles microphone and agent audio. Media frames never enter WebSocket control messages.
5. `LiveVoiceOrchestrator` coordinates STT, interview state, LLM generation, TTS scheduling, interruption, cancellation, fallback, and timestamped artifacts.
6. Completion persists transcript, recording metadata, events, and evaluation artifacts. Evaluation runs only after completion from final transcript evidence.
7. History, replay, transcript, results, retention, and deletion use owner-checked boundaries.

The local profile exercises these contracts without credentials or external network calls. It does not prove speech quality, model quality, Firebase behavior, or production WebRTC connectivity.

## Architecture

Business logic is provider-neutral. Capability interfaces define normalized payloads, cancellation, timeouts, errors, health, and discovery. Vendor formats, SDK imports, credentials, retries, and provider failures remain in adapters.

```text
React browser UI
    | HTTP REST: setup, sessions, history, transcript, results
    | WebSocket: control, signaling, transcript, status, replay
    | WebRTC: microphone and agent audio
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

Provider paths currently include `OpenRouterHTTPTransport`, `FasterWhisperLocalBackend`, `PiperCommandBackend`, `FirebaseAdminAuthBackend`, `FirestoreGoogleBackend`, and `Boto3ObjectBackend`. In-memory providers remain available for deterministic tests. Optional SDKs are imported lazily, model weights are never downloaded automatically, and configured providers must not silently fall back to memory.

## Repository layout

```text
src/interviewer_domain/       Models, contracts, providers, routing, orchestration
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

Requirements are Python 3.12+, `pip`, Node.js, npm, and optionally Docker.

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

Open <http://127.0.0.1:5173>. The current frontend uses local identity and a development token. A reverse proxy must route `/api` and WebSocket upgrades to the API. Real microphone/WebRTC use requires HTTPS.

```bash
npm run lint
npm test
npm run test:coverage
npm run build
```

### Run with Docker

The supplied Compose file runs the API only. It does not serve React, provide Firebase, start model workers, provide TURN, or provision durable storage.

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
| WS | `/ws/v1/sessions/{id}/signaling` | Authenticated signaling channel |

The FastAPI composition root is still development-oriented: it creates in-memory auth, persistence, and storage at startup. Concrete production provider classes exist, but complete production composition and verification remain outstanding.

## Provider integrations

Phase 15 profiles distinguish `exercised`, `skipped`, and `failed`. Missing configuration is a skip, not a readiness pass. A selected profile that fails is a failure.

```bash
export PYTHONPATH="$PWD/src"
./scripts/test_phase15.sh
export PHASE15_PROFILES=openrouter,faster-whisper,piper,firebase,firestore,storage,webrtc
./scripts/test_phase15.sh
```

The current Phase 15 runner validates configuration and writes evidence, but does not automatically execute every selected live operation. Real readiness requires deliberate configured runs with real inputs, safe test accounts or buckets, and recorded evidence.

- **OpenRouter:** set `OPENROUTER_API_KEY`, `LLM_MODEL`, and `LLM_PROVIDER=openrouter`. Review data sharing, retention, region, cost, and rate limits.
- **Faster-Whisper:** install the optional package and provide an already-downloaded model directory through `STT_MODEL_PATH`. Weights are never downloaded by the application. Set `STT_PROVIDER=faster-whisper`.
- **Piper or Kokoro:** provide an operator-installed command plus `TTS_MODEL_PATH` and `TTS_COMMAND`. Verify output sample rate, codec, playback, latency, cancellation, and license.
- **Firebase and Firestore:** provide `FIREBASE_PROJECT_ID` and a protected `FIREBASE_CREDENTIALS_PATH`. Use a non-production project and verify claims, revoked tokens, rules, owner isolation, deletion, and region.
- **S3-compatible storage:** set `STORAGE_BACKEND`, `STORAGE_BUCKET`, and provider credentials. Use a dedicated test bucket and verify upload, download, prefixes, retries, lifecycle, and deletion.
- **Browser and WebRTC:** set `PHASE15_BROWSER_URL` to an HTTPS browser environment and configure `WEBRTC_ICE_SERVERS` with deployment STUN/TURN. This repository does not provide a TURN server.

## Configuration

```bash
cp .env.example .env
```

| Variable | Purpose |
|---|---|
| `APP_PROFILE` | `local` for deterministic development; `production` requires explicit providers |
| `PHASE15_PROFILES` | Opt-in integration profiles |
| `STT_PROVIDER`, `STT_MODEL_PATH` | STT selection and local model path |
| `TTS_PROVIDER`, `TTS_MODEL_PATH`, `TTS_COMMAND` | TTS selection and command |
| `LLM_PROVIDER`, `LLM_MODEL`, `OPENROUTER_API_KEY` | LLM selection and credential |
| `FIREBASE_PROJECT_ID`, `FIREBASE_CREDENTIALS_PATH` | Firebase Admin and Firestore |
| `STORAGE_BACKEND`, `STORAGE_BUCKET` | Durable object storage |
| `PHASE15_BROWSER_URL` | Browser integration target |
| `WEBRTC_ICE_SERVERS` | STUN/TURN list |
| `RETENTION_DAYS` | Default retention, currently 14 days |
| `RATE_LIMIT`, `RATE_WINDOW_SECONDS` | Rate limiting |
| `CORS_ORIGINS` | Allowed browser origins |

Never put credentials in `.env.example`, source, Git history, screenshots, logs, evidence, or frontend bundles.

## Testing and evidence

Default gates are credential-free:

```bash
export PYTHONPATH="$PWD/src"
./scripts/lint_and_typecheck.sh
./scripts/test_backend.sh
./scripts/test_frontend.sh
./scripts/test_phase11.sh
./scripts/test_phase13.sh
./scripts/test_phase14.sh
./scripts/test_phase15.sh
```

Evidence is written under `.agent_tmp/` and ignored by Git. Offline evidence proves application contracts, not external availability, speech quality, LLM quality, Firebase rules, TURN connectivity, or production security.

## Production deployment

Production is not yet a supported one-command deployment. Before accepting real candidate data:

1. Replace development auth, in-memory persistence, and in-memory storage with Firebase/Auth, Firestore or another reviewed datastore, and durable object storage.
2. Implement browser Firebase sign-in/session restoration and server-side ID-token verification. Remove `dev-token` from production composition.
3. Benchmark STT, TTS, and LLM providers for first-audio latency, turn latency, interruption, cancellation, retries, rate limits, cost, quality, and fallback.
4. Deploy HTTPS, secure WebSocket origin checks, STUN/TURN, microphone permissions, compatible codecs and sample rates, and browser-to-server media verification.
5. Add encryption, owner-scoped keys, retention jobs, deletion verification, backups, restore tests, and provider-side deletion review.
6. Add secrets management, redacted logs, metrics, traces, alerts, readiness probes, abuse controls, patching, rollback, and incident procedures.
7. Build the frontend with `npm run build`, serve it over HTTPS, and route `/api` plus WebSocket upgrades to the API.
8. Run configured Phase 15 integrations with test accounts and real browser media, then complete the Phase 16 coverage and live-demo gate.

Use separate frontend, API, model/audio worker, and asynchronous evaluation services as load requires. The current Compose file is a local API definition, not a production topology.

## Security and privacy

Resumes, job descriptions, voice recordings, transcripts, and evaluations may contain personal data.

- Treat documents and provider responses as untrusted input and never allow them to override system instructions.
- Send only the minimum permitted context to external providers.
- Review provider training, retention, region, and deletion policies before enabling them.
- Use separate test projects, buckets, credentials, and model configurations.
- Redact credentials, prompts, transcript text, audio, and personal data from logs and evidence.
- Enforce owner checks on sessions, transcripts, recordings, evaluations, and deletion.
- Use HTTPS and secure WebSocket origins in production.
- Keep the default retention decision at 14 days unless a reviewed deployment policy changes it.
- Verify deletion in every durable store and external provider that received the data.

## Roadmap and readiness

Phases 1 through 15 establish product specifications, capability contracts, local PDF/RAG, live voice orchestration, persistence/evaluation boundaries, browser transport, offline acceptance, and concrete opt-in provider transports.

Phase 15 is merged, but its real-provider execution checkbox remains incomplete. The latest evidence says OpenRouter, Faster-Whisper, Piper/Kokoro, Firebase, Firestore, storage, and WebRTC were skipped because required configuration was absent. The project is therefore **not ready to claim a live production interview**.

Phase 16 must not be closed until it has separate backend/frontend/browser/provider coverage, a clean Docker release candidate, real authentication and owner isolation, real STT/TTS/LLM voice turns, durable artifact and deletion verification, HTTPS/CORS/WebSocket/TURN security, operations procedures, and a scripted live-browser rehearsal recording provider/model, latency, cost, quality, and limitations.

## Known limitations

- Text PDFs are supported; scanned or encrypted PDFs need a future OCR adapter.
- The default frontend uses local identity and a development bearer token.
- The API composition uses in-memory auth, persistence, and storage locally.
- Docker Compose does not include the frontend, model workers, durable stores, or TURN.
- Browser media is a provider-neutral seam, not proof of microphone, codec, playback, or TURN behavior.
- Phase 15 transports exist, but the repository contains no model weights, Firebase credentials, TURN service, or production secrets.
- Phase 15 evidence is not live readiness. A profile must produce an `exercised` result from a deliberate real run.

## Contributing

Use the SDD workflow for every feature or fix: specification, plan, marker contract, capability-first implementation, behavior tests, evidence, documentation, quality gates, and `/no-mistakes` before pushing or opening a pull request. Keep commits focused and never commit secrets or generated evidence.

## License

No license has been declared in this repository yet.
