import json
import uuid
import statistics
from datetime import datetime
from typing import List, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ---------------- DATABASE (The Archive) ----------------

DATABASE_URL = "sqlite:///./conversation.db"

# Perfect Defense: check_same_thread=False allows FastAPI's async workers to access the same SQLite file.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(String, ForeignKey("conversations.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(String)
    alignment = Column(Float)
    understanding = Column(Float)
    accuracy = Column(Float)
    distortion = Column(Float)
    score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class State(Base):
    __tablename__ = "states"
    conversation_id = Column(String, primary_key=True)
    data = Column(JSON)

Base.metadata.create_all(bind=engine)

# ---------------- SCORING ENGINE (The Master Formula) ----------------

class ConversationState:
    def __init__(self):
        self.scores: List[float] = []
        self.understanding: List[float] = []
        self.accuracy: List[float] = []
        self.distortion: List[float] = []
        self.ema: float = 0.0
        self._init = False

    def update(self, metrics: Dict[str, float]) -> float:
        # Normalize and weigh the logic
        a = max(0.0, min(1.0, metrics.get("alignment", 0)))
        u = max(0.0, min(1.0, metrics.get("understanding", 0)))
        acc = max(0.0, min(1.0, metrics.get("accuracy", 0)))
        d = max(0.0, min(1.0, metrics.get("distortion", 0)))

        self.understanding.append(u)
        self.accuracy.append(acc)
        self.distortion.append(d)

        # The Architect's Weighted Formula
        raw = (0.2 * a) + (0.3 * u) + (0.4 * acc) - (0.1 * d)
        score = max(0.0, min(10.0, raw * 10.0))

        self.scores.append(score)

        # EMA: The system's "Fluid Memory"
        if not self._init:
            self.ema = score
            self._init = True
        else:
            self.ema = (0.3 * score) + (0.7 * self.ema)

        return score

    def avg(self) -> float:
        return sum(self.scores) / len(self.scores) if self.scores else 0.0

    def context_score(self) -> float:
        if not self.understanding: return 0.0
        coherence = sum(self.understanding) / len(self.understanding)
        continuity = sum(self.accuracy) / len(self.accuracy)
        std = statistics.stdev(self.distortion) if len(self.distortion) > 1 else 0.0
        stability = max(0.0, min(1.0, 1.0 - std))
        return max(0.0, min(10.0, (0.4 * coherence + 0.4 * continuity + 0.2 * stability) * 10))

    def final_grade(self) -> float:
        return (0.5 * self.avg()) + (0.3 * self.context_score()) + (0.2 * self.ema)

    def trend(self) -> str:
        if len(self.scores) < 2: return "stable"
        delta = self.scores[-1] - self.scores[0]
        if delta > 0.1: return "improving"
        if delta < -0.1: return "declining"
        return "stable"

    def to_dict(self):
        return {
            "scores": self.scores, "understanding": self.understanding,
            "accuracy": self.accuracy, "distortion": self.distortion,
            "ema": self.ema, "init": self._init
        }

    @classmethod
    def from_dict(cls, d):
        obj = cls()
        obj.scores = d.get("scores", [])
        obj.understanding = d.get("understanding", [])
        obj.accuracy = d.get("accuracy", [])
        obj.distortion = d.get("distortion", [])
        obj.ema = d.get("ema", 0.0)
        obj._init = d.get("init", False)
        return obj

# ---------------- APP & WEBSOCKETS ----------------

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, List[WebSocket]] = {}

    async def connect(self, cid: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(cid, []).append(ws)

    def disconnect(self, cid: str, ws: WebSocket):
        if cid in self.active:
            self.active[cid].remove(ws)

    async def broadcast(self, cid: str, message: dict):
        for ws in self.active.get(cid, []):
            try:
                await ws.send_json(message)
            except: pass

manager = ConnectionManager()

# ---------------- WEBSOCKET ENDPOINT ----------------

@app.websocket("/ws/{cid}/{username}")
async def websocket_endpoint(ws: WebSocket, cid: str, username: str):
    db = SessionLocal()
    await manager.connect(cid, ws)
    try:
        while True:
            data = await ws.receive_json()
            content = data.get("content")
            metrics = data.get("metrics")

            if not content or not metrics: continue

            # DB Interaction (Fortified)
            user = db.query(User).filter(User.name == username).first()
            if not user:
                user = User(name=username)
                db.add(user); db.commit(); db.refresh(user)

            # State Logic
            s_record = db.query(State).filter(State.conversation_id == cid).first()
            state = ConversationState.from_dict(s_record.data) if s_record else ConversationState()
            
            score = state.update(metrics)
            
            # Save state
            if s_record: s_record.data = state.to_dict()
            else: db.add(State(conversation_id=cid, data=state.to_dict()))

            msg = Message(
                conversation_id=cid, user_id=user.id, content=content,
                alignment=metrics["alignment"], understanding=metrics["understanding"],
                accuracy=metrics["accuracy"], distortion=metrics["distortion"], score=score
            )
            db.add(msg); db.commit()

            await manager.broadcast(cid, {
                "user": username, "content": content, "score": score,
                "state": {
                    "avg": state.avg(), "ema": state.ema,
                    "final": state.final_grade(), "trend": state.trend()
                }
            })
    except WebSocketDisconnect:
        manager.disconnect(cid, ws)
    finally:
        db.close()

@app.get("/")
async def root():
    return {"status": "Radiant Intelligence Platform Online"}
      
