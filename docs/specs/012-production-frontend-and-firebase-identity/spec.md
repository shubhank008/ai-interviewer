# Spec 012 - Production frontend and Firebase identity

## What the feature is about and what the user experiences

Candidates use a calm, high-trust interview workspace rather than a shell. They can restore a local development session or sign up and sign in through a provider-neutral identity boundary, then move through protected setup, a live interview workspace, history, replay, transcript, evaluation, and account controls. Setup accepts a job description, validates an optional PDF resume with visible progress and errors, and requires a supported interview mode before starting.

The live workspace makes microphone permission, mute, stop, reconnect, connection state, transcript updates, and interruption feedback understandable and keyboard accessible. History uses the versioned API resources exposed by the backend and provides honest empty, loading, offline, provider-error, deletion, retention, and unavailable-result states. The local profile is deterministic and credential-free; Firebase is an opt-in adapter and is never represented as configured merely because the local journey works.

The visual direction is an editorial field notebook: warm paper surfaces, ink typography, moss status accents, and a single terracotta action color. The composition uses generous margins, a session rail, strong focus rings, and restrained motion to communicate care and concentration instead of a generic dashboard.

## Numbers

| Value | Number | Source |
|---|---:|---|
| Maximum resume upload | 5 MB / 5,242,880 bytes | Existing `SPEC.md` sections 2.1 and 8; byte conversion DESIGN-FRESH |
| Default interview retention | 14 days | Existing `SPEC.md` section 8 |
| Supported interview modes | 2 | Existing `SPEC.md` sections 2.2 and `models.py` |
| Offline auth restoration delay | 250 ms | DESIGN-FRESH local UX simulation |

## Out of scope

- Claiming configured Firebase, Firestore, WebSocket, WebRTC, microphone, storage, STT, TTS, or LLM readiness without integration evidence.
- Adding Firebase SDK credentials, secrets, network calls, or provider imports to default tests.
- Implementing the Phase 13 browser WebSocket/WebRTC voice loop; this phase presents transport-ready controls and deterministic local state.
- Replacing capability interfaces with vendor-specific business logic.
- Introducing a new CSS framework dependency when the existing Vite dependency set can support a token/component layer.

## Acceptance

- [x] Marker contract written (`contracts/log-markers.md`) BEFORE implementation
- [x] Pure logic unit-test created and tested
- [x] e2e run prints every required marker, no failure patterns
- [x] Visual features: frame evidence reviewed, not just logs
- [x] Protected local journey exposes loading, validation, provider-error, permission-denied, reconnect, offline, empty, and deletion states; configured auth remains an injected seam
- [x] No new engine surprise required an `AGENTS.md` invariant
