"""Behavior tests for the Phase 13 browser control and media seams."""

import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from interviewer_api.app import app, application
from interviewer_domain.transport import (
    BrowserSessionState,
    LocalWebRTCBoundary,
    SessionCommand,
    SessionCommandType,
    SessionEventType,
    SignalingMessage,
    SignalingType,
    TransportValidationError,
)


class Phase13BrowserLoopTests(unittest.TestCase):
    """Exercise browser session state, command boundaries, WebSocket, and signaling."""

    def test_session_state_enforces_owner_replay_and_monotonic_ack(self) -> None:
        """Owner connects replay events; non-owner and stale ack are rejected."""
        session_id = uuid4()
        state = BrowserSessionState(session_id, "owner")
        state.publish(SessionEventType.TRANSCRIPT_PARTIAL, {"text": "hello"}, "turn-1")
        with self.assertRaises(TransportValidationError):
            state.connect("other")
        replay = state.connect("owner")
        self.assertEqual(replay[0].payload["text"], "hello")
        state.acknowledge("owner", replay[0].sequence)
        with self.assertRaises(TransportValidationError):
            state.acknowledge("owner", 0)

    def test_command_and_media_boundaries_reject_media_control_payloads(self) -> None:
        """Commands and signaling reject raw media bytes in control payloads."""
        with self.assertRaises(TransportValidationError):
            SessionCommand(
                uuid4(), SessionCommandType.TURN_START, "turn",
                {"audio_bytes": b"secret"},
            )
        boundary = LocalWebRTCBoundary(uuid4())
        with self.assertRaises(TransportValidationError):
            boundary.accept_signaling(
                SignalingMessage(uuid4(), SignalingType.ICE_CANDIDATE, {}, "ice")
            )

    def test_real_asgi_websocket_path_authenticates_and_replays(self) -> None:
        """WebSocket connects, receives replay, heartbeat, and rejects bad tokens."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/sessions",
            headers={"Authorization": "Bearer dev-token"},
            json={"mode": "technical"},
        )
        self.assertEqual(response.status_code, 201)
        session_id = response.json()["id"]
        with client.websocket_connect(
            f"/ws/v1/sessions/{session_id}?token=dev-token"
        ) as socket:
            socket.send_json({
                "session_id": session_id,
                "type": "connect",
                "correlation_id": "c1",
                "payload": {},
            })
            connected = socket.receive_json()
            self.assertEqual(connected["type"], "connection")
            socket.send_json({
                "session_id": session_id,
                "type": "heartbeat",
                "correlation_id": "h1",
                "payload": {},
            })
            self.assertEqual(socket.receive_json()["type"], "heartbeat")
        with client.websocket_connect(
            f"/ws/v1/sessions/{session_id}?token=bad"
        ) as socket:
            with self.assertRaises(Exception):
                socket.receive_json()

    def test_signaling_path_accepts_ice_without_media_bytes(self) -> None:
        """Signaling WebSocket relays ICE candidates without media payloads."""
        session_id = uuid4()
        application.browser_sessions[session_id] = BrowserSessionState(
            session_id, "local-user"
        )
        application.media_boundaries[session_id] = LocalWebRTCBoundary(session_id)
        client = TestClient(app)
        with client.websocket_connect(
            f"/ws/v1/sessions/{session_id}/signaling?token=dev-token"
        ) as socket:
            socket.send_json({
                "type": "ice_candidate",
                "correlation_id": "ice-1",
                "payload": {"candidate": "candidate"},
            })
            self.assertEqual(socket.receive_json()["type"], "ice_candidate")


if __name__ == "__main__":
    unittest.main()

class LiveExecutionPathTests(unittest.TestCase):
    """Verify the browser transport reaches live providers and evaluation."""

    def test_media_turn_and_completion_evaluation_use_application_runtime(self) -> None:
        """A buffered microphone frame is transcribed, answered, and evaluated."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/sessions",
            headers={"Authorization": "Bearer dev-token"},
            json={"mode": "recruiter"},
        )
        self.assertEqual(response.status_code, 201)
        session_id = response.json()["id"]
        with client.websocket_connect(
            f"/ws/v1/sessions/{session_id}/media?token=dev-token"
        ) as media:
            media.send_bytes(b"candidate microphone audio")
        with client.websocket_connect(
            f"/ws/v1/sessions/{session_id}?token=dev-token"
        ) as control:
            control.send_json({
                "session_id": session_id,
                "type": "turn.start",
                "correlation_id": "turn-1",
                "payload": {"sequence": 1},
            })
            event = control.receive_json()
            self.assertEqual(event["type"], "playback.started")
            self.assertIn("text", event["payload"])
        completed = client.post(
            f"/api/v1/sessions/{session_id}/complete",
            headers={"Authorization": "Bearer dev-token"},
        )
        self.assertEqual(completed.status_code, 200)
        self.assertIn("score", completed.json())
        results = client.get(
            f"/api/v1/sessions/{session_id}/results",
            headers={"Authorization": "Bearer dev-token"},
        )
        self.assertEqual(results.status_code, 200)
        self.assertIn("evaluation", results.json()["payload"])
