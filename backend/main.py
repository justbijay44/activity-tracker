import os
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker
from urllib.parse import urlparse

from datetime import datetime, date
from database import Session as SessionModel, engine
from ai import classify_sessions, set_provider, get_provider

app = FastAPI()
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

class Session(BaseModel):
    title: str
    url: str
    timeSpent: float

def clean_url(url):
    parsed = urlparse(url)
    return parsed.netloc

@app.get("/hello")
def hello():
    return {"message": "hello world"}

@app.post("/sessions")
def session_req(sessions: list[Session]):
    to_classify = []

    for val in sessions:
        cleaned_url = clean_url(val.url)

        if not cleaned_url:
            continue

        existing = db.query(SessionModel).filter(
            SessionModel.url == cleaned_url,
            SessionModel.label != None,
            SessionModel.label != "neutral"
        ).first()

        record = SessionModel(
            title = val.title,
            url = cleaned_url,
            timeSpent = val.timeSpent,
            timeStamp = datetime.now(),
            label = existing.label if existing else None,
            reason = existing.reason if existing else None,
        )
        db.add(record)

        if not existing:
            to_classify.append({"title": val.title, "url": cleaned_url, "timeSpent": val.timeSpent})
    
    db.commit()

    if to_classify:
        results = []
        for i in range(0, len(to_classify), 3):
            batch = to_classify[i:i+5]
            batch_results = classify_sessions(batch)
            results.extend(batch_results)
        
        for ai_result in results:
            record = db.query(SessionModel).filter(
                SessionModel.url == clean_url(ai_result["url"])
            ).order_by(SessionModel.id.desc()).first()
            if record:
                record.label = ai_result["label"]
                record.reason = ai_result["reason"]
        db.commit()
    return {"status": "received"}

@app.get("/sessions/summary")
def aggregated_data(date: date = None):
    query = db.query(
        SessionModel.url,
        SessionModel.title,
        func.max(SessionModel.label).label("label"),
        func.max(SessionModel.reason).label("reason"),
        func.sum(SessionModel.timeSpent).label("totalTime")
    ).group_by(SessionModel.url)

    if date:
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())
        query = query.filter(
            SessionModel.timeStamp >= start,
            SessionModel.timeStamp <= end
        )

    result = query.all()
    return [{"url": r.url, "title": r.title, "label": r.label, "reason": r.reason, "totalTime": r.totalTime}
            for r in result]

@app.post("/set-provider")
def update_provider(provider: str):
    set_provider(provider)
    return {"provider": provider}

@app.get("/get-provider")
def current_provider():
    return {"provider": get_provider()}

@app.on_event("startup")
def warmup_ollama():
    try:
        host = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        requests.post(f"{host}/api/chat", json={
            "model": "mistral:7b",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False
        })
    except:
        pass