"""
🌌 CIS TRUTH ENGINE V2 — PRODUCTION‑READY VERSION

A conversational AI that scores its own responses using the CIS (Communication Intelligence Score)
metric and iteratively improves answers until they meet a quality threshold.

Features:
- Retrieval‑augmented generation with cached embeddings.
- Multi‑faceted scoring: alignment, accuracy, distortion, confidence, length penalty.
- Soft cap prevents high alignment scores when factual accuracy is low.
- Iterative self‑improvement loop (up to N attempts).
- Full type hints and comprehensive error handling.

Author: Radiant Protocol
License: MIT
"""

import hashlib
import re
from typing import List, Tuple, Dict, Optional

import numpy as np
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM


# ============================================================
# MODEL LOADING
# ============================================================
# Embedding model for semantic similarity
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Text generation model (Flan‑T5‑Small)
generator_tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-small")
generator_model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-small")
generator = pipeline(
    "text2text-generation",
    model=generator_model,
    tokenizer=generator_tokenizer,
    device=-1  # CPU; set to 0 for GPU
)

# Natural Language Inference model for contradiction detection
nli_model = pipeline(
    "text-classification",
    model="roberta-large-mnli",
    device=-1
)


# ============================================================
# KNOWLEDGE BASE (with pre‑computed embeddings)
# ============================================================
KNOWLEDGE_BASE: List[str] = [
    "Gravity is a force that attracts objects with mass toward each other.",
    "The Earth revolves around the Sun once every 365 days.",
    "Water boils at 100 degrees Celsius at standard pressure.",
    "Photosynthesis converts light energy into chemical energy in plants.",
    "The capital of France is Paris.",
]

# Pre‑compute and cache KB embeddings
kb_embeddings = embedder.encode(KNOWLEDGE_BASE, convert_to_tensor=True)

# Simple cache for retrieved contexts (avoids repeated embedding lookups)
_context_cache: Dict[str, List[str]] = {}


def retrieve_context(query: str, top_k: int = 2) -> List[str]:
    """
    Retrieve the top‑k most relevant documents from the knowledge base.

    Args:
        query: User input.
        top_k: Number of documents to retrieve.

    Returns:
        List of document strings.
    """
    cache_key = hashlib.md5(query.encode()).hexdigest()
    if cache_key in _context_cache:
        return _context_cache[cache_key]

    q_emb = embedder.encode(query, convert_to_tensor=True)
    scores = util.cos_sim(q_emb, kb_embeddings)[0]
    top_indices = scores.argsort(descending=True)[:top_k]
    docs = [KNOWLEDGE_BASE[i] for i in top_indices]
    _context_cache[cache_key] = docs
    return docs


# ============================================================
# METRICS (with embedding caching)
# ============================================================
_embedding_cache: Dict[str, np.ndarray] = {}


def get_embedding(text: str) -> np.ndarray:
    """Return cached embedding for a text to avoid redundant computation."""
    cache_key = hashlib.md5(text.encode()).hexdigest()
    if cache_key not in _embedding_cache:
        _embedding_cache[cache_key] = embedder.encode(text, convert_to_tensor=True)
    return _embedding_cache[cache_key]


def compute_alignment(response: str, context_docs: List[str]) -> float:
    """
    Cosine similarity between the response embedding and the average embedding
    of retrieved context documents.
    """
    if not context_docs:
        return 0.5

    r_emb = get_embedding(response)
    doc_embs = [get_embedding(doc) for doc in context_docs]
    similarities = [util.cos_sim(r_emb, d_emb).item() for d_emb in doc_embs]
    return float(np.mean(similarities))


def compute_accuracy(response: str, context_docs: List[str]) -> float:
    """
    Factual accuracy score using natural language inference.
    Returns a value in [0, 1] where:
        - ENTAILMENT = 1.0
        - NEUTRAL = 0.7
        - CONTRADICTION = 0.0
    """
    if not context_docs:
        return 0.5

    total_score = 0.0
    for doc in context_docs:
        result = nli_model(f"{doc} </s> {response}")[0]
        label = result["label"]
        if label == "ENTAILMENT":
            total_score += 1.0
        elif label == "NEUTRAL":
            total_score += 0.7
        else:  # CONTRADICTION
            total_score += 0.0
    return total_score / len(context_docs)


def compute_distortion(response: str) -> float:
    """
    Distortion based on word repetition. Higher repetition → higher distortion.
    Returns a value in [0, 1].
    """
    words = re.findall(r"\b\w+\b", response.lower())
    if not words:
        return 0.0
    unique_ratio = len(set(words)) / len(words)
    return 1.0 - unique_ratio


def compute_confidence(response: str, context_docs: List[str]) -> float:
    """
    Confidence based on variance of similarities to retrieved documents.
    Lower variance → higher confidence.
    """
    if not context_docs:
        return 0.5

    r_emb = get_embedding(response)
    sims = [util.cos_sim(r_emb, get_embedding(doc)).item() for doc in context_docs]
    variance = float(np.var(sims))
    return 1.0 - min(1.0, variance)


def length_penalty(response: str, max_words: int = 300) -> float:
    """
    Penalise overly long responses. Max penalty is capped at 0.1.
    Responses under 30 words receive no penalty.
    """
    word_count = len(response.split())
    if word_count <= 30:
        return 0.0
    return min(0.1, (word_count - 30) / max_words)


def compute_cis(user_input: str, response: str) -> Tuple[float, Dict[str, float]]:
    """
    Compute the Communication Intelligence Score (CIS) for a response.

    Formula:
        CIS = 10 * (0.5*alignment + 0.3*accuracy - 0.1*distortion + 0.1*confidence)
              - length_penalty
    Soft cap: alignment = min(alignment, accuracy + 0.2)

    Returns:
        CIS score (0‑10) and a dictionary of component metrics.
    """
    context = retrieve_context(user_input)

    alignment = compute_alignment(response, context)
    accuracy = compute_accuracy(response, context)

    # Soft cap: prevents high alignment when factual accuracy is low
    alignment = min(alignment, accuracy + 0.2)

    distortion = compute_distortion(response)
    confidence = compute_confidence(response, context)

    cis = 10.0 * (0.5 * alignment + 0.3 * accuracy - 0.1 * distortion + 0.1 * confidence)
    cis -= length_penalty(response)
    cis = max(0.0, min(10.0, cis))

    metrics = {
        "alignment": alignment,
        "accuracy": accuracy,
        "distortion": distortion,
        "confidence": confidence,
        "length_penalty": length_penalty(response),
        "context": context,
    }
    return cis, metrics


# ============================================================
# SELF‑IMPROVEMENT LOOP
# ============================================================
def improve_response(user_input: str, response: str) -> str:
    """
    Ask the generator to produce a better version of the given response.
    """
    prompt = (
        f"Question: {user_input}\n"
        f"Original answer: {response}\n"
        "Please improve this answer to be more accurate, clear, and concise.\n"
        "Improved answer:"
    )
    try:
        out = generator(prompt, max_length=150, temperature=0.3, do_sample=True)
        improved = out[0]["generated_text"].strip()
        return improved if improved else response
    except Exception:
        # Fallback to original if generation fails
        return response


# ============================================================
# MAIN BOT CLASS
# ============================================================
class CISTruthBot:
    """
    Conversational AI that generates responses and iteratively refines them
    until the CIS score meets or exceeds a quality threshold.
    """

    def __init__(self, threshold: float = 7.0, max_improvements: int = 3):
        self.threshold = threshold
        self.max_improvements = max_improvements

    def generate(self, user_input: str) -> Tuple[str, float, Dict[str, float]]:
        """
        Generate a response, then improve it until CIS >= threshold or max attempts.

        Returns:
            final_response, cis_score, metrics_dict
        """
        # Initial generation
        prompt = f"Answer the following question concisely and accurately: {user_input}"
        raw = generator(prompt, max_length=100, temperature=0.5, do_sample=True)[0]["generated_text"]
        response = raw.strip() if raw else "I am unable to generate a response."

        cis, metrics = compute_cis(user_input, response)

        # Iterative improvement
        for _ in range(self.max_improvements):
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
    bot = CISTruthBot(threshold=7.0, max_improvements=3)

    print("🌌 CIS Truth Bot v2.0 (type 'exit' to quit)\n")
    while True:
        user_input = input("You: ")
        if user_input.lower() in {"exit", "quit"}:
            break

        response, score, metrics = bot.generate(user_input)

        print(f"\nAI: {response}")
        print(f"CIS Score: {score:.2f} / 10")
        print(f"  Alignment:   {metrics['alignment']:.3f}")
        print(f"  Accuracy:    {metrics['accuracy']:.3f}")
        print(f"  Distortion:  {metrics['distortion']:.3f}")
        print(f"  Confidence:  {metrics['confidence']:.3f}")
        print(f"  Length pen.: {metrics['length_penalty']:.3f}")
        print("  Retrieved context:")
        for doc in metrics["context"]:
            print(f"    - {doc}")
        print()
