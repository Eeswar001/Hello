"""In-memory chat session storage for GameVerse AI."""

from __future__ import annotations

from collections import defaultdict
from threading import Lock
from typing import Any


class ConversationStore:
    """Keep short rolling histories for independent browser chat sessions."""

    def __init__(self, max_messages: int = 80):
        self.max_messages = max_messages
        self._sessions: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
        self._lock = Lock()

    def hydrate(self, session_id: str, messages: list[dict[str, str]]) -> None:
        """Seed a new server-side session from trusted client history."""

        clean_messages = self._sanitize_messages(messages)
        if not clean_messages:
            return
        with self._lock:
            if not self._sessions[session_id]:
                self._sessions[session_id] = clean_messages[-self.max_messages :]

    def add(self, session_id: str, role: str, content: str) -> None:
        if role not in {"user", "assistant"} or not content.strip():
            return
        with self._lock:
            self._sessions[session_id].append({"role": role, "content": content.strip()})
            self._sessions[session_id] = self._sessions[session_id][-self.max_messages :]

    def get(self, session_id: str) -> list[dict[str, str]]:
        with self._lock:
            return list(self._sessions[session_id])

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    @staticmethod
    def _sanitize_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
        clean: list[dict[str, str]] = []
        for message in messages:
            if not isinstance(message, dict):
                continue
            role = str(message.get("role", "")).strip()
            content = str(message.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                clean.append({"role": role, "content": content})
        return clean
