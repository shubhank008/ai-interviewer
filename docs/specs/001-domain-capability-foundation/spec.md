# Spec 001 - Domain Capability Foundation

## What the feature is about and what the user experiences

This feature establishes the stable foundation used by the future voice-first
interview experience. A candidate's interview can be represented consistently
as a session with ordered voice turns, transcript and recording metadata,
provider measurements, lifecycle state, and eventual evaluation data. The
future interview engine can exchange speech, text, events, and stored records
without exposing which vendor or infrastructure produced them.

The foundation also provides deterministic local behavior for development and
mock interviews. A developer can run a complete text-to-audio-shaped mock turn
through the same capability boundaries that production adapters will use,
observe ordered lifecycle events, and receive normalized failures for timeout,
cancellation, unavailable capability, and invalid state conditions.

The product remains voice-first: text models represent transcript and control
state, while audio input and output are represented by STT, TTS, and transport
capabilities. This feature does not add a text interview UI or a vendor
integration.

## Numbers

| Value | Number | Source |
| --- | --- | --- |
| Default retention period | 14 days | SPEC.md, section 8 |
| Maximum resume upload | 5 MB | SPEC.md, sections 2.1 and 8 |
| Supported initial interview modes | 2 | SPEC.md, section 2.2 |

## Out of scope

- Browser UI, WebRTC signaling, WebSocket endpoints, or REST endpoints
- The live interview state machine, planning, persona behavior, or evaluation
  scoring logic
- PDF parsing, embeddings, retrieval, hosted providers, or vendor SDKs
- Authentication, authorization, persistence, retention enforcement, or secrets
- Production audio codecs and provider routing policy

## Acceptance

- [x] Marker contract written (`contracts/log-markers.md`) before implementation
- [x] Pure domain and contract unit tests pass
- [x] Deterministic mock-turn test prints every required marker
- [x] Capability interfaces are provider-independent and business logic uses them
- [x] Normalized errors, cancellation, timeout, health, and capability contracts
  are explicit
- [x] No secrets or provider credentials are committed
- [x] Available linting and type validation commands are run and reported
