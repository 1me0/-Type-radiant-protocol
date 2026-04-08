"""
feedback.py
Collect user corrections and periodically fine‑tune the model (simulated federated learning).
"""

import json
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
FEEDBACK_FILE = "data/user_feedback.jsonl"

class Feedback(BaseModel):
    prompt: str
    response: str
    correction: str = None
    accepted: bool = False

@app.post("/feedback")
async def record_feedback(fb: Feedback):
    """Store user feedback for later fine‑tuning."""
    os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
    with open(FEEDBACK_FILE, "a") as f:
        f.write(json.dumps({
            "prompt": fb.prompt,
            "response": fb.response,
            "correction": fb.correction,
            "accepted": fb.accepted,
            "timestamp": datetime.utcnow().isoformat()
        }) + "\n")
    return {"status": "recorded"}

# Stub for federated learning – in production you would aggregate weight updates.
def federated_aggregate():
    # Placeholder: send local updates to central server or average weights
    pass
