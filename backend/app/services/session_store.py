"""In-memory session state for demo; swap for Redis at scale."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionState:
    session_id: str
    videos: list[dict[str, Any]] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)
    chunks_indexed: int = 0


_sessions: dict[str, SessionState] = {}


def create_session(session_id: str) -> SessionState:
    state = SessionState(session_id=session_id)
    _sessions[session_id] = state
    return state


def get_session(session_id: str) -> SessionState | None:
    return _sessions.get(session_id)


def save_session(state: SessionState) -> None:
    _sessions[state.session_id] = state
