# Spec 008 - Post-interview evaluation

## What the feature is about and what the user experiences

After a completed interview, a candidate can open a results resource containing a stable, structured evaluation. The result is calculated only after the interview ends from the final transcript and the interview setup context. It preserves the selected mode, role, seniority, job description, resume context, and evaluation version so feedback can be understood and reproduced later.

The result shows an overall score out of 100, a concise summary, strengths, weaknesses, concrete improvement recommendations, and a recruiter-style or technical/hiring-manager-style assessment. Each rubric dimension includes its score, normalized weight, confidence, explanation, and references to exact transcript turns or segments. Missing or ambiguous evidence is visible as low confidence or an explicit gap rather than invented candidate claims.

Evaluation is provider-independent. The first implementation is a deterministic local evaluator suitable for offline tests. A future evaluator provider may replace it through a narrow interface without changing the structured result, access control, or retention behavior. Evaluation cannot run for an active interview, cannot expose a hidden score during a live turn, and cannot read another user's interview.

## Numbers

| Value | Number | Source |
|---|---:|---|
| Overall score range | 0-100 | SPEC.md section 7 and DESIGN-FRESH validation bound |
| Recruiter rubric dimensions | 5 | DESIGN-FRESH initial rubric |
| Technical rubric dimensions | 5 | DESIGN-FRESH initial rubric |
| Default transcript evidence limit per dimension | 3 references | DESIGN-FRESH bounded output |
| Default retention period | 14 days | SPEC.md section 8 and Phase 7 contract |

## Out of scope

- Running evaluation while an interview is active.
- Calling a network service, loading model weights, or requiring credentials.
- Generating audio, changing the live interview, or exposing hidden grading to the live agent.
- OCR, semantic LLM judging, plagiarism detection, hiring decisions, or unsupported claims about an employer.
- A frontend implementation. Phase 7 resource contracts remain the UI boundary.

## Acceptance

- [x] Marker contract written (`contracts/log-markers.md`) BEFORE implementation
- [x] Pure deterministic evaluator unit tests cover both modes and edge cases
- [x] Real mock evaluation path exercises transcript, context, evaluator, persistence, and results resource
- [x] Scores are bounded and weights normalize deterministically
- [x] Missing and ambiguous evidence is represented safely
- [x] Failed, cancelled, empty, and active interviews are rejected safely
- [x] Access control and retention boundaries remain enforced through persistence interfaces
- [x] Lint, type, compile, and full available test gates pass
- [x] Durable surprises are recorded in `AGENTS.md` if discovered
