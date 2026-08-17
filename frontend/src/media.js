import { markBrowser } from './observability.js'

export function createMediaTransport({ navigatorImpl = globalThis.navigator, peerConnectionFactory = globalThis.RTCPeerConnection, onState = () => {} } = {}) {
  let stream = null
  let peer = null
  let state = 'idle'
  const setState = value => { state = value; onState(value) }
  async function requestMicrophone() {
    if (!navigatorImpl?.mediaDevices?.getUserMedia) { setState('denied'); markBrowser('MEDIA_DENIED'); throw new Error('microphone unavailable') }
    try { stream = await navigatorImpl.mediaDevices.getUserMedia({ audio: true }); setState('ready'); markBrowser('MEDIA_READY'); return stream } catch (error) { setState('denied'); markBrowser('MEDIA_DENIED'); throw error }
  }
  async function negotiate() {
    if (!peerConnectionFactory) { setState('unavailable'); throw new Error('webrtc unavailable') }
    peer = new peerConnectionFactory(); if (stream) stream.getTracks().forEach(track => peer.addTrack(track, stream)); setState('negotiating'); return peer
  }
  function teardown() { stream?.getTracks().forEach(track => track.stop()); peer?.close(); stream = null; peer = null; setState('closed'); markBrowser('MEDIA_CLOSED') }
  return { requestMicrophone, negotiate, teardown, getState: () => state }
}
