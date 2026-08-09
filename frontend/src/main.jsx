/* eslint-disable no-unused-vars */
import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { createSessionRequest, historyRequest, setupValidation } from './api.js'
import { localAuthProvider } from './auth.js'
import { ActiveView, AuthScreen, HistoryView, ResultsView, SetupView, Shell } from './ui.jsx'
import './style.css'

const auth = localAuthProvider()
const token = 'dev-token'
const client = { validate: setupValidation, create: (mode, authToken) => createSessionRequest(mode, authToken) }

export function App({ authProvider = auth, fetcher = fetch }) {
  const [user, setUser] = useState(undefined)
  const [view, setView] = useState('setup')
  const [session, setSession] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [offline, setOffline] = useState(!navigator.onLine)
  useEffect(() => { authProvider.restore().then(setUser).catch(() => setUser(null)); const online = () => setOffline(false); const offlineEvent = () => setOffline(true); window.addEventListener('online', online); window.addEventListener('offline', offlineEvent); return () => { window.removeEventListener('online', online); window.removeEventListener('offline', offlineEvent) } }, [authProvider])
  useEffect(() => { const setup = () => setView('setup'); window.addEventListener('go-setup', setup); return () => window.removeEventListener('go-setup', setup) }, [])
  async function loadHistory() { setLoading(true); try { const request = historyRequest(token); const response = await fetcher(request.url, request.init); if (!response.ok) throw new Error('history'); const data = await response.json(); setHistory(data.payload?.interviews || []); setView('history') } catch { setHistory([]); setView('history') } finally { setLoading(false) } }
  function deleteInterview(id) { setHistory(current => current.filter(item => item.id !== id)) }
  if (user === undefined) return <main className="loading-screen"><span className="auth-mark">◎</span><p>Restoring your workspace…</p></main>
  if (!user) return <AuthScreen auth={authProvider} onAuthenticated={setUser} />
  function navigate(next) { if (next === 'history') loadHistory(); else setView(next) }
  return <Shell user={user} activeView={view} onView={navigate} onSignOut={async () => { try { await authProvider.signOut() } catch { /* signOut errors are non-blocking */ } setUser(null) }}>{offline && <div className="offline-bar">You are offline. Local controls remain available; synced resources may be out of date.</div>}{view === 'setup' && <SetupView api={client} token={token} onStarted={data => { setSession(data); setView('active') }} />}{view === 'active' && <ActiveView session={session} onComplete={() => setView('results')} />}{view === 'history' && <HistoryView history={history} loading={loading} onOpen={() => setView('results')} onDelete={deleteInterview} />}{view === 'results' && <ResultsView />}</Shell>
}

createRoot(document.getElementById('root')).render(<App />)
