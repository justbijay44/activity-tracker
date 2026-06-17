import os
import requests
from jose import jwt
from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import func
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker, Session as DBSession
from urllib.parse import urlparse
from passlib.context import CryptContext

from datetime import datetime, date, timedelta, timezone
from database import Session as SessionModel, engine, CustomRule, SiteLimit, User as UserModel
from ai import classify_sessions, set_provider, get_provider
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()
SessionLocal = sessionmaker(bind=engine)
pwd_context = CryptContext(schemes=["bcrypt"])
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
ALGORITHM = "HS256"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_token(user_id: int):
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=30)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(authorization: str = Header(...), db: DBSession = Depends(get_db)):
    try:
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload["sub"]
    except:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

class Session(BaseModel):
    title: str
    url: str
    timeSpent: float

def clean_url(url):
    parsed = urlparse(url)
    netloc = parsed.netloc or url 
    return netloc.replace("www.", "")

@app.post("/sessions")
def session_req(sessions: list[Session], db: DBSession = Depends(get_db), current_user = Depends(get_current_user)):
    to_classify = []
    seen_urls = set()

    for val in sessions:
        cleaned_url = clean_url(val.url)

        if not cleaned_url:
            continue
            
        custom_rule = db.query(CustomRule).filter(
            cleaned_url == CustomRule.domain,
            CustomRule.is_active == True,
            CustomRule.user_id == current_user.id    
        ).first()

        if custom_rule:
            record = SessionModel(
                title = val.title,
                url = cleaned_url,
                timeSpent = val.timeSpent,
                timeStamp = datetime.now(),
                label = custom_rule.label,
                reason = "Custom Rule",
                user_id = current_user.id,
            )

            db.add(record)
            continue

        existing = db.query(SessionModel).filter(
            SessionModel.url == cleaned_url,
            SessionModel.title == val.title,
            SessionModel.label != None,
            SessionModel.label != "neutral",
            SessionModel.user_id == current_user.id
        ).first()
        
        record = SessionModel(
            title = val.title,
            url = cleaned_url,
            timeSpent = val.timeSpent,
            timeStamp = datetime.now(),
            label = existing.label if existing else None,
            reason = existing.reason if existing else None,
            user_id = current_user.id,

        )
        db.add(record)

        if not existing and (cleaned_url, val.title) not in seen_urls:
            to_classify.append({"title": val.title, "url": cleaned_url, "timeSpent": val.timeSpent})
            seen_urls.add((cleaned_url, val.title))
    
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
            records = db.query(SessionModel).filter(
                SessionModel.url == ai_result["url"],
                SessionModel.title == ai_result["title"],
                SessionModel.label == None,
                SessionModel.user_id == current_user.id,
            ).all()
            for record in records:
                record.label = ai_result["label"]
                record.reason = ai_result["reason"]
        db.commit()
    return {"status": "received"}

@app.get("/sessions/summary")
def aggregated_data(date: date = None, db: DBSession = Depends(get_db), current_user = Depends(get_current_user)):
    query = db.query(
        SessionModel.url,
        func.max(SessionModel.title).label("title"),
        func.max(SessionModel.label).label("label"),
        func.max(SessionModel.reason).label("reason"),
        func.sum(SessionModel.timeSpent).label("totalTime")
    ).group_by(SessionModel.url)

    query = query.filter(SessionModel.user_id == current_user.id)

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
def get_rules(db: DBSession = Depends(get_db), current_user = Depends(get_current_user)):
    query = db.query(
        CustomRule.id,
        CustomRule.domain,
        CustomRule.label,
        CustomRule.is_active,
        CustomRule.created_at
    )

    query = query.filter(CustomRule.user_id == current_user.id)

    results = query.all()
    return [{"id":r.id, "domain": r.domain, "label": r.label, "is_active": r.is_active, "created_at": r.created_at}
            for r in results]

@app.post("/rules")
def post_rules(rule: RulesBase ,db: DBSession = Depends(get_db), current_user = Depends(get_current_user)):
    domain = clean_url(rule.domain) or rule.domain

    existing = db.query(CustomRule).filter(
        CustomRule.domain == domain,
        CustomRule.user_id == current_user.id
    ).first()
    
    if existing:
        return {"status": "already exists"}
    
    record = CustomRule(
        domain = domain,
        label = rule.label,
        is_active = rule.is_active,
        user_id = current_user.id
    )

    db.add(record)
    db.commit()

    return {"status": "created"}

@app.delete("/rules/{id}")
def delete_rule(id: int, db:DBSession = Depends(get_db), current_user = Depends(get_current_user)):
    get_id = db.query(CustomRule).filter(
        id == CustomRule.id,
        CustomRule.user_id == current_user.id
    ).first()

    if not get_id:
        return {"status": "not found"}
    
    db.delete(get_id)
    db.commit()
    return {"status": "Deleted"}

@app.patch("/rules/{id}")
def update_rule(id: int, db:DBSession = Depends(get_db), current_user = Depends(get_current_user)):
    get_id = db.query(CustomRule).filter(
        id == CustomRule.id,
        CustomRule.user_id == current_user.id
    ).first()

    if not get_id:
        return {"status": "not found"}
    
    get_id.is_active = not get_id.is_active
    db.commit()
    return {"is_active": get_id.is_active}

@app.get("/sessions/hourly")
def active_hours(date: date = None, db: DBSession = Depends(get_db), current_user = Depends(get_current_user)):
    query = db.query(
        func.strftime("%H", SessionModel.timeStamp).label("hour"),
        func.sum(SessionModel.timeSpent).label("totalTime"),
    ).group_by(func.strftime("%H", SessionModel.timeStamp))
    
    query = query.filter(SessionModel.user_id == current_user.id)

    if date:
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())
        query = query.filter(
            SessionModel.timeStamp >= start,
            SessionModel.timeStamp <= end
        )
    
    result = query.all()
    return [{"hour": r.hour, "totalTime": r.totalTime} for r in result]

class LimitBase(BaseModel):
    domain: str
    daily_limits: int 
    
@app.get("/limits")
def get_limits(db: DBSession = Depends(get_db), current_user = Depends(get_current_user)):
    limits = db.query(SiteLimit).filter(SiteLimit.user_id == current_user.id).all()

    result = []
    for limit in limits:
        start = limit.created_at
        end = datetime.combine(date.today(), datetime.max.time())
        usages = db.query(func.sum(SessionModel.timeSpent)).filter(
            SessionModel.url == limit.domain,
            SessionModel.timeStamp >= start,
            SessionModel.timeStamp <= end,
            SessionModel.user_id == current_user.id,
        ).scalar() or 0

        result.append({
            "id": limit.id,
            "domain": limit.domain, 
            "daily_limits": limit.daily_limits, 
            "is_blocked": limit.is_blocked, 
            "created_at": limit.created_at,
            "usage_today_minutes": round(usages / 60, 1)
        })
    return result

@app.post("/limits")
def upload_limits(limit: LimitBase, db: DBSession = Depends(get_db), current_user = Depends(get_current_user)):
    domain = clean_url(limit.domain) or limit.domain

    existing = db.query(SiteLimit).filter(
        SiteLimit.domain == domain,
        SiteLimit.user_id == current_user.id    
    ).first()
    
    if existing:
        existing.daily_limits = limit.daily_limits
        db.commit()
        return {"status": "updated"}
    
    record = SiteLimit(
        domain = domain,
        daily_limits = limit.daily_limits,
        user_id = current_user.id
    )
    db.add(record)
    db.commit()

    return {"status": "successfully created"}

@app.delete("/limits/{id}")
def delete_limit(id: int, db: DBSession = Depends(get_db), current_user = Depends(get_current_user)):
    get_id = db.query(SiteLimit).filter(
        SiteLimit.id == id,
        SiteLimit.user_id == current_user.id
    ).first()

    if not get_id:
        return {"status": "Couldn't find the id"}

    db.delete(get_id)
    db.commit()
    return {"status": "successfully deleted"}

@app.post("/limits/check")
def check_limit(db: DBSession = Depends(get_db), current_user = Depends(get_current_user)):
    limits = db.query(SiteLimit).filter(
        SiteLimit.is_blocked == False,
        SiteLimit.user_id == current_user.id
    ).all()
    
    newly_blocked = []

    for limit in limits:
        start = limit.created_at
        end = datetime.combine(date.today(), datetime.max.time())

        usage = db.query(func.sum(SessionModel.timeSpent)).filter(
            SessionModel.url == limit.domain,
            SessionModel.timeStamp >= start,
            SessionModel.timeStamp <= end,
            SessionModel.user_id == current_user.id,
        ).scalar() or 0

        if usage >= limit.daily_limits * 60:
            limit.is_blocked = True
            newly_blocked.append(limit.domain)
    db.commit()
    return {"blocked": newly_blocked}

class User(BaseModel):
    email: str
    password: str

@app.post("/signup")
def signup(user: User, db: DBSession = Depends(get_db)):
    existing = db.query(UserModel).filter(UserModel.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    password_hash = pwd_context.hash(user.password)
    record = UserModel(
        email = user.email,
        password_hash = password_hash
    )
    db.add(record)
    db.commit()
    return {"status": "User Successfully added"}

@app.post("/login")
def login(user: User, db: DBSession = Depends(get_db)):
    existing = db.query(UserModel).filter(UserModel.email == user.email).first()
    
    if not existing:
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    if not pwd_context.verify(user.password, existing.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    
    token = create_token(existing.id)
    return {"access_token": token}
