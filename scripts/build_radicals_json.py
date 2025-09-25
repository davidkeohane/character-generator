# scripts/build_radicals_json.py
# Pull a vetted 214-radical list and normalize to our schema.

import json, re, pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT  = ROOT / "data" / "radicals_214.json"

SOURCE_URL = "https://gist.githubusercontent.com/branneman/f93d596ac236f0dbd9fb5b1a5099122f/raw/radicals.json"

# very small synonym expander for nicer matches; tweak freely
SYN = {
    "water": ["liquid","river","sea","ocean","wave","wet","flow"],
    "fire": ["heat","hot","flame","burn","ember"],
    "wood": ["tree","forest","timber","plant"],
    "metal": ["gold","money","iron","metalwork"],
    "earth": ["soil","ground","clay","dirt"],
    "stone": ["rock","pebble","mountain"],
    "mouth": ["speak","say","voice","taste","speech"],
    "heart": ["mind","feeling","emotion","love","thought"],
    "hand": ["hold","grasp","touch","handy","manual"],
    "foot": ["walk","step","kick","leg"],
    "rain": ["cloud","storm","weather","drop","wet"],
    "sun": ["day","light","bright"],
    "moon": ["night","month","time"],
    "knife": ["cut","blade","sharp"],
    "food": ["eat","meal","grain","rice"],
    "silk": ["thread","string","textile","cloth"],
    "door": ["gate","house","enter"],
    "bird": ["feather","wing","fly"],
    "dog": ["animal","beast"],
    "horse": ["ride","animal"],
    "fish": ["seafood","river","swim"],
}

def fetch_json(url: str):
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read().decode("utf-8"))

def tokenize(s: str):
    return [w for w in re.split(r"[^a-z]+", s.lower()) if w]

def build_tags(eng: str):
    base = tokenize(eng)
    extra = []
    for w in list(base):
        extra += SYN.get(w, [])
    return sorted(set(base + extra))

def main():
    src = fetch_json(SOURCE_URL)
    out = []
    for item in src:
        # source fields: radical, pinyin, english, strokes, number
        radical = item["radical"]
        num     = int(item["id"])
        pinyin  = item["pinyin"]
        eng     = item["english"]
        strokes = int(item["strokeCount"])

        out.append({
            "num": num,
            "id": radical,           # the radical glyph itself
            "pinyin": pinyin,
            "gloss": eng.lower(),    # normalized English gloss
            "strokes": strokes,
            "tags": build_tags(eng), # simple auto-tags for matching
            "svg_path": f"../svg/radicals/{num:03d}.svg"  # you can rename later
        })

    # sort by num, write pretty
    out.sort(key=lambda x: x["num"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Wrote {OUT} with {len(out)} radicals.")

if __name__ == "__main__":
    main()
