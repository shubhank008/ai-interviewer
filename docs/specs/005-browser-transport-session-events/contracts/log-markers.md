# Phase 5 marker contract

The deterministic transport test harness must print these exact lines on success:

```text
[REST] schemas validated
[WS] ordered session events delivered
[WS] reconnect replay correlated
[WEBRTC] signaling validated
[TRANSPORT] media and control separated
```

The harness must not print or raise these failure patterns:

```text
Script Error
Traceback
AssertionError
media tunneled over websocket
```

Markers are evidence of executable local behavior, not a substitute for assertions. No browser frame is required because this phase adds seams and protocol logic rather than a rendered UI.
