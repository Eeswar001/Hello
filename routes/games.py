"""Game listing and detail routes."""

from __future__ import annotations

from flask import Blueprint, abort, current_app, render_template, request

from services.compatibility_service import CompatibilityService
from services.database_service import GameQuery
from services.fps_service import FPSService


games_bp = Blueprint("games", __name__, url_prefix="/games")


@games_bp.route("")
def list_games():
    database = current_app.extensions["game_database"]
    query = GameQuery(
        search=request.args.get("q", ""),
        genre=request.args.get("genre", ""),
        platform=request.args.get("platform", ""),
        developer=request.args.get("developer", ""),
        game_mode=request.args.get("game_mode", ""),
        sort=request.args.get("sort", "alphabetical"),
    )
    return render_template(
        "games.html",
        games=database.query(query),
        facets=database.facets(),
        query=query,
    )


@games_bp.route("/<slug>", methods=["GET", "POST"])
def detail(slug: str):
    database = current_app.extensions["game_database"]
    game = database.get_by_slug_or_name(slug)
    if not game:
        abort(404)

    compatibility = None
    if request.method == "POST":
        try:
            compatibility = CompatibilityService().evaluate(
                game=game,
                processor=request.form.get("processor", ""),
                graphics_card=request.form.get("graphics_card", ""),
                ram=int(request.form.get("ram", "0")),
                storage=int(request.form.get("storage", "0")),
            )
        except ValueError:
            compatibility = {"status": "Invalid input", "recommended_graphics": "Unavailable", "checks": {}}

    return render_template(
        "game_detail.html",
        game=game,
        fps=FPSService.summarize(game),
        compatibility=compatibility,
    )
