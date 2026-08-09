# Spec 007 - Persistence, user identity, and user experience

## What the feature is about and what the user experiences

An authenticated candidate can create and access only their own interview records. The setup flow accepts a job description and an optional PDF resume, validates the upload before persistence, and starts a voice-first interview. Afterward, the candidate can view a history list, open an interview, replay its recording, inspect its transcript, and view the available results through stable API/domain contracts.

The persistence layer records interview metadata, lifecycle events, transcript segments, recordings, evaluations, uploaded documents, and derived references without coupling business logic to Firebase, Firestore, a filesystem, or S3. Local development and deterministic tests use injected in-memory or filesystem seams. Firebase Authentication, Firestore, and S3-compatible adapters are optional and never initialize credentials or make network calls during import or deterministic tests.

Access checks require an authenticated identity and an owning user ID. Interview data carries retention metadata and is unavailable after the retention boundary. A user can delete an interview and all associated metadata and opaque artifacts as one operation. Sensitive content remains behind datastore and storage boundaries.

## Numbers

| Value | Number | Source |
|---|---:|---|
| Default retention period | 14 days | SPEC.md, section 8 |
| Maximum resume upload | 5 MB / 5,242,880 bytes | SPEC.md, sections 2.1 and 8; byte conversion DESIGN-FRESH |
| Initial rate-limit window | 60 seconds | DESIGN-FRESH |
| Initial requests per rate-limit window | 60 | DESIGN-FRESH |
| Maximum persisted document size | 5 MB | SPEC.md, section 2.1 |

## Out of scope

- A new frontend application or browser automation. No established frontend tree exists in this repository, so this slice defines UI-independent API/domain contracts.
- Firebase project provisioning, credentials, network calls, deployment configuration, and cloud integration tests.
- Final evaluation generation or rubric weighting, which belongs to Phase 8.
- OCR, scanned PDF support, external research, and media transcoding.

## Acceptance

- [x] Marker contract written before implementation
- [x] Auth, datastore, and storage capability seams remain provider-independent
- [x] Firebase Authentication, Firestore, local filesystem, and S3-compatible adapters are injectable and import-safe
- [x] Ownership authorization isolates users and supports complete interview deletion
- [x] Retention metadata is stored and expired records are rejected and purgeable
- [x] Resume upload validation enforces PDF type and the 5 MB limit
- [x] Rate limiting is deterministic and injectable
- [x] Tests cover concrete adapters, authorization, retention, deletion, uploads, rate limits, and a real mock persistence path
- [x] Markers and forbidden-output checks pass
- [x] Documentation and durable landmines are updated
