import test from 'node:test'
import assert from 'node:assert/strict'
import { createMediaTransport } from './media.js'
import { createSessionTransport } from './transport.js'

class FakeSocket {
  static OPEN = 1
  constructor() { this.readyState = 0; FakeSocket.last = this }
  open() { this.readyState = 1; this.onopen?.() }
  close() { this.readyState = 3; this.onclose?.() }
  send(value) { this.sent = JSON.parse(value) }
}

test('browser transport sends normalized connect and preserves cursor', () => {
  const events = []
  const transport = createSessionTransport({ WebSocketImpl: FakeSocket, url: 'ws://local', token: 'dev-token', sessionId: 's1', onEvent: event => events.push(event) })
  transport.connect(); FakeSocket.last.open()
  assert.equal(FakeSocket.last.sent.type, 'connect')
  FakeSocket.last.onmessage({ data: JSON.stringify({ type: 'heartbeat', sequence: 3, payload: {} }) })
  assert.equal(transport.getCursor(), 3)
  assert.equal(events.at(-1).type, 'heartbeat')
})

test('media transport reports microphone denial and tears down tracks', async () => {
  const states = []
  const media = createMediaTransport({ navigatorImpl: { mediaDevices: { getUserMedia: async () => { throw new Error('denied') } } }, onState: state => states.push(state) })
  await assert.rejects(media.requestMicrophone(), /denied/)
  assert.deepEqual(states, ['denied'])
})
