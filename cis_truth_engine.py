"""
🌌 CIS TRUTH ENGINE V2 — PRODUCTION‑READY VERSION

A conversational AI that scores its own responses using the CIS (Communication Intelligence Score)
metric and iteratively improves answers until they meet a quality threshold.

License: MIT
Mathematical models covered by the Radiant Protocol Master Formula License (RPML) v1.0.

Features:
- Retrieval‑augmented generation with FAISS vector search.
- Multi‑faceted scoring: alignment, accuracy (factual + internal consistency),
  distortion, confidence, specificity (anti‑gaming).
- Soft cap prevents high alignment scores when factual accuracy is low.
- Iterative self‑improvement loop with dynamic depth based on question complexity.
- GPU acceleration when available.
- Full type hints and comprehensive error handling.

Author: Radiant Protocol
License: MIT (code) / RPML v1.0 (mathematical models)
"""

import hashlib
import json
import re
from pathlib import Path
from typing import List, Tuple, Dict, Optional

import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM

# FAISS for scalable vector search
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("Warning: FAISS not installed. Falling back to brute‑force cosine similarity.")


# ============================================================
# DEVICE CONFIGURATION
# ============================================================
DEVICE = 0 if torch.cuda.is_available() else -1


# ============================================================
# MODEL LOADING
# ============================================================
# Embedding model
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Text generation model
generator_tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-small")
generator_model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-small").to(
    torch.device("cuda" if DEVICE == 0 else "cpu")
)
generator = pipeline(
    "text2text-generation",
    model=generator_model,
    tokenizer=generator_tokenizer,
    device=DEVICE
)

# NLI model
nli_model = pipeline(
    "text-classification",
    model="roberta-large-mnli",
    device=DEVICE
)

# Claim extraction
claim_extractor = pipeline(
    "text2text-generation",
    model="google/flan-t5-small",
    tokenizer=AutoTokenizer.from_pretrained("google/flan-t5-small"),
    device=DEVICE
)


# ============================================================
# KNOWLEDGE BASE (loaded from file or built‑in)
# ============================================================
def _load_knowledge_base() -> List[str]:
    kb_file = Path("radiant_knowledge.json")
    if kb_file.exists():
        try:
            with open(kb_file, "r") as f:
                data = json.load(f)
                if isinstance(data, list) and all(isinstance(item, str) for item in data):
                    return data
        except Exception:
            pass
    # Built‑in corpus
    return [
        "Gravity is a force that attracts objects with mass toward each other.",
        "The Earth revolves around the Sun once every 365.25 days.",
        "Water boils at 100 degrees Celsius at standard atmospheric pressure.",
        "Photosynthesis converts light energy into chemical energy in plants.",
        "The capital of France is Paris.",
        "DNA stores genetic information using a double‑helix structure.",
        "The speed of light in a vacuum is approximately 299,792,458 meters per second.",
        "Humans have 23 pairs of chromosomes.",
        "Mitochondria are the powerhouses of the cell, producing ATP.",
        "The Pythagorean theorem states that a² + b² = c² in a right‑angled triangle.",
        "Oxygen is essential for aerobic respiration in most organisms.",
        "The currency of Japan is the Yen.",
        "Mount Everest is the highest mountain above sea level.",
        "Shakespeare wrote 'Hamlet', a tragedy about a Danish prince.",
        "The Amazon River is the largest river by discharge volume of water.",
        "C is a general‑purpose programming language created by Dennis Ritchie.",
        "The Great Wall of China is over 13,000 miles long.",
        "Cold water is denser than warm water until it reaches 4°C.",
        "Sound travels faster in solids than in gases.",
        "Bats are the only mammals capable of sustained flight.",
    ]

KNOWLEDGE_BASE: List[str] = _load_knowledge_base()

# ============================================================
# FAISS INDEX (or fallback to brute force)
# ============================================================
context_cache: Dict[str, List[str]] = {}
if FAISS_AVAILABLE:
    # Compute embeddings for all documents and build index
    kb_embeddings = embedder.encode(KNOWLEDGE_BASE, convert_to_tensor=True).cpu().numpy()
    dimension = kb_embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)  # inner product (cosine similarity after normalisation)
    # Normalize for cosine similarity
    faiss.normalize_L2(kb_embeddings)
    index.add(kb_embeddings)
else:
    kb_embeddings = embedder.encode(KNOWLEDGE_BASE, convert_to_tensor=True)


def retrieve_context(query: str, top_k: int = 3) -> List[str]:
    """Retrieve top‑k documents using FAISS (or brute‑force)."""
    cache_key = hashlib.md5(query.encode()).hexdigest()
    if cache_key in context_cache:
        return context_cache[cache_key]

    q_emb = embedder.encode(query, convert_to_tensor=True)
    if FAISS_AVAILABLE:
        q_emb_np = q_emb.cpu().numpy().reshape(1, -1)
        faiss.normalize_L2(q_emb_np)
        scores, indices = index.search(q_emb_np, top_k)
        docs = [KNOWLEDGE_BASE[i] for i in indices[0] if i >= 0]
    else:
        scores = util.cos_sim(q_emb, kb_embeddings)[0]
        top_indices = scores.argsort(descending=True)[:top_k]
        docs = [KNOWLEDGE_BASE[i] for i in top_indices]

    context_cache[cache_key] = docs
    return docs


# ============================================================
# EMBEDDING CACHE
# ============================================================
_embedding_cache: Dict[str, np.ndarray] = {}

def get_embedding(text: str) -> np.ndarray:
    cache_key = hashlib.md5(text.encode()).hexdigest()
    if cache_key not in _embedding_cache:
        _embedding_cache[cache_key] = embedder.encode(text, convert_to_tensor=True)
    return _embedding_cache[cache_key]


# ============================================================
# CLAIM EXTRACTION
# ============================================================
def extract_claims(text: str) -> List[str]:
    prompt = f"List all factual statements contained in the following text, one per line:\n{text}\nFacts:"
    try:
        raw = claim_extractor(prompt, max_length=300, temperature=0.0)[0]["generated_text"]
        lines = [line.strip() for line in raw.split("\n") if line.strip()]
        if not lines or len(lines) > 20:
            lines = re.split(r'(?<=[.!?])\s+', text)
            lines = [l.strip() for l in lines if l.strip()]
        return lines
    except Exception:
        return [text]


# ============================================================
# FACTUAL VERIFICATION
# ============================================================
def verify_claims(claims: List[str], context_docs: List[str]) -> Tuple[float, float, float]:
    if not claims:
        return 0.5, 0.0, 0.5

    support_scores = []
    for claim in claims:
        best = 0.0
        for doc in context_docs:
            result = nli_model(f"{doc} </s> {claim}")[0]
            label = result["label"]
            if label == "ENTAILMENT":
                best = max(best, 1.0)
            elif label == "NEUTRAL":
                best = max(best, 0.5)
        support_scores.append(best)
    factual_acc = float(np.mean(support_scores)) if support_scores else 0.5

    contradictions = 0
    total_pairs = 0
    for i in range(len(claims)):
        for j in range(i + 1, len(claims)):
            total_pairs += 1
            res = nli_model(f"{claims[i]} </s> {claims[j]}")[0]
            if res["label"] == "CONTRADICTION":
                contradictions += 1
    internal_contra = contradictions / total_pairs if total_pairs else 0.0

    response_tokens = set(re.findall(r'\b\w+\b', " ".join(claims).lower()))
    context_tokens = set()
    for doc in context_docs:
        context_tokens.update(re.findall(r'\b\w+\b', doc.lower()))
    novel = len(response_tokens - context_tokens)
    specificity = novel / len(response_tokens) if response_tokens else 0.5
    specificity = max(0.0, min(1.0, specificity))

    return factual_acc, internal_contra, specificity


# ============================================================
# METRICS
# ============================================================
def compute_alignment(response: str, context_docs: List[str]) -> float:
    if not context_docs:
        return 0.5
    r_emb = get_embedding(response)
    doc_embs = [get_embedding(d) for d in context_docs]
    sims = [util.cos_sim(r_emb, d_emb).item() for d_emb in doc_embs]
    return float(np.mean(sims))


def compute_distortion(response: str) -> float:
    words = re.findall(r"\b\w+\b", response.lower())
    if not words:
        return 0.0
    return 1.0 - len(set(words)) / len(words)


def compute_confidence(response: str, context_docs: List[str]) -> float:
    if not context_docs:
        return 0.5
    r_emb = get_embedding(response)
    sims = [util.cos_sim(r_emb, get_embedding(d)).item() for d in context_docs]
    var = float(np.var(sims))
    return 1.0 - min(1.0, var * 10)


def length_penalty(response: str, max_words: int = 300) -> float:
    wc = len(response.split())
    if wc <= 30:
        return 0.0
    return min(0.15, (wc - 30) / max_words)


# ============================================================
# CIS COMPUTATION
# ============================================================
def compute_cis(user_input: str, response: str) -> Tuple[float, Dict[str, float]]:
    context = retrieve_context(user_input)
    claims = extract_claims(response)
    factual_acc, contradict_rate, specificity = verify_claims(claims, context)
    alignment = compute_alignment(response, context)
    alignment = min(alignment, factual_acc + 0.2)
    distortion = compute_distortion(response)
    confidence = compute_confidence(response, context)

    neutrality_boost = 0.0
    if 0.4 <= factual_acc <= 0.7:
        neutrality_boost = 0.2

    cis = 10.0 * (
        0.4 * alignment
        + 0.3 * factual_acc
        + 0.15 * neutrality_boost
        - 0.1 * distortion
        + 0.05 * confidence
        - 0.05 * contradict_rate
        + 0.05 * specificity
    )
    cis -= length_penalty(response)
    cis = max(0.0, min(10.0, cis))

    return cis, {
        "alignment": alignment,
        "factual_accuracy": factual_acc,
        "internal_contradiction_rate": contradict_rate,
        "specificity": specificity,
        "distortion": distortion,
        "confidence": confidence,
        "neutrality_boost": neutrality_boost,
        "claims_count": len(claims),
        "context": context,
    }


# ============================================================
# SELF‑IMPROVEMENT
# ============================================================
def improve_response(user_input: str, response: str) -> str:
    prompt = (
        f"Question: {user_input}\n"
        f"Original answer: {response}\n"
        "Improve the answer to be more accurate, specific, and concise.\n"
        "Improved answer:"
    )
    try:
        out = generator(prompt, max_length=200, temperature=0.3, do_sample=True)
        return out[0]["generated_text"].strip()
    except Exception:
        return response


# ============================================================
# MAIN BOT
# ============================================================
class CISTruthBot:
    def __init__(self, threshold: float = 7.0, base_improvements: int = 2):
        self.threshold = threshold
        self.base_improvements = base_improvements

    def _question_complexity(self, text: str) -> float:
        """Heuristic complexity score (0‑1)."""
        words = text.split()
        wc = len(words)
        proper_nouns = len([w for w in words if w[0].isupper() and w.lower() not in {"i"}])
        # Complexity grows with length and presence of proper nouns
        return min(1.0, (wc / 50) * 0.5 + (proper_nouns / 3) * 0.5)

    def generate(self, user_input: str) -> Tuple[str, float, Dict[str, float]]:
        complexity = self._question_complexity(user_input)
        max_improvements = min(5, int(self.base_improvements + complexity * 3))

        prompt = f"Answer concisely and accurately: {user_input}"
        raw = generator(prompt, max_length=150, temperature=0.5, do_sample=True)[0]["generated_text"]
        response = raw.strip() if raw else "Unable to generate a response."

        cis, metrics = compute_cis(user_input, response)

        for _ in range(max_improvements):
            if cis >= self.threshold:
                break
            improved = improve_response(user_input, response)
            new_cis, new_metrics = compute_cis(user_input, improved)
            if new_cis > cis:
                response, cis, metrics = improved, new_cis, new_metrics
            else:
                break
        return response, cis, metrics


# ============================================================
# INTERACTIVE DEMO
# ============================================================
if __name__ == "__main__":
    bot = CISTruthBot(threshold=7.0, base_improvements=2)
    print("🌌 CIS Truth Bot v2.0 – Scalable Edition (FAISS + GPU + Dynamic Depth)")
    print("Type 'exit' to quit.\n")
    while True:
        user_input = input("You: ")
        if user_input.lower() in {"exit", "quit"}:
            break
        response, score, metrics = bot.generate(user_input)
        print(f"\nAI: {response}")
        print(f"CIS Score: {score:.2f} / 10")
        for k, v in metrics.items():
            if isinstance(v, float):
                print(f"  {k}: {v:.3f}")
            elif isinstance(v, list):
                print(f"  {k}:")
                for item in v:
                    print(f"    - {item}")
        print()
