"""FPS helpers."""

from __future__ import annotations

from typing import Any


class FPSService:
    """Build FPS summaries for games."""

    @staticmethod
    def summarize(game: dict[str, Any]) -> dict[str, int]:
        return {
            "low": int(game["low_fps"]),
            "medium": int(game["medium_fps"]),
            "high": int(game["high_fps"]),
            "ultra": int(game["ultra_fps"]),
            "average": int(game["average_fps"]),
            "minimum": int(game["minimum_fps"]),
            "maximum": int(game["maximum_fps"]),
        }
