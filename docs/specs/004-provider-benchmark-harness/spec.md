# Spec 004 - Provider Implementations and Benchmark Harness

## What the feature is about and what the user experiences

Operators can run the same voice-turn workload against interchangeable STT, LLM, and TTS providers without changing interview business logic. A local deterministic mode works without network access, credentials, model downloads, or GPU hardware. Optional Faster-Whisper, Piper or Kokoro, and OpenRouter adapters report the same health, capability, cancellation, timeout, and error shapes when dependencies are installed. A configured fallback can continue a turn when the preferred provider is unavailable.

A benchmark report compares providers using repeatable inputs and records first-byte latency, end-to-end latency, quality, estimated cost, failures, and resource-use samples. Unavailable optional providers are reported as skipped or failed measurements rather than preventing local tests from running.

## Numbers

| Value | Number | Source |
|---|---:|---|
| Benchmark warm-up turns | 1 | DESIGN-FRESH |
| Default measured turns | 3 | DESIGN-FRESH |
| Default benchmark timeout | 30 seconds | DESIGN-FRESH |
| Maximum benchmark input bytes | 1 MiB | DESIGN-FRESH |
| Default fallback attempts | 1 | DESIGN-FRESH |

## Out of scope

- Downloading model weights during tests or requiring a GPU.
- Selecting a permanent production vendor from benchmark results.
- Browser WebRTC/WebSocket transport, persistence, authentication, or UI.
- Sending credentials, candidate data, or benchmark fixtures to external services unless an operator explicitly enables an adapter.
- Claiming objective speech quality from a deterministic substitute; local quality is a documented fixture score.

## Acceptance

- [x] Marker contract written before implementation.
- [x] Capability interfaces remain the only dependency of turn business logic.
- [x] Concrete Faster-Whisper, Piper/Kokoro-compatible, and OpenRouter adapters have unit coverage with injected local fakes.
- [x] Health and capability results are normalized, and unavailable optional dependencies fail safely.
- [x] Fallback routing is configurable and preserves normalized provider errors.
- [x] A deterministic benchmark path measures all required dimensions without network access.
- [x] A real mock benchmark path prints every required marker and no forbidden failure pattern.
- [x] README and PLAN describe setup, optional dependencies, and limitations.
- [x] Durable surprises are recorded in AGENTS.md.
