import json, pathlib, numpy as np
from sentence_transformers import SentenceTransformer

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAD_PATH = ROOT / "data" / "radicals_214.json"
EMB_NPY  = ROOT / "data" / "radicals_embeds.npy"
IDX_JSON = ROOT / "data" / "radicals_index.json"

def text_for(item):
    # what we embed for each radical
    gloss = item.get("gloss","")
    tags  = " ".join(item.get("tags", []))
    # tiny description helps the model
    return f"radical {item['id']} ({item['pinyin']}), meaning: {gloss}. related: {tags}"

def main():
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    items = json.loads(RAD_PATH.read_text(encoding="utf-8"))
    corpus = [text_for(it) for it in items]
    X = model.encode(corpus, normalize_embeddings=True)
    np.save(EMB_NPY, X.astype("float32"))
    # save a slim index to re-map rows → radical
    index = [{"num":it["num"], "id":it["id"], "pinyin":it["pinyin"], "gloss":it["gloss"]} for it in items]
    IDX_JSON.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Saved {len(items)} embeddings to {EMB_NPY} and index to {IDX_JSON}")

if __name__ == "__main__":
    main()
