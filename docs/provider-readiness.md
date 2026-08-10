# Provider readiness and operational characteristics

Phase 11 provides configuration and provider-shaped capability paths. It does not certify an external provider or a live browser deployment. Run the default local profile for deterministic offline development. Select `APP_PROFILE=production` only in a deployment that supplies the required identifiers, credentials, injected transports or model backends, and integration evidence.

## Data sharing and retention

The STT provider receives candidate audio for transcription, the LLM provider receives the normalized interview prompt and permitted job or resume context, and the TTS provider receives interviewer response text. Provider adapters must keep wire formats and credentials behind the existing capability interfaces. Do not send resume, transcript, audio, or credentials to a provider unless the deployment has explicitly reviewed that provider's data policy.

The application retains interview records for 14 days by default, keeps the 5 MB PDF upload limit, and exposes complete deletion through the persistence boundary. Provider-side retention, training use, regional processing, and deletion guarantees are deployment-specific and are not inferred from passing local tests. Operators must verify those terms before enabling a provider.

## Candidate provider characteristics

| Capability | Provider-shaped path | Sharing and cost | Latency and failure behavior |
|---|---|---|---|
| STT | `FasterWhisperSTT` via an injected Faster-Whisper-compatible backend | Audio remains in the configured runtime; compute cost is local infrastructure and model resource use | Model startup and CPU inference can be high-latency; unavailable backends produce normalized failure and the configured fallback is attempted |
| TTS | `PiperKokoroTTS` via an injected Piper/Kokoro-compatible backend | Response text remains in the configured runtime; cost is local CPU/GPU infrastructure | First audio depends on model load and synthesis speed; empty or failed audio is rejected and fallback routing remains provider-neutral |
| LLM | `OpenRouterLLM` via an injected OpenAI-compatible transport | Prompt context is sent to the selected hosted endpoint; cost and retention depend on the selected model and account | Network and model latency are variable; malformed, unavailable, or empty responses become normalized failures and ordered fallback can continue |
| Local fixture | `InMemorySTT`, `InMemoryTTS`, `InMemoryLLM` | No network, credentials, provider charge, or external data sharing | Deterministic and fast, but not evidence of real speech quality, model quality, browser behavior, or production readiness |

Cost and latency values are intentionally not estimated in this phase. The existing benchmark harness records deployment-specific measurements such as end-to-end latency, quality, estimated cost, failures, and CPU time. Use representative integration evidence before selecting final providers.

## Startup and diagnostics

Startup diagnostics may show profile, provider names, fallback names, configuration-presence flags, retention, rate limits, CORS origins, and health states. They must never show API key values, Firebase private material, bearer tokens, user content, or provider payloads. Missing required production configuration fails before serving traffic; missing optional local dependencies is reported as unhealthy and does not trigger a model download.

## Phase 15 opt-in integration suite

Run `./scripts/test_phase15.sh` for the offline adapter contract and redacted evidence. It never selects a provider by default. Set `PHASE15_PROFILES` to a comma-separated selection before running configured checks. Each selected profile must be exercised by a provider-specific test or is reported as failed; absent configuration is reported as skipped and is not production evidence.

| Profile | Required configuration | Setup boundary |
|---|---|---|
| `openrouter` | `OPENROUTER_API_KEY`, `LLM_MODEL` | OpenRouter HTTP API; hosted prompt sharing, account charges, model retention, and region are deployment-specific |
| `faster-whisper` | `STT_MODEL_PATH` | Install `faster-whisper` from PyPI and supply an already-downloaded model directory; no automatic download |
| `piper` | `TTS_MODEL_PATH`, `TTS_COMMAND` | Install Piper or Kokoro from its official distribution and supply a local voice model |
| `firebase` | `FIREBASE_PROJECT_ID`, `FIREBASE_CREDENTIALS_PATH` | Install `firebase-admin` from PyPI; keep service-account files outside the repository and verify ID-token claims |
| `firestore` | `FIREBASE_PROJECT_ID` and application credentials | Install `google-cloud-firestore` from PyPI; test owner isolation and complete deletion |
| `storage` | `STORAGE_BUCKET` and cloud credentials | Install `boto3` from PyPI; test upload, download, prefix deletion, and deletion failures |
| `webrtc` | `PHASE15_BROWSER_URL` and configured ICE/TURN | Use the Phase 13 browser/media boundary; browser permission and TURN evidence require configured infrastructure |

Never put API keys, bearer credentials, service-account files, transcript, resume, or audio in logs or evidence. Local model setup is intentionally manual because model downloads are large and may incur licensing or storage costs. Hosted calls can incur charges and may process sensitive interview context. Delete test users, Firestore documents, and objects after each run and verify provider-side retention terms independently.

Troubleshoot skips by checking variable presence, file permissions, model path validity, cloud project and region, service-account scopes, bucket policy, HTTPS/CORS, browser microphone permission, and ICE/TURN reachability. Redacted JSON, Markdown, and HTML reports are written under `.agent_tmp/phase15-evidence/`, which is not versioned.
