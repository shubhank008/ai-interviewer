# Spec 016 - Live Beta Enablement

## What the feature is about and what the user experiences

A beta user can open the deployed React application, create an account with Firebase Auth, submit a job description, upload an optional PDF resume, start a recruiter or technical interview, speak through the browser microphone, hear a real AI interviewer, see live transcript updates, interrupt and reconnect, complete the interview, review persisted feedback and recording, and delete the complete interview dataset.

The beta uses one explicit provider set rather than a collection of unexercised alternatives:

| Capability | Beta provider | Boundary |
|---|---|---|
| Authentication | Firebase Web Auth email/password and Google Sign-In | `AuthProvider` |
| Datastore | Firestore | `DataStore` |
| Storage | Firebase Storage `gs://the-interviewer-c3a01.firebasestorage.app` plus local/NFS | `StorageProvider` |
| Live LLM | OpenRouter using `LLM_API_KEY` and `LLM_MODEL` | `LLMProvider` |
| STT | WhisperX using the `small` model | `STTProvider` |
| TTS | Kokoro 0.9.4 English, `af_bella` or `af_sky`, 24 kHz mono PCM | `TTSProvider` |
| Voice input | Programmatic timestamped audio buffers exchanged by Interviewer and Interviewee agents | `AudioTransport` |
| Evaluation | GPT-5.6 Luna Pro through OpenRouter after completion | `Evaluator` |
| Runtime | One Docker container for the beta benchmark; split workers are a roadmap item | service composition |
| Resume retention | 14 days | policy service |
| Combined audio retention | 7 days | policy service |
| Audit-log retention | 30 days | policy service |

The beta is a live vertical slice. Offline tests and deterministic providers are contract protection only. They are not release evidence and must never mark beta readiness as passed. Phase 16 live rehearsal is programmatic: an Interviewer Agent and an Interviewee Agent complete recruiter and technical flows through the backend audio-buffer path. Browser execution is deferred and is not required for Phase 16 evidence.

## Authoritative implementation decisions

These Phase 16 decisions are final and must be taken from the main `SPEC.md` without reopening ordinary product choices:

- Load the existing `.env` safely for live runs; never print or commit its values.
- Use `FIREBASE_CREDENTIALS_PATH` for backend Firebase Admin credentials and Firebase Web Auth settings for the browser.
- Use `LLM_API_KEY`, not `OPENROUTER_API_KEY`.
- Use WhisperX `small` on CPU by default. Do not require `STT_MODEL_PATH`.
- Use Kokoro Python with `TTS_LANGUAGE=en` and random supported voice selection. Do not require `TTS_MODEL_PATH` or `TTS_COMMAND`.
- Use Firebase Storage `gs://the-interviewer-c3a01.firebasestorage.app` and local/NFS. Ignore FTP for Phase 16; S3/GCS are out of scope.
- Use timestamped audio buffers between the Interviewer Agent and Interviewee Agent. Browser URL, browser automation, WebRTC, and TURN are not Phase 16 prerequisites.
- Use one Docker container for the initial beta benchmark.
- Live provider and agent-to-agent execution is mandatory evidence. Offline tests protect contracts only.

## Service flow

```text
Firebase Web Auth
  -> Firebase ID token
  -> FastAPI auth middleware
  -> Firebase uid and owner scope

React setup
  -> Firebase email/password or Google signup/login
  -> POST job description and optional resume metadata
  -> API validates 10 MB job-description and 10 MB resume limits
  -> StorageProvider stores original resume
  -> DocumentParser extracts text from a text PDF or returns a descriptive unsupported-format error
  -> RetrievalProvider stores source-linked chunks

POST /sessions
  -> Firestore session record
  -> authorized WebSocket control channel
  -> authenticated browser audio session
  -> selected microphone chunk transport and timestamp contract

Candidate audio
  -> Interviewee Agent timestamped audio buffers
  -> backend audio-buffer transport
  -> CPU WhisperX worker
  -> partial/final transcript events
  -> interview state machine and RAG context
  -> OpenRouter structured streaming response
  -> sentence chunker and Kokoro CPU TTS worker
  -> 24 kHz mono linear PCM audio chunks
  -> Firestore transcript/event persistence
  -> combined interview recording storage for 7 days

POST /sessions/{id}/complete
  -> immutable final transcript
  -> CPU evaluation worker
  -> OpenRouter evaluator response
  -> schema validation and score bounds
  -> Firestore evaluation
  -> recording/transcript replay resources

DELETE /sessions/{id}
  -> delete Firestore records
  -> delete local or Firebase objects
  -> delete derived chunks, cached context, transcript, recording, and evaluation
  -> verify no owned artifacts remain across every selected backend
```

## Service decisions

### Authentication and account policy

- Firebase Web Auth is the only beta browser authentication path.
- The sign-in methods are email/password and Google Sign-In.
- Open signup is enabled.
- The Firebase project and Admin SDK JSON configured in the environment are beta resources. Production may use a different project and credential file without changing this contract.
- Domain authorization is not a beta requirement for email/password or Google sign-in.
- The current scope does not include an operator or recruiter administration panel. A separate backend or panel will later provide approved system-admin access to interview data.

### Firebase and Firestore

- Firestore is hosted in the EU region.
- Firestore security rules are managed in Firebase/Firestore rather than this repository.
- The application must still enforce server-side owner checks for every user-owned resource.
- Audit logs and access records retain for 30 days.
- Account deletion removes all user-owned Firestore, storage, transcript, recording, evaluation, cache, and derived data.

### Storage

- Supported beta storage adapters are Firebase Storage and local filesystem/NFS. FTP is deferred.
- S3 and GCS adapters are out of scope for this phase and must not be presented as selected beta providers.
- Local filesystem storage must support an externally mounted filesystem such as NFS.
- Firebase Storage uses `gs://the-interviewer-c3a01.firebasestorage.app` in the beta configuration and the US-EAST1 region.
- The live storage rehearsal must switch between local/NFS and Firebase Storage and exercise upload, download, replay, retention, partial failure, and deletion.
- Resume objects retain for 14 days. Combined interview audio retains for 7 days. Other user-owned artifacts follow the resume policy unless a more restrictive lifecycle is required.

### Inputs and resume processing

- The sample fixtures are `tests/demo_resume.pdf` and `tests/demo_jobdescription.txt`; absence is a failed rehearsal precondition.
- Job descriptions and PDF resumes have a 10 MB maximum each, regardless of whether the job description is uploaded, supplied as text, or pasted into the UI.
- Password-protected PDFs must produce a graceful user-facing error requesting an unlocked PDF.
- Scanned or encrypted PDFs fail gracefully with a descriptive error; Phase 16 does not perform OCR or guessed extraction.
- Resume content may be sent to the selected LLM or injected into the system context when the interview script is generated. This is disclosed in the privacy notice.

### Speech and audio

- WhisperX is the active STT provider and the active model is `small` from `STT_PROVIDER=whisperx` and `STT_MODEL=small`.
- No fixed latency or concurrency target is assumed initially. The live benchmark matrix measures provider, model, latency, CPU, memory, and failure behavior using the supplied sample audio and Kokoro-generated test audio.
- Kokoro uses `TTS_LANGUAGE=en`. Voice selection is randomized per invocation from the supported voices for that language.
- Kokoro emits 24 kHz mono linear PCM chunks with ordering, interruption, and cancellation metadata.
- The browser microphone flow should prefer a proven chunked capture or VAD/streaming-Whisper approach over a custom full WebRTC media pipeline when benchmark and reliability evidence support it. Silero VAD and SimulStreaming are candidate integrations, not yet selected providers.

### LLM and evaluation

- OpenRouter uses the configured `LLM_MODEL=~deepseek/deepseek-v4-flash-latest`, normalized by configuration as needed.
- The live benchmark records token usage, elapsed time, provider/model, and cost when available. There is no pre-set maximum cost per interview yet.
- OpenRouter requests have a 60 second timeout and up to 3 retries. Permanent failures such as insufficient balance, invalid model, or HTTP 404 must not be retried.
- A permanent or exhausted provider failure fails the interview and presents a safe service-unavailable error to the user. Detailed errors and stack traces are internal-only. No fallback provider is required in this phase.
- The live E2E benchmark must emit a redacted table of token, time, and cost metrics.

### Deployment and operations

- The beta deployment target is Docker containers, initially tested as a single container on a self-hosted host or Railway profile.
- The first benchmark measures the single-container resource profile. API, model/audio, and evaluation workers may later be split into separate containers for scaling; that separation is a roadmap item, not a Phase 16 prerequisite.
- Beta users are real candidates. Privacy and consent must be shown before data collection and must disclose external LLM processing.
- Only the account owner and the system administrator may access recordings and evaluations. The separate administration surface is out of scope for this repository.

### Privacy and consent placeholder

Before interview setup, the UI must show a placeholder consent notice stating that the service collects job descriptions, resumes, microphone audio, transcripts, recordings, and evaluations; sends resume, transcript, audio-derived content, and evaluation context to OpenRouter or the selected LLM provider; retains resumes for 14 days and combined recordings for 7 days; retains audit/access records for 30 days; and deletes user-owned data when the account is deleted. The final legal text, controller identity, regional disclosures, and provider-specific terms require a later legal review.

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
  "provider_set": {"stt": "whisperx-small", "tts": "kokoro", "llm": "openrouter"},
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
  "source": "whisperx|llm|correction"
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
- [ ] Local/NFS-compatible and Firebase Storage adapters satisfy upload, download, replay, retention, partial-failure, and deletion contracts. FTP is deferred.
- [ ] A real PDF resume and job description pass through storage, parsing, source-linked retrieval, and prompt context.
- [ ] Interviewee Agent audio buffers reach WhisperX and produce partial and final timestamped transcript events.
- [ ] OpenRouter generates validated structured interviewer responses with streaming, cancellation, 60 second timeout, up to 3 retries, cost, and model metadata.
- [ ] Kokoro uses English and randomized per-invocation voices to produce browser-compatible audio with benchmarked sequencing, interruption, and cancellation.
- [ ] Interviewer and Interviewee agents complete recruiter and technical interviews through the backend using real providers.
- [ ] Browser/WebRTC/STUN/TURN are explicitly deferred from Phase 16 acceptance.
- [ ] Candidate and interviewer audio, final transcript, events, and evaluation persist and replay from durable storage.
- [ ] The LLM evaluator runs only after completion and stores validated feedback with score 0 through 100.
- [ ] Deleting an interview removes raw, derived, cached, transcript, recording, evaluation, and provider-created test artifacts.
- [ ] The beta reports provider, model, version, device, latency, cost, quality, failure, and limitation metadata without sensitive payloads.
- [ ] Negative cases cover invalid auth, owner mismatch, malformed PDF/audio, provider timeout, cancellation, quota/rate limit, selected browser-audio transport failure, storage failure, and deletion failure.
- [ ] Live tests are the only release evidence. Offline tests may protect contracts but cannot mark any Phase 16 acceptance item as passed.
- [ ] Every live marker is backed by an exercised run, and skipped configuration never passes readiness.
