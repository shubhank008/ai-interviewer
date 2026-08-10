export const CONNECTION_STATES = Object.freeze({ DISCONNECTED: 'disconnected', CONNECTING: 'connecting', CONNECTED: 'connected', RECONNECTING: 'reconnecting', FAILED: 'failed' })

export function createSessionTransport({ WebSocketImpl = globalThis.WebSocket, url, token: _token, sessionId, maxReconnects = 3, onEvent = () => {} }) {
  let socket = null
  let cursor = 0
  let attempts = 0
  let state = CONNECTION_STATES.DISCONNECTED
  let eventHandler = onEvent
  let intentionalDisconnect = false
  const setState = value => { state = value; eventHandler({ type: 'connection', payload: { state: value }, sequence: cursor }) }
  const connect = () => {
    if (!WebSocketImpl) { setState(CONNECTION_STATES.FAILED); return }
    if (socket) { socket.onopen = null; socket.onmessage = null; socket.onclose = null; socket.onerror = null; if (socket.readyState === 0 || socket.readyState === 1) socket.close(); socket = null }
    intentionalDisconnect = false
    setState(attempts ? CONNECTION_STATES.RECONNECTING : CONNECTION_STATES.CONNECTING)
    socket = new WebSocketImpl(url)
    socket.onopen = () => { attempts = 0; setState(CONNECTION_STATES.CONNECTED); send('connect', {}, `connect-${Date.now()}`, cursor) }
    socket.onmessage = message => {
      const event = JSON.parse(message.data)
      if (event.sequence && event.sequence > cursor) cursor = event.sequence
      eventHandler(event)
    }
    socket.onclose = () => { if (intentionalDisconnect) return; if (attempts < maxReconnects) { attempts += 1; setState(CONNECTION_STATES.RECONNECTING) } else setState(CONNECTION_STATES.FAILED) }
    socket.onerror = () => { if (!intentionalDisconnect) setState(CONNECTION_STATES.RECONNECTING) }
  }
  const send = (type, payload = {}, correlationId = `command-${Date.now()}`, acknowledgedSequence = cursor) => {
    if (!socket || socket.readyState !== 1) return false
    socket.send(JSON.stringify({ session_id: sessionId, type, payload, correlation_id: correlationId, acknowledged_sequence: acknowledgedSequence }))
    return true
  }
  const disconnect = () => { intentionalDisconnect = true; if (socket?.readyState === 1) send('close'); socket?.close(); setState(CONNECTION_STATES.DISCONNECTED) }
  return { connect, disconnect, send, setEventHandler: handler => { eventHandler = handler }, getState: () => state, getCursor: () => cursor, heartbeat: () => send('heartbeat'), cancel: () => send('cancel'), interrupt: () => send('interrupt'), signaling: message => send('signaling', message.payload, message.correlation_id) }
}
