# Spec 015 - Opt-in provider integration suite

## What the feature is about and what the user experiences

An operator can select one or more explicitly configured integration profiles and run the same capability paths used by the interview application against real local models, hosted services, Firebase, object storage, and configured browser media infrastructure. The report clearly distinguishes exercised, skipped, and failed integrations. A missing credential or local model is an honest skip with a precise safe reason, never a deterministic local pass.

When configured, the operator can verify authenticated claims and owner isolation, upload and delete a PDF and interview artifacts, transcribe real audio with partial and final timestamps, synthesize playable audio, stream and cancel an LLM response, exercise fallback, retry, timeout, rate-limit, and quota behavior, and run the browser voice boundary. Measurements include provider, model, version, region, device, timing, cost estimate, quality, errors, and limitations without sensitive payloads.

## Numbers

| Value | Number | Source |
|---|---:|---|
| Resume upload limit | 5 MB | Existing `SPEC.md` product requirement |
| Default retention | 14 days | Existing `SPEC.md` product requirement |
| Integration timeout | 30 seconds | DESIGN-FRESH, configurable |
| Evidence schema version | 1 | DESIGN-FRESH |
| Maximum retry attempts | 2 | DESIGN-FRESH, configurable |

## Out of scope

- Automatic model downloads, credentials, registry changes, or provider selection for production.
- Treating deterministic fixtures, injected fake backends, marker-only checks, or skipped integrations as real readiness.
- Committing evidence, secrets, personal data, model weights, or browser recordings.
- Certifying TURN, Firebase, or hosted provider behavior when the deployment does not supply safe configuration.

## Acceptance

- [x] Marker contract written before implementation
- [ ] Concrete provider transports and adapters use existing capability interfaces
- [ ] Every selected profile has behavior-level integration coverage and explicit negative cases
- [ ] Missing configuration skips with a precise redacted reason; configured failures fail
- [ ] JSON, Markdown, and HTML evidence includes metadata and limitations without sensitive data
- [ ] Offline gates remain credential-free and deterministic
- [ ] Documentation, environment examples, roadmap, and durable landmines are accurate
