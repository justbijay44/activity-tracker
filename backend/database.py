from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    title = Column(String)
    url = Column(String)
    timeSpent = Column(Float)
    timeStamp = Column(DateTime)
    label = Column(String)
    reason = Column(String)

    def __repr__(self):
        return f"<Session title = {self.title} url = {self.url} timeSpent = {self.timeSpent}>"

engine = create_engine("sqlite:///productivity.db")
Base.metadata.create_all(engine)