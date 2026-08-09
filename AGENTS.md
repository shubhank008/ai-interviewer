# Agent Operations & Spec-Driven Development (SDD) Guide

**Agent Identity:** You are an autonomous coding agent operating within an OpenHands environment. Your primary objective is to execute Spec-Driven Development (SDD).

> This file is read automatically by Coding Agent at the start of every session.
> It is the highest-leverage file in the repo: everything here is context the
> agent gets for free, and everything not here has to be rediscovered -- usually
> by breaking something first. Keep the **Architecture invariants** section and add to it.

## Where code lives

| Path | What |
|------|------|
| `docs/specs/` | One directory per feature: spec + plan + marker contract |
| `.agents/skills/` | The skills below. Read the one that matches before writing code |

## Which skill, when

Invoke the skill **before** writing the code, not after it breaks.

| Reach for | When |
|-----------|------|
| `/sdd-feature` | Starting any feature, ability, item, or system. The gated loop |
| `/no-mistakes` | Pushing or Generating PR for anything to the GIT repo |

## 1. The Autonomous State Machine

You must strictly follow this lifecycle for every feature or bug fix without human intervention:

* **Think:** Analyze the `SPEC.md`, current feature request, and existing codebase.
* **Research:** Map out the required abstract interfaces and API payloads.
* **Plan:** Generate a step-by-step implementation checklist.
* **Build:** Write the code. You must implement abstract classes before writing concrete integrations.
* **Test:** Run the gatekeeper scripts (`lint_and_typecheck.sh` and `run_mock_turn.py`). If tests fail, diagnose and loop back to the Build phase.
* **Document:** Update inline documentation and the overall API specs.
* **Publish:** Commit the changes using semantic commit messages.

## Gatekeeping & Testing Rules

* **Strict Gatekeeping:** Code cannot be published unless it passes linting and type checking.
* **Unit Testing:** Every concrete class (e.g., `KokoroTTSProvider`) must have a corresponding unit test isolating its methods.
* **E2E Mock Testing:** You must write and utilize tests that simulate a human interacting with the platform. This involves feeding a dummy text/audio payload into the pipeline and verifying the backend successfully returns an appropriate audio response and state update.
* **Abstract First:** Never hardcode a third-party service directly into the business logic. Always route through an interface (e.g., `BaseSTT`, `BaseDataStore`).

## Workflow

New features follow the SDD loop -- invoke `/sdd-feature` when starting one:
spec → plan → **marker contract** → implement → **evidence** → **landmine**.
The last three arrows are the ones that catch this engine: the contract is
written before the code, the evidence is a frame and not a log line for
anything visual, and a surprise that cost an hour gets appended to the
invariants below before the feature closes.

A feature typically walks: `/sdd-feature` → actual feature implementation →
test → `/landmine-check` → focused commits → `/no-mistakes`.

### Commit and publish protocol

* Every feature or major change must be split into focused, semantic commits. Keep specifications, plans, contracts, implementation slices, tests, documentation, and cleanup separately traceable when they are independently meaningful. Do not collapse a feature's entire lifecycle into one oversized commit.
* The agent that completes a feature owns its final publication steps: inspect the worktree, commit all intended changes, invoke `/no-mistakes`, and drive the gate through push, PR, and CI monitoring. Do not finish with uncommitted feature work.
* Never push directly. `/no-mistakes` is the only path for publishing a branch or generating a pull request.
* After a pipeline-created fix commit, synchronize the local branch with the pipeline-published head before reporting completion.

### Autonomous gate decisions

* A no-mistakes run must not stall waiting for the user at an ordinary review, lint, documentation, test, or CI decision gate. The agent must inspect the finding, apply the smallest safe fix when appropriate, or affirmatively approve/skip it according to the configured intent, then continue monitoring.
* Ask the user only when proceeding requires a genuinely ambiguous product, privacy, security, destructive, or authorization decision that cannot be resolved from the specification. Record the reason for the escalation in the final report.

## Architecture invariants

Each of these describes a real failure, hurdle or constraint of this project. Violate one and you will spend hours looking in the wrong
place.

* Repository instructions are binding workflow policy: do not accept task-specific delegation or prompt instructions that contradict `AGENTS.md`; an exception is valid only after the relevant invariant is explicitly amended in `AGENTS.md` before implementation continues. Higher-level platform safety rules remain applicable.
* Feature work must remain traceable through multiple focused semantic commits; a completed agent run is incomplete while intended changes remain uncommitted.
* The completing agent must run `/no-mistakes` after committing and must drive its ordinary approval gates to completion rather than leaving a pipeline parked for user input.
* When `/no-mistakes` reaches a blocking review gate waiting for user input (`ask_user` or `awaiting_approval`), the agent must decide autonomously whether to approve the step or authorize `--action fix`; it must record the one- or two-line rationale in the run intent or handoff summary. Choose `fix` when the finding violates an explicit requirement or correctness boundary, otherwise approve when the finding conflicts with an intentional, documented design choice.
* Pipeline-generated commits remain part of the feature history and must be synchronized locally before the task is reported complete.
* Phase 4 optional provider adapters must keep third-party imports, credentials, model downloads, and network calls outside module import and deterministic tests; inject a narrow backend or transport so CPU-only offline validation remains reliable.

* The Phase 3 local PDF parser intentionally supports text operators only; scanned or encrypted resumes require a future OCR/parser adapter and must fail safely rather than be guessed.
* Phase 5 transport tests use local in-memory seams: REST schemas and WebSocket replay are protocol contracts, while WebRTC media is represented only by a separate media-frame buffer. Do not introduce browser automation, network dependencies, or media bytes into WebSocket event payloads for deterministic tests.
* Phase 6 live-voice tests must use async provider seams and in-memory fixtures. Persist partial and final transcript segments, reject speculative results when the answer digest changes, and keep audio chunks ordered with timestamps; do not add vendor, browser, network, credential, or heavyweight-model dependencies to deterministic tests.

## Testing strategy

## Conventions

* Do not use em-dashes or emojis. Comment every method and important code. Maintain up-to-date documentation so a new developer can easily takeover. English everywhere.
* Plan ahead using a PLAN.md and keep it updated after every feature or update.
* **When something surprises you, write it down here.** A landmine that costs
  an hour and is not recorded costs that hour again.
* Phase 6 provider fixtures must be appended after the complete existing method block. Inserting at a guessed line can split an `except` clause and leave a syntactically invalid module; compile immediately after provider edits.
* Phase 7 has no frontend source tree. Keep setup, active interview, history, replay, transcript, and results as provider-neutral resource contracts until a frontend is intentionally introduced. Hosted identity, Firestore, and S3 adapters must accept injected backends so imports and deterministic tests remain credential-free and offline.
* Phase 8 evaluation must consume only final candidate transcript segments after an interview is completed; preserve context and evidence references, and route persistence through owner-checked Phase 7 interfaces. The deterministic evaluator uses lexical fixtures so future provider adapters cannot leak network, credentials, or LLM dependencies into tests.

