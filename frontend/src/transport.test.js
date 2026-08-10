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

test('media negotiate creates a peer connection and adds tracks when stream is present', async () => {
  const tracks = [{ stop: () => {} }]
  const stream = { getTracks: () => tracks }
  const addedTracks = []
  const fakePeer = { addTrack: (track, s) => { addedTracks.push({ track, stream: s }) }, close: () => {} }
  const PeerConnectionFactory = function () { return fakePeer }
  const media = createMediaTransport({
    navigatorImpl: { mediaDevices: { getUserMedia: async () => stream } },
    peerConnectionFactory: PeerConnectionFactory,
  })
  await media.requestMicrophone()
  const peer = await media.negotiate()
  assert.equal(peer, fakePeer)
  assert.equal(addedTracks.length, 1)
  assert.equal(addedTracks[0].track, tracks[0])
})

test('media negotiate throws when peerConnectionFactory is missing', async () => {
  const media = createMediaTransport({ peerConnectionFactory: null })
  await assert.rejects(media.negotiate(), /webrtc unavailable/)
  assert.equal(media.getState(), 'unavailable')
})

test('media teardown stops stream tracks and closes peer', () => {
  const stopped = []
  const closed = []
  const stream = { getTracks: () => [{ stop: () => stopped.push(true) }] }
  const fakePeer = { close: () => closed.push(true), addTrack: () => {} }
  const PeerConnectionFactory = function () { return fakePeer }
  const states = []
  const media = createMediaTransport({
    navigatorImpl: { mediaDevices: { getUserMedia: async () => stream } },
    peerConnectionFactory: PeerConnectionFactory,
    onState: state => states.push(state),
  })
  media.teardown()
  assert.deepEqual(states, ['closed'])
})

test('transport disconnect sends close and sets disconnected state', () => {
  const events = []
  const transport = createSessionTransport({ WebSocketImpl: FakeSocket, url: 'ws://local', token: 't', sessionId: 's1', onEvent: e => events.push(e) })
  transport.connect(); FakeSocket.last.open()
  transport.disconnect()
  assert.equal(FakeSocket.last.sent.type, 'close')
  assert.equal(transport.getState(), 'disconnected')
})

test('transport connect sets failed state when WebSocketImpl is missing', () => {
  const events = []
  const transport = createSessionTransport({ WebSocketImpl: null, url: 'ws://local', token: 't', sessionId: 's1', onEvent: e => events.push(e) })
  transport.connect()
  assert.equal(transport.getState(), 'failed')
})

test('transport send returns false when socket is not open', () => {
  const transport = createSessionTransport({ WebSocketImpl: FakeSocket, url: 'ws://local', token: 't', sessionId: 's1' })
  const result = transport.send('heartbeat')
  assert.equal(result, false)
})

test('transport heartbeat and cancel send correct types', () => {
  const transport = createSessionTransport({ WebSocketImpl: FakeSocket, url: 'ws://local', token: 't', sessionId: 's1' })
  transport.connect(); FakeSocket.last.open()
  transport.heartbeat()
  assert.equal(FakeSocket.last.sent.type, 'heartbeat')
  transport.cancel()
  assert.equal(FakeSocket.last.sent.type, 'cancel')
})

test('transport interrupt sends interrupt type', () => {
  const transport = createSessionTransport({ WebSocketImpl: FakeSocket, url: 'ws://local', token: 't', sessionId: 's1' })
  transport.connect(); FakeSocket.last.open()
  transport.interrupt()
  assert.equal(FakeSocket.last.sent.type, 'interrupt')
})

test('transport signaling wraps payload and correlation_id', () => {
  const transport = createSessionTransport({ WebSocketImpl: FakeSocket, url: 'ws://local', token: 't', sessionId: 's1' })
  transport.connect(); FakeSocket.last.open()
  transport.signaling({ payload: { sdp: 'x' }, correlation_id: 'sig-1' })
  assert.equal(FakeSocket.last.sent.type, 'signaling')
  assert.deepEqual(FakeSocket.last.sent.payload, { sdp: 'x' })
  assert.equal(FakeSocket.last.sent.correlation_id, 'sig-1')
})

test('transport onclose triggers reconnecting when attempts remain', () => {
  const events = []
  const transport = createSessionTransport({ WebSocketImpl: FakeSocket, url: 'ws://local', token: 't', sessionId: 's1', maxReconnects: 2, onEvent: e => events.push(e) })
  transport.connect(); FakeSocket.last.open()
  FakeSocket.last.close()
  const states = events.filter(e => e.type === 'connection').map(e => e.payload.state)
  assert.ok(states.includes('reconnecting'))
})

test('transport onclose sets failed after exhausting reconnects', () => {
  const events = []
  const transport = createSessionTransport({ WebSocketImpl: FakeSocket, url: 'ws://local', token: 't', sessionId: 's1', maxReconnects: 0, onEvent: e => events.push(e) })
  transport.connect(); FakeSocket.last.open()
  FakeSocket.last.close()
  const states = events.filter(e => e.type === 'connection').map(e => e.payload.state)
  assert.ok(states.includes('failed'))
})

test('transport onerror triggers reconnecting when not intentional', () => {
  const events = []
  const transport = createSessionTransport({ WebSocketImpl: FakeSocket, url: 'ws://local', token: 't', sessionId: 's1', onEvent: e => events.push(e) })
  transport.connect(); FakeSocket.last.open()
  FakeSocket.last.onerror()
  const states = events.filter(e => e.type === 'connection').map(e => e.payload.state)
  assert.ok(states.includes('reconnecting'))
})

test('transport setEventHandler replaces the active handler', () => {
  const first = []
  const second = []
  const transport = createSessionTransport({ WebSocketImpl: FakeSocket, url: 'ws://local', token: 't', sessionId: 's1', onEvent: e => first.push(e) })
  transport.connect(); FakeSocket.last.open()
  const firstCount = first.length
  transport.setEventHandler(e => second.push(e))
  FakeSocket.last.onmessage({ data: JSON.stringify({ type: 'test', payload: {} }) })
  assert.equal(first.length, firstCount)
  assert.equal(second.length, 1)
})

test('transport reconnecting state is set on second connect after close', () => {
  const events = []
  const transport = createSessionTransport({ WebSocketImpl: FakeSocket, url: 'ws://local', token: 't', sessionId: 's1', onEvent: e => events.push(e) })
  transport.connect(); FakeSocket.last.open()
  FakeSocket.last.close()
  transport.connect()
  const states = events.filter(e => e.type === 'connection').map(e => e.payload.state)
  assert.ok(states.includes('reconnecting'))
})
