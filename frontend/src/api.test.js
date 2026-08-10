import test from 'node:test'
import assert from 'node:assert/strict'
import { authHeaders, createSessionRequest, historyRequest, sessionResourceRequest, sessionWebSocketUrl, signalingWebSocketUrl, completeSessionRequest } from './api.js'

test('createSessionRequest builds an authenticated JSON request', () => {
  const request = createSessionRequest('technical', 'test-token')
  assert.equal(request.url, '/api/v1/sessions')
  assert.equal(request.init.method, 'POST')
  assert.deepEqual(request.init.headers, {
    Authorization: 'Bearer test-token',
    'Content-Type': 'application/json',
  })
  assert.equal(request.init.body, JSON.stringify({ mode: 'technical' }))
})

test('historyRequest builds an authenticated read request', () => {
  const request = historyRequest('test-token')
  assert.equal(request.url, '/api/v1/history')
  assert.deepEqual(request.init.headers, { Authorization: 'Bearer test-token' })
})

test('authHeaders does not add JSON metadata to read requests', () => {
  assert.deepEqual(authHeaders('test-token'), { Authorization: 'Bearer test-token' })
})

test('sessionResourceRequest keeps resource views on the versioned boundary', () => {
  const request = sessionResourceRequest('abc', 'transcript', 'test-token')
  assert.equal(request.url, '/api/v1/sessions/abc/transcript')
  assert.deepEqual(request.init.headers, { Authorization: 'Bearer test-token' })
})

test('sessionWebSocketUrl builds a ws endpoint for the given session', () => {
  const url = sessionWebSocketUrl('s1', 'tok', { protocol: 'http:', host: 'localhost:3000' })
  assert.match(url, /^ws:\/\/localhost:3000\/ws\/v1\/sessions\/s1\?token=tok$/)
})

test('sessionWebSocketUrl uses wss for https locations', () => {
  const url = sessionWebSocketUrl('s2', 'tok', { protocol: 'https:', host: 'app.example.com' })
  assert.match(url, /^wss:\/\/app\.example\.com\/ws\/v1\/sessions\/s2\?token=tok$/)
})

test('signalingWebSocketUrl builds a signaling endpoint', () => {
  const url = signalingWebSocketUrl('s1', 'tok', { protocol: 'http:', host: 'localhost:3000' })
  assert.match(url, /^ws:\/\/localhost:3000\/ws\/v1\/sessions\/s1\/signaling\?token=tok$/)
})

test('signalingWebSocketUrl uses wss for https locations', () => {
  const url = signalingWebSocketUrl('s2', 'tok', { protocol: 'https:', host: 'app.example.com' })
  assert.match(url, /^wss:\/\/app\.example\.com\/ws\/v1\/sessions\/s2\/signaling\?token=tok$/)
})

test('sessionWebSocketUrl falls back to localhost when host is missing', () => {
  const url = sessionWebSocketUrl('s3', 'tok', { protocol: 'http:' })
  assert.match(url, /^ws:\/\/localhost\/ws\/v1\/sessions\/s3\?token=tok$/)
})

test('completeSessionRequest builds a POST request for the session boundary', () => {
  const request = completeSessionRequest('abc', 'test-token')
  assert.equal(request.url, '/api/v1/sessions/abc/complete')
  assert.equal(request.init.method, 'POST')
  assert.deepEqual(request.init.headers, { Authorization: 'Bearer test-token' })
})
