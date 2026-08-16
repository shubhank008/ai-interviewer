# Marker contract

## Required success markers

- `[DOC17] vision-parser-contract-ok`
- `[DOC17] document-source-boundary-ok`
- `[DOC17] document-model-config-ok`
- `[END17] llm-directed-ending-ok`
- `[END17] time-limit-ending-ok`
- `[END17] turn-limit-ending-ok`
- `[END17] explicit-stop-ending-ok`
- `[END17] provider-failure-ending-ok`
- `[END17] rehearsal-parity-ok`

## Forbidden evidence

Evidence must not contain API keys, bearer tokens, raw OpenRouter payloads, resume text, transcript text, audio bytes, or personal data. It must not claim a skipped or unconfigured provider was exercised. It must not contain `Traceback`, `Script Error`, or an unbounded model response accepted as a valid structured decision.

## End-decision contract

A valid decision contains only a boolean `should_end`, a bounded `reason` selected from the documented end reasons, and a bounded rationale. Malformed, missing, or out-of-range decision data is a provider failure and never silently treated as continuation or completion.
