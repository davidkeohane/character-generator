# scripts/app.py
# Minimal Flask app: type a word → see chosen radicals + explanations,
# and show a composed "new character" SVG from your 214 inputs.

from flask import Flask, request, render_template_string, send_from_directory
import pathlib, time, json, re

# --- Imports for your logic ---
#from scripts.choose_embed import choose          # embedding-based chooser
#from scripts.cedict_lookup import search_en      # CC-CEDICT lookups
#from scripts.compose_svg import compose_lr, compose_tb  # ⿰ (lr) and ⿱ (tb)
from choose_embed import choose
from cedict_lookup import search_en
from compose_svg import compose_lr, compose_tb


# --- Paths & globals ---
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "svg" / "out"
RAD_JSON = ROOT / "data" / "radicals_214.json"

app = Flask(__name__)

# ---------------- Utilities ----------------

_id2num_cache = None
def id_to_num_map():
    """Map radical glyph (e.g. '心') and zero-padded numbers ('061') -> int 1..214."""
    global _id2num_cache
    if _id2num_cache is None:
        data = json.loads(RAD_JSON.read_text(encoding="utf-8"))
        m = {}
        for item in data:
            n = int(item["num"])
            m[item["id"]] = n
            m[f"{n:03d}"] = n
        _id2num_cache = m
    return _id2num_cache

def normalize_picks_with_nums(picks):
    """Ensure each pick dict has 'num' (int)."""
    m = id_to_num_map()
    out = []
    for p in picks or []:
        q = dict(p)
        if "num" in q and str(q["num"]).isdigit():
            q["num"] = int(q["num"]); out.append(q); continue
        if "id" in q and q["id"] in m:
            q["num"] = m[q["id"]]; out.append(q); continue
        if "num" in q:
            digits = "".join(ch for ch in str(q["num"]) if ch.isdigit())
            if digits.isdigit():
                q["num"] = int(digits); out.append(q); continue
    return out

def sanitize_svg_file(path_obj: pathlib.Path):
    """
    Ensure the root <svg> tag has EXACTLY ONE xmlns.
    Strategy: remove all xmlns=... attributes from the root tag, then insert one standard xmlns.
    """
    try:
        txt = path_obj.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return
    m = re.search(r"<svg\b[^>]*>", txt, flags=re.IGNORECASE)
    if not m:
        return
    root = m.group(0)
    # strip ALL xmlns="...":
    root_no_xmlns = re.sub(r'\s+xmlns="[^"]*"', "", root, flags=re.IGNORECASE)
    # add a single standard xmlns after <svg
    if "xmlns=" not in root_no_xmlns:
        root_fixed = root_no_xmlns.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    else:
        root_fixed = root_no_xmlns
    if root_fixed != root:
        txt = txt[:m.start()] + root_fixed + txt[m.end():]
        try:
            path_obj.write_text(txt, encoding="utf-8")
        except Exception:
            pass

# ---------------- HTML ----------------

HTML = """
<!doctype html>
<meta charset="utf-8">
<title>Radical Recommender</title>
<style>
  body { font: 16px/1.4 system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial; margin: 24px; }
  form { margin-bottom: 16px; }
  input[type=text]{ padding:8px; width:340px; }
  select, button { padding:8px; }
  table { border-collapse: collapse; margin-top: 10px; }
  th, td { border:1px solid #ddd; padding:8px; }
  th { background:#f6f6f6; }
  .glyph { font-size: 28px; text-align:center; width:64px; }
  .muted { color:#666; }
</style>

<h1>Character Creator</h1>
<form method="GET">
  <input type="text" name="q" placeholder="Type a word here please" value="{{q or ''}}" autofocus>
  <select name="k">
    {% for n in [2,3] %}<option value="{{n}}" {% if k==n %}selected{% endif %}>Top {{n}}</option>{% endfor %}
  </select>
  <select name="layout">
    <option value="lr" {% if layout=='lr' %}selected{% endif %}>⿰ left-right</option>
    <option value="tb" {% if layout=='tb' %}selected{% endif %}>⿱ top-bottom</option>
  </select>
  <button>Generate</button>
</form>

{% if composed_name %}
  <h2>Composed Character ({{ '⿰' if layout=='lr' else '⿱' }})</h2>
  <div style="display:flex;align-items:center;gap:16px;margin:10px 0 18px;">
    <img src="/gen/{{composed_name}}" alt="composed glyph"
         style="width:256px;height:256px;border:1px solid #ddd;border-radius:8px;background:#fff;">
    <div class="muted">
      Built from top {{k}} radical{{'' if k==1 else 's'}} using {{ 'left–right (⿰)' if layout=='lr' else 'top–bottom (⿱)' }} layout.<br>
      <div><a class="muted" href="/gen/{{composed_name}}" target="_blank">Open composed SVG</a></div>
    </div>
  </div>
{% endif %}

{% if q %}
  {% if picks %}
    <div class="muted">Query: <strong>{{q}}</strong> → showing top {{k}} radical{{'' if k==1 else 's'}}</div>
    <table>
      <tr><th>#</th><th>Radical</th><th>Num</th><th>Pinyin</th><th>English</th><th>Score</th><th>Why this radical?</th></tr>
      {% for i, r in enumerate(picks, start=1) %}
        <tr>
          <td>{{i}}</td>
          <td class="glyph">{{r.id}}</td>
          <td>{{r.num}}</td>
          <td>{{r.pinyin}}</td>
          <td>{{r.gloss}}</td>
          <td>{{r.score}}</td>
          <td>
            {% if r.matched_tokens %}<b>matches</b>: {{", ".join(r.matched_tokens)}}{% endif %}
            {% if r.fuzzy_tokens %}{% if r.matched_tokens %}; {% endif %}<b>fuzzy</b>: {{", ".join(r.fuzzy_tokens)}}{% endif %}
            {% if not r.matched_tokens and not r.fuzzy_tokens %}semantic nearest by embedding{% endif %}
          </td>
        </tr>
      {% endfor %}
    </table>
    {% if dict_hits %}
      <h2>Actual Character</h2>
      <table>
        <tr><th>Simplified / Traditional</th><th>Pinyin</th><th>Definition(s)</th></tr>
        {% for d in dict_hits %}
          <tr>
            <td style="font-size:28px">{{ d.simp }} <span class="muted">/ {{ d.trad }}</span></td>
            <td>{{ d.pinyin }}</td>
            <td>{{ "; ".join(d.defs[:3]) }}</td>
          </tr>
        {% endfor %}
      </table>
    {% else %}
      <p class="muted">No direct CC-CEDICT hit for “{{q}}”. Try a near synonym.</p>
    {% endif %}
  {% else %}
    <p>No results (this shouldn’t happen). Try another word.</p>
  {% endif %}
{% else %}
  <p class="muted">Create your own pictogram for only 79.99 a month!</p>
{% endif %}
"""
#<p class="muted">Tip: words with <i>ism</i> at the end can be funny.</p>
# ---------------- Composition ----------------

def compose_new_character(word, picks, layout="lr"):
    """
    Compose 2 or 3 radicals into one SVG and return the output filename.
    layout: 'lr' (⿰) or 'tb' (⿱). For 3 parts we nest; on error we fall back to 2.
    """
    if not picks or len(picks) < 2:
        return None

    def fp(n: int) -> str:
        return (ROOT / "svg" / f"{int(n):03d}.svg").as_posix()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time())
    base = "".join(ch for ch in (word or "generated").lower() if ch.isalnum() or ch in "-_") or "generated"

    n0, n1 = int(picks[0]["num"]), int(picks[1]["num"])

    # 2 components
    if len(picks) == 2:
        out_name = f"{base}_{layout}_{stamp}.svg"
        out_path = (OUT_DIR / out_name)
        if layout == "lr":
            compose_lr(fp(n0), fp(n1), out_path.as_posix(), size=1024, gutter_ratio=0.0)
        else:
            compose_tb(fp(n0), fp(n1), out_path.as_posix(), size=1024, gutter_ratio=0.0)
        sanitize_svg_file(out_path)
        print(f"✅ Wrote {out_path}")
        return out_name

    # 3 components with nesting; sanitize the temp before re-parse
    n2 = int(picks[2]["num"])
    tmp_path = OUT_DIR / f"tmp_{base}_{layout}_{stamp}.svg"

    try:
        if layout == "lr":
            # ⿰( n0 , ⿱( n1 , n2 ) )
            compose_tb(fp(n1), fp(n2), tmp_path.as_posix(), size=1024, gutter_ratio=0.0)
            sanitize_svg_file(tmp_path)  # <-- fix duplicate xmlns before re-using
            out_name = f"{base}_lr3_{stamp}.svg"
            out_path = OUT_DIR / out_name
            compose_lr(fp(n0), tmp_path.as_posix(), out_path.as_posix(), size=1024, gutter_ratio=0.0)
        else:
            # ⿱( n0 , ⿰( n1 , n2 ) )
            compose_lr(fp(n1), fp(n2), tmp_path.as_posix(), size=1024, gutter_ratio=0.0)
            sanitize_svg_file(tmp_path)  # <-- fix duplicate xmlns before re-using
            out_name = f"{base}_tb3_{stamp}.svg"
            out_path = OUT_DIR / out_name
            compose_tb(fp(n0), tmp_path.as_posix(), out_path.as_posix(), size=1024, gutter_ratio=0.0)

        sanitize_svg_file(out_path)
        print(f"✅ Wrote {out_path}")

        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

        return out_name

    except Exception as e:
        print(f"⚠️ 3-part compose failed ({e}). Falling back to 2-part.")
        out_name = f"{base}_{layout}_{stamp}.svg"
        out_path = OUT_DIR / out_name
        if layout == "lr":
            compose_lr(fp(n0), fp(n1), out_path.as_posix(), size=1024, gutter_ratio=0.0)
        else:
            compose_tb(fp(n0), fp(n1), out_path.as_posix(), size=1024, gutter_ratio=0.0)
        sanitize_svg_file(out_path)
        print(f"✅ Wrote {out_path} (fallback 2-part)")
        return out_name

# ---------------- Serving ----------------

@app.route("/gen/<path:name>")
def gen_file(name):
    path = (OUT_DIR / name)
    if not path.exists():
        return f"Not found: {path}", 404
    sanitize_svg_file(path)  # guarantee a clean root
    return send_from_directory(OUT_DIR.as_posix(), name, mimetype="image/svg+xml")

# ---------------- Main page ----------------

@app.route("/", methods=["GET"])
def index():
    q = (request.args.get("q") or "").strip()
    layout = (request.args.get("layout") or "lr").lower()  # 'lr' or 'tb'

    try:
        k = int(request.args.get("k") or "2")
    except ValueError:
        k = 2

    picks_raw = choose(q, k) if q else None
    picks = normalize_picks_with_nums(picks_raw)
    dict_hits = search_en(q, limit=1) if q else []

    composed_name = None
    if q and picks and len(picks) >= 2:
        composed_name = compose_new_character(q, picks, layout=layout)

    return render_template_string(
        HTML,
        q=q,
        k=k,
        layout=layout,
        picks=picks,
        dict_hits=dict_hits,
        composed_name=composed_name,
        enumerate=enumerate
    )

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=7860, debug=False, use_reloader=False)
