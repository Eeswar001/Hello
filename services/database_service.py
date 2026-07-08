"""Excel-backed game database access."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = {
    "name",
    "developer",
    "publisher",
    "genre",
    "story_summary",
    "release_date",
    "release_year",
    "platforms",
    "engine",
    "steam_rating",
    "metacritic",
    "minimum_requirements",
    "recommended_requirements",
    "low_fps",
    "medium_fps",
    "high_fps",
    "ultra_fps",
    "average_fps",
    "minimum_fps",
    "maximum_fps",
    "game_mode",
    "image_url",
    "popularity",
}


@dataclass(frozen=True)
class GameQuery:
    """Search, filter, and sort parameters for game listings."""

    search: str = ""
    genre: str = ""
    platform: str = ""
    developer: str = ""
    game_mode: str = ""
    sort: str = "alphabetical"


class DatabaseService:
    """Load and query the Excel game database."""

    def __init__(self, dataset_path: Path):
        self.dataset_path = Path(dataset_path)
        self._games: list[dict[str, Any]] | None = None

    def load_games(self) -> list[dict[str, Any]]:
        """Return normalized games from the Excel dataset."""

        if self._games is not None:
            return self._games
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Missing dataset: {self.dataset_path}")

        frame = pd.read_excel(self.dataset_path).fillna("")
        frame.columns = [self._normalize_key(column) for column in frame.columns]
        missing = REQUIRED_COLUMNS.difference(frame.columns)
        if missing:
            raise ValueError(f"Dataset missing columns: {', '.join(sorted(missing))}")

        games = frame.to_dict(orient="records")
        for game in games:
            game["slug"] = self.slugify(str(game["name"]))
            game["release_year"] = int(game["release_year"])
            game["steam_rating"] = float(game["steam_rating"])
            game["metacritic"] = int(game["metacritic"])
            for key in ("low_fps", "medium_fps", "high_fps", "ultra_fps", "average_fps", "minimum_fps", "maximum_fps", "popularity"):
                game[key] = int(game[key])
        self._games = games
        return games

    def get_all(self) -> list[dict[str, Any]]:
        """Return every game."""

        return list(self.load_games())

    def get_by_slug_or_name(self, value: str) -> dict[str, Any] | None:
        """Find a game by slug or exact case-insensitive name."""

        needle = self.slugify(value)
        for game in self.load_games():
            if game["slug"] == needle or self.slugify(game["name"]) == needle:
                return game
        return None

    def query(self, query: GameQuery) -> list[dict[str, Any]]:
        """Search, filter, and sort games."""

        games = self.load_games()
        search = query.search.strip().lower()
        if search:
            searchable = ("name", "genre", "developer", "publisher", "platforms", "release_year")
            games = [
                game for game in games
                if any(search in str(game[field]).lower() for field in searchable)
            ]

        games = self._filter_contains(games, "genre", query.genre)
        games = self._filter_contains(games, "platforms", query.platform)
        games = self._filter_contains(games, "developer", query.developer)
        games = self._filter_contains(games, "game_mode", query.game_mode)
        return self._sort(games, query.sort)

    def facets(self) -> dict[str, list[str]]:
        """Return distinct filter options."""

        games = self.load_games()
        return {
            "genres": self._unique_split(games, "genre"),
            "platforms": self._unique_split(games, "platforms"),
            "developers": sorted({str(game["developer"]) for game in games}),
            "game_modes": self._unique_split(games, "game_mode"),
        }

    def featured(self) -> list[dict[str, Any]]:
        return sorted(self.load_games(), key=lambda game: game["metacritic"], reverse=True)[:4]

    def popular(self) -> list[dict[str, Any]]:
        return sorted(self.load_games(), key=lambda game: game["popularity"], reverse=True)[:4]

    def latest(self) -> list[dict[str, Any]]:
        return sorted(self.load_games(), key=lambda game: game["release_year"], reverse=True)[:4]

    @staticmethod
    def slugify(value: str) -> str:
        return "-".join("".join(char.lower() if char.isalnum() else " " for char in value).split())

    @staticmethod
    def _normalize_key(value: str) -> str:
        return str(value).strip().lower().replace(" ", "_")

    @staticmethod
    def _filter_contains(games: list[dict[str, Any]], field: str, value: str) -> list[dict[str, Any]]:
        if not value:
            return games
        needle = value.lower()
        return [game for game in games if needle in str(game[field]).lower()]

    @staticmethod
    def _unique_split(games: list[dict[str, Any]], field: str) -> list[str]:
        values: set[str] = set()
        for game in games:
            for item in str(game[field]).split(","):
                if item.strip():
                    values.add(item.strip())
        return sorted(values)

    @staticmethod
    def _sort(games: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
        options = {
            "steam_rating": lambda game: (-game["steam_rating"], game["name"]),
            "metacritic": lambda game: (-game["metacritic"], game["name"]),
            "alphabetical": lambda game: game["name"],
            "newest": lambda game: (-game["release_year"], game["name"]),
            "oldest": lambda game: (game["release_year"], game["name"]),
        }
        return sorted(games, key=options.get(sort, options["alphabetical"]))
