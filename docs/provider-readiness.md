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
