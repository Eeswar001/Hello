"""Groq API integration with safe local fallback."""

from __future__ import annotations

from typing import Any

import requests


class GroqService:
    """Generate gaming assistant responses through Groq."""

    endpoint = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def chat(self, message: str, context_games: list[dict[str, Any]] | None = None) -> str:
        """Return an AI response or a clear configuration message."""

        if not self.available:
            return (
                "Groq is not configured. Add GROQ_API_KEY to your .env file to enable "
                "live AI reasoning. I can still answer from the local game database."
            )

        context = self._build_context(context_games or [])
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are GameVerse AI, an accurate gaming assistant. Use the supplied "
                        "database context for factual game details. If information is absent, say so."
                    ),
                },
                {"role": "user", "content": f"{context}\n\nUser question: {message}"},
            ],
            "temperature": 0.4,
            "max_tokens": 800,
        }
        try:
            response = requests.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=25,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except (requests.RequestException, KeyError, IndexError, TypeError) as exc:
            return f"Groq request failed: {exc}. Local database features are still available."

    @staticmethod
    def _build_context(games: list[dict[str, Any]]) -> str:
        if not games:
            return "No matching database games were supplied."
        lines = ["Database context:"]
        for game in games[:8]:
            lines.append(
                f"- {game['name']} ({game['release_year']}): {game['genre']}; "
                f"developer {game['developer']}; rating {game['steam_rating']}; "
                f"metacritic {game['metacritic']}; platforms {game['platforms']}."
            )
        return "\n".join(lines)
