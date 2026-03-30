from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
from typing import List, Dict
import statistics

app = FastAPI(title="Radiant Intelligence API")

# In‑memory storage for demonstration
scores = []

class ScoreRequest(BaseModel):
    text: str
    context: str = "general"

class ScoreResponse(BaseModel):
    score: float
    metrics: Dict[str, float]

def compute_cis(alignment: float, understanding: float, accuracy: float, distortion: float) -> float:
    raw = 0.2*alignment + 0.3*understanding + 0.4*accuracy - 0.1*distortion
    return max(0.0, min(10.0, raw * 10.0))

def extract_metrics(text: str) -> Dict[str, float]:
    # Dummy implementation – replace with actual AI
    return {"alignment": 0.8, "understanding": 0.7, "accuracy": 0.9, "distortion": 0.1}

@app.post("/score", response_model=ScoreResponse)
async def score_text(req: ScoreRequest):
    metrics = extract_metrics(req.text)
    score = compute_cis(**metrics)
    scores.append({"text": req.text, "score": score, "metrics": metrics})
    return ScoreResponse(score=score, metrics=metrics)

@app.get("/trend")
async def trend():
    if len(scores) < 2:
        return {"trend": "stable", "message": "Not enough data"}
    last_10 = scores[-10:]
    recent = [s["score"] for s in last_10]
    avg = statistics.mean(recent)
    std = statistics.stdev(recent) if len(recent) > 1 else 0.0
    if len(recent) >= 5:
        diff = recent[-1] - recent[-5]
        trend = "improving" if diff > 0.5 else ("declining" if diff < -0.5 else "stable")
    else:
        trend = "stable"
    return {"trend": trend, "average": avg, "volatility": std}
