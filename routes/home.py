"""Home and informational pages."""

from __future__ import annotations

from flask import Blueprint, current_app, render_template


home_bp = Blueprint("home", __name__)


@home_bp.route("/")
def index():
    database = current_app.extensions["game_database"]
    return render_template(
        "index.html",
        featured_games=database.featured(),
        popular_games=database.popular(),
        latest_games=database.latest(),
        facets=database.facets(),
    )


@home_bp.route("/about")
def about():
    return render_template("about.html")
