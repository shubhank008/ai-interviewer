import { markBrowser } from './observability.js'

export function createMediaTransport({
  navigatorImpl = globalThis.navigator,
  peerConnectionFactory = globalThis.RTCPeerConnection,
  mediaRecorderFactory = globalThis.MediaRecorder,
  mediaSocketFactory = globalThis.WebSocket,
  mediaUrl = '',
  onState = () => {},
} = {}) {
  let stream = null
  let peer = null
  let recorder = null
  let mediaSocket = null
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
  function startCapture() {
    if (!stream) throw new Error('microphone is required before capture')
    if (!mediaUrl || !mediaSocketFactory || !mediaRecorderFactory) throw new Error('media capture is unavailable')
    mediaSocket = new mediaSocketFactory(mediaUrl)
    mediaSocket.onerror = () => { setState('error') }
    mediaSocket.onclose = () => { if (recorder && recorder.state !== 'inactive') { recorder.stop() } setState('error') }
    recorder = new mediaRecorderFactory(stream)
    recorder.ondataavailable = event => { if (event.data?.size && mediaSocket.readyState === 1) mediaSocket.send(event.data) }
    recorder.onerror = () => { setState('error') }
    recorder.start(250)
    setState('capturing')
  }
  function stopCapture() { recorder?.stop?.(); recorder = null; mediaSocket?.close?.(); mediaSocket = null }
  function teardown() { stopCapture(); stream?.getTracks().forEach(track => track.stop()); peer?.close(); stream = null; peer = null; setState('closed'); markBrowser('MEDIA_CLOSED') }
  return { requestMicrophone, negotiate, startCapture, stopCapture, teardown, getState: () => state, setOnState: callback => { onState = callback } }
}
