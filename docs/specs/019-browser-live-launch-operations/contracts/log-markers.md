# Phase 19 marker contract

## Required browser markers

- `[BROWSER19] auth-restored`
- `[BROWSER19] auth-sign-in`
- `[BROWSER19] auth-sign-up`
- `[BROWSER19] auth-google-sign-in`
- `[BROWSER19] auth-sign-out`
- `[BROWSER19] media-ready`
- `[BROWSER19] media-denied`
- `[BROWSER19] media-closed`
- `[BROWSER19] websocket-connecting`
- `[BROWSER19] websocket-connected`
- `[BROWSER19] websocket-reconnecting`
- `[BROWSER19] websocket-failed`
- `[BROWSER19] websocket-disconnected`

## Required deployment markers

- `[OPS19] compose-healthchecks-ok`
- `[OPS19] production-origins-ok`
- `[OPS19] operational-config-ok`

## Forbidden evidence patterns

- Firebase ID tokens, bearer tokens, API keys, passwords, private keys, raw audio, provider payloads, or personal data.
- `[BROWSER19] owner-isolation-ok`
- `[OPS19] live-launch-ready`
