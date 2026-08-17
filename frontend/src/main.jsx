import { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { completeSessionRequest, createSessionRequest, historyRequest, mediaWebSocketUrl, sessionWebSocketUrl, setupValidation } from './api.js'
import { createMediaTransport } from './media.js'
import { createSessionTransport } from './transport.js'
import { firebaseAuthProvider, localAuthProvider } from './auth.js'
import { ActiveView, AuthScreen, HistoryView, ResultsView, SetupView, Shell } from './ui.jsx'
import './style.css'

const production = import.meta.env.PROD
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
}
const configuredForFirebase = Object.values(firebaseConfig).every(Boolean)
if (production && !configuredForFirebase) throw new Error('Firebase web authentication is not configured')
const auth = production || configuredForFirebase ? firebaseAuthProvider(firebaseConfig) : localAuthProvider()
const client = { validate: setupValidation, create: (mode, authToken) => createSessionRequest(mode, authToken) }

export function App({ authProvider = auth, fetcher = fetch }) {
  const [user, setUser] = useState(undefined)
  const token = user?.token || (production ? '' : 'dev-token')
  const [view, setView] = useState('setup')
  const [session, setSession] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [offline, setOffline] = useState(!navigator.onLine)
  useEffect(() => { authProvider.restore().then(setUser).catch(() => setUser(null)); const online = () => setOffline(false); const offlineEvent = () => setOffline(true); window.addEventListener('online', online); window.addEventListener('offline', offlineEvent); return () => { window.removeEventListener('online', online); window.removeEventListener('offline', offlineEvent) } }, [authProvider])
  useEffect(() => { const setup = () => setView('setup'); window.addEventListener('go-setup', setup); return () => window.removeEventListener('go-setup', setup) }, [])
  async function loadHistory() { setLoading(true); try { const request = historyRequest(token); const response = await fetcher(request.url, request.init); if (!response.ok) throw new Error('history'); const data = await response.json(); setHistory(data.payload?.interviews || []); setView('history') } catch { setHistory([]); setView('history') } finally { setLoading(false) } }
  function deleteInterview(id) { setHistory(current => current.filter(item => item.id !== id)) }
  const transport = useMemo(() => session ? createSessionTransport({ url: sessionWebSocketUrl(session.id, token), token, sessionId: session.id }) : null, [session, token])
  const media = useMemo(() => session ? createMediaTransport({ mediaUrl: mediaWebSocketUrl(session.id, token) }) : null, [session, token])
  if (user === undefined) return <main className="loading-screen"><span className="auth-mark">◎</span><p>Restoring your workspace…</p></main>
  if (!user) return <AuthScreen auth={authProvider} onAuthenticated={setUser} />
  function navigate(next) { if (next === 'history') loadHistory(); else setView(next) }
  async function completeSession() {
    if (!session) return
    const request = completeSessionRequest(session.id, token)
    const response = await fetcher(request.url, request.init)
    if (!response.ok) throw new Error('completion')
    setView('results')
  }
  return <Shell user={user} activeView={view} onView={navigate} onSignOut={async () => { try { await authProvider.signOut() } catch { /* signOut errors are non-blocking */ } setUser(null) }}>{offline && <div className="offline-bar">You are offline. Local controls remain available; synced resources may be out of date.</div>}{view === 'setup' && <SetupView api={client} token={token} onStarted={data => { setSession(data); setView('active') }} />}{view === 'active' && <ActiveView session={session} transport={transport} media={media} onComplete={completeSession} />}{view === 'history' && <HistoryView history={history} loading={loading} onOpen={() => setView('results')} onDelete={deleteInterview} />}{view === 'results' && <ResultsView />}</Shell>
}

createRoot(document.getElementById('root')).render(<App />)
