"""
slm_api.py
FastAPI server for SLM‑based generation with CIS alignment check.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import pipeline, DistilBertTokenizer, DistilBertForSequenceClassification
import requests
import torch
import os

app = FastAPI(title="Radiant SLM API")

# Load model
model_path = os.getenv("SLM_MODEL_PATH", "./cis_slm_model")
tokenizer = DistilBertTokenizer.from_pretrained(model_path)
model = DistilBertForSequenceClassification.from_pretrained(model_path)
generator = pipeline("text-generation", model=model, tokenizer=tokenizer, device=0 if torch.cuda.is_available() else -1)

CIS_API = os.getenv("CIS_API_URL", "http://localhost:8000/score")
CIS_THRESHOLD = 7.0   # minimum acceptable CIS score

class GenerateRequest(BaseModel):
    prompt: str
    context: str = "general"

class GenerateResponse(BaseModel):
    response: str
    cis_score: float
    aligned: bool

@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    # Generate raw response (limit length)
    raw = generator(req.prompt, max_new_tokens=50, do_sample=True, temperature=0.7)[0]["generated_text"]
    # Evaluate with CIS API
    try:
        cis_resp = requests.post(CIS_API, json={"text": raw, "context": req.context}, timeout=5)
        cis_resp.raise_for_status()
        data = cis_resp.json()
        score = data["score"]
        aligned = score >= CIS_THRESHOLD
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CIS scoring failed: {str(e)}")
    
    if not aligned:
        # Return a clarification request instead of the low‑quality response
        return GenerateResponse(
            response="I'm not sure I understood correctly. Could you rephrase?",
            cis_score=score,
            aligned=False
        )
    return GenerateResponse(response=raw, cis_score=score, aligned=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
