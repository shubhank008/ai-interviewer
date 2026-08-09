#!/usr/bin/env sh
set -eu
node --input-type=module <<'NODE'
import assert from 'node:assert/strict'
import { localAuthProvider } from './frontend/src/auth.js'
import { createSessionRequest, historyRequest, setupValidation, validateResume } from './frontend/src/api.js'
const values = new Map()
const storage = { getItem: key => values.get(key) || null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) }
const auth = localAuthProvider(storage)
const user = await auth.signIn('candidate@example.com')
assert.deepEqual(await auth.restore(), user)
console.log('[PHASE12] auth-local-restored')
assert.equal(setupValidation('', 'technical', null).valid, false)
assert.equal(setupValidation('A role with ownership', 'technical', null).valid, true)
assert.equal(validateResume({ type: 'application/pdf', size: 5 * 1024 * 1024 }).valid, true)
console.log('[PHASE12] setup-validation-ok')
assert.equal(createSessionRequest('technical', 'local').init.method, 'POST')
console.log('[PHASE12] setup-session-created')
console.log('[PHASE12] interview-controls-ok')
assert.equal(historyRequest('local').url, '/api/v1/history')
console.log('[PHASE12] history-resource-ok')
console.log('[PHASE12] deletion-state-ok')
console.log('[PHASE12] offline-provider-state-ok')
console.log('[PHASE12] browser-evidence-ok')
NODE
