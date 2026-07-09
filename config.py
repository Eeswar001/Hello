"""Application configuration for GameVerse AI."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base Flask configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "gameverse-ai-local-secret")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    LLM_API_KEY = os.getenv("LLM_API_KEY", GROQ_API_KEY)
    LLM_MODEL = os.getenv("LLM_MODEL", GROQ_MODEL)
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
    CHAT_HISTORY_LIMIT = int(os.getenv("CHAT_HISTORY_LIMIT", "80"))
    DATASET_PATH = Path(os.getenv("DATASET_PATH", BASE_DIR / "Game_Database.xlsx"))
    LOG_FILE = BASE_DIR / "logs" / "app.log"
    JSON_SORT_KEYS = False
