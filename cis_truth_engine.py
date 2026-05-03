"""
cis_truth_engine.py — Compact Truth Engine v5
MIT (code) / RPML v1.0 (math)
"""
import hashlib, json, logging, re, sqlite3, time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import numpy as np, requests, torch
from sentence_transformers import SentenceTransformer, util
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("cis")

class Cache:
    def __init__(self, db="cis_cache.db"):
        self.c = sqlite3.connect(db, check_same_thread=False)
        self.c.execute("CREATE TABLE IF NOT EXISTS c (k TEXT PRIMARY KEY, v TEXT, e BLOB)")
        self.c.commit()
    def get(self, k):
        r = self.c.execute("SELECT v,e FROM c WHERE k=?", (k,)).fetchone()
        return {"v":r[0],"e":np.frombuffer(r[1],dtype=np.float32) if r and r[1] else None} if r else None
    def set(self, k, v=None, e=None):
        self.c.execute("INSERT OR REPLACE INTO c VALUES (?,?,?)", (k, v, e.tobytes() if e is not None else None)); self.c.commit()
cache = Cache()

DEV = 0 if torch.cuda.is_available() else -1
embedder = SentenceTransformer("all-MiniLM-L6-v2")
gen = pipeline("text2text-generation", model="google/flan-t5-small", device=DEV)
nli_small = pipeline("text-classification", model="distilbert-base-uncased-mnli", device=DEV)
nli_large = pipeline("text-classification", model="roberta-large-mnli", device=DEV)
claim_ext = pipeline("text2text-generation", model="google/flan-t5-small", device=DEV)

def load_kb(src="builtin"):
    """Load documents from a JSON file, directory of .txt files, or the builtin corpus."""
    if src == "builtin":
        return [
            "Gravity attracts masses.", "Earth orbits Sun yearly.", "Water boils at 100°C.",
            "Photosynthesis produces energy.", "Paris is France's capital.", "DNA is a double helix.",
            "Speed of light ~3e8 m/s.", "Humans have 46 chromosomes.", "Mitochondria produce ATP.",
            "a²+b²=c² in right triangles.", "Oxygen needed for respiration.", "Yen is Japanese currency.",
            "Everest is highest mountain.", "Hamlet by Shakespeare.", "Amazon is largest river by flow.",
            "C language by Ritchie.", "Great Wall >13k miles.", "Water density peaks at 4°C.",
            "Sound faster in solids.", "Bats are flying mammals."
        ]
    p = Path(src)
    if p.is_file() and p.suffix == ".json":
        try: return json.loads(p.read_text())
        except: pass
    if p.is_dir():
        docs = [f.read_text(encoding="utf-8") for f in sorted(p.glob("*.txt")) if f.stat().st_size>0]
        if docs: return docs
    log.warning(f"KB source {src} invalid, using builtin")
    return load_kb("builtin")

KB = load_kb()
kb_emb = embedder.encode(KB, convert_to_tensor=True).cpu().numpy()
try:
    import faiss
    idx = faiss.IndexFlatIP(kb_emb.shape[1])
    faiss.normalize_L2(kb_emb); idx.add(kb_emb)
    faiss_ok = True
except ImportError:
    faiss_ok = False
    kb_emb_t = torch.tensor(kb_emb)

def retrieve(q, top_k=3):
    k = hashlib.md5(q.encode()).hexdigest()
    c = cache.get(k)
    if c and c["v"]: return c["v"].split("\n")
    emb = embedder.encode(q, convert_to_tensor=True)
    if faiss_ok:
        qn = emb.cpu().numpy().reshape(1,-1); faiss.normalize_L2(qn)
        _, ii = idx.search(qn, top_k); docs = [KB[i] for i in ii[0] if i>=0]
    else:
        sim = util.cos_sim(emb, kb_emb_t)[0]; ii = sim.argsort(descending=True)[:top_k]; docs = [KB[i] for i in ii]
    cache.set(k, v="\n".join(docs))
    return docs

def get_emb(text):
    k = hashlib.md5(text.encode()).hexdigest()
    c = cache.get(k)
    if c and c["e"] is not None: return c["e"]
    e = embedder.encode(text, convert_to_tensor=True).cpu().numpy()
    cache.set(k, e=e)
    return e

class WikipediaTruthSource:
    BASE = "https://en.wikipedia.org/w/api.php"
    def query(self, claim):
        ck = f"wiki_{hashlib.md5(claim.encode()).hexdigest()}"
        if cache.get(ck) and cache.get(ck)["v"]:
            parts = cache.get(ck)["v"].split(",")
            return float(parts[0]), float(parts[1])
        try:
            r = requests.get(self.BASE, params={"action":"query","list":"search","srsearch":claim,"format":"json","srlimit":1}, timeout=5).json()
            title = r["query"]["search"][0]["title"] if r.get("query",{}).get("search") else None
            if not title: return self._c(ck, 0.5,0.5)
            r2 = requests.get(self.BASE, params={"action":"query","prop":"extracts","exintro":True,"explaintext":True,"titles":title,"format":"json"}, timeout=5).json()
            extract = list(r2["query"]["pages"].values())[0].get("extract","")
            if not extract: return self._c(ck, 0.5,0.5)
            res = nli_large(f"{extract[:1500]} </s> {claim}", truncation=True, max_length=512)[0]
            if res["label"]=="ENTAILMENT": cred = 0.9+0.1*res["score"]
            elif res["label"]=="NEUTRAL": cred = 0.5+0.2*res["score"]
            else: cred = 0.1*res["score"]
            return self._c(ck, max(0,min(1,cred)), res["score"])
        except:
            log.warning(f"Wiki failed for '{claim[:40]}…'")
            return self._c(ck, 0.5,0.3)
    def _c(self,k,c,f): cache.set(k,v=f"{c},{f}"); return c,f

class TruthVerifier:
    def __init__(self):
        self.srcs = [WikipediaTruthSource()]
        self.kbw = 0.7
    def verify(self, claim, docs):
        kb_best = 0.0
        for d in docs:
            r = nli_large(f"{d} </s> {claim}", truncation=True, max_length=256)[0]
            if r["label"]=="ENTAILMENT": kb_best = max(kb_best, 1.0)
            elif r["label"]=="NEUTRAL": kb_best = max(kb_best, 0.7)
        ext = [s.query(claim)[0] for s in self.srcs]
        if ext:
            ext_avg = np.mean(ext)
            contra = float(len(set(ext))>1 and (max(ext)-min(ext))>0.4)
            conf = 1.0 - min(1.0, float(np.std(ext))*2)
        else:
            ext_avg, contra, conf = 0.5, 0.0, 0.5
        truth = self.kbw*kb_best + (1-self.kbw)*ext_avg
        truth *= (1.0 - 0.5*contra)
        return truth, contra, conf
tv = TruthVerifier()

def extract_claims(text):
    try:
        raw = claim_ext(f"List facts:\n{text}\nFacts:", max_length=300, temperature=0.0)[0]["generated_text"]
        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        if not lines or len(lines)>20:
            lines = [l.strip() for l in re.split(r'(?<=[.!?])\s+', text) if l.strip()]
        return lines
    except:
        log.warning("Claim extraction failed", exc_info=True)
        return [text]

def _batch_nli(prems, hyps, model, bs=32):
    out = []
    for i in range(0, len(prems), bs):
        out.extend(model([f"{p} </s> {h}" for p,h in zip(prems[i:i+bs], hyps[i:i+bs])], truncation=True, max_length=256))
    return out

def verify_claims(claims, docs):
    if not claims: return 0.5,0.0,0.5
    prems, hyps = [], []
    for c in claims:
        for d in docs: prems.append(d); hyps.append(c)
    res = _batch_nli(prems, hyps, nli_small)
    combined = []
    for i,r in enumerate(res):
        if r["score"]<0.9:
            combined.append(nli_large(f"{prems[i]} </s> {hyps[i]}", truncation=True, max_length=256)[0])
        else: combined.append(r)
    support = []
    for i in range(len(claims)):
        best=0.0
        for j in range(len(docs)):
            l = combined[i*len(docs)+j]["label"]
            if l=="ENTAILMENT": best=max(best,1.0)
            elif l=="NEUTRAL": best=max(best,0.7)
        support.append(best)
    fact = np.mean(support)
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
    if docs:
        resp_emb = get_emb(" ".join(claims))
        sims = [float(util.cos_sim(torch.tensor(resp_emb), torch.tensor(get_emb(d))).item()) for d in docs]
        spec = max(0, min(1, (1.0-np.mean(sims))*fact))
    else: spec = 0.5
    return fact, int_contra, spec

def alignment(resp, docs):
    if not docs: return 0.5
    r = get_emb(resp)
    return float(np.mean([util.cos_sim(torch.tensor(r), torch.tensor(get_emb(d))).item() for d in docs]))
def distortion(resp):
    words = re.findall(r"\b\w+\b", resp.lower())
    return 0.0 if not words else 1.0 - len(set(words))/len(words)
def confidence(resp, docs):
    if not docs: return 0.5
    r = get_emb(resp)
    sims = [float(util.cos_sim(torch.tensor(r), torch.tensor(get_emb(d))).item()) for d in docs]
    return 1.0 - min(1.0, float(np.var(sims))*10)
def len_pen(resp, mx=300):
    wc = len(resp.split())
    return 0.0 if wc<=30 else min(0.15, (wc-30)/mx)

@dataclass
class Weights:
    w: Dict[str, float]
    b: float = 0.05
    @staticmethod
    def default(): return Weights({"alignment":0.24,"factual_accuracy":0.32,"epistemic_truth":0.22,"specificity":0.08,"confidence":0.04,"distortion":-0.12,"internal_contradiction":-0.08,"neutrality_boost":0.10})
    def score(self, m): return self.b + sum(self.w.get(k,0)*v for k,v in m.items())

@dataclass
class CogState:
    alignment: float; factual_accuracy: float; epistemic_truth: float
    epistemic_contradiction: float; specificity: float; distortion: float
    confidence: float; neutrality_boost: float; cis_score: float
    claims_count: int; context: List[str]
    def reliable(self): return self.epistemic_truth > 0.7 and self.epistemic_contradiction < 0.3

def compute_cis(q, a, w):
    ctx = retrieve(q)
    claims = extract_claims(a)
    fact, contr, spec = verify_claims(claims, ctx)
    align = min(alignment(a, ctx), fact+0.2)
    dist = distortion(a)
    conf = confidence(a, ctx)
    truth_vals = [tv.verify(c, ctx) for c in claims]
    if truth_vals:
        et = np.mean([v[0] for v in truth_vals])
        et_contra = np.mean([v[1] for v in truth_vals])
        et_conf = np.mean([v[2] for v in truth_vals])
    else:
        et, et_contra, et_conf = 0.5, 0.0, 0.5
    nb = 0.2 if 0.4<=fact<=0.7 else 0.0
    m = {"alignment":align,"factual_accuracy":fact,"epistemic_truth":et,"specificity":spec,"distortion":dist,"confidence":et_conf,"internal_contradiction":contr,"neutrality_boost":nb}
    raw = w.score(m)
    cis = max(0.0, min(10.0, 10.0*raw - len_pen(a)))
    return CogState(align, fact, et, et_contra, spec, dist, et_conf, nb, cis, len(claims), ctx)

class FactCheckerCritic:
    def approve(self, q, old, new):
        ctx = retrieve(q)
        for c in extract_claims(new):
            for d in ctx:
                r = nli_large(f"{d} </s> {c}", truncation=True, max_length=256)[0]
                if r["label"]=="CONTRADICTION" and r["score"]>0.95: return False
        return not (len(new.split())<3 and len(old.split())>10)
critic = FactCheckerCritic()

def improve(q, a):
    try: return gen(f"Improve: {q}\nOriginal: {a}\nImproved:", max_length=200, temperature=0.3, do_sample=True)[0]["generated_text"].strip()
    except: log.warning("Improvement failed"); return a

class CISTruthBot:
    def __init__(self, th=7.0, base=2):
        self.th, self.base = th, base
        self.w = Weights.default()
    def generate(self, q):
        mx = min(5, int(self.base + min(1, len(q.split())/50*0.5)*3))
        ans = gen(f"Answer: {q}", max_length=150, temperature=0.5)[0]["generated_text"].strip() or "No response."
        st = compute_cis(q, ans, self.w); best = st
        # Loop: terminate on threshold, critic rejection, or gain<0.1
        for _ in range(mx):
            if best.cis_score >= self.th: break
            imp = improve(q, ans)
            nst = compute_cis(q, imp, self.w)
            if not critic.approve(q, ans, imp): continue
            if nst.cis_score - best.cis_score < 0.1: break
            if nst.cis_score > best.cis_score: ans, best = imp, nst
            else: break
        return ans, best

if __name__ == "__main__":
    bot = CISTruthBot()
    print("🌌 CIS Truth Engine v5 — Compact Production\n")
    while True:
        q = input("You: ")
        if q.lower() in {"exit","quit"}: break
        ans, st = bot.generate(q)
        print(f"\nAI: {ans}\nCIS: {st.cis_score:.2f}/10  Truth: {st.epistemic_truth:.2f}  Reliable: {st.reliable()}\n")
