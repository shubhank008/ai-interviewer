import test from 'node:test'
import assert from 'node:assert/strict'
import { localAuthProvider, configuredAuthProvider, firebaseAuthProvider, validateCredentials } from './auth.js'

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

test('configured auth delegates Google sign-in', async () => {
  const calls = []
  const provider = configuredAuthProvider({
    restore: async () => null,
    signIn: async () => null,
    signUp: async () => null,
    signInWithGoogle: async () => { calls.push('google'); return { provider: 'firebase' } },
    signOut: async () => {},
  })
  assert.deepEqual(await provider.signInWithGoogle(), { provider: 'firebase' })
  assert.deepEqual(calls, ['google'])
})

test('local auth signs up and persists the profile', async () => {
  const provider = localAuthProvider(storage())
  const signedUp = await provider.signUp('new@example.com')
  assert.equal(signedUp.provider, 'local')
  assert.deepEqual(await provider.restore(), signedUp)
})

test('firebaseAuthProvider restore normalizes the authenticated user', async () => {
  const mockUser = { uid: 'fb-1', email: 'firebase@test.com', getIdToken: async () => 'fb-token' }
  const provider = firebaseAuthProvider({}, async () => ({
    auth: {},
    onAuthStateChanged: (auth, cb) => { Promise.resolve().then(() => cb(mockUser)); return () => {} },
  }))
  const user = await provider.restore()
  assert.equal(user.uid, 'fb-1')
  assert.equal(user.email, 'firebase@test.com')
  assert.equal(user.provider, 'firebase')
  assert.equal(user.token, 'fb-token')
})

test('firebaseAuthProvider restore returns null for null user', async () => {
  const provider = firebaseAuthProvider({}, async () => ({
    auth: {},
    onAuthStateChanged: (auth, cb) => { Promise.resolve().then(() => cb(null)); return () => {} },
  }))
  assert.equal(await provider.restore(), null)
})

test('firebaseAuthProvider restore defaults empty email', async () => {
  const mockUser = { uid: 'fb-5', getIdToken: async () => 'tok4' }
  const provider = firebaseAuthProvider({}, async () => ({
    auth: {},
    onAuthStateChanged: (auth, cb) => { Promise.resolve().then(() => cb(mockUser)); return () => {} },
  }))
  const user = await provider.restore()
  assert.equal(user.email, '')
})

test('firebaseAuthProvider signIn delegates to signInWithEmailAndPassword', async () => {
  const mockUser = { uid: 'fb-2', email: 's@t.com', getIdToken: async () => 'tok' }
  const provider = firebaseAuthProvider({}, async () => ({
    auth: {},
    signInWithEmailAndPassword: async (_auth, _email, _password) => ({ user: mockUser }),
  }))
  const user = await provider.signIn('s@t.com', 'pass')
  assert.equal(user.uid, 'fb-2')
  assert.equal(user.token, 'tok')
})

test('firebaseAuthProvider signUp delegates to createUserWithEmailAndPassword', async () => {
  const mockUser = { uid: 'fb-3', email: 'u@t.com', getIdToken: async () => 'tok2' }
  const provider = firebaseAuthProvider({}, async () => ({
    auth: {},
    createUserWithEmailAndPassword: async (_auth, _email, _password) => ({ user: mockUser }),
  }))
  const user = await provider.signUp('u@t.com', 'pass')
  assert.equal(user.uid, 'fb-3')
  assert.equal(user.token, 'tok2')
})

test('firebaseAuthProvider signInWithGoogle delegates to signInWithPopup', async () => {
  const mockUser = { uid: 'fb-4', email: 'g@t.com', getIdToken: async () => 'tok3' }
  const provider = firebaseAuthProvider({}, async () => ({
    auth: {},
    GoogleAuthProvider: class {},
    signInWithPopup: async (_auth, _provider) => ({ user: mockUser }),
  }))
  const user = await provider.signInWithGoogle()
  assert.equal(user.uid, 'fb-4')
  assert.equal(user.token, 'tok3')
})

test('firebaseAuthProvider signOut delegates to Firebase signOut', async () => {
  let signOutCalled = false
  const provider = firebaseAuthProvider({}, async () => ({
    auth: {},
    signOut: async (_auth) => { signOutCalled = true },
  }))
  await provider.signOut()
  assert.equal(signOutCalled, true)
})
