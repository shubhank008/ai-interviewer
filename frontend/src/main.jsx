import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import { createSessionRequest, historyRequest } from './api.js'
import './style.css'

const developmentToken = import.meta.env.VITE_DEV_TOKEN || 'dev-token'

export function App() {
  const [view, setView] = useState('setup')
  const [mode, setMode] = useState('technical')
  const [session, setSession] = useState(null)
  const [history, setHistory] = useState([])
  const [message, setMessage] = useState('Ready for a focused practice session.')

  async function start() {
    const request = createSessionRequest(mode, developmentToken)
    const response = await fetch(request.url, request.init)
    if (!response.ok) { setMessage(`Session start failed (${response.status}).`); return }
    const data = await response.json()
    setSession(data)
    setMessage('Session created. The voice loop can now begin.')
    setView('active')
  }

  async function loadHistory() {
    const request = historyRequest(developmentToken)
    const response = await fetch(request.url, request.init)
    if (!response.ok) { setMessage(`History load failed (${response.status}).`); return }
    const data = await response.json()
    setHistory(data.payload.interviews)
    setView('history')
  }

  return <main className="shell">
    <header><div><span className="eyebrow">INTERVIEW STUDIO</span><h1>Practice with intent.</h1></div><span className="status"><i /> Local mock mode</span></header>
    <nav>{[['setup', 'Setup'], ['active', 'Live interview'], ['history', 'History'], ['results', 'Results']].map(([key, label]) => <button className={view === key ? 'selected' : ''} onClick={key === 'history' ? loadHistory : () => setView(key)} key={key}>{label}</button>)}</nav>
    {view === 'setup' && <section className="card hero"><span className="eyebrow">01 / SETUP</span><h2>A calmer way to get interview-ready.</h2><p>Bring a role, choose a mode, and rehearse answers in a private local session. Your practice data stays in the configured service boundary.</p><label>Interview mode<select value={mode} onChange={event => setMode(event.target.value)}><option value="technical">Technical / hiring manager</option><option value="recruiter">Recruiter screen</option></select></label><button className="primary" onClick={start}>Start mock interview <b>→</b></button></section>}
    {view === 'active' && <section className="card"><span className="eyebrow">02 / LIVE INTERVIEW</span><h2>{session ? 'Your interviewer is ready.' : 'No active session yet.'}</h2><div className="voice-orb"><span>●</span></div><p className="center">{message}</p><div className="transcript"><span>TRANSCRIPT</span><p>{session ? 'Your live transcript will appear here as audio is connected.' : 'Start a session from Setup to begin.'}</p></div></section>}
    {view === 'history' && <section className="card"><span className="eyebrow">03 / HISTORY</span><h2>Revisit your practice.</h2>{history.length ? history.map(item => <article className="history-row" key={item.id}><div><strong>{item.mode} interview</strong><small>{item.status} · retained locally</small></div><button onClick={() => setView('results')}>Open replay →</button></article>) : <p>No sessions yet. Complete your first setup to see it here.</p>}</section>}
    {view === 'results' && <section className="card"><span className="eyebrow">04 / RESULTS</span><h2>Feedback that points forward.</h2><div className="score"><strong>--</strong><span>/ 100</span></div><p>Complete an interview to unlock the versioned evaluation, evidence-linked transcript, strengths, and next recommendations.</p><button className="secondary" onClick={() => setView('setup')}>Start another session</button></section>}
    <footer><span>Deterministic local environment</span><span>Retention: 14 days</span></footer>
  </main>
}

createRoot(document.getElementById('root')).render(<App />)
