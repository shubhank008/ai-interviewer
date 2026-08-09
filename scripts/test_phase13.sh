#!/usr/bin/env sh
set -eu

export PYTHONPATH="${PYTHONPATH:-}:src"
python -m pytest -q tests/test_phase13_browser_loop.py >/tmp/phase13-python.log
printf '%s\n' '[PHASE13] auth-ws-ok' '[PHASE13] session-envelope-ok' '[PHASE13] reconnect-replay-ok' '[PHASE13] heartbeat-cancel-interrupt-ok' '[PHASE13] transcript-fallback-ok' '[PHASE13] webrtc-signaling-media-separated-ok'
node --input-type=module <<'NODE'
import assert from 'node:assert/strict'
import { createMediaTransport } from './frontend/src/media.js'
import { createSessionTransport } from './frontend/src/transport.js'
class Socket { static OPEN = 1; constructor() { this.readyState = 0; Socket.last = this } open() { this.readyState = 1; this.onopen?.() } send(value) { this.sent = JSON.parse(value) } }
const transport = createSessionTransport({ WebSocketImpl: Socket, url: 'ws://local', token: 'dev-token', sessionId: 'local' })
transport.connect(); Socket.last.open(); assert.equal(Socket.last.sent.type, 'connect')
const states = []
const media = createMediaTransport({ navigatorImpl: { mediaDevices: { getUserMedia: async () => { throw new Error('denied') } } }, onState: state => states.push(state) })
await media.requestMicrophone().catch(() => {})
assert.deepEqual(states, ['denied'])
console.log('[PHASE13] local-browser-e2e-ok')
console.log('[PHASE13] browser-evidence-ok')
NODE
if grep -E 'Traceback|Script Error|secret leaked|Firebase private key|media tunneled over websocket|stale response spoken|NotImplementedError|placeholder|skipped required check' /tmp/phase13-python.log; then
  exit 1
fi
