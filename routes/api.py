"""JSON API routes."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, jsonify, request

from config import Config
from services.compatibility_service import CompatibilityService
from services.database_service import GameQuery
from services.fps_service import FPSService
from services.groq_service import GroqService
from services.recommendation_service import RecommendationService


api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/search")
def search():
    database = current_app.extensions["game_database"]
    query = GameQuery(
        search=request.args.get("q", ""),
        genre=request.args.get("genre", ""),
        platform=request.args.get("platform", ""),
        developer=request.args.get("developer", ""),
        game_mode=request.args.get("game_mode", ""),
        sort=request.args.get("sort", "alphabetical"),
    )
    return jsonify({"results": database.query(query), "count": len(database.query(query))})


@api_bp.route("/game/<name>")
def game_detail(name: str):
    database = current_app.extensions["game_database"]
    game = database.get_by_slug_or_name(name)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    data = dict(game)
    data["fps"] = FPSService.summarize(game)
    return jsonify(data)


@api_bp.route("/recommend", methods=["POST"])
def recommend():
    payload = _json_payload()
    preferences = str(payload.get("preferences", ""))
    limit = _positive_int(payload.get("limit", 5), default=5, maximum=12)
    database = current_app.extensions["game_database"]
    games = RecommendationService().recommend(database.get_all(), preferences, limit)
    return jsonify({"recommendations": games})


@api_bp.route("/compare", methods=["POST"])
def compare():
    payload = _json_payload()
    names = payload.get("games", [])
    if not isinstance(names, list) or not names:
        return jsonify({"error": "Provide a non-empty games list"}), 400
    database = current_app.extensions["game_database"]
    games = [database.get_by_slug_or_name(str(name)) for name in names[:4]]
    found = [game for game in games if game]
    if not found:
        return jsonify({"error": "No matching games found"}), 404
    return jsonify(RecommendationService().compare(found))


@api_bp.route("/compatibility", methods=["POST"])
def compatibility():
    payload = _json_payload()
    database = current_app.extensions["game_database"]
    game = database.get_by_slug_or_name(str(payload.get("game", "")))
    if not game:
        return jsonify({"error": "Game not found"}), 404
    try:
        result = CompatibilityService().evaluate(
            game,
            str(payload.get("processor", "")),
            str(payload.get("graphics_card", "")),
            int(payload.get("ram", 0)),
            int(payload.get("storage", 0)),
        )
    except (TypeError, ValueError):
        return jsonify({"error": "RAM and storage must be numbers"}), 400
    return jsonify(result)


@api_bp.route("/chat", methods=["POST"])
def chat():
    payload = _json_payload()
    message = str(payload.get("message", "")).strip()
    history = payload.get("history", [])
    if not message:
        return jsonify({"error": "Message is required"}), 400
    if not isinstance(history, list):
        return jsonify({"error": "History must be a list"}), 400

    database = current_app.extensions["game_database"]
    matches = database.query(GameQuery(search=message, sort="metacritic"))[:5]
    lower_message = message.lower()
    reasoning_terms = ("recommend", "compare", "similar", "tip", "ending", "why", "explain", "best", "suggest")

    if matches and not any(term in lower_message for term in reasoning_terms):
        response = _database_answer(message, matches)
        source = "database"
    else:
        groq = GroqService(Config.GROQ_API_KEY, Config.GROQ_MODEL)
        context_games = matches or database.get_all()[:8]
        response = groq.chat(message, context_games)
        source = "groq" if groq.available else "local"

    return jsonify({"reply": response, "source": source})


def _database_answer(message: str, matches: list[dict[str, Any]]) -> str:
    game = matches[0]
    return (
        f"**{game['name']}** is in the GameVerse database.\n\n"
        f"- Genre: {game['genre']}\n"
        f"- Developer: {game['developer']}\n"
        f"- Publisher: {game['publisher']}\n"
        f"- Release: {game['release_date']}\n"
        f"- Platforms: {game['platforms']}\n"
        f"- Steam Rating: {game['steam_rating']}/10\n"
        f"- Metacritic: {game['metacritic']}\n\n"
        f"{game['story_summary']}"
    )


def _json_payload() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def _positive_int(value: Any, default: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(number, maximum))
