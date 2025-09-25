# scripts/cedict_lookup.py
# Minimal CC-CEDICT loader: returns best Chinese matches for an English word.

import re, gzip, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CEDICT_GZ = ROOT/"data"/"cedict_1_0_ts_utf-8_mdbg.txt.gz"
CEDICT_TXT = ROOT/"data"/"cedict_ts.u8"

LINE_RE = re.compile(r"^(?P<trad>\S+)\s+(?P<simp>\S+)\s+\[(?P<pinyin>[^\]]+)\]\s+/(?P<defs>.+)/$")

def _ensure_txt():
    if CEDICT_TXT.exists(): return CEDICT_TXT
    # If only the .gz is present, unzip it
    if CEDICT_GZ.exists():
        import gzip, shutil
        with gzip.open(CEDICT_GZ, "rb") as g, open(CEDICT_TXT, "wb") as o:
            shutil.copyfileobj(g, o)
        return CEDICT_TXT
    raise FileNotFoundError("Missing CC-CEDICT. Put cedict_ts.u8 or the MDBG .gz in data/")

def load_entries():
    path = _ensure_txt()
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line or line.startswith("#"): continue
            m = LINE_RE.match(line.strip())
            if not m: continue
            d = m.groupdict()
            # defs: e.g. "sea/ocean/CL:..."
            glosses = [seg for seg in d["defs"].split("/") if seg and ":" not in seg]
            entries.append({
                "trad": d["trad"], "simp": d["simp"], "pinyin": d["pinyin"],
                "defs": glosses
            })
    return entries

# Simple English → Chinese search
def search_en(word: str, limit=5):
    w = (word or "").strip().lower()
    if not w: return []
    items = load_entries()

    def score(item):
        text = " ".join(item["defs"]).lower()
        s = 0
        # exact word token
        if re.search(rf"\b{re.escape(w)}\b", text): s += 5
        # substring (e.g., 'oceanic' in 'ocean')
        if w in text: s += 2
        # prefer single-character headwords for your demo
        if len(item["simp"]) == 1 or len(item["trad"]) == 1: s += 1
        return s

    ranked = sorted(items, key=score, reverse=True)
    # dedupe by headword, keep first few
    seen, out = set(), []
    for it in ranked:
        key = it["simp"] + "|" + it["trad"]
        if key in seen: continue
        seen.add(key)
        out.append(it)
        if len(out) >= limit: break
    return out
