"""Deterministic executable coverage for Phase 5 browser transport contracts."""

import asyncio
import unittest
from uuid import uuid4

from interviewer_domain.transport import (
    CreateSessionRequest,
    LocalBrowserControlTransport,
    LocalSessionEventChannel,
    LocalWebRTCMediaTransport,
    RestResourceCatalog,
    SessionEventType,
    SignalingMessage,
    SignalingType,
    TransportValidationError,
)


class BrowserTransportTests(unittest.TestCase):
    """Exercise real local transport implementations without network services."""

    def test_rest_schemas_and_versioned_resources(self) -> None:
        """Validate bootstrap schemas and stable versioned resource paths."""
        request = CreateSessionRequest("candidate-1", "technical")
        response = RestResourceCatalog.create_session(request)
        self.assertEqual("/api/v1/sessions", RestResourceCatalog.session_collection())
        self.assertEqual(f"/api/v1/sessions/{response.session_id}", RestResourceCatalog.session(response.session_id))
        self.assertEqual("candidate-1", response.to_dict()["user_id"])
        with self.assertRaises(TransportValidationError):
            CreateSessionRequest("", "technical")
        print("[REST] schemas validated")

    def test_ordering_and_session_correlation(self) -> None:
        """Deliver strictly ordered events and reject another session."""
        session_id = uuid4()
        channel = LocalSessionEventChannel(session_id)
        first = channel.publish(SessionEventType.SESSION_STARTED, {}, "bootstrap", "event-1")
        duplicate = channel.publish(SessionEventType.SESSION_STARTED, {}, "bootstrap", "event-1")
        second = channel.publish(SessionEventType.SESSION_ACTIVE, {}, "bootstrap", "event-2")
        self.assertIs(first, duplicate)
        self.assertEqual([1, 2], [event.sequence for event in channel.replay(session_id)])
        self.assertEqual(first.correlation_id, second.correlation_id)
        with self.assertRaises(TransportValidationError):
            channel.replay(uuid4())
        print("[WS] ordered session events delivered")

    def test_reconnect_replays_after_acknowledged_cursor(self) -> None:
        """Resume a session from an acknowledged sequence without mixing sessions."""
        session_id = uuid4()
        channel = LocalSessionEventChannel(session_id)
        channel.publish(SessionEventType.SESSION_STARTED, {}, "request-1")
        channel.publish(SessionEventType.TRANSCRIPT_PARTIAL, {"text": "hel"}, "turn-1")
        channel.publish(SessionEventType.TRANSCRIPT_FINAL, {"text": "hello"}, "turn-1")
        replay = channel.replay(session_id, after_sequence=1)
        self.assertEqual([2, 3], [event.sequence for event in replay])
        self.assertEqual("turn-1", replay[0].correlation_id)
        print("[WS] reconnect replay correlated")

    def test_signaling_and_media_control_separation(self) -> None:
        """Keep signaling on control and audio frames on the WebRTC media seam."""
        session_id = uuid4()
        control = LocalBrowserControlTransport()
        media = LocalWebRTCMediaTransport()
        offer = SignalingMessage(session_id, SignalingType.OFFER, {"sdp": "v=0"}, "negotiation-1")
        asyncio.run(control.send_signaling(offer))
        asyncio.run(media.send_media(b"audio-frame"))
        self.assertEqual([offer], control.signaling)
        self.assertEqual(b"audio-frame", asyncio.run(media.receive_media()))
        with self.assertRaises(TransportValidationError):
            SignalingMessage(session_id, SignalingType.OFFER, {"sdp": "v=0", "audio": b"bad"}, "negotiation-1")
        self.assertFalse(control.events)
        print("[WEBRTC] signaling validated")
        print("[TRANSPORT] media and control separated")


if __name__ == "__main__":
    unittest.main()
