# GameVerse AI

GameVerse AI is a Flask web application for game discovery, FPS summaries, PC compatibility checks, JSON APIs, and a hybrid gaming chatbot.

## Features

- Responsive dark glassmorphism UI with Bootstrap 5
- Excel-backed game database loaded with Pandas
- Search by name, genre, developer, publisher, platform, and release year
- Filters for genre, platform, developer, and game mode
- Sorting by Steam rating, Metacritic, alphabetical order, newest, and oldest
- Game detail pages with story, requirements, ratings, platforms, and FPS
- PC compatibility checks using CPU/GPU ranking dictionaries
- Chatbot with local database grounding and optional Groq reasoning
- JSON APIs for chat, search, game details, recommendations, comparison, and compatibility
- Render deployment configuration

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Open `http://127.0.0.1:5000`.

## Groq Setup

Add your key to `.env`:

```bash
GROQ_API_KEY=your_key_here
```

The app still works without a key. Factual game lookups come from `Game_Database.xlsx`; reasoning tasks return a clear configuration message until the key is set.

## Render Deployment

1. Push this folder to GitHub.
2. Create a new Render web service from the repository.
3. Render will use `render.yaml`.
4. Confirm the Python version is `3.11.9`.
5. Set `GROQ_API_KEY` in Render environment variables.

Start command:

```bash
gunicorn app:app
```

## API

- `POST /api/chat` with `{ "message": "Tell me about Elden Ring" }`
- `GET /api/search?q=rpg&sort=metacritic`
- `GET /api/game/elden-ring`
- `POST /api/recommend` with `{ "preferences": "open world rpg", "limit": 5 }`
- `POST /api/compare` with `{ "games": ["Elden Ring", "Baldur's Gate 3"] }`
- `POST /api/compatibility` with `{ "game": "Cyberpunk 2077", "processor": "Intel i7", "graphics_card": "RTX 3060", "ram": 16, "storage": 100 }`
