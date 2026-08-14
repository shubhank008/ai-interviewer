# Provider readiness and operational characteristics

Phase 16 is the live-provider phase. Contract tests and local fixtures remain useful for protecting boundaries, but they are not provider or beta evidence. The production profile must load the configured `.env`, initialize the selected providers, and fail closed when a required provider is unavailable. The first beta uses Firebase Auth/Admin, EU Firestore, local/NFS storage, WhisperX small on CPU, Kokoro Python, OpenRouter through `LLM_API_KEY`, and timestamped browser microphone chunks.

## Data sharing and retention

The STT provider receives candidate audio for transcription, the LLM provider receives the normalized interview prompt and permitted job or resume context, and the TTS provider receives interviewer response text. Provider adapters must keep wire formats and credentials behind the existing capability interfaces. Do not send resume, transcript, audio, or credentials to a provider unless the deployment has explicitly reviewed that provider's data policy.

The application retains interview records for 14 days by default, keeps the Phase 16 10 MB PDF upload limit, and exposes complete deletion through the persistence boundary. Provider-side retention, training use, regional processing, and deletion guarantees are deployment-specific and are not inferred from passing local tests. Operators must verify those terms before enabling a provider.

## Candidate provider characteristics

| Capability | Provider-shaped path | Sharing and cost | Latency and failure behavior |
|---|---|---|---|
| STT | `WhisperXSTT` using the `small` model on CPU | Audio remains in the configured runtime; compute cost is local infrastructure and model resource use | Model startup and CPU inference can be high-latency; unavailable or malformed audio produces normalized failure |
| TTS | `KokoroTTS` via the Kokoro Python runtime | Response text remains in the configured runtime; cost is local CPU infrastructure | First audio depends on model load and synthesis speed; empty or failed audio is rejected |
| LLM | `OpenRouterLLM` via `LLM_API_KEY` and the configured model | Prompt context is sent to the selected hosted endpoint; cost and retention depend on the selected model and account | Network and model latency are variable; malformed, unavailable, timeout, and rate-limit responses become normalized failures |
| Local fixture | `InMemorySTT`, `InMemoryTTS`, `InMemoryLLM` | No network, credentials, provider charge, or external data sharing | Deterministic and fast, but not evidence of real speech quality, model quality, browser behavior, or production readiness |

Cost and latency values are intentionally not estimated in this phase. The existing benchmark harness records deployment-specific measurements such as end-to-end latency, quality, estimated cost, failures, and CPU time. Use representative integration evidence before selecting final providers.

## Startup and diagnostics

Startup diagnostics may show profile, provider names, fallback names, configuration-presence flags, retention, rate limits, CORS origins, and health states. They must never show API key values, Firebase private material, bearer tokens, user content, or provider payloads. Missing required production configuration fails before serving traffic; missing optional local dependencies is reported as unhealthy and does not trigger a model download.

## Phase 16 live integration gate

Run `./scripts/test_phase16.sh` for contract checks plus the live rehearsal. The runner must load the configured environment and execute the selected provider and browser operations. Missing configuration is `skipped`; a configured provider that cannot be initialized or exercised is `failed`; only an exercised operation can satisfy beta evidence.

| Operation | Required configuration | Setup boundary |
|---|---|---|
| `openrouter` | `LLM_API_KEY`, `LLM_MODEL` | OpenRouter structured interviewer and evaluator calls with bounded timeout/retries |
| `whisperx` | `STT_PROVIDER=whisperx`, `STT_MODEL=small`, `STT_CPU=true` | Install and exercise WhisperX using model-name configuration; no model-path setting is required |
| `kokoro` | `TTS_PROVIDER=kokoro`, `TTS_LANGUAGE=en` | Install and exercise Kokoro Python with normalized browser audio and random supported voice |
| `firebase` | Firebase Web settings and `FIREBASE_CREDENTIALS_PATH` | Exercise email/password and Google Auth, Admin verification, owner isolation, token refresh, and logout/deletion |
| `firestore` | `FIREBASE_PROJECT_ID`, `FIRESTORE_DATABASE`, backend credentials | Exercise session, event, transcript, evaluation, retention, and exact deletion |
| `storage-local` | `STORAGE_BACKEND=local`, `STORAGE_PATH` | Exercise upload, download, replay, retention, partial failure, and deletion |
| `browser` | Frontend URL and configured test account | Exercise recruiter and technical journeys using timestamped microphone chunks |

Never put API keys, bearer credentials, service-account files, transcript, resume, or audio in logs or evidence. Local model setup is intentionally manual because model downloads are large and may incur licensing or storage costs. Hosted calls can incur charges and may process sensitive interview context. Delete test users, Firestore documents, and objects after each run and verify provider-side retention terms independently.

Troubleshoot skips by checking environment loading, dependency installation, Firebase credential-path permissions, cloud project and region, Firestore rules, local/NFS storage access, HTTPS/CORS, browser microphone permission, and browser transport reachability. Redacted JSON, Markdown, and HTML reports are written under `.agent_tmp/phase16-evidence/`, which is not versioned.


## Phase 16 locked beta decisions

Phase 16 live readiness is measured by a programmatic Interviewer Agent and Interviewee Agent E2E flow, not browser automation. The flow uses real OpenRouter, WhisperX, Kokoro, Firebase Auth/Firestore, Firebase Storage (`gs://the-interviewer-c3a01.firebasestorage.app`), and local/NFS checks. FTP, browser URL, WebRTC, and TURN are deferred. Offline or deterministic runs are not beta evidence.
