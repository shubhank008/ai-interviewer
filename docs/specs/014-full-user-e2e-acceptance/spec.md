# Spec 014 - Full user E2E acceptance

## What the feature is about and what the user experiences

A repeatable acceptance journey follows one candidate from account access through a completed, evaluated interview. The journey uses the real application boundary: deterministic local authentication, setup submission, a valid local PDF resume, document parsing and retrieval, mode selection, REST session creation, authenticated WebSocket control, WebRTC media transport, voice turns, interruption, reconnect, completion, persisted artifacts, evaluation, replay/history, and deletion.

The local profile is observable and honest. Separate candidate and interviewer provider instances exchange generated candidate audio through the browser media seam, the STT capability transcribes that audio, the interviewer LLM generates questions or follow-ups, and TTS returns interviewer audio. The test records timestamped state and provider evidence rather than substituting expected strings. Configured integrations run only when explicitly enabled and fully configured; absent providers are reported as skipped with redacted diagnostics, never presented as passing production evidence.

Each negative journey exposes a user-visible failure or safe recovery: invalid login, unauthorized resource access, malformed PDF, provider outage and fallback, denied microphone, reconnect, cancellation, timeout, stale response, and incomplete interview. Human-readable JSON, Markdown, and HTML artifacts explain every pass, fail, or configured-provider skip.

## Numbers

| Value | Number | Source |
|---|---:|---|
| Maximum resume size | 5 MB | Existing `SPEC.md` product requirement |
| Default retention | 14 days | Existing `SPEC.md` product requirement |
| Maximum reconnect attempts | 3 | Phase 13 design constant |
| Required positive candidate turns | 2 | DESIGN-FRESH acceptance threshold |
| Evidence schema version | 1 | DESIGN-FRESH |

## Out of scope

- Claiming Firebase, hosted STT/TTS/LLM, object storage, TURN, or real browser microphone readiness when configuration is absent.
- Downloading heavyweight models or making network calls in default offline tests.
- Sending audio bytes through WebSocket control events.
- Replacing the live pipeline with expected-string assertions or source-text tests.
- Opening a pull request, pushing a branch, or running the no-mistakes publication workflow.

## Acceptance

- [ ] Marker contract written before implementation
- [ ] Offline acceptance exercises real API, document, retrieval, provider, session, transport, persistence, evaluation, replay, and deletion paths
- [ ] Candidate and interviewer provider instances are separate and audio crosses the media boundary
- [ ] Negative journeys report safe behavior and explicit diagnostics
- [ ] Opt-in configured integrations are skipped with reasons or report redacted metadata
- [ ] JSON, Markdown, HTML, and visual browser evidence are produced outside version control
- [ ] Required repository gates, mock-turn checks, and Phase 14 checks pass
- [ ] Documentation and any durable landmine are updated
