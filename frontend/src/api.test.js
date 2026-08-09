import test from 'node:test'
import assert from 'node:assert/strict'
import { authHeaders, createSessionRequest, historyRequest } from './api.js'

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
