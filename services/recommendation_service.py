"""Recommendation and comparison logic."""

from __future__ import annotations

from typing import Any


class RecommendationService:
    """Recommend and compare games from the local database."""

    def recommend(self, games: list[dict[str, Any]], preferences: str = "", limit: int = 5) -> list[dict[str, Any]]:
        pref = preferences.lower()
        scored: list[tuple[float, dict[str, Any]]] = []
        for game in games:
            score = game["metacritic"] + game["steam_rating"] * 10 + game["popularity"] / 2
            haystack = " ".join(str(game[field]).lower() for field in ("name", "genre", "developer", "platforms", "game_mode", "story_summary"))
            if pref and any(word in haystack for word in pref.split()):
                score += 25
            scored.append((score, game))
        return [game for _, game in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]

    @staticmethod
    def compare(games: list[dict[str, Any]]) -> dict[str, Any]:
        """Return side-by-side comparison data."""

        if not games:
            return {"games": [], "winner": None}
        winner = max(games, key=lambda game: (game["metacritic"], game["steam_rating"], game["popularity"]))
        return {
            "games": games,
            "winner": {
                "name": winner["name"],
                "reason": "Best combined Metacritic score, Steam rating, and popularity in the database.",
            },
        }
