# Spec 017 - Live document parsing and adaptive interview ending

## What the feature is about and what the user experiences

During interview setup, a candidate resume PDF can be parsed by a configured vision-capable model when the local text parser is insufficient or when the live profile selects hosted parsing. The model returns faithful resume content and bounded structured fields. Resume content remains untrusted data: instructions inside the document never become platform instructions, and uncertainty is preserved instead of invented. If hosted parsing is unavailable, the local parser remains an explicit development fallback; production does not silently claim hosted parsing succeeded.

During an interview, every completed candidate response receives a structured continuation decision. An unsuitable candidate can end immediately after the current response is safely persisted. Otherwise the interview continues until the model requests an end, the hard wall-clock limit, or the maximum interviewer-turn limit is reached. Explicit stop, cancellation, provider failure, and timeout remain terminal conditions. The final lifecycle event, session result, and rehearsal transcript identify the end reason and triggering decision.

## Numbers

| Value | Number | Source |
|---|---:|---|
| Default document model | `gemma4` | PLAN.md P0.2 / DESIGN-FRESH configuration default |
| OpenRouter document request timeout | 60 seconds | AGENTS.md Phase 16 locked provider policy |
| Maximum interview wall-clock duration | 30 minutes | PLAN.md P0.3 / DESIGN-FRESH hard limit |
| Maximum interviewer turns | 10 | PLAN.md P0.3 / DESIGN-FRESH hard limit |
| Maximum structured resume fields | 12 | DESIGN-FRESH bounded adapter contract |
| Maximum extracted resume text | 12000 characters | DESIGN-FRESH bounded adapter contract |

## Out of scope

- OCR implementation, browser automation, WebRTC, TURN, or Firebase browser identity.
- Treating hosted parsing as available without configured credentials and an exercised transport.
- Replacing the local parser for deterministic tests or silently falling back in production.
- Letting document text alter system/developer instructions.
- A new interviewer model provider separate from the existing LLM capability boundary.

## Acceptance

- [x] Marker contract written before implementation.
- [x] Vision parsing uses the existing document parser interface and injected OpenRouter transport.
- [x] Structured parser output is validated, bounded, attributed, and safe on malformed/unavailable responses.
- [x] `DOCUMENT_LLM_MODEL` defaults to `gemma4`, is documented, and appears in diagnostics/readiness metadata without secrets.
- [x] Every completed candidate turn produces a validated end decision.
- [x] LLM ending, 30-minute, 10-turn, explicit stop, cancellation, timeout, and provider failure paths are tested.
- [x] Phase 16 rehearsal uses the same policy, clock seam, limits, and end-reason evidence as the session engine.
- [x] Focused tests, lint/typecheck, and mock-turn gates pass.
- [x] Any implementation surprise is recorded in `AGENTS.md` invariants.
