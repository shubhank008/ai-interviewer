export const API_BASE = '/api/v1'

export function authHeaders(token, json = false) {
  const headers = { Authorization: `Bearer ${token}` }
  if (json) headers['Content-Type'] = 'application/json'
  return headers
}

export function createSessionRequest(mode, token) {
  return {
    url: `${API_BASE}/sessions`,
    init: {
      method: 'POST',
      headers: authHeaders(token, true),
      body: JSON.stringify({ mode }),
    },
  }
}

export function historyRequest(token) {
  return {
    url: `${API_BASE}/history`,
    init: { headers: authHeaders(token) },
  }
}
