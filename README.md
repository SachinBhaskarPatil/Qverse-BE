# qverse

qverse is a Django-based platform for generating and playing interactive story universes, quests, trivia, audio stories, and more. It leverages AI for content generation and provides admin tools for managing universes, quests, and user gameplay.

## Features

- AI-powered universe and quest generation
- Story-driven quests with audio, images, and collectibles
- Trivia, comics, and audio stories
- User gameplay tracking and leaderboards
- Admin interface for content management
- REST API for frontend/backend integration

## Requirements

- Python 3.8+
- Django 3.2+
- Redis (for Celery)
- PostgreSQL (recommended)
- Node.js (if using a frontend)
- See `requirements.txt` for Python dependencies

## Setup

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd qverse-main
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   - Copy `.env.example` to `.env` and fill in required values (DB, API keys, etc).

4. **Apply migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser:**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

7. **(Optional) Start Celery worker:**
   ```bash
   celery -A qverse.celery_manager worker --loglevel=info
   ```

## API Endpoints

- User: `/api/user/`
- Generator (universes, quests, trivia, etc): `/api/generator/`
- Gameplay: `/api/gameplay/`
- Game tester: `/api/gametester/`

## Project Structure

- `generator/` – Universe, quest, trivia, and content generation logic
- `game_interface/` – User gameplay tracking and leaderboard
- `user/` – User profiles, scores, and authentication
- `gametester/` – Tools for testing and validating game content
- `qverse/` – Project settings and configuration

## License

[Specify your license here]