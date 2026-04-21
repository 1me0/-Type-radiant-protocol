"""
feedback.py
Collect user corrections and periodically fine‑tune the model (simulated federated learning).

This module provides a FastAPI endpoint to record user feedback (prompt, response,
correction, acceptance) into a JSONL file. It serves as a data collection layer for
future fine‑tuning or federated learning updates.

Usage:
    uvicorn feedback:app --reload
"""

import json
import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configuration – can be overridden via environment variable
FEEDBACK_FILE = os.getenv("FEEDBACK_FILE", "data/user_feedback.jsonl")
MAX_FILE_SIZE_MB = 100  # Optional: prevent unbounded growth

app = FastAPI(title="Radiant Feedback Collector", version="1.0.0")

class Feedback(BaseModel):
    """Feedback structure for a single interaction."""
    prompt: str
    response: str
    correction: str | None = None
    accepted: bool = False

@app.post("/feedback")
async def record_feedback(fb: Feedback) -> dict:
    """
    Store user feedback for later fine‑tuning.
    Appends a JSON object to a line‑delimited file.
    """
    try:
        # Ensure directory exists
        Path(FEEDBACK_FILE).parent.mkdir(parents=True, exist_ok=True)

        # Optional: check file size (simple warning)
        if os.path.exists(FEEDBACK_FILE) and os.path.getsize(FEEDBACK_FILE) > MAX_FILE_SIZE_MB * 1024 * 1024:
            # In production, rotate or archive the file; here we just log.
            print(f"Warning: feedback file {FEEDBACK_FILE} exceeds {MAX_FILE_SIZE_MB} MB. Consider archiving.")

        record = {
            "prompt": fb.prompt,
            "response": fb.response,
            "correction": fb.correction,
            "accepted": fb.accepted,
            "timestamp": datetime.utcnow().isoformat()
        }
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return {"status": "recorded", "file": FEEDBACK_FILE}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record feedback: {str(e)}")

def federated_aggregate() -> None:
    """
    Stub for federated learning.
    In production, this would collect local weight updates from multiple nodes,
    average them (e.g., FedAvg), and apply the aggregated update to the global model.
    """
    print("Federated aggregation placeholder – implement with actual model weights.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
