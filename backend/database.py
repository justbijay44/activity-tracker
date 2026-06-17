from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)
    title = Column(String)
    url = Column(String, index=True)
    timeSpent = Column(Float)
    timeStamp = Column(DateTime, index=True)
    label = Column(String)
    reason = Column(String)

    def __repr__(self):
        return f"<Session title = {self.title} url = {self.url} timeSpent = {self.timeSpent}>"

class CustomRule(Base):
    __tablename__ = "customrules"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)
    domain = Column(String, index=True)
    label = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Domain = {self.domain} label = {self.label} is_active = {self.is_active} created_at = {self.created_at}>"
    
class SiteLimit(Base):
    __tablename__ = "sitelimits"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)
    domain = Column(String, index=True)
    daily_limits = Column(Integer)
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Domain = {self.domain} Daily Limit = {self.daily_limits} Blocked = {self.is_blocked}>"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.now)

engine = create_engine("sqlite:///productivity.db")
Base.metadata.create_all(engine)