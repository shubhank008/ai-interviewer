const LOCAL_KEY = 'interview-studio.local-session'

export function localAuthProvider(storage = globalThis.sessionStorage) {
  return {
    async restore() {
      const raw = storage?.getItem(LOCAL_KEY)
      return raw ? JSON.parse(raw) : null
    },
    async signIn(email) {
      return persist({ uid: 'local-user', email: email.trim(), provider: 'local' }, storage)
    },
    async signUp(email) {
      return persist({ uid: 'local-user', email: email.trim(), provider: 'local' }, storage)
    },
    async signOut() {
      storage?.removeItem(LOCAL_KEY)
    },
  }
}

export function configuredAuthProvider(adapter) {
  if (!adapter) return null
  return {
    restore: () => adapter.restore(),
    signIn: email => adapter.signIn(email),
    signUp: email => adapter.signUp(email),
    signOut: () => adapter.signOut(),
  }
}

function persist(user, storage) {
  storage?.setItem(LOCAL_KEY, JSON.stringify(user))
  return Promise.resolve(user)
}

export function validateCredentials(email) {
  return email.includes('@') ? '' : 'Enter a valid email address.'
}
