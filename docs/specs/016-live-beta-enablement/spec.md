# Spec 016 - Live Beta Enablement

## What the feature is about and what the user experiences

A beta user can open the deployed React application, create an account with Firebase Auth, submit a job description, upload an optional PDF resume, start a recruiter or technical interview, speak through the browser microphone, hear a real AI interviewer, see live transcript updates, interrupt and reconnect, complete the interview, review persisted feedback and recording, and delete the complete interview dataset.

The beta uses one explicit provider set rather than a collection of unexercised alternatives:

| Capability | Beta provider | Boundary |
|---|---|---|
| Authentication | Firebase Auth | `AuthProvider` |
| Datastore | Firestore | `DataStore` |
| Storage | Firebase Storage and local filesystem | `StorageProvider` |
| Live LLM | OpenRouter | `LLMProvider` |
| STT | Faster-Whisper | `STTProvider` |
| TTS | Kokoro | `TTSProvider` |
| Voice service | WebRTC | `AudioTransport` |
| Evaluation | LLM-based evaluator | `Evaluator` |
| Workers | CPU-only | worker process boundary |
| Retention | 14 days | policy service |

The beta is a real vertical slice. Deterministic providers remain available for offline development, but they cannot satisfy beta acceptance criteria.

## Service flow

```text
Firebase Web Auth
  -> Firebase ID token
  -> FastAPI auth middleware
  -> Firebase uid and owner scope

React setup
  -> POST job description and resume metadata
  -> API validates 5 MB PDF limit
  -> StorageProvider stores original resume
  -> DocumentParser extracts text
  -> RetrievalProvider stores source-linked chunks

POST /sessions
  -> Firestore session record
  -> authorized WebSocket control channel
  -> WebRTC offer/answer and ICE signaling
  -> server audio worker receives microphone track

Candidate audio
  -> WebRTC audio track
  -> CPU Faster-Whisper worker
  -> partial/final transcript events
  -> interview state machine and RAG context
  -> OpenRouter structured streaming response
  -> sentence chunker and Kokoro CPU TTS worker
  -> WebRTC agent audio track
  -> Firestore transcript/event persistence
  -> recording storage

POST /sessions/{id}/complete
  -> immutable final transcript
  -> CPU evaluation worker
  -> OpenRouter evaluator response
  -> schema validation and score bounds
  -> Firestore evaluation
  -> recording/transcript replay resources

DELETE /sessions/{id}
  -> delete Firestore records
  -> delete Firebase/local objects
  -> delete derived chunks and evaluation
  -> verify no owned artifacts remain
```

## Normalized schemas

### Identity

`AuthProvider.verify_id_token(token)` returns `UserIdentity` with `user_id`, `email` when available, provider name, issued-at, expiry, and authentication assurance. Raw tokens and Firebase claims not required by the domain never leave the adapter.

### Setup

```json
{
  "job_description": "string, non-empty",
  "resume_upload_id": "uuid|null",
  "mode": "recruiter|technical",
  "role_metadata": {"seniority": "optional", "location": "optional"}
}
```

The API stores normalized job-description text, source references, content hashes, and ingestion status. Resume originals are never placed in WebSocket messages or logs.

### Session

```json
{
  "id": "uuid",
  "owner_id": "firebase uid",
  "mode": "recruiter|technical",
  "status": "created|connecting|active|interrupted|completed|failed|deleted",
  "provider_set": {"stt": "faster-whisper", "tts": "kokoro", "llm": "openrouter"},
  "created_at": "RFC3339",
  "expires_at": "RFC3339"
}
```

### WebSocket event

```json
{
  "schema_version": 1,
  "session_id": "uuid",
  "sequence": 12,
  "correlation_id": "uuid",
  "type": "transcript.partial|transcript.final|agent.text|agent.audio.status|state|error",
  "occurred_at": "RFC3339",
  "payload": {}
}
```

Events are ordered, replayable after acknowledgement, idempotent where applicable, and contain metadata rather than raw audio bytes.

### Transcript segment

```json
{
  "id": "uuid",
  "speaker": "candidate|interviewer",
  "text": "string",
  "start_ms": 0,
  "end_ms": 1200,
  "final": true,
  "confidence": 0.0,
  "source": "faster-whisper|llm|correction"
}
```

### LLM interviewer response

The OpenRouter adapter must validate a structured response before it reaches the voice scheduler:

```json
{
  "spoken_text": "string",
  "question_type": "opening|follow_up|clarification|transition|closing",
  "topic": "string",
  "evidence_request": "optional string",
  "should_end": false,
  "state_update": {"key": "value"}
}
```

The evaluator uses a separate structured schema containing `score`, `summary`, `strengths`, `weaknesses`, `missed_opportunities`, `recommendations`, `role_assessment`, `rubric_version`, `model`, and evidence references. Scores are bounded from 0 through 100.

## Provider implementation requirements

- Abstract interfaces live under `src/interviewer_domain/capabilities/`.
- Concrete provider adapters live under `src/interviewer_domain/adapters/` grouped by capability.
- Deterministic providers live under `src/interviewer_domain/providers/in_memory/`.
- Domain services must import capability protocols, never Firebase, Firestore, OpenRouter, Faster-Whisper, Kokoro, or browser SDKs directly.
- Adapters own wire formats, SDK imports, credentials, timeout/retry policy, rate-limit normalization, redaction, and provider metadata.
- Production composition must select the explicit beta provider set and fail safely if required configuration is absent.
- Every concrete adapter must have a deterministic contract test and a separately tagged live integration test.

## Beta acceptance

- [ ] A clean deployment starts with the documented CPU-only configuration.
- [ ] Firebase browser signup, login, logout, refresh, protected routes, and server-side token verification work.
- [ ] Firestore stores and retrieves owner-scoped setup, sessions, events, transcripts, evaluations, and deletion state.
- [ ] Firebase Storage and local filesystem adapters both satisfy upload, download, replay, retention, and deletion contracts.
- [ ] A real PDF resume and job description pass through storage, parsing, source-linked retrieval, and prompt context.
- [ ] A real browser microphone track reaches Faster-Whisper and produces partial and final timestamped transcript events.
- [ ] OpenRouter generates validated structured interviewer responses with streaming, cancellation, timeout, cost, and model metadata.
- [ ] Kokoro produces browser-compatible audio with bounded latency, sequencing, interruption, and cancellation.
- [ ] WebRTC works over the configured STUN/TURN deployment from an external browser network.
- [ ] The browser completes at least one recruiter and one technical interview using real providers.
- [ ] Candidate and interviewer audio, final transcript, events, and evaluation persist and replay from durable storage.
- [ ] The LLM evaluator runs only after completion and stores validated feedback with score 0 through 100.
- [ ] Deleting an interview removes raw, derived, cached, transcript, recording, evaluation, and provider-created test artifacts.
- [ ] The beta reports provider, model, version, device, latency, cost, quality, failure, and limitation metadata without sensitive payloads.
- [ ] Negative cases cover invalid auth, owner mismatch, malformed PDF/audio, provider timeout, cancellation, quota/rate limit, WebRTC failure, storage failure, and deletion failure.
- [ ] Offline tests remain credential-free and cannot mark this beta acceptance as passed.
