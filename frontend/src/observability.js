const BROWSER_MARKERS = Object.freeze({
  AUTH_RESTORED: '[BROWSER19] auth-restored',
  AUTH_SIGN_IN: '[BROWSER19] auth-sign-in',
  AUTH_SIGN_UP: '[BROWSER19] auth-sign-up',
  AUTH_GOOGLE_SIGN_IN: '[BROWSER19] auth-google-sign-in',
  AUTH_SIGN_OUT: '[BROWSER19] auth-sign-out',
  MEDIA_READY: '[BROWSER19] media-ready',
  MEDIA_DENIED: '[BROWSER19] media-denied',
  MEDIA_CLOSED: '[BROWSER19] media-closed',
  WEBSOCKET_CONNECTING: '[BROWSER19] websocket-connecting',
  WEBSOCKET_CONNECTED: '[BROWSER19] websocket-connected',
  WEBSOCKET_RECONNECTING: '[BROWSER19] websocket-reconnecting',
  WEBSOCKET_FAILED: '[BROWSER19] websocket-failed',
  WEBSOCKET_DISCONNECTED: '[BROWSER19] websocket-disconnected',
})

export function markBrowser(event, logger = console.info) {
  const marker = BROWSER_MARKERS[event]
  if (marker) logger(marker)
}

export { BROWSER_MARKERS }
