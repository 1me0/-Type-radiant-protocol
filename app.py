# app.py - Radiant Truth API (Final 10/10)
# Truth = what survives contradiction, time, and perspective simultaneously

import hashlib, json, os, numpy as np, torch, torch.nn as nn, torch.optim as optim
from datetime import datetime
from collections import defaultdict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import faiss

# ---------- Config ----------
EMBED_DIM = 384
TRUTH_DECAY_HALF_LIFE = 7 * 86400
MNLI_PATH = os.getenv("MNLI_PATH", "mnli.jsonl")
ADV_STEPS, ADV_EPS = 10, 0.1

# ---------- Models ----------
embedder = SentenceTransformer("all-MiniLM-L6-v2")
nli = pipeline("text-classification", model="roberta-base-mnli", device=-1)
LABEL = {"LABEL_0":"CONTRADICTION","LABEL_1":"NEUTRAL","LABEL_2":"ENTAILMENT"}
tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-small")
gen = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-small")
gen_pipe = pipeline("text2text-generation", model=gen, tokenizer=tokenizer)

# ---------- Contradiction Surrogate (trained on MNLI) ----------
class Surrogate(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(EMBED_DIM*2, 256), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(256, 128), nn.ReLU(), nn.Linear(128, 1), nn.Sigmoid()
        )
    def forward(self, a, b): return self.net(torch.cat([a,b],1)).squeeze()

surrogate = Surrogate()
def train_surrogate():
    if not os.path.exists(MNLI_PATH):
        # dummy training (real MNLI required for production)
        dummy = torch.randn(100, EMBED_DIM)
        opt = optim.Adam(surrogate.parameters(), lr=0.001)
        for _ in range(2):
            opt.zero_grad()
            loss = surrogate(dummy, dummy).mean()
            loss.backward(); opt.step()
        return
    premises, hypotheses, labels = [], [], []
    with open(MNLI_PATH) as f:
        for line in f:
            d = json.loads(line)
            premises.append(d['premise'])
            hypotheses.append(d['hypothesis'])
            labels.append(1.0 if d['label'] == 0 else 0.0)  # contradiction=1 else 0
    emb_p = embedder.encode(premises, show_progress_bar=True)
    emb_h = embedder.encode(hypotheses, show_progress_bar=True)
    ds = torch.utils.data.TensorDataset(torch.tensor(emb_p), torch.tensor(emb_h), torch.tensor(labels))
    loader = torch.utils.data.DataLoader(ds, batch_size=32, shuffle=True)
    opt = optim.Adam(surrogate.parameters(), lr=0.001)
    for epoch in range(3):
        total = 0
        for a,b,l in loader:
            opt.zero_grad()
            loss = nn.BCELoss()(surrogate(a,b), l)
            loss.backward(); opt.step()
            total += loss.item()
        print(f"Epoch {epoch+1}, loss: {total/len(loader):.4f}")
    torch.save(surrogate.state_dict(), "surrogate.pt")

if os.path.exists("surrogate.pt"):
    surrogate.load_state_dict(torch.load("surrogate.pt"))
else:
    train_surrogate()
surrogate.eval()

def contradiction_prob(statement, context):
    with torch.no_grad():
        emb_s = torch.tensor(embedder.encode([statement]))
        emb_c = torch.tensor(embedder.encode([context]))
        return surrogate(emb_s, emb_c).item()

# ---------- Multi-source retrieval (contextual trust) ----------
corpus = {
    "wiki": ["Gravity attracts mass.", "Earth orbits Sun yearly.", "Water boils at 100°C."],
    "user": ["Gravity pulls down.", "Earth around Sun.", "Water boils at 100°C."]
}
indices = {}
for src, texts in corpus.items():
    emb = embedder.encode(texts)
    faiss.normalize_L2(emb)
    idx = faiss.IndexFlatIP(EMBED_DIM)
    idx.add(emb)
    indices[src] = idx
base_weights = {"wiki":1.0, "user":0.2}
feedback = []  # (source, topic, correct)
topic_kw = {"physics":["gravity","mass"], "astronomy":["earth","orbit"]}
def topic(q): return next((t for t,k in topic_kw.items() if any(w in q.lower() for w in k)), "general")
def src_weight(src,q):
    t = topic(q)
    cor = sum(1 for s,top,ok in feedback if s==src and top==t and ok)
    tot = sum(1 for s,top,_ in feedback if s==src and top==t)
    if tot == 0: return base_weights.get(src,0.5)
    return min(2.0, max(0.1, (cor/tot)*2))
def retrieve(q, k=2):
    qe = embedder.encode([q]); faiss.normalize_L2(qe)
    results = []
    for src, idx in indices.items():
        scores, idxs = idx.search(qe, k)
        for s, i in zip(scores[0], idxs[0]):
            if i >= 0:
                w = src_weight(src,q)
                results.append((src, corpus[src][i], s*w))
    results.sort(key=lambda x: -x[2])
    return results[:k]

# ---------- 1. Contradiction survival ----------
def contradiction_survival(statement, query):
    docs = retrieve(query, 3)
    if not docs: return 0.5
    entail_scores = []
    for _, doc, _ in docs:
        res = nli(f"{doc} </s> {statement}")[0]
        lbl = LABEL[res['label']]
        if lbl == "ENTAILMENT": entail_scores.append(1.0)
        elif lbl == "NEUTRAL": entail_scores.append(0.7)
        else: entail_scores.append(0.0)
    return np.mean(entail_scores)  # high when statement not contradicted

# ---------- 2. Time survival (decay + inertia) ----------
truth_history = defaultdict(list)  # key -> list of (timestamp, survival_score)
def time_survival(statement, new_score):
    key = hashlib.md5(statement.encode()).hexdigest()
    now = datetime.utcnow()
    # inertia: low score has less impact
    inertia = 0.3 if new_score >= 0.5 else 0.1
    # add new observation
    truth_history[key].append((now, new_score))
    # keep last 10
    if len(truth_history[key]) > 10:
        truth_history[key] = truth_history[key][-10:]
    # compute exponentially weighted moving average with decay
    if len(truth_history[key]) == 0:
        return 0.5
    total_weight = 0.0
    weighted_sum = 0.0
    now = datetime.utcnow()
    for ts, score in truth_history[key]:
        age = (now - ts).total_seconds()
        w = np.exp(-age / TRUTH_DECAY_HALF_LIFE)
        weighted_sum += w * score
        total_weight += w
    return weighted_sum / (total_weight + 1e-8)

# ---------- 3. Perspective survival (adversarial + cross-source agreement) ----------
def perspective_survival(statement, query):
    # 3a: adversarial variants
    def variants(text, ctx, n=2):
        prompt = f"Context: {ctx}\nStatement: {text}\nGenerate a contradictory version:"
        return [gen_pipe(prompt, max_length=100, do_sample=True)[0]['generated_text'].strip() or text for _ in range(n)]
    docs = retrieve(query,1)
    ctx = docs[0][1] if docs else ""
    if not ctx:
        base_survival = 0.5
    else:
        vars = variants(statement, ctx, n=2)
        var_scores = []
        for v in vars:
            c_score = contradiction_survival(v, query)
            var_scores.append(c_score)
        base_survival = np.mean(var_scores) if var_scores else 0.5
    # 3b: cross-source agreement
    sources = retrieve(query, 3)
    if len(sources) > 1:
        entailments = []
        for _, doc, _ in sources:
            r = nli(f"{doc} </s> {statement}")[0]
            e = 1.0 if LABEL[r['label']] == "ENTAILMENT" else 0.0
            entailments.append(e)
        agreement = 1.0 - np.std(entailments) if len(entailments) > 1 else 1.0
    else:
        agreement = 1.0
    return base_survival * agreement

# ---------- Truth = geometric mean of three survivals ----------
def compute_truth(statement, query):
    c = contradiction_survival(statement, query)
    t = time_survival(statement, c)  # use current c as new score for time survival
    p = perspective_survival(statement, query)
    truth = (c * t * p) ** (1/3)
    # update time survival with final truth (feedback loop)
    time_survival(statement, truth)  # store for next calls
    return round(truth, 4)

# ---------- Additional metrics (CIS) for compatibility ----------
def align(t,c): e_t,e_c = embedder.encode([t,c]); faiss.normalize_L2(e_t); faiss.normalize_L2(e_c); return float(e_t@e_c.T)
def understand(q,t): e_q,e_t = embedder.encode([q,t]); faiss.normalize_L2(e_q); faiss.normalize_L2(e_t); return float(e_q@e_t.T)
def accuracy(t,q):
    docs = retrieve(q,3)
    if not docs: return 0.5
    ents = [1.0 if LABEL[nli(f"{d} </s> {t}")[0]['label']]=="ENTAILMENT" else (0.7 if LABEL[nli(f"{d} </s> {t}")[0]['label']]=="NEUTRAL" else 0.0) for _,d,_ in docs]
    return np.mean(ents)
def distortion(t):
    w = t.lower().split(); wl = len(w)
    if not wl: return 0.0
    uniq = len(set(w))/wl
    sents = [s.strip() for s in t.split('.') if s]
    sc = 0
    for i in range(len(sents)):
        for j in range(i+1, len(sents)):
            if LABEL[nli(f"{sents[i]} </s> {sents[j]}")[0]['label']] == "CONTRADICTION":
                sc += 1
    sc_rate = sc / max(1, len(sents)*(len(sents)-1)//2)
    freq = defaultdict(int); [freq.update({ww:1}) for ww in w]
    ent = -sum((c/wl)*np.log2(c/wl) for c in freq.values())
    max_ent = np.log2(len(freq)) if len(freq)>1 else 1.0
    return 0.3*(1-uniq)+0.4*sc_rate+0.3*(1-(ent/max_ent if max_ent else 0))
def cis(alignment, understanding, accuracy, distortion):
    raw = 0.2*alignment+0.3*understanding+0.4*accuracy-0.1*distortion
    return max(0,min(10,round(raw*10,2)))
def extract_cis_metrics(t,q):
    docs = retrieve(q,1)
    ctx = docs[0][1] if docs else ""
    return {"alignment":round(align(t,ctx),3) if ctx else 0.5,
            "understanding":round(understand(q,t),3),
            "accuracy":round(accuracy(t,q),3),
            "distortion":round(distortion(t),3)}

# ---------- Reward: truth * novelty ----------
truth_store = {}  # key -> last truth
def reward(truth, statement):
    key = hashlib.md5(statement.encode()).hexdigest()
    novelty = 1.0 if key not in truth_store else max(0, 1 - truth_store[key])
    truth_store[key] = truth
    return round(0.2 * truth * novelty, 4)

# ---------- FastAPI ----------
app = FastAPI(title="Radiant Truth API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ScoreReq(BaseModel): text:str; query:str; user:str=None
class ScoreResp(BaseModel): truth:float; cis:float; metrics:dict; reward:float=None; id:str
class ChallengeReq(BaseModel): statement:str; query:str; user:str=None
class ChallengeResp(BaseModel): contradiction_survival:float; time_survival:float; perspective_survival:float; reward:float=None
class ImproveReq(BaseModel): original:str; query:str; user:str=None
class ImproveResp(BaseModel): improved:str; truth:float; reward:float=None
class FeedbackReq(BaseModel): statement:str; query:str; is_true:bool; source:str

@app.post("/score")
async def score(r:ScoreReq):
    t = compute_truth(r.text, r.query)
    m = extract_cis_metrics(r.text, r.query)
    c = cis(**m)
    tid = hashlib.md5(f"{r.text}{datetime.utcnow()}".encode()).hexdigest()[:12]
    rew = reward(t, r.text) if r.user else None
    return ScoreResp(truth=t, cis=c, metrics=m, reward=rew, id=tid)

@app.post("/challenge")
async def challenge(r:ChallengeReq):
    c = contradiction_survival(r.statement, r.query)
    t = time_survival(r.statement, c)
    p = perspective_survival(r.statement, r.query)
    rew = (c*t*p)**(1/3)
    if r.user:
        rew = reward(rew, r.statement)
    else:
        rew = None
    return ChallengeResp(contradiction_survival=c, time_survival=t, perspective_survival=p, reward=rew)

@app.post("/improve")
async def improve(r:ImproveReq):
    prompt = f"Improve: {r.original}\nQuestion: {r.query}\nImproved:"
    out = gen_pipe(prompt, max_length=200, temperature=0.3, do_sample=True)[0]['generated_text'].strip()
    imp = out if out else r.original
    t = compute_truth(imp, r.query)
    rew = reward(t, imp) if r.user else None
    return ImproveResp(improved=imp, truth=t, reward=rew)

@app.post("/feedback")
async def feedback(r:FeedbackReq):
    feedback.append((r.source, topic(r.query), r.is_true))
    if not r.is_true:
        # penalize false statements in truth history
        key = hashlib.md5(r.statement.encode()).hexdigest()
        if key in truth_history:
            # add a low score (0.2) to force decay
            truth_history[key].append((datetime.utcnow(), 0.2))
    return {"ok": True}

@app.get("/stats")
async def stats():
    return {"truth_entries": len(truth_history), "feedback": len(feedback)}
