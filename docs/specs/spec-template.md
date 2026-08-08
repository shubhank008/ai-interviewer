# Spec NNN -  <feature name>

<!-- Copy this directory pattern per feature:
       docs/specs/NNN-feature-name/spec.md        (this file)
       docs/specs/NNN-feature-name/plan.md        (from plan-template.md)
       docs/specs/NNN-feature-name/contracts/log-markers.md
     The `/sdd-feature` skill walks the full loop. -->

## What the feature is about and what the user experiences

Describe the feature from the user's side — what they see, press, and feel.
No implementation detail here.

## Numbers

| Value | Number | Source |
|---|---|---|
| e.g. value-1 | 1200 | DESIGN-FRESH |
| e.g. value-2 | 8 s | <link/citation, or DESIGN-FRESH> |

Every number carries a source. `DESIGN-FRESH` means "we invented this" - that
is fine, but it must be *visibly* an invention, so a later balance and optimization pass knows
what is sacred and what is guessable.

## Out of scope

What this feature deliberately does not do.

## Acceptance

- [ ] Marker contract written (`contracts/log-markers.md`) BEFORE implementation
- [ ] Pure logic unit-test created and tested
- [ ] e2e run prints every required marker, no failure patterns
- [ ] Visual features: frame evidence reviewed, not just logs
- [ ] Any engine surprise recorded in `AGENTS.md` invariants
