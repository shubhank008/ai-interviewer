export const API_BASE = '/api/v1'
export const MAX_RESUME_BYTES = 10 * 1024 * 1024

export function authHeaders(token, json = false) {
  const headers = { Authorization: `Bearer ${token}` }
  if (json) headers['Content-Type'] = 'application/json'
  return headers
}

export function createSessionRequest(mode, token) {
  return { url: `${API_BASE}/sessions`, init: { method: 'POST', headers: authHeaders(token, true), body: JSON.stringify({ mode }) } }
}

export function historyRequest(token) {
  return { url: `${API_BASE}/history`, init: { headers: authHeaders(token) } }
}

export function sessionResourceRequest(id, view, token) {
  return { url: `${API_BASE}/sessions/${id}/${view}`, init: { headers: authHeaders(token) } }
}

export function sessionWebSocketUrl(id, token, locationObject = globalThis.location) {
  const protocol = locationObject?.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${locationObject?.host || 'localhost'}/ws/v1/sessions/${id}?token=${encodeURIComponent(token)}`
}

export function signalingWebSocketUrl(id, token, locationObject = globalThis.location) {
  const protocol = locationObject?.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${locationObject?.host || 'localhost'}/ws/v1/sessions/${id}/signaling?token=${encodeURIComponent(token)}`
}

export function mediaWebSocketUrl(id, token, locationObject = globalThis.location) {
  const protocol = locationObject?.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${locationObject?.host || 'localhost'}/ws/v1/sessions/${id}/media?token=${encodeURIComponent(token)}`
}

export function completeSessionRequest(id, token) {
  return { url: `${API_BASE}/sessions/${id}/complete`, init: { method: 'POST', headers: authHeaders(token) } }
}

export function validateResume(file) {
  if (!file) return { valid: true, error: '' }
  if (file.type !== 'application/pdf') return { valid: false, error: 'Resume must be a PDF file.' }
  if (file.size > MAX_RESUME_BYTES) return { valid: false, error: 'Resume must be smaller than 10 MB.' }
  return { valid: true, error: '' }
}

export function setupValidation(jobDescription, mode, file) {
  const errors = {}
  if (!jobDescription.trim()) errors.jobDescription = 'Add the job description before continuing.'
  if (!['recruiter', 'technical'].includes(mode)) errors.mode = 'Choose an interview mode.'
  const resume = validateResume(file)
  if (!resume.valid) errors.resume = resume.error
  return { valid: Object.keys(errors).length === 0, errors }
}
