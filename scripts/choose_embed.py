import json, pathlib, numpy as np
from sentence_transformers import SentenceTransformer

ROOT = pathlib.Path(__file__).resolve().parents[1]
EMB_NPY  = ROOT / "data" / "radicals_embeds.npy"
IDX_JSON = ROOT / "data" / "radicals_index.json"

# tiny, human-readable trace for "why"
def explain(query, item):
    q = query.lower()
    hits = []
    for tok in (item["gloss"].split()):
        if tok in q or q in tok:
            hits.append(tok)
    why = f'matches: {", ".join(hits)}' if hits else "semantic nearest by embedding"
    return why

_model = None
def model():
    global _model
    if _model is None:
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model

def choose(word: str, k: int = 2):
    X = np.load(EMB_NPY)
    idx = json.loads(pathlib.Path(IDX_JSON).read_text(encoding="utf-8"))
    qv = model().encode([word], normalize_embeddings=True)[0]
    sims = (X @ qv)  # cosine since both normalized
    order = np.argsort(-sims)[:k]
    picks = []
    for i, j in enumerate(order, 1):
        it = idx[j]
        picks.append({
            "rank": i,
            "num": it["num"],
            "id": it["id"],
            "pinyin": it["pinyin"],
            "gloss": it["gloss"],
            "score": float(sims[j]),
            "why": explain(word, it)
        })
    return picks

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python scripts/choose_embed.py <word> [k]")
        raise SystemExit(1)
    word = sys.argv[1]
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    for r in choose(word, k):
        print(f"{r['rank']}. {r['id']}  (#{r['num']} {r['pinyin']} — {r['gloss']})  sim={r['score']:.3f}  [{r['why']}]")
