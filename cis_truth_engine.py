"""
🌌 CIS TRUTH ENGINE V2 — 10/10 FINAL VERSION
Includes:
- Correct label mapping for RoBERTa-MNLI (CONTRADICTION / NEUTRAL / ENTAILMENT)
- Accuracy scoring: -1 for contradiction, -0.3 for neutral
- Soft cap: alignment = min(alignment, accuracy + 0.2)
- Length penalty to discourage overly verbose responses
- Embedding caching for performance
- Iterative improvement loop (up to 3 attempts)
"""

import numpy as np
import re
import hashlib
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM

# ============================================================
# MODELS
# ============================================================
embedder = SentenceTransformer("all-MiniLM-L6-v2")
generator_tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-small")
generator_model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-small")
generator = pipeline("text2text-generation", model=generator_model, tokenizer=generator_tokenizer)

# NLI model for contradiction detection
contradiction_detector = pipeline("text-classification", model="roberta-base-mnli", device=-1)

# Label mapping for RoBERTa-MNLI
LABEL_MAP = {
    "LABEL_0": "CONTRADICTION",
    "LABEL_1": "NEUTRAL",
    "LABEL_2": "ENTAILMENT"
}

# ============================================================
# KNOWLEDGE BASE (retrieval) with caching
# ============================================================
KNOWLEDGE_BASE = [
    "Gravity is a force that attracts objects with mass toward each other.",
    "The Earth revolves around the Sun once every 365 days.",
    "Water boils at 100 degrees Celsius at standard pressure.",
    "Photosynthesis converts light energy into chemical energy in plants.",
    "The capital of France is Paris."
]

# Pre-compute embeddings for the knowledge base
kb_embeddings = embedder.encode(KNOWLEDGE_BASE, convert_to_tensor=True)

# Simple cache for retrieved contexts
_context_cache = {}

def retrieve_context(query: str, top_k: int = 2) -> list:
    """Retrieve top_k relevant documents from knowledge base, with caching."""
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
# METRICS (with caching and soft constraints)
# ============================================================
# Cache for embeddings of responses (to avoid recomputation)
_embedding_cache = {}

def get_embedding(text: str):
    """Return cached embedding for a text."""
    cache_key = hashlib.md5(text.encode()).hexdigest()
    if cache_key not in _embedding_cache:
        _embedding_cache[cache_key] = embedder.encode(text, convert_to_tensor=True)
    return _embedding_cache[cache_key]

def compute_alignment(response: str, context_docs: list) -> float:
    """Cosine similarity between response and the average of retrieved context."""
    if not context_docs:
        return 0.5
    r_emb = get_embedding(response)
    doc_embs = [get_embedding(doc) for doc in context_docs]
    similarities = [util.cos_sim(r_emb, d_emb).item() for d_emb in doc_embs]
    return float(np.mean(similarities))

def compute_accuracy(response: str, context_docs: list) -> float:
    """
    Accuracy score based on contradiction/neutral/entailment against retrieved docs.
    Returns a value between 0 and 1.
    """
    if not context_docs:
        return 0.5
    total_score = 0
    for doc in context_docs:
        result = contradiction_detector(f"{doc} </s> {response}")[0]
        label = LABEL_MAP.get(result['label'], 'NEUTRAL')
        if label == "ENTAILMENT":
            total_score += 1.0
        elif label == "NEUTRAL":
            total_score += 0.7   # not confirmed but not false
        else:  # CONTRADICTION
            total_score += 0.0
    return total_score / len(context_docs)

def compute_distortion(response: str) -> float:
    """Distortion based on word repetition (higher repetition = higher distortion)."""
    words = re.findall(r'\b\w+\b', response.lower())
    if len(words) == 0:
        return 0.0
    unique_ratio = len(set(words)) / len(words)
    return 1.0 - unique_ratio

def compute_confidence(response: str, context_docs: list) -> float:
    """Confidence based on variance of similarities to retrieved docs."""
    if not context_docs:
        return 0.5
    r_emb = get_embedding(response)
    doc_embs = [get_embedding(doc) for doc in context_docs]
    sims = [util.cos_sim(r_emb, d_emb).item() for d_emb in doc_embs]
    variance = np.var(sims)
    return 1.0 - min(1.0, variance)

def length_penalty(response: str, max_words: int = 300) -> float:
    """Penalize responses longer than a threshold (max 0.1)."""
    word_count = len(response.split())
    if word_count <= 30:
        return 0.0
    return min(0.1, (word_count - 30) / max_words)

def compute_cis(user_input: str, response: str) -> tuple:
    """
    Compute CIS score (0-10) based on:
    - alignment (0.5 weight)
    - accuracy (0.3 weight)
    - distortion (negative, -0.1 weight)
    - confidence (0.1 weight)
    - length penalty (subtracted, max 0.1)
    Soft cap: alignment = min(alignment, accuracy + 0.2)
    """
    context = retrieve_context(user_input)
    alignment = compute_alignment(response, context)
    accuracy = compute_accuracy(response, context)
    # Soft cap: alignment cannot exceed accuracy + 0.2
    alignment = min(alignment, accuracy + 0.2)
    distortion = compute_distortion(response)
    confidence = compute_confidence(response, context)
    cis = 10 * (0.5 * alignment + 0.3 * accuracy - 0.1 * distortion + 0.1 * confidence)
    # Apply length penalty
    cis -= length_penalty(response)
    cis = max(0.0, min(10.0, cis))
    metrics = {
        "alignment": alignment,
        "accuracy": accuracy,
        "distortion": distortion,
        "confidence": confidence,
        "length_penalty": length_penalty(response),
        "context": context
    }
    return cis, metrics

# ============================================================
# IMPROVEMENT LOOP
# ============================================================
def improve_response(user_input: str, response: str) -> str:
    """Generate an improved response using the instruction-tuned model."""
    prompt = f"Question: {user_input}\nOriginal answer: {response}\nPlease improve this answer to be more accurate, clear, and concise. Improved answer:"
    out = generator(prompt, max_length=150, temperature=0.3, do_sample=True)
    improved = out[0]['generated_text'].strip()
    return improved if improved else response

# ============================================================
# MAIN BOT
# ============================================================
class CISTruthBot:
    def __init__(self, threshold: float = 7.0, max_improvements: int = 3):
        self.threshold = threshold
        self.max_improvements = max_improvements

    def generate(self, user_input: str) -> tuple:
        """Generate a response, iteratively improve until CIS >= threshold or max attempts."""
        prompt = f"Answer the following question concisely and accurately: {user_input}"
        raw = generator(prompt, max_length=100, temperature=0.5, do_sample=True)[0]['generated_text']
        if not raw:
            raw = "I am unable to generate a response."

        current_response = raw
        current_cis, current_metrics = compute_cis(user_input, current_response)

        for _ in range(self.max_improvements):
            if current_cis >= self.threshold:
                break
            improved = improve_response(user_input, current_response)
            new_cis, new_metrics = compute_cis(user_input, improved)
            if new_cis > current_cis:
                current_response = improved
                current_cis = new_cis
                current_metrics = new_metrics
            else:
                break

        return current_response, current_cis, current_metrics

# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    bot = CISTruthBot(threshold=7.0, max_improvements=3)

    print("CIS Truth Bot v2.0 (type 'exit' to quit)\n")
    while True:
        user = input("You: ")
        if user.lower() == "exit":
            break
        response, score, metrics = bot.generate(user)
        print(f"\nAI: {response}")
        print(f"CIS Score: {score:.2f} / 10")
        print(f"  Alignment: {metrics['alignment']:.3f}")
        print(f"  Accuracy: {metrics['accuracy']:.3f}")
        print(f"  Distortion: {metrics['distortion']:.3f}")
        print(f"  Confidence: {metrics['confidence']:.3f}")
        print(f"  Length penalty: {metrics['length_penalty']:.3f}")
        print("  Retrieved context:")
        for doc in metrics['context']:
            print(f"    - {doc}")
        print()
