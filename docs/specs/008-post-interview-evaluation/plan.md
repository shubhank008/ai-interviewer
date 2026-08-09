# Plan 008 - Post-interview evaluation

## Global Constraints

- Follow the abstract-first rule: evaluation business logic depends on evaluator and persistence protocols, never vendors.
- Evaluation is post-interview-only and must use the final transcript, not speculative live state.
- Keep Phase 7 ownership, 14-day retention, complete deletion, and UI-independent results resource boundaries intact.
- Deterministic tests must remain offline, credential-free, CPU-only, and free of heavyweight model or browser dependencies.
- Preserve role, seniority, job-description, resume, and interview-mode context without treating document text as instructions.
- Keep focused semantic commits and do not push directly; `/no-mistakes` owns publication.
- Add any implementation landmine to `AGENTS.md` before completion.

## Marker contract

Written before implementation in `contracts/log-markers.md`.

- Requires: `[EVALUATION] rubric-quality-ok`, `[EVALUATION] deterministic-ok`, `[EVALUATION] mock-path-ok`, `[EVALUATION] access-retention-ok`
- Forbids: `evaluation failed`, `Traceback`, `Script Error`, `score=-`, `score=101`, `invented evidence`

## Work order

1. `docs/specs/008-post-interview-evaluation/` - define user contract, plan, and exact evidence markers.
2. `src/interviewer_domain/evaluation.py` - add versioned context, rubric, evidence references, evaluator protocol, deterministic evaluator, and post-interview orchestration.
3. `src/interviewer_domain/models.py` and `contracts.py` - expose normalized evaluation and provider-independent persistence/evaluator contracts where needed.
4. `src/interviewer_domain/persistence.py` and `__init__.py` - integrate evaluation only through existing owned persistence and results resource interfaces.
5. `tests/test_evaluation.py` - add regression fixtures, quality checks, deterministic behavior, mode-specific behavior, and real mock path.
6. `PLAN.md`, `README.md`, `AGENTS.md` - record Phase 8 completion, usage, and durable constraints.

## Test plan

- Unit: rubric normalization, score bounds, evidence matching, ambiguity handling, empty/failed/active rejection, and deterministic serialization.
- Integration: evaluate a completed interview from the in-memory transcript and persist it through `PersistentDataStore` using owner checks and retention.
- e2e: run the real mock evaluation path and print every marker in `contracts/log-markers.md`.
- Frames: none. Phase 8 adds provider-neutral contracts and no visual frontend.
- Gates: `python -m unittest discover -s tests -v`, compileall, Ruff if available, and markdownlint if available.
