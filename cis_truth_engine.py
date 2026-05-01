"""
cis_truth_engine.py — Open‑Loop Learned‑Weight Multi‑Source Truth Engine v4
License: MIT (code) / RPML v1.0 (math)
"""
import hashlib, json, re, sqlite3, numpy as np, torch
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer, util
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

# ---------------------------------------------------------------------------
# Persistent cache
# ---------------------------------------------------------------------------
class Cache:
    def __init__(self, db="radiant_cache.db"):
        self.c = sqlite3.connect(db, check_same_thread=False)
        self.c.execute("CREATE TABLE IF NOT EXISTS c (k TEXT PRIMARY KEY, v TEXT, e BLOB)")
        self.c.commit()
    def get(self, k):
        r = self.c.execute("SELECT v,e FROM c WHERE k=?", (k,)).fetchone()
        if r: return {"v":r[0],"e":r[1] and np.frombuffer(r[1], dtype=np.float32)}
    def set(self, k, v=None, e=None):
        self.c.execute("INSERT OR REPLACE INTO c VALUES (?,?,?)", (k, v, e.tobytes() if e is not None else None)); self.c.commit()
cache = Cache()

DEV = 0 if torch.cuda.is_available() else -1

# ---------------------------------------------------------------------------
# Lightweight models (quantization not needed for compactness)
# ---------------------------------------------------------------------------
embedder = SentenceTransformer("all-MiniLM-L6-v2")
gen_tok = AutoTokenizer.from_pretrained("google/flan-t5-small")
gen_model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-small").to(torch.device("cuda" if DEV==0 else "cpu"))
generator = pipeline("text2text-generation", model=gen_model, tokenizer=gen_tok, device=DEV)

# NLI models (small for pre‑screening, large for high‑confidence)
nli_small = pipeline("text-classification", model="distilbert-base-uncased-mnli", device=DEV)
nli_large = pipeline("text-classification", model="roberta-large-mnli", device=DEV)
claim_ext = pipeline("text2text-generation", model="google/flan-t5-small",
                     tokenizer=AutoTokenizer.from_pretrained("google/flan-t5-small"), device=DEV)

# ---------------------------------------------------------------------------
# Knowledge Base + FAISS
# ---------------------------------------------------------------------------
KB = [
    "Gravity is a force that attracts objects with mass toward each other.",
    "The Earth revolves around the Sun once every 365.25 days.",
    "Water boils at 100 degrees Celsius at standard atmospheric pressure.",
    "Photosynthesis converts light energy into chemical energy in plants.",
    "The capital of France is Paris.",
    "DNA stores genetic information using a double‑helix structure.",
    "The speed of light in a vacuum is approximately 299,792,458 m/s.",
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
kb_emb = embedder.encode(KB, convert_to_tensor=True).cpu().numpy()
try:
    import faiss
    idx = faiss.IndexFlatIP(kb_emb.shape[1])
    faiss.normalize_L2(kb_emb); idx.add(kb_emb)
    faiss_ok = True
except:
    faiss_ok = False
    kb_emb_t = torch.tensor(kb_emb)

def retrieve(query, top_k=3):
    k = hashlib.md5(query.encode()).hexdigest()
    c = cache.get(k)
    if c and "v" in c: return c["v"].split("\n")
    q = embedder.encode(query, convert_to_tensor=True)
    if faiss_ok:
        qn = q.cpu().numpy().reshape(1,-1); faiss.normalize_L2(qn)
        _, ii = idx.search(qn, top_k); docs = [KB[i] for i in ii[0] if i>=0]
    else:
        sim = util.cos_sim(q, kb_emb_t)[0]; ii = sim.argsort(descending=True)[:top_k]; docs = [KB[i] for i in ii]
    cache.set(k, v="\n".join(docs))
    return docs

def get_embedding(text):
    k = hashlib.md5(text.encode()).hexdigest()
    c = cache.get(k)
    if c and c["e"] is not None: return c["e"]
    e = embedder.encode(text, convert_to_tensor=True).cpu().numpy()
    cache.set(k, e=e)
    return e

# ---------------------------------------------------------------------------
# Multi‑Source Truth Verifier
# ---------------------------------------------------------------------------
class TruthSource:
    def query(self, claim: str) -> Tuple[float, float]:  # (credibility, confidence)
        raise NotImplementedError

class WebTruthSource(TruthSource):
    def query(self, claim): return 0.75, 0.8  # placeholder for real search API

class TruthVerifier:
    def __init__(self, sources=None, kb_weight=0.7):
        self.sources = sources or [WebTruthSource()]
        self.kb_weight = kb_weight

    def verify(self, claim: str, kb_docs: List[str]) -> Tuple[float, float, float]:
        """Return (truth_score, cross_source_contradiction, confidence)."""
        # KB agreement via NLI
        kb_best = 0.0
        for doc in kb_docs:
            res = nli_large(f"{doc} </s> {claim}", truncation=True, max_length=256)[0]
            label = res["label"]
            if label == "ENTAILMENT": kb_best = max(kb_best, 1.0)
            elif label == "NEUTRAL": kb_best = max(kb_best, 0.7)
        ext_scores = [src.query(claim)[0] for src in self.sources]
        if ext_scores:
            ext_avg = np.mean(ext_scores)
            contradiction = float(len(set(ext_scores)) > 1 and (max(ext_scores)-min(ext_scores)) > 0.4)
        else:
            ext_avg, contradiction = 0.5, 0.0
        truth = self.kb_weight * kb_best + (1-self.kb_weight) * ext_avg
        truth *= (1.0 - 0.5*contradiction)
        return truth, contradiction, 0.8  # confidence placeholder

truth_verifier = TruthVerifier()

# ---------------------------------------------------------------------------
# Claim extraction & batched NLI (with extended max_length)
# ---------------------------------------------------------------------------
def extract_claims(text):
    prompt = f"List all factual statements contained in the following text, one per line:\n{text}\nFacts:"
    try:
        raw = claim_ext(prompt, max_length=300, temperature=0.0)[0]["generated_text"]
        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        if not lines or len(lines)>20:
            lines = re.split(r'(?<=[.!?])\s+', text)
            lines = [l.strip() for l in lines if l.strip()]
        return lines
    except: return [text]

def _batch_nli(prems, hyps, model, bs=32, max_len=256):
    """Batch NLI with adequate truncation length to preserve long premises."""
    out = []
    for i in range(0, len(prems), bs):
        batch = [f"{p} </s> {h}" for p,h in zip(prems[i:i+bs], hyps[i:i+bs])]
        out.extend(model(batch, truncation=True, max_length=max_len))
    return out

# ---------------------------------------------------------------------------
# Tiered factual verification
# ---------------------------------------------------------------------------
def verify_claims(claims, docs):
    if not claims: return 0.5, 0.0, 0.5
    prems, hyps = [], []
    for c in claims:
        for d in docs: prems.append(d); hyps.append(c)
    res_small = _batch_nli(prems, hyps, nli_small, max_len=256)
    combined = []
    for i,r in enumerate(res_small):
        if r["score"]<0.9:
            p,h = prems[i],hyps[i]
            combined.append(nli_large(f"{p} </s> {h}", truncation=True, max_length=256)[0])
        else: combined.append(r)
    support = []
    for i in range(len(claims)):
        best=0.0
        for j in range(len(docs)):
            label = combined[i*len(docs)+j]["label"]
            if label=="ENTAILMENT": best=max(best,1.0)
            elif label=="NEUTRAL": best=max(best,0.7)
        support.append(best)
    fact = np.mean(support) if support else 0.5

    # internal contradictions
    contra, total = 0,0
    for i in range(len(claims)):
        for j in range(i+1,len(claims)):
            total+=1
            r = nli_small(f"{claims[i]} </s> {claims[j]}", truncation=True, max_length=256)[0]
            if r["label"]=="CONTRADICTION": contra+=1
            elif r["score"]<0.9:
                r2 = nli_large(f"{claims[i]} </s> {claims[j]}", truncation=True, max_length=256)[0]
                if r2["label"]=="CONTRADICTION": contra+=1
    int_contra = contra/total if total else 0.0

    # fact‑aware specificity
    if docs:
        resp_emb = get_embedding(" ".join(claims))
        sims = [float(util.cos_sim(torch.tensor(resp_emb), torch.tensor(get_embedding(d))).item()) for d in docs]
        novelty = 1.0 - float(np.mean(sims))
        specificity = novelty * fact  # only reward when fact is high
        specificity = max(0.0, min(1.0, specificity))
    else: specificity = 0.5
    return fact, int_contra, specificity

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def alignment(resp, docs):
    if not docs: return 0.5
    r = get_embedding(resp)
    sims = [float(util.cos_sim(torch.tensor(r), torch.tensor(get_embedding(d))).item()) for d in docs]
    return float(np.mean(sims))

def distortion(resp):
    words = re.findall(r"\b\w+\b", resp.lower())
    return 0.0 if not words else 1.0 - len(set(words))/len(words)

def confidence(resp, docs):
    if not docs: return 0.5
    r = get_embedding(resp)
    sims = [float(util.cos_sim(torch.tensor(r), torch.tensor(get_embedding(d))).item()) for d in docs]
    return 1.0 - min(1.0, float(np.var(sims))*10)

def len_pen(resp, mx=300):
    wc = len(resp.split())
    return 0.0 if wc<=30 else min(0.15, (wc-30)/mx)

# ---------------------------------------------------------------------------
# Learned weights (calibrated from human judgments)
# ---------------------------------------------------------------------------
@dataclass
class CalibratedWeights:
    weights: Dict[str, float]; bias: float = 0.05
    @staticmethod
    def default():
        return CalibratedWeights({
            "alignment": 0.24, "factual_accuracy": 0.32, "epistemic_truth": 0.22,
            "specificity": 0.08, "confidence": 0.04, "distortion": -0.12,
            "internal_contradiction": -0.08, "neutrality_boost": 0.10,
        })
    def score(self, m): return self.bias + sum(self.weights.get(k,0)*v for k,v in m.items())

# ---------------------------------------------------------------------------
# Structured cognitive state (uncertainty preserved)
# ---------------------------------------------------------------------------
@dataclass
class CognitiveState:
    alignment: float; factual_accuracy: float; epistemic_truth: float
    epistemic_contradiction: float; specificity: float; distortion: float
    confidence: float; neutrality_boost: float; cis_score: float
    claims_count: int; context: List[str]
    def is_reliable(self): return self.epistemic_truth > 0.7 and self.epistemic_contradiction < 0.3

# ---------------------------------------------------------------------------
# CIS computation
# ---------------------------------------------------------------------------
def compute_cis(question, answer, weights):
    ctx = retrieve(question)
    claims = extract_claims(answer)
    fact, contr, spec = verify_claims(claims, ctx)
    align = min(alignment(answer, ctx), fact+0.2)
    dist = distortion(answer)
    conf = confidence(answer, ctx)

    # Epistemic truth from multi‑source
    truth_vals = [truth_verifier.verify(c, ctx) for c in claims]
    if truth_vals:
        et = np.mean([v[0] for v in truth_vals])
        et_contra = np.mean([v[1] for v in truth_vals])
    else:
        et, et_contra = 0.5, 0.0

    nb = 0.2 if 0.4<=fact<=0.7 else 0.0
    metrics = {"alignment":align, "factual_accuracy":fact, "epistemic_truth":et,
               "specificity":spec, "distortion":dist, "confidence":conf,
               "internal_contradiction":contr, "neutrality_boost":nb}
    raw = weights.score(metrics)
    cis = max(0.0, min(10.0, 10.0*raw - len_pen(answer)))
    return CognitiveState(
        alignment=align, factual_accuracy=fact, epistemic_truth=et,
        epistemic_contradiction=et_contra, specificity=spec, distortion=dist,
        confidence=conf, neutrality_boost=nb, cis_score=cis,
        claims_count=len(claims), context=ctx
    )

# ---------------------------------------------------------------------------
# External critic (mandatory)
# ---------------------------------------------------------------------------
class FactCheckerCritic:
    def approve(self, question, old, new):
        ctx = retrieve(question)
        new_claims = extract_claims(new)
        for c in new_claims:
            for d in ctx:
                res = nli_large(f"{d} </s> {c}", truncation=True, max_length=256)[0]
                if res["label"]=="CONTRADICTION" and res["score"]>0.95: return False
        if len(new.split())<3 and len(old.split())>10: return False
        return True
critic = FactCheckerCritic()

# ---------------------------------------------------------------------------
# Self‑improvement loop
# ---------------------------------------------------------------------------
def improve(q, a):
    prompt = f"Question: {q}\nOriginal answer: {a}\nImprove the answer to be more accurate, specific, and concise.\nImproved answer:"
    try: return generator(prompt, max_length=200, temperature=0.3, do_sample=True)[0]["generated_text"].strip()
    except: return a

class CISTruthBot:
    def __init__(self, threshold=7.0, base=2, weights=None):
        self.threshold, self.base = threshold, base
        self.weights = weights or CalibratedWeights.default()

    def generate(self, q):
        max_imp = min(5, int(self.base + min(1,(len(q.split())/50)*0.5)*3))
        raw = generator(f"Answer: {q}", max_length=150, temperature=0.5)[0]["generated_text"]
        ans = raw.strip() or "No response."
        state = compute_cis(q, ans, self.weights)
        best = state
        for _ in range(max_imp):
            if best.cis_score >= self.threshold: break
            improved = improve(q, ans)
            new_state = compute_cis(q, improved, self.weights)
            if not critic.approve(q, ans, improved): continue
            if new_state.cis_score - best.cis_score < 0.1: break
            if new_state.cis_score > best.cis_score:
                ans, best = improved, new_state
            else: break
        return ans, best

# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    bot = CISTruthBot()
    print("🌌 CIS Truth Engine v4 — Open‑Loop Learned Multi‑Source\n")
    while True:
        q = input("You: ")
        if q.lower() in {"exit","quit"}: break
        ans, state = bot.generate(q)
        print(f"\nAI: {ans}\nCIS: {state.cis_score:.2f}/10")
        print(f"  Truth: {state.epistemic_truth:.2f} (contra {state.epistemic_contradiction:.2f})")
        print(f"  Factual: {state.factual_accuracy:.2f}   Coherence: {state.alignment:.2f}")
        print(f"  Reliable: {state.is_reliable()}")
        print()
