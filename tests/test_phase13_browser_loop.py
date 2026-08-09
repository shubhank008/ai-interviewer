"""Behavior tests for the Phase 13 browser control and media seams."""
from uuid import uuid4

import pytest
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


def test_session_state_enforces_owner_replay_and_monotonic_ack() -> None:
    session_id = uuid4()
    state = BrowserSessionState(session_id, "owner")
    state.publish(SessionEventType.TRANSCRIPT_PARTIAL, {"text": "hello"}, "turn-1")
    with pytest.raises(TransportValidationError):
        state.connect("other")
    replay = state.connect("owner")
    assert replay[0].payload["text"] == "hello"
    state.acknowledge("owner", replay[0].sequence)
    with pytest.raises(TransportValidationError):
        state.acknowledge("owner", 0)


def test_command_and_media_boundaries_reject_media_control_payloads() -> None:
    with pytest.raises(TransportValidationError):
        SessionCommand(uuid4(), SessionCommandType.TURN_START, "turn", {"audio_bytes": b"secret"})
    boundary = LocalWebRTCBoundary(uuid4())
    with pytest.raises(TransportValidationError):
        boundary.accept_signaling(SignalingMessage(uuid4(), SignalingType.ICE_CANDIDATE, {}, "ice"))


def test_real_asgi_websocket_path_authenticates_and_replays() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/sessions", headers={"Authorization": "Bearer dev-token"}, json={"mode": "technical"})
    assert response.status_code == 201
    session_id = response.json()["id"]
    with client.websocket_connect(f"/ws/v1/sessions/{session_id}?token=dev-token") as socket:
        socket.send_json({"session_id": session_id, "type": "connect", "correlation_id": "c1", "payload": {}})
        connected = socket.receive_json()
        assert connected["type"] == "connection"
        socket.send_json({"session_id": session_id, "type": "heartbeat", "correlation_id": "h1", "payload": {}})
        assert socket.receive_json()["type"] == "heartbeat"
    with client.websocket_connect(f"/ws/v1/sessions/{session_id}?token=bad") as socket:
        with pytest.raises(Exception):
            socket.receive_json()


def test_signaling_path_accepts_ice_without_media_bytes() -> None:
    session_id = uuid4()
    application.browser_sessions[session_id] = BrowserSessionState(session_id, "local-user")
    application.media_boundaries[session_id] = LocalWebRTCBoundary(session_id)
    client = TestClient(app)
    with client.websocket_connect(f"/ws/v1/sessions/{session_id}/signaling?token=dev-token") as socket:
        socket.send_json({"type": "ice_candidate", "correlation_id": "ice-1", "payload": {"candidate": "candidate"}})
        assert socket.receive_json()["type"] == "ice_candidate"
