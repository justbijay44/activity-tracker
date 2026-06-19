# Activity Tracker:
This project is a browser-based productivity tracker which monitors users browser behaviour and uses a local AI model to classify activity as productive, unproductive, or neutral   with reasons to support each label.

## What it does
- Tracks the active browser and time spent
- Pauses tracking when you leave the browser
- Batches sessions every 5 minutes and sends to the backend
- Classifies domains via AI (Ollama, Groq, or Gemini)
- Custom rules to override AI classification for specific domains
- Daily time limits per domain, site gets blocked when limit is exceeded
- Streamlit dashboard with daily summary, charts, rules, limits, and AI settings
- Multi-user with JWT auth, each user sees only their own data
- User can plug in their own Groq/Gemini API key from the dashboard

## Architecture flow
- **Browser Extension** — tracks active tab and time spent, sends batches every 5 minutes
- **FastAPI Backend** — receives sessions, stores to SQLite, deduplicates by domain, sends new URLs to AI for classification
- **AI Provider** — returns label (productive / unproductive / neutral) with reason.
- **Streamlit Dashboard** — aggregated summary, metrics, charts, rules, limits, settings.

## Tech stack

- Browser extension: Javascript (to access the browser tab data with Manifest V3)
- Backend: FastAPI and Python (to create endpoint APIs)
- Database: SQLite and SQLAlchemy (simplest database and no sql query required)
- AI: Ollama (local), Groq (free cloud), or Gemini (free cloud)
- Dashboard: Streamlit (fast and easy to build with simple ui)
- Auth: JWT (python-jose), bcrypt (passlib)
- Infrastructure: Docker, Docker Compose

## How to run

### Prerequisites
- Docker Desktop
- Google Chrome
- Ollama (optional, for local AI) or a Groq/Gemini API key

#### 1. Clone the project

#### 2. Create a '.env'file in the root folder

```
SECRET_KEY=your-secret-key-here
FERNET_KEY=your-fernet-key-here
OLLAMA_HOST=http://host.docker.internal:11434
```

Generate the keys:
```bash
# SECRET_KEY — any random string
python -c "import secrets; print(secrets.token_hex(32))"

# FERNET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

#### 3. Start the backend and dashboard with docker

- First time or after code changes:
    - docker-compose up --build 
- Normal Start:
    - docker-compose up or docker-compose up -d (for detached mode)

#### 4. Create your account
Go to `http://localhost:8000/docs` → `POST /signup` → create your account.

#### 5. Load the Chrome extension

- Go to chrome://extensions
- Enable Developer mode
- Click Load unpacked
- Select the 'extension/' folder

#### 6. Open the dashboard
- Go to `http://localhost:8501` and log in.

## If you want to try a local llm — Using Ollama (Local AI)
If you prefer a fully local setup with no API keys:

1. Install Ollama from https://ollama.com
2. Set `OLLAMA_HOST=0.0.0.0` in Windows Environment Variables and restart Ollama
3. Pull the model: `ollama pull mistral:7b` or model you desire
4. Run `docker-compose up -d`

## BYOK (Bring Your Own Key)

From the dashboard → Settings tab → select provider (Groq/Gemini) and enter your API key. The key is encrypted and stored per user. Switch back to Ollama anytime by selecting it and saving.

## The Upcoming development

- Postgres migration
- Weekly/monthly trends
- Data export (CSV/JSON)
- Focus mode