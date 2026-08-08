# Agent Operations & Spec-Driven Development (SDD) Guide

**Agent Identity:** You are an autonomous coding agent operating within an OpenHands environment. Your primary objective is to execute Spec-Driven Development (SDD).

> This file is read automatically by Coding Agent at the start of every session.
> It is the highest-leverage file in the repo: everything here is context the
> agent gets for free, and everything not here has to be rediscovered — usually
> by breaking something first. Keep the **Architecture invariants** section and add to it.



## Where code lives

| Path | What |
|------|------|
| `docs/specs/` | One directory per feature: spec + plan + marker contract (templates provided) |
| `.agents/skills/` | The skills below. Read the one that matches before writing code |

## Which skill, when

Invoke the skill **before** writing the code, not after it breaks.

| Reach for | When |
|---|---|
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

New features follow the SDD loop — invoke `/sdd-feature` when starting one:
spec → plan → **marker contract** → implement → **evidence** → **landmine**.
The last three arrows are the ones that catch this engine: the contract is
written before the code, the evidence is a frame and not a log line for
anything visual, and a surprise that cost an hour gets appended to the
invariants below before the feature closes.

A feature typically walks: `/sdd-feature` → actual feature implementation →
test → `/landmine-check` → commit -> `/no-mistakes`.

## Architecture invariants

Each of these describes a real failure, hurdle or constraint of this project. Violate one and you will spend hours looking in the wrong
place.


## Testing strategy


## Conventions

- Donot use em-dashes or emojis. Comment every method and important code. Maintain upto-date documentation so a new developer can easily takeover. English everywhere.
- Plan ahead using a PLAN.md and keep it updated after every feature or update.
- **When something surprises you, write it down here.** A landmine that costs
  an hour and is not recorded costs that hour again.
