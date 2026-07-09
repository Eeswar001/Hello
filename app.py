"""Flask entry point for GameVerse AI."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template, request

from config import Config
from routes.api import api_bp
from routes.chat import chat_bp
from routes.games import games_bp
from routes.home import home_bp
from services.ai_service import AIService
from services.conversation_store import ConversationStore
from services.database_service import DatabaseService


def configure_logging(app: Flask) -> None:
    """Configure rotating file and console logging."""

    Config.LOG_FILE.parent.mkdir(exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    try:
        with Config.LOG_FILE.open("a", encoding="utf-8"):
            pass
        file_handler = RotatingFileHandler(
            Config.LOG_FILE,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
    except OSError as exc:
        app.logger.warning("File logging disabled: %s", exc)
    app.logger.setLevel(logging.INFO)


def create_app() -> Flask:
    """Create and configure the Flask application."""

    app = Flask(__name__)
    app.config.from_object(Config)
    configure_logging(app)

    database = DatabaseService(app.config["DATASET_PATH"])
    app.extensions["game_database"] = database
    app.extensions["conversation_store"] = ConversationStore(
        app.config["CHAT_HISTORY_LIMIT"]
    )
    app.extensions["ai_service"] = AIService(
        api_key=app.config["LLM_API_KEY"],
        model=app.config["LLM_MODEL"],
        base_url=app.config["LLM_BASE_URL"],
        timeout=app.config["LLM_TIMEOUT"],
        max_history_messages=app.config["CHAT_HISTORY_LIMIT"],
        logger=app.logger,
    )

    app.register_blueprint(home_bp)
    app.register_blueprint(games_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(api_bp)

    @app.before_request
    def log_request() -> None:
        app.logger.info("%s %s", request.method, request.path)

    @app.errorhandler(404)
    def not_found(error: Exception):
        app.logger.warning("404: %s", request.path)
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(error: Exception):
        app.logger.exception("500 error: %s", error)
        return render_template("500.html"), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
