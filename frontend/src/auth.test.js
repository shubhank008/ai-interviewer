import test from 'node:test'
import assert from 'node:assert/strict'
import { localAuthProvider, validateCredentials } from './auth.js'

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
