import test from 'node:test'
import assert from 'node:assert/strict'
import { localAuthProvider, configuredAuthProvider, validateCredentials } from './auth.js'

function storage() {
  const values = new Map()
  return { getItem: key => values.get(key) || null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) }
}

test('local auth signs in and restores the same profile', async () => {
  const provider = localAuthProvider(storage())
  const signedIn = await provider.signIn('candidate@example.com')
  assert.equal(signedIn.provider, 'local')
  assert.deepEqual(await provider.restore(), signedIn)
  await provider.signOut()
  assert.equal(await provider.restore(), null)
})

test('credential validation rejects an address without a domain', () => {
  assert.equal(validateCredentials('candidate'), 'Enter a valid email address.')
  assert.equal(validateCredentials('candidate@example.com'), '')
})

test('configuredAuthProvider delegates to the adapter and returns null for falsy', () => {
  assert.equal(configuredAuthProvider(null), null)
  assert.equal(configuredAuthProvider(undefined), null)
  const calls = []
  const adapter = {
    restore: async () => { calls.push('restore'); return { email: 'a@b.com' } },
    signIn: async email => { calls.push('signIn'); return { email } },
    signUp: async email => { calls.push('signUp'); return { email } },
    signOut: async () => { calls.push('signOut') },
  }
  const provider = configuredAuthProvider(adapter)
  assert.ok(provider)
  assert.equal(typeof provider.restore, 'function')
  assert.equal(typeof provider.signIn, 'function')
  assert.equal(typeof provider.signUp, 'function')
  assert.equal(typeof provider.signOut, 'function')
})
