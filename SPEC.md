# Product Specification: AI Mock Interview Platform

## 1. Product objective

Build a browser-based, voice-native mock interview platform that lets a candidate practice realistic recruiter and technical interviews with an LLM agent. The interview is tailored to the supplied job description, optional resume, seniority, location, company context, and other relevant candidate or role information.

The platform must feel conversational and adaptive rather than playing a fixed script. It must support low-latency spoken interaction, preserve the complete interview, and provide structured post-interview feedback.

## 2. User experience

### 2.1 Interview setup

The candidate can provide:

- A text-only job description
- An optional PDF resume upload
- Interview mode: recruiter screen or technical or hiring-manager interview

The first release limits uploaded resume files to 5 MB. The system extracts role requirements, topics, seniority signals, company and culture signals, and useful resume facts before the interview starts. Prompt-injection and content-security guardrails must treat uploaded resume text and job-description text as untrusted data, never as system instructions.

No separate text or chat interview mode is planned. Text appears as setup input, live transcript, status, and post-interview feedback while the interview itself is voice-based.

### 2.2 Interview modes

The first release supports two modes:

- **Recruiter screen:** background, motivation, role fit, communication, logistics, compensation, availability, location, and work authorization when relevant.
- **Technical or hiring-manager interview:** technical depth, problem solving, system design or domain knowledge, project experience, behavioral signals, and role-specific follow-up questions.

The agent impersonates the appropriate recruiter, hiring manager, or technical interviewer. Persona behavior should reflect the job description and available company context without making unsupported claims about a real person or company.

### 2.3 Live conversation

During the interview, the agent must:

- Ask questions appropriate to the selected role and seniority
- Follow up on the candidate's actual answers
- Maintain a coherent interview state and topic progression
- Adapt difficulty and questioning style based on observed evidence
- Use short acknowledgements or company and culture context when appropriate
- Allow natural pauses, interruptions, corrections, and turn-taking

Substantive questions must remain dynamically grounded in the latest conversation. The system may prepare candidate topics, follow-up hypotheses, acknowledgements, or short informational responses ahead of time, but it must be able to discard them when the candidate changes direction.

### 2.4 Interview records and results

The system records:

- Downloadable interview audio
- A timestamped, speaker-labeled transcript
- Interview events and state transitions needed for replay and debugging
- Final structured evaluation and rendered feedback

After the interview, the candidate can replay the audio, inspect the transcript, and view:

- An overall score out of 100
- A concise summary
- Strengths and standout answers
- Weaknesses and missed opportunities
- Role-specific and communication feedback
- Concrete improvement recommendations
- A recruiter-style or hiring-manager-style assessment

Evaluation is performed after the interview from the final transcript and related interview metadata. The live agent must not expose a hidden grading result while the interview is in progress.

## 3. Capability-based architecture

Business logic must depend on capability interfaces, not vendors. Every production, local, test, and experimental implementation is an interchangeable provider selected through configuration and runtime routing.

Initial capabilities include:

- `LLMProvider`: streaming generation, structured generation, cancellation, token usage, and model metadata
- `STTProvider`: streaming or batch transcription, partial results, final results, timestamps, and speaker or channel metadata where available
- `TTSProvider`: low-latency synthesis, streaming audio chunks, cancellation, voice metadata, and playback format information
- `DataStore`: users, interview sessions, events, transcripts, recordings, provider measurements, and evaluations
- `AuthProvider`: sign-in, session validation, and user identity claims
- `DocumentParser`: resume and job-description text extraction and normalization
- `EmbeddingProvider`: document embedding and semantic retrieval
- `VectorStore`: resume and job-description chunk storage and retrieval
- `AudioTransport`: browser media and server-side audio stream abstractions
- `EventBus`: asynchronous domain events, status updates, retries, and optional fan-out
- `StorageProvider`: audio, document, transcript, evaluation, and export file storage
- `ResearchProvider`: optional external company or culture research, with source metadata and explicit trust boundaries
- `ObservabilityProvider`: latency, quality, errors, and provider comparison metrics

Interfaces should define normalized domain payloads, cancellation behavior, timeout behavior, errors, health checks, and capability discovery. Provider-specific request and response formats must remain inside provider adapters.

### 3.1 Provider experimentation and routing

Each capability can have multiple implementations for local, hosted, open-source, and commercial options. Examples include:

- Local STT: Faster-Whisper or Whisper.cpp
- Hosted STT: Groq Whisper
- Local TTS: Kokoro or Piper in CPU-capable containers
- Hosted or remote TTS: any provider that satisfies `TTSProvider`
- Hosted LLM: OpenRouter models, initially including a fast live-interview model and a stronger asynchronous evaluator
- Local or self-hosted LLM: added when hardware and latency permit
- Datastore: Firestore and a local test implementation behind `DataStore`
- Storage: local Docker volume or filesystem implementation, with cloud or S3-compatible implementations added behind `StorageProvider`
- Research: optional model-supported web search or a dedicated research adapter behind `ResearchProvider`

These are candidate implementations, not permanent product commitments. The platform must support A/B testing and controlled comparison using common metrics such as first-byte latency, end-to-end turn latency, quality, interruption behavior, cost, failure rate, and resource consumption. Production selection should be based on measured results rather than vendor assumptions.

## 4. Communication and transport model

The browser and backend use separate transports for separate concerns:

- **WebRTC:** real-time microphone capture and agent audio playback, using media tracks and low-latency media delivery where supported
- **WebSocket:** bidirectional interview control and state communication, including session events, partial transcripts, agent response state, playback commands, interruptions, errors, and provider telemetry needed by the active client
- **HTTP REST API:** authentication-related bootstrap, interview creation, document upload, session history, transcript retrieval, recording download, evaluation retrieval, provider configuration, and administrative operations
- **Event bus or Pub/Sub:** optional backend-only asynchronous communication for transcript processing, recording finalization, evaluation jobs, analytics, retries, and fan-out notifications. The frontend should normally receive user-visible updates through the WebSocket session channel rather than connecting directly to infrastructure Pub/Sub.

A session event model must provide ordering, correlation IDs, idempotency, reconnect behavior, cancellation, and a clear distinction between partial and final results. WebRTC signaling may use the WebSocket or REST layer, but media must not be tunneled through WebSockets unless a specific fallback requires it.

## 5. Interview agent architecture

The live agent is composed of explicit layers:

1. **Context builder:** normalizes the job description, resume facts, role metadata, and interview mode.
2. **Resume and job-description RAG:** retrieves only context relevant to the current topic instead of sending the entire resume on every turn.
3. **Interview state machine:** tracks persona, topics, evidence, unanswered threads, time budget, turn ownership, and completion conditions.
4. **Question planner:** selects the next topic and prepares follow-up hypotheses without locking the session to a pre-generated script.
5. **Live response generator:** produces the substantive interviewer response through `LLMProvider`.
6. **Secondary response layer:** produces short acknowledgements, natural fillers, or factual company and culture explanations grounded in allowed job-description context. This layer may use a smaller, faster model or deterministic templates. Its output is optional and may be spoken, skipped, or cancelled depending on readiness and relevance.
7. **Audio scheduler:** coordinates text streaming, TTS chunking, playback, interruption, and cancellation.

The system may precompute a small set of likely follow-up topics or secondary responses while the candidate is speaking. It must never blindly speak a stale question after an unexpected candidate answer.

## 6. Resume, job-description RAG, and external context

The ingestion pipeline should:

- Parse PDF resumes and pasted job-description text
- Normalize sections and metadata
- Chunk content with source references
- Store embeddings through `EmbeddingProvider` and `VectorStore`
- Retrieve relevant evidence for the current interview topic
- Preserve source attribution for evaluation and debugging
- Apply privacy, retention, and deletion rules

Company information, culture, and policy context should be extracted from the job description and resume where relevant. If the selected LLM or a configured `ResearchProvider` supports web research, it may retrieve additional public metadata. External facts must retain source metadata, remain clearly separated from user-provided content, and never override explicit job-description evidence without an auditable reason.

The live prompt should contain the smallest useful retrieved context. Resume content, job-description content, and external research must remain distinguishable so the agent does not present candidate claims as employer requirements or unverified research as fact.

## 7. Evaluation rubric

Post-interview evaluation must return structured data before generating prose. The rubric is mode-specific and configurable. Initial dimensions may include:

- Communication and clarity
- Role relevance and motivation
- Technical depth or domain understanding
- Evidence of impact and ownership
- Problem solving and reasoning
- Behavioral signals and collaboration
- Interview readiness and response quality

Each dimension has a documented weight, evidence references, score, confidence, and explanation. The weighted result produces the overall score out of 100. Recruiter and technical interviews use different weights and criteria, and the rubric must be versioned with the evaluation.

## 8. Security, privacy, and reliability requirements

The design must support:

- Authenticated access to a user's sessions and files
- A default retention period of 14 days for interview data
- User deletion of the complete interview dataset, including resume, job description, transcript, recording, feedback, derived embeddings, and external-context cache entries
- Encryption in transit and at rest through the selected infrastructure
- Redaction or restricted handling of sensitive resume information
- Provider-specific data-sharing controls
- Rate limits and upload validation, including the 5 MB PDF limit
- Prompt-injection defenses that isolate untrusted document and research content from system and developer instructions
- Content validation and output constraints for secondary responses and external research
- Recovery from provider timeouts, disconnects, and partial audio failures
- Auditable session, provider, research-source, and evaluation versions

The system must run locally through Docker with CPU-only development assumptions, including approximately 4 GB RAM and 250 GB storage. Deployment boundaries must support separate frontend, API, audio, and worker services, with local storage first and remote providers such as S3-compatible storage, Vercel, or Railway added through interfaces and deployment adapters.

## 9. Delivery phases

1. **Domain and capability foundation:** define normalized models, interfaces, errors, provider routing, configuration, and local test providers.
2. **Voice session engine:** build the voice-first interview state machine, persona rules, topic planning, cancellation, and session events.
3. **Document intelligence:** implement job-description parsing, PDF resume parsing, RAG retrieval, prompt-injection defenses, and privacy boundaries.
4. **Provider benchmark harness:** implement local and hosted STT, TTS, and LLM adapters plus repeatable A/B measurements.
5. **Browser transport:** implement WebRTC media, WebSocket events, REST APIs, reconnect behavior, and optional backend Pub/Sub workflows.
6. **Live voice loop:** connect streaming STT, live LLM generation, secondary responses, TTS scheduling, interruption, and recording.
7. **Persistence and identity:** integrate Firebase Authentication, Firestore, `StorageProvider`, retention, deletion, and provider-independent data access.
8. **Post-interview analytics:** compile final transcripts, run versioned rubric evaluation, and render feedback.
9. **Hardening and operations:** security review, load and latency testing, observability, fallback routing, retention controls, and deployment documentation.

All features must follow the repository's SDD workflow: feature specification, implementation plan, marker contract, implementation, unit tests, end-to-end evidence, documentation, and landmine recording where applicable.
