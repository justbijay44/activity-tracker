from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker
from urllib.parse import urlparse, urlunparse

from datetime import datetime, date, timedelta
from ai import classify_sessions
from database import Session as SessionModel, engine

app = FastAPI()
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

class Session(BaseModel):
    title: str
    url: str
    timeSpent: float

def clean_url(url):
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))

@app.get("/hello")
def hello():
    return {"message": "hello world"}

@app.post("/sessions")
def session_req(sessions: list[Session]):
    to_classify = []

    for val in sessions:
        cleaned_url = clean_url(val.url)

        existing = db.query(SessionModel).filter(
            SessionModel.url == cleaned_url,
            SessionModel.label != None
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
            to_classify.append(val)
    
    db.commit()

    if to_classify:
        results = classify_sessions([s.model_dump() for s in to_classify])
        for ai_result in results:
            record = db.query(SessionModel).filter(
                SessionModel.url == clean_url(ai_result["url"])
            ).order_by(SessionModel.id.desc()).first()
            record.label = ai_result["label"]
            record.reason = ai_result["reason"]
        db.commit()
    return {"status": "received"}

@app.get("/sessions")
def get_sessions(date: date = None):
    if date:
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())
        sessions = db.query(SessionModel).filter(
            SessionModel.timeStamp >= start,
            SessionModel.timeStamp <= end
        ).all()
    else:
        sessions = db.query(SessionModel).all()
    
    return [{"title": s.title, "url": s.url, "label": s.label, "reason": s.reason, "timeSpent": s.timeSpent}
                for s in sessions]

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