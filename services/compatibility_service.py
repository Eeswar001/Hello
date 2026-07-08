"""PC compatibility checks using ranked hardware tables."""

from __future__ import annotations

import re
from typing import Any


CPU_RANKS = {
    "intel graphics": 1,
    "intel ultra 5 125h": 5,
    "intel i3": 2,
    "intel i5": 4,
    "intel i7": 6,
    "intel i9": 8,
    "ryzen 3": 2,
    "ryzen 5": 4,
    "ryzen 7": 6,
    "ryzen 9": 8,
}

GPU_RANKS = {
    "intel graphics": 1,
    "gtx 1050 ti": 2,
    "gtx 1650": 3,
    "rtx 2060": 5,
    "rtx 3060": 6,
    "rtx 4060": 7,
    "rtx 4070": 8,
    "rtx 4080": 9,
    "rtx 4090": 10,
    "rx 580": 3,
    "rx 6600": 5,
    "rx 7600": 6,
    "rx 7800": 8,
}


class CompatibilityService:
    """Compare user hardware against game requirements."""

    def evaluate(self, game: dict[str, Any], processor: str, graphics_card: str, ram: int, storage: int) -> dict[str, Any]:
        """Return compatibility status and graphics recommendation."""

        minimum = str(game["minimum_requirements"])
        recommended = str(game["recommended_requirements"])
        min_cpu = self._required_rank(minimum, CPU_RANKS, default=3)
        rec_cpu = self._required_rank(recommended, CPU_RANKS, default=5)
        min_gpu = self._required_rank(minimum, GPU_RANKS, default=3)
        rec_gpu = self._required_rank(recommended, GPU_RANKS, default=5)
        min_ram = self._extract_gb(minimum, default=8)
        rec_ram = self._extract_gb(recommended, default=16)
        user_cpu = self._rank(processor, CPU_RANKS)
        user_gpu = self._rank(graphics_card, GPU_RANKS)

        meets_minimum = user_cpu >= min_cpu and user_gpu >= min_gpu and ram >= min_ram and storage >= 60
        meets_recommended = user_cpu >= rec_cpu and user_gpu >= rec_gpu and ram >= rec_ram and storage >= 80

        if meets_recommended:
            status = "Excellent"
            graphics = "High" if user_gpu < 8 else "Ultra"
        elif meets_minimum:
            status = "Playable"
            graphics = "Low" if user_gpu <= min_gpu else "Medium"
        else:
            status = "Not Supported"
            graphics = "Unavailable"

        return {
            "status": status,
            "recommended_graphics": graphics,
            "checks": {
                "processor_rank": user_cpu,
                "graphics_rank": user_gpu,
                "minimum_processor_rank": min_cpu,
                "recommended_processor_rank": rec_cpu,
                "minimum_graphics_rank": min_gpu,
                "recommended_graphics_rank": rec_gpu,
                "ram_gb": ram,
                "minimum_ram_gb": min_ram,
                "recommended_ram_gb": rec_ram,
                "storage_gb": storage,
            },
        }

    @staticmethod
    def _rank(value: str, ranks: dict[str, int]) -> int:
        normalized = value.lower()
        matches = [rank for name, rank in ranks.items() if name in normalized]
        return max(matches) if matches else 0

    @classmethod
    def _required_rank(cls, text: str, ranks: dict[str, int], default: int) -> int:
        rank = cls._rank(text, ranks)
        return rank or default

    @staticmethod
    def _extract_gb(text: str, default: int) -> int:
        matches = [int(match) for match in re.findall(r"(\d+)\s*gb\s*ram", text.lower())]
        if not matches:
            matches = [int(match) for match in re.findall(r"(\d+)\s*gb", text.lower())]
        return max(matches) if matches else default
