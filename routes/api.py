"""JSON API routes."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context

from services.ai_service import AIServiceError
from services.compatibility_service import CompatibilityService
from services.database_service import GameQuery
from services.fps_service import FPSService
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
    session_id = _session_id(payload)
    if not message:
        return jsonify({"error": "Message is required"}), 400
    if not isinstance(history, list):
        return jsonify({"error": "History must be a list"}), 400

    store = current_app.extensions["conversation_store"]
    store.hydrate(session_id, _previous_history(history, message))
    store.add(session_id, "user", message)

    context_games = _context_games(message)
    ai_service = current_app.extensions["ai_service"]
    try:
        response = ai_service.complete_chat(store.get(session_id), context_games)
    except AIServiceError as exc:
        return jsonify({"error": str(exc)}), 503
    store.add(session_id, "assistant", response)
    return jsonify({"reply": response, "session_id": session_id, "source": "llm"})


@api_bp.route("/chat/stream", methods=["POST"])
def chat_stream():
    payload = _json_payload()
    message = str(payload.get("message", "")).strip()
    history = payload.get("history", [])
    session_id = _session_id(payload)
    if not message:
        return jsonify({"error": "Message is required"}), 400
    if not isinstance(history, list):
        return jsonify({"error": "History must be a list"}), 400

    store = current_app.extensions["conversation_store"]
    store.hydrate(session_id, _previous_history(history, message))
    store.add(session_id, "user", message)
    context_games = _context_games(message)
    ai_service = current_app.extensions["ai_service"]

    @stream_with_context
    def generate():
        assistant_reply: list[str] = []
        try:
            yield _sse("meta", {"session_id": session_id})
            for chunk in ai_service.stream_chat(store.get(session_id), context_games):
                assistant_reply.append(chunk)
                yield _sse("token", {"content": chunk})
            reply = "".join(assistant_reply).strip()
            if not reply:
                raise AIServiceError("The AI provider returned an empty response.")
            store.add(session_id, "assistant", reply)
            yield _sse("done", {"session_id": session_id})
        except AIServiceError as exc:
            current_app.logger.warning("Chat stream failed: %s", exc)
            yield _sse("error", {"error": str(exc)})

    return Response(generate(), mimetype="text/event-stream")


def _json_payload() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def _session_id(payload: dict[str, Any]) -> str:
    session_id = str(payload.get("session_id", "")).strip()
    return session_id[:80] if session_id else uuid4().hex


def _previous_history(history: list[Any], current_message: str) -> list[Any]:
    if not history:
        return history
    last_message = history[-1]
    if not isinstance(last_message, dict):
        return history
    if (
        last_message.get("role") == "user"
        and str(last_message.get("content", "")).strip() == current_message
    ):
        return history[:-1]
    return history


def _context_games(message: str) -> list[dict[str, Any]]:
    database = current_app.extensions["game_database"]
    matches = database.query(GameQuery(search=message, sort="metacritic"))[:5]
    return matches or database.get_all()[:8]


def _sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _positive_int(value: Any, default: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(number, maximum))
