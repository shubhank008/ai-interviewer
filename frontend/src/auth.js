import { markBrowser } from './observability.js'

const LOCAL_KEY = 'interview-studio.local-session'

export function localAuthProvider(storage = globalThis.sessionStorage) {
  return {
    async restore() {
      const user = storage?.getItem(LOCAL_KEY) ? JSON.parse(storage.getItem(LOCAL_KEY)) : null
      markBrowser('AUTH_RESTORED')
      return user
    },
    async signIn(email) {
      const user = await persist({ uid: 'local-user', email: email.trim(), provider: 'local' }, storage)
      markBrowser('AUTH_SIGN_IN')
      return user
    },
    async signUp(email) {
      const user = await persist({ uid: 'local-user', email: email.trim(), provider: 'local' }, storage)
      markBrowser('AUTH_SIGN_UP')
      return user
    },
    async signOut() {
      storage?.removeItem(LOCAL_KEY)
      markBrowser('AUTH_SIGN_OUT')
    },
  }
}

export function configuredAuthProvider(adapter) {
  if (!adapter) return null
  return {
    restore: async () => { const user = await adapter.restore(); markBrowser('AUTH_RESTORED'); return user },
    signIn: async (email, password) => { const user = await adapter.signIn(email, password); markBrowser('AUTH_SIGN_IN'); return user },
    signUp: async (email, password) => { const user = await adapter.signUp(email, password); markBrowser('AUTH_SIGN_UP'); return user },
    ...(adapter.signInWithGoogle ? { signInWithGoogle: async () => { const user = await adapter.signInWithGoogle(); markBrowser('AUTH_GOOGLE_SIGN_IN'); return user } } : {}),
    signOut: async () => { const result = await adapter.signOut(); markBrowser('AUTH_SIGN_OUT'); return result },
  }
}

async function defaultFirebaseLoader(config) {
  const [app, auth] = await Promise.all([import('firebase/app'), import('firebase/auth')])
  const firebaseApp = app.initializeApp(config)
  return { auth: auth.getAuth(firebaseApp), ...auth }
}

export function firebaseAuthProvider(config, loadFn = defaultFirebaseLoader) {
  let initialized
  const load = async () => {
    if (!initialized) {
      initialized = loadFn(config)
    }
    return initialized
  }
  const normalize = async user => user ? ({
    uid: user.uid,
    email: user.email || '',
    provider: 'firebase',
    token: await user.getIdToken(),
  }) : null
  return {
    async restore() {
      const { auth, onAuthStateChanged } = await load()
      return new Promise((resolve, reject) => {
        const unsubscribe = onAuthStateChanged(auth, user => {
          unsubscribe()
          normalize(user).then(result => { markBrowser('AUTH_RESTORED'); resolve(result) }, reject)
        }, reject)
      })
    },
    async signIn(email, password) {
      const { auth, signInWithEmailAndPassword } = await load()
      const result = await signInWithEmailAndPassword(auth, email.trim(), password)
      const user = await normalize(result.user)
      markBrowser('AUTH_SIGN_IN')
      return user
    },
    async signUp(email, password) {
      const { auth, createUserWithEmailAndPassword } = await load()
      const result = await createUserWithEmailAndPassword(auth, email.trim(), password)
      const user = await normalize(result.user)
      markBrowser('AUTH_SIGN_UP')
      return user
    },
    async signInWithGoogle() {
      const { auth, GoogleAuthProvider, signInWithPopup } = await load()
      const result = await signInWithPopup(auth, new GoogleAuthProvider())
      const user = await normalize(result.user)
      markBrowser('AUTH_GOOGLE_SIGN_IN')
      return user
    },
    async signOut() {
      const { auth, signOut } = await load()
      const result = await signOut(auth)
      markBrowser('AUTH_SIGN_OUT')
      return result
    },
  }
}

function persist(user, storage) {
  storage?.setItem(LOCAL_KEY, JSON.stringify(user))
  return Promise.resolve(user)
}

export function validateCredentials(email) {
  return email.includes('@') ? '' : 'Enter a valid email address.'
}
