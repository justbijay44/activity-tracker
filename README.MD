# Activity Tracker:
This project is a browser-based productivity tracker which monitors users browser behaviour and uses a local AI model to classify activity as productive, unproductive, or neutral   with reasons to support each label.

## What it does
- Tracks which browser you have been actively using and for how long
- Pause the tracking if you are off the browser.
- Batches the session every 5 minutes and sends to the local backend.
- Displays a daily dashboard with productive vs unproductive time.

## Architecture flow
- **Browser Extension** — tracks active tab and time spent, sends batches every 5 minutes
- **FastAPI Backend** — receives sessions, stores to SQLite, deduplicates by domain, sends new URLs to AI for classification
- **AI Provider** — returns label (productive / unproductive / neutral) with reason.
- **Streamlit Dashboard** — fetches aggregated summary from backend, displays metrics and charts.

## Tech stack

- Browser extension: Javascript (to access the browser tab data with Manifest V3)
- Backend: FastAPI and Python (to create endpoint APIs)
- Database: SQLite and SQLAlchemy (simplest database and no sql query required)
- AI: Ollama (local), Groq (free cloud), or Gemini (free cloud)
- Dashboard: Streamlit (fast and easy to build with simple ui)
- Infrastructure: Docker, Docker Compose

## How to run

### Prerequisites
- Docker Desktop
- Google Chrome
- Ollama or API Key provider

#### 1. Clone the project

#### 2. Create a '.env'file in the root folder

```
AI_PROVIDER=groq
GROQ_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
OLLAMA_HOST=http://host.docker.internal:11434
```

- Get a free Groq key at https://console.groq.com
- Get a free Gemini key at https://aistudio.google.com

#### 3. Start the backend and dashboard with docker

- First time or after code changes:
    - docker-compose up --build 
- Normal Start:
    - docker-compose up or docker-compose up -d (for detached mode)

#### 4. Load the Chrome extension

- Go to chrome://extensions
- Enable Developer mode
- Click Load unpacked
- Select the 'extension/' folder

#### 5. Open the dashboard
- Go to http://localhost:8501

## If you want to try a local llm — Using Ollama (Local AI)
If you prefer a fully local setup with no API keys:

1. Install Ollama from https://ollama.com
2. Set `OLLAMA_HOST=0.0.0.0` in Windows Environment Variables and restart Ollama
3. Pull the model: `ollama pull mistral:7b` or model you desire
4. Set `AI_PROVIDER=ollama` in your `.env`
5. Run `docker-compose up -d`

## The Upcoming development

- Custom URL rules (user-defined productive/unproductive sites)
- Daily time limits with alerts
- Richer charts and statistics
- Most visited sites analysis