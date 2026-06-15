import os
import requests
from fastapi import FastAPI
from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker, Session as DBSession
from urllib.parse import urlparse

from datetime import datetime, date
from database import Session as SessionModel, engine, CustomRule
from ai import classify_sessions, set_provider, get_provider

app = FastAPI()
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Session(BaseModel):
    title: str
    url: str
    timeSpent: float

def clean_url(url):
    parsed = urlparse(url)
    netloc = parsed.netloc or url 
    return netloc.replace("www.", "")

@app.post("/sessions")
def session_req(sessions: list[Session], db: DBSession = Depends(get_db)):
    to_classify = []
    seen_urls = set()

    for val in sessions:
        cleaned_url = clean_url(val.url)

        if not cleaned_url:
            continue
        
        custom_rule = db.query(CustomRule).filter(
            cleaned_url == CustomRule.domain, CustomRule.is_active == True).first()
        if custom_rule:
            record = SessionModel(
                title = val.title,
                url = cleaned_url,
                timeSpent = val.timeSpent,
                timeStamp = datetime.now(),
                label = custom_rule.label,
                reason = "Custom Rule",
            )

            db.add(record)
            continue
            

        existing = db.query(SessionModel).filter(
            SessionModel.url == cleaned_url,
            SessionModel.title == val.title,
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

        if not existing and cleaned_url not in seen_urls:
            to_classify.append({"title": val.title, "url": cleaned_url, "timeSpent": val.timeSpent})
            seen_urls.add(cleaned_url)
    
    db.commit()

    if to_classify:
        results = []
        for i in range(0, len(to_classify), 3):
            batch = to_classify[i:i+3]
            try:
                batch_results = classify_sessions(batch)
                results.extend(batch_results)
            except Exception as e:
                print(f"Batch failed: {e}")
                continue

        for ai_result in results:
            record = db.query(SessionModel).filter(
                SessionModel.url == ai_result["url"]
            ).order_by(SessionModel.id.desc()).first()
            if record:
                record.label = ai_result["label"]
                record.reason = ai_result["reason"]
        db.commit()
    return {"status": "received"}

@app.get("/sessions/summary")
def aggregated_data(date: date = None, db: DBSession = Depends(get_db)):
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

class RulesBase(BaseModel):
    domain: str
    label: str
    is_active: bool = True

@app.get("/rules")
def get_rules(db: DBSession = Depends(get_db)):
    query = db.query(
        CustomRule.id,
        CustomRule.domain,
        CustomRule.label,
        CustomRule.is_active,
        CustomRule.created_at
    )
    results = query.all()
    return [{"id":r.id, "domain": r.domain, "label": r.label, "is_active": r.is_active, "created_at": r.created_at}
            for r in results]

@app.post("/rules")
def post_rules(rule: RulesBase ,db: DBSession = Depends(get_db)):
    domain = clean_url(rule.domain) or rule.domain

    existing = db.query(CustomRule).filter(CustomRule.domain == domain).first()
    if existing:
        return {"status": "already exists"}
    
    record = CustomRule(
        domain = domain,
        label = rule.label,
        is_active = rule.is_active,
    )

    db.add(record)
    db.commit()

    return {"status": "created"}

@app.delete("/rules/{id}")
def delete_rule(id: int, db:DBSession = Depends(get_db)):
    get_id = db.query(CustomRule).filter(id == CustomRule.id).first()

    if not get_id:
        return {"status": "not found"}
    
    db.delete(get_id)
    db.commit()
    return {"status": "Deleted"}

@app.patch("/rules/{id}")
def update_rule(id: int, db:DBSession = Depends(get_db)):
    get_id = db.query(CustomRule).filter(id == CustomRule.id).first()

    if not get_id:
        return {"status": "not found"}
    
    get_id.is_active = not get_id.is_active
    db.commit()
    return {"is_active": get_id.is_active}

@app.get("/sessions/hourly")
def active_hours(date: date = None, db: DBSession = Depends(get_db)):
    query = db.query(
        func.strftime("%H", SessionModel.timeStamp).label("hour"),
        func.sum(SessionModel.timeSpent).label("totalTime"),
    ).group_by(func.strftime("%H", SessionModel.timeStamp))

    if date:
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())
        query = query.filter(
            SessionModel.timeStamp >= start,
            SessionModel.timeStamp <= end
        )
    
    result = query.all()
    return [{"hour": r.hour, "totalTime": r.totalTime} for r in result]