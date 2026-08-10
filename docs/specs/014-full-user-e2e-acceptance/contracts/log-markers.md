# Phase 14 marker contract

The Phase 14 executable gate must emit these exact markers after behavior assertions pass:

```text
[PHASE14] auth-setup-ok
[PHASE14] pdf-rag-ok
[PHASE14] providers-separated-ok
[PHASE14] browser-media-loop-ok
[PHASE14] interruption-reconnect-ok
[PHASE14] persisted-evaluation-ok
[PHASE14] replay-deletion-ok
[PHASE14] negative-journeys-ok
[PHASE14] configured-integrations-report-ok
[PHASE14] evidence-artifacts-ok
```

The gate must fail if output or generated diagnostics contains any of:

```text
Traceback
Script Error
secret leaked
Firebase private key
media tunneled over websocket
stale response spoken
NotImplementedError
placeholder
skipped required check
EXPECTED_STRING_SUBSTITUTION
```

Markers are evidence summaries only. Each marker is asserted by a behavior-level test before it is printed. Configured integration markers mean the report was produced and each unavailable integration has an explicit reason; they do not claim that an absent provider was exercised.
