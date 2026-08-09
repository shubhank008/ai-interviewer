# Spec 011 - Runtime configuration and provider readiness

## What the feature is about and what the user experiences

Operators can start the application with an explicit local or production profile. Local development starts without credentials, network access, model downloads, or cloud services and uses the deterministic providers already used by the offline interview path. Production startup validates required configuration, reports only redacted provider readiness, and fails before serving traffic when a required capability is missing or unhealthy.

A deployment can select provider-shaped STT, TTS, and LLM adapters through existing capability interfaces, configure ordered fallbacks, and inspect normalized capability and health results. The runtime exposes safe diagnostics that identify the active profile, selected provider names, and readiness states without printing secrets or user data. Documentation tells operators what data each provider may receive, retention and deletion boundaries, expected cost and latency considerations, and failure or fallback behavior.

This phase does not claim that any external provider, browser, Firebase project, or WebRTC deployment is live. Such readiness requires configured integration evidence outside the default offline suite.

## Numbers

| Value | Number | Source |
|---|---:|---|
| Maximum resume upload | 5 MB / 5,242,880 bytes | Existing `SPEC.md` sections 2.1 and 8; byte conversion DESIGN-FRESH |
| Default interview retention | 14 days | Existing `SPEC.md` section 8 |
| Default API rate limit | 60 requests / 60 seconds | Existing Phase 9 `InterviewApplication`; DESIGN-FRESH operational default |
| Default provider health timeout | 2 seconds | DESIGN-FRESH operational default |
| Default WebRTC media sample rate | 48,000 Hz | DESIGN-FRESH configuration default |

## Out of scope

- Real cloud credentials, provider network calls, Firebase provisioning, or WebRTC infrastructure
- Heavyweight model downloads or vendor SDK imports during module import or default tests
- Declaring production readiness from deterministic local fixtures
- Browser identity, media, and frontend implementation owned by later phases
- Changing the 5 MB upload or 14-day retention product decisions

## Acceptance

- [ ] Marker contract written (`contracts/log-markers.md`) before implementation
- [ ] `.env.example` documents non-secret settings across all requested runtime surfaces
- [ ] Typed configuration loading validates profiles, values, and secret presence without exposing secret values
- [ ] Local profile is deterministic, credential-free, and offline; production profile fails safely when required provider configuration is absent
- [ ] Provider capability and health checks normalize results and fail fast for required production capabilities
- [ ] Existing capability interfaces expose at least one provider-shaped STT, TTS, and LLM route with ordered fallback behavior
- [ ] Every new concrete class has behavior-level tests and a real mock end-to-end configuration path is exercised
- [ ] Provider data sharing, retention, cost, latency, and failure characteristics are documented
- [ ] Required gates pass and evidence emits every marker without forbidden failure patterns
- [ ] Any engine surprise is recorded in `AGENTS.md` invariants
