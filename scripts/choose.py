# scripts/choose.py
# Usage:  python scripts/choose.py ocean 3
# Prints the top-k radicals (default k=2) with simple explanations.

import json, pathlib, re, sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAD_PATH = ROOT / "data" / "radicals_214.json"

# tiny synonym expander (extend freely)
SYN = {
    "ocean": ["sea","water","wave","liquid","river"],
    "sea": ["ocean","water","wave","fish"],
    "love": ["heart","feeling","emotion","affection"],
    "speak": ["mouth","voice","speech","say","talk"],
    "fire": ["heat","hot","flame","burn","ember"],
    "tree": ["wood","forest","plant"],
    "mountain": ["hill","rock","peak","stone"],
    "rain": ["cloud","storm","wet","drop"],
    "knife": ["cut","blade","sharp"],
    "gold": ["metal","money"],
    "water": ["liquid","river","sea","ocean","wave","wet","flow"],
    "fire": ["heat","hot","flame","burn","ember"],
    "wood": ["tree","forest","plant","timber"],
    "earth": ["ground","soil","clay","dirt"],
    "stone": ["rock","mountain","pebble"],
    "mouth": ["speak","say","voice","taste","speech","language","talk"],
    "heart": ["mind","feeling","emotion","love","thought","spirit"],
    "hand": ["hold","grasp","touch","manual","craft"],
    "foot": ["walk","step","kick","leg","run"],
    "rain": ["cloud","storm","weather","drop","wet"],
    "sun": ["day","light","bright"],
    "moon": ["night","month","time"],
    "knife": ["cut","blade","sharp"],
    "metal": ["gold","money","iron","steel"],
    "food": ["eat","grain","rice","meal"],
    "silk": ["thread","string","textile","cloth"],
    "bird": ["feather","wing","fly"],
    "dog": ["animal","beast","hound"],
    "horse": ["ride","animal","stallion"],
    "fish": ["seafood","river","swim"],
}

def toks(s: str):
    return [w for w in re.split(r"[^a-z]+", s.lower()) if w]

def query_tokens(q: str):
    base = toks(q)
    expanded = []
    for w in base:
        expanded += SYN.get(w, [])
    return base + expanded

def load_radicals():
    return json.loads(RAD_PATH.read_text(encoding="utf-8"))

def score_and_explain(q_tokens, item):
    # text for each radical = gloss + tags
    text_tokens = set(toks(item["gloss"]) + item.get("tags", []))
    hits = [t for t in q_tokens if t in text_tokens]
    # score = exact token matches + small bonus for substring matches
    substr_hits = []
    for t in set(q_tokens):
        if not any(t == h for h in text_tokens):
            if any(t in x or x in t for x in text_tokens):
                substr_hits.append(t)
    score = len(hits) * 3 + len(substr_hits)
    return score, hits, substr_hits

def choose(word: str, k: int = 2):
    items = load_radicals()
    q_tokens = query_tokens(word)
    ranked = []
    for it in items:
        sc, hits, subs = score_and_explain(q_tokens, it)
        ranked.append((sc, hits, subs, it))
    ranked.sort(key=lambda x: x[0], reverse=True)
    top = [r for r in ranked if r[0] > 0][:k] or ranked[:k]  # fallback to top arbitrary
    result = []
    for sc, hits, subs, it in top:
        result.append({
            "num": it["num"],
            "id": it["id"],
            "pinyin": it["pinyin"],
            "gloss": it["gloss"],
            "score": sc,
            "matched_tokens": hits,
            "fuzzy_tokens": subs,
        })
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/choose.py <english_word> [k]")
        sys.exit(1)
    word = sys.argv[1]
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    picks = choose(word, k)
    print(f'Query: "{word}" → top {k} radicals')
    for i, r in enumerate(picks, 1):
        why = []
        if r["matched_tokens"]:
            why.append("matches: " + ", ".join(r["matched_tokens"]))
        if r["fuzzy_tokens"]:
            why.append("fuzzy: " + ", ".join(r["fuzzy_tokens"]))
        why_s = "; ".join(why) or "no direct match (fallback)"
        print(f"{i}. {r['id']}  (#{r['num']} {r['pinyin']} — {r['gloss']})  score={r['score']}  [{why_s}]")
