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
    signIn: (email, password) => adapter.signIn(email, password),
    signUp: (email, password) => adapter.signUp(email, password),
    ...(adapter.signInWithGoogle ? { signInWithGoogle: () => adapter.signInWithGoogle() } : {}),
    signOut: () => adapter.signOut(),
  }
}

export function firebaseAuthProvider(config) {
  let initialized
  const load = async () => {
    if (!initialized) {
      initialized = Promise.all([import('firebase/app'), import('firebase/auth')]).then(([app, auth]) => {
        const firebaseApp = app.initializeApp(config)
        return { auth: auth.getAuth(firebaseApp), ...auth }
      })
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
          normalize(user).then(resolve, reject)
        }, reject)
      })
    },
    async signIn(email, password) {
      const { auth, signInWithEmailAndPassword } = await load()
      const result = await signInWithEmailAndPassword(auth, email.trim(), password)
      return normalize(result.user)
    },
    async signUp(email, password) {
      const { auth, createUserWithEmailAndPassword } = await load()
      const result = await createUserWithEmailAndPassword(auth, email.trim(), password)
      return normalize(result.user)
    },
    async signInWithGoogle() {
      const { auth, GoogleAuthProvider, signInWithPopup } = await load()
      const result = await signInWithPopup(auth, new GoogleAuthProvider())
      return normalize(result.user)
    },
    async signOut() {
      const { auth, signOut } = await load()
      return signOut(auth)
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
