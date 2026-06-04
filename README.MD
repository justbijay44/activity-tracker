# Activity Tracker:
This project is a browser-based productivity tracker which monitors users browser behaviour and uses a local AI model to classify activity as productive, unproductive, or neutral   with reasons to support each label.

## What it does
- Tracks which browser you have been actively using and for how long
- Pause the tracking if you are off the browser.
- Batches the session every 5 minutes and sends to the local backend.
- Displays a daily dashboard with productive vs unproductive time.

## Architecture flow
- Browser Extension: 
    - We have the extension which is use to track the active browser tab.
    - The sesssion are of 5 minutes and data are send in batches.
- FastAPI Backend
    - It receives and stores sessions it to the db(sqlite).
    - We check if URL already has a label for consistent labeling.
    - sends new URLs to Ollama for classification.
- Ollama (Local LLM)
    - returns label (productive / unproductive / neutral) + reason.
- Streamlit Dashboard
    - fetches aggregated summary from backend.
    - displays the information in tables and bar chart.

## Tech stack

- Browser extension: Javascript (to access the browser tab data)
- Backend: FastAPI and Python (to create endpoint apis)
- Database: SQLite and SQLAlchemy (simplest database and no sql query required)
- AI: Ollama (qwen2.5-coder - free and local)
- Dashboard: Streamlit (fast and easy to build with simple ui)

## How to run

### Prerequisites
- python
- google chrome
- ollama

#### 1. Clone the project

#### 2. Setup backend

```
cd backend
python -m venv venv
.\venv\Scripts\activate

pip install -r requirements.txt
```

#### 3. Pull the Ollama model

```
ollama pull yourfavmodel
```

#### 4. Start everything

- Ensure the ollama is live

- FastAPI backend
```
cd backend
.\venv\Scripts\activate
uvicorn main:app --reload
```

- Streamlit dashboard
```
cd backend
venv\Scripts\activate
streamlit run dashboard.py
```

#### 5. Load the Chrome extension

- Go to chrome://extensions
- Enable Developer mode
- Click Load unpacked
- Select the extension folder