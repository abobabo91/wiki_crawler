import json, os, re, time, uuid, threading
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, render_template
from datetime import datetime

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WIKI_BASE = "https://en.wikipedia.org"
MAX_STEPS = 20

# Pages that are banned as navigation targets — they're universal hubs that
# trivially connect to almost anything and break the spirit of WikiRace.
LINK_BLACKLIST = {
    "/wiki/Main_Page",
    "/wiki/Wikipedia",
    "/wiki/English_Wikipedia",
    "/wiki/Simple_English_Wikipedia",
    "/wiki/Free_content",
    "/wiki/Encyclopedia",
    "/wiki/Online_encyclopedia",
    "/wiki/Internet_encyclopedia_project",
}
RESULTS_FILE = os.path.join(BASE_DIR, "results.json")
CONFIG_FILE  = os.path.join(BASE_DIR, "config.json")
TESTS_FILE   = os.path.join(BASE_DIR, "test_sets.json")

runs = {}
runs_lock = threading.Lock()

# ── Config ───────────────────────────────────────────────
DEFAULTS = {"openai_key":"","gemini_key":"","anthropic_key":"","xai_key":""}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f: return {**DEFAULTS, **json.load(f)}
    return DEFAULTS.copy()

def save_config(c):
    with open(CONFIG_FILE,"w") as f: json.dump(c, f, indent=2)

# ── Results ──────────────────────────────────────────────
def load_results():
    try:
        if os.path.exists(RESULTS_FILE):
            with open(RESULTS_FILE) as f: return json.load(f)
    except: pass
    return []

def append_result(rec):
    r = load_results(); r.append(rec)
    with open(RESULTS_FILE,"w") as f: json.dump(r, f, indent=2)

# ── Wikipedia ─────────────────────────────────────────────
def get_wiki_page(url):
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent":"WikiRaceAI/1.0"})
        if resp.status_code == 429:
            time.sleep(10)
            resp = requests.get(url, timeout=10, headers={"User-Agent":"WikiRaceAI/1.0"})
        if resp.status_code != 200: return "", []
        soup = BeautifulSoup(resp.text, "html.parser")
        div = soup.find("div", {"id":"mw-content-text"})
        text = (div.get_text() if div else soup.get_text())[:3000]
        seen, links = set(), []
        for a in soup.find_all("a", href=True):
            h = a.get("href","")
            if h.startswith("/wiki/") and ":" not in h and h not in seen and h not in LINK_BLACKLIST:
                seen.add(h); links.append(WIKI_BASE + h)
        return text, links[:120]
    except: return "", []

def article_name(url): return url.split("/wiki/")[-1].replace("_"," ")

# ── AI Models — fast / mini / flash tier only ─────────────
MODELS = [
    # OpenAI — newest to oldest, no reasoning/audio/image/codex variants
    {"id":"openai/gpt-5.4",                    "name":"GPT-5.4",                 "provider":"openai",    "color":"#10c87f"},
    {"id":"openai/gpt-5.4-mini",               "name":"GPT-5.4 Mini",            "provider":"openai",    "color":"#34d99a"},
    {"id":"openai/gpt-5.4-nano",               "name":"GPT-5.4 Nano",            "provider":"openai",    "color":"#2ea88c"},
    {"id":"openai/gpt-5",                      "name":"GPT-5",                   "provider":"openai",    "color":"#1a9e6c"},
    {"id":"openai/gpt-5-mini",                 "name":"GPT-5 Mini",              "provider":"openai",    "color":"#148a5a"},
    {"id":"openai/gpt-4.1",                    "name":"GPT-4.1",                 "provider":"openai",    "color":"#0e7a4a"},
    {"id":"openai/gpt-4.1-mini",               "name":"GPT-4.1 Mini",            "provider":"openai",    "color":"#0e6651"},
    {"id":"openai/gpt-4.1-nano",               "name":"GPT-4.1 Nano",            "provider":"openai",    "color":"#0a5040"},
    {"id":"openai/gpt-4o",                     "name":"GPT-4o",                  "provider":"openai",    "color":"#1a8c6c"},
    {"id":"openai/gpt-4o-mini",                "name":"GPT-4o Mini",             "provider":"openai",    "color":"#148a6b"},
    # Gemini — flash (non-thinking) + pro previews user requested
    {"id":"gemini/gemini-3.1-pro-preview",     "name":"Gemini 3.1 Pro",          "provider":"gemini",    "color":"#0d652b"},
    {"id":"gemini/gemini-3.1-flash-lite-preview","name":"Gemini 3.1 Flash Lite", "provider":"gemini",    "color":"#0f9d58"},
    {"id":"gemini/gemini-3-pro-preview",       "name":"Gemini 3 Pro",            "provider":"gemini",    "color":"#1b7a35"},
    {"id":"gemini/gemini-3-flash-preview",     "name":"Gemini 3 Flash",          "provider":"gemini",    "color":"#34a853"},
    {"id":"gemini/gemini-2.5-flash",           "name":"Gemini 2.5 Flash",        "provider":"gemini",    "color":"#4285f4"},
    {"id":"gemini/gemini-2.5-flash-lite",      "name":"Gemini 2.5 Flash Lite",   "provider":"gemini",    "color":"#1565c0"},
    # gemini-2.0-flash and gemini-2.0-flash-lite deprecated (404)
    # Anthropic — latest of each tier only
    {"id":"anthropic/claude-opus-4-7",         "name":"Claude Opus 4.7",         "provider":"anthropic", "color":"#b05e38"},
    {"id":"anthropic/claude-sonnet-4-6",       "name":"Claude Sonnet 4.6",       "provider":"anthropic", "color":"#e8937a"},
    {"id":"anthropic/claude-haiku-4-5-20251001","name":"Claude Haiku 4.5",       "provider":"anthropic", "color":"#f0b8a0"},
    # xAI
    {"id":"xai/grok-3",                        "name":"Grok 3",                  "provider":"xai",       "color":"#8b5cf6"},
    {"id":"xai/grok-3-mini",                   "name":"Grok 3 Mini",             "provider":"xai",       "color":"#a78bfa"},
]
MODEL_MAP = {m["id"]: m for m in MODELS}

# ── AI provider calls ─────────────────────────────────────
def call_ai(model_id, prompt, cfg):
    prov, name = model_id.split("/", 1)
    if prov == "openai":
        from openai import OpenAI
        # Reasoning models (gpt-5, gpt-5-mini, o-series) don't support temperature=0
        REASONING_MODELS = {"gpt-5", "gpt-5-mini", "o1", "o1-mini", "o3", "o3-mini", "o4-mini"}
        # Reasoning models use hidden CoT tokens; 300 is too low — they'd output nothing
        max_tok = 4000 if name in REASONING_MODELS else 300
        kwargs = {"max_completion_tokens": max_tok, "timeout": 60}
        if name not in REASONING_MODELS:
            kwargs["temperature"] = 0
        r = OpenAI(api_key=cfg["openai_key"]).chat.completions.create(
            model=name, messages=[{"role":"user","content":prompt}], **kwargs)
        return r.choices[0].message.content.strip()
    if prov == "gemini":
        from google import genai as google_genai
        client = google_genai.Client(api_key=cfg["gemini_key"])
        return client.models.generate_content(model=name, contents=prompt).text.strip()
    if prov == "anthropic":
        import anthropic
        r = anthropic.Anthropic(api_key=cfg["anthropic_key"]).messages.create(
            model=name, max_tokens=300, messages=[{"role":"user","content":prompt}])
        return r.content[0].text.strip()
    if prov == "xai":
        from openai import OpenAI
        r = OpenAI(api_key=cfg["xai_key"], base_url="https://api.x.ai/v1").chat.completions.create(
            model=name, messages=[{"role":"user","content":prompt}],
            max_tokens=300, temperature=0, timeout=30)
        return r.choices[0].message.content.strip()
    raise ValueError(f"Unknown provider: {prov}")

# ── Prompt & Parsing ─────────────────────────────────────
def build_prompt(cur_url, text, links, history, target):
    path = " -> ".join(article_name(u) for u in history[-6:])
    visited = set(history)
    fresh = [l for l in links if l not in visited][:50]
    seen  = [l for l in links if l in visited][:10]
    links_section = "Unvisited links:\n" + "\n".join(fresh)
    if seen:
        links_section += "\n\nPreviously visited links (backtrack here only if truly stuck):\n" + "\n".join(seen)
    return (
        f'You are playing Wikipedia Race. Reach "{target}" in as few clicks as possible.\n\n'
        f"Current page: {article_name(cur_url)}\n"
        f"Path so far: {path}\n"
        f"Target: {target}\n\n"
        f"Page excerpt:\n{text[:1500]}\n\n"
        f"{links_section}\n\n"
        f'Rules:\n'
        f'- You MUST pick a link from the "Unvisited links" list above. Do not invent URLs.\n'
        f'- If "{target}" appears in any list, pick it immediately.\n'
        f'- Navigate through real content articles — avoid meta/hub pages.\n'
        f'- You may pick a previously visited link to backtrack only if truly stuck.\n\n'
        f"Reply in EXACTLY this format:\n"
        f"LINK: <exact URL from the list above>\n"
        f"REASON: <one sentence why this page leads toward {target}>"
    )

def parse_response(resp, links):
    m = re.search(r"LINK:\s*(https?://[^\s\n]+)", resp)
    if m:
        cand = m.group(1).strip().rstrip(".,)")
        if cand in links: return cand
        for l in links:
            if cand in l or l in cand: return l
    for l in links:
        slug = l.split("/wiki/")[-1]
        if len(slug) > 3 and slug.lower() in resp.lower(): return l
    return None

# ── Race runner ──────────────────────────────────────────
def run_model(run_id, model_id, start_url, target, cfg):
    def upd(**kw):
        with runs_lock: runs[run_id]["model_results"][model_id].update(kw)

    target_slug = target.replace(" ","_")
    target_url  = f"{WIKI_BASE}/wiki/{target_slug}"
    cur = start_url
    history = [cur]
    steps = 0
    t0 = time.time()

    upd(status="running", current_page=article_name(cur), steps=0,
        path=[cur], score=0, last_reason="Starting...")
    try:
        for _ in range(MAX_STEPS):
            with runs_lock:
                if runs[run_id].get("cancelled"): upd(status="cancelled"); return

            if target_slug.lower() in cur.lower().split("/wiki/")[-1]:
                elapsed = round(time.time()-t0, 1)
                score = max(0, 1000 - steps*50 - int(elapsed*2))
                upd(status="success", steps=steps, time=elapsed, score=score, path=history)
                append_result({"model_id":model_id, "model_name":MODEL_MAP[model_id]["name"],
                               "start":start_url, "target":target, "steps":steps,
                               "time":elapsed, "score":score, "success":True,
                               "timestamp":datetime.now().isoformat()})
                return

            text, links = get_wiki_page(cur)
            if not links: upd(status="failed", error="No links found", steps=steps); return

            if target_url in links:
                history.append(target_url); steps += 1
                elapsed = round(time.time()-t0, 1)
                score = max(0, 1000 - steps*50 - int(elapsed*2))
                upd(status="success", steps=steps, time=elapsed, score=score,
                    path=history, current_page=target)
                append_result({"model_id":model_id, "model_name":MODEL_MAP[model_id]["name"],
                               "start":start_url, "target":target, "steps":steps,
                               "time":elapsed, "score":score, "success":True,
                               "timestamp":datetime.now().isoformat()})
                return

            prompt = build_prompt(cur, text, links, history, target)
            try:
                resp = call_ai(model_id, prompt, cfg)
            except Exception as e:
                upd(status="failed", error=f"AI error: {str(e)[:120]}", steps=steps); return

            chosen = parse_response(resp, links)
            if not chosen:
                fresh = [l for l in links if l not in history]
                chosen = fresh[0] if fresh else (links[0] if links else None)
            if not chosen:
                upd(status="failed", error="No valid link", steps=steps); return
            if history.count(chosen) >= 2:
                upd(status="failed", error="Loop detected", steps=steps)
                elapsed = round(time.time()-t0, 1)
                append_result({"model_id":model_id,"model_name":MODEL_MAP[model_id]["name"],
                               "start":start_url,"target":target,"steps":steps,
                               "time":elapsed,"score":0,"success":False,
                               "timestamp":datetime.now().isoformat()})
                return

            reason_m = re.search(r"REASON:\s*(.+)", resp, re.DOTALL)
            reason = reason_m.group(1).strip()[:200] if reason_m else ""
            cur = chosen; history.append(cur); steps += 1
            upd(steps=steps, current_page=article_name(cur), path=history[:], last_reason=reason)
            time.sleep(1.2)

        elapsed = round(time.time()-t0, 1)
        upd(status="failed", steps=steps, time=elapsed, score=0,
            error=f"Max {MAX_STEPS} steps reached")
        append_result({"model_id":model_id, "model_name":MODEL_MAP[model_id]["name"],
                       "start":start_url, "target":target, "steps":steps,
                       "time":elapsed, "score":0, "success":False,
                       "timestamp":datetime.now().isoformat()})
    except Exception as e:
        upd(status="failed", error=str(e)[:120], steps=steps)

# ── Flask Routes ─────────────────────────────────────────
@app.route("/")
def index(): return render_template("index.html")

@app.route("/api/models")
def api_models():
    cfg = load_config()
    key_map = {"openai":"openai_key","gemini":"gemini_key","anthropic":"anthropic_key","xai":"xai_key"}
    return jsonify([{**m, "available": bool(cfg.get(key_map[m["provider"]],"").strip())} for m in MODELS])

@app.route("/api/test_sets")
def api_tests():
    with open(TESTS_FILE) as f: return jsonify(json.load(f))

@app.route("/api/config", methods=["GET","POST"])
def api_config():
    if request.method == "POST":
        cfg = load_config(); cfg.update(request.json); save_config(cfg)
        return jsonify({"ok": True})
    cfg = load_config()
    return jsonify({"has_key": {k: bool(v) for k,v in cfg.items()},
                    "masked":  {k: (v[:8]+"..."+v[-4:] if len(v)>12 else ("set" if v else "")) for k,v in cfg.items()}})

@app.route("/api/run", methods=["POST"])
def api_run():
    data = request.json
    start  = data.get("start","").strip()
    target = data.get("target","").strip()
    mids   = data.get("models", [])
    if not start or not target or not mids:
        return jsonify({"error":"Missing start, target, or models"}), 400

    start_url = f"{WIKI_BASE}/wiki/{start.replace(' ','_')}"
    cfg = load_config()
    run_id = str(uuid.uuid4())[:8]
    model_results = {mid: {"status":"pending","steps":0,"score":0,"current_page":start,
                           "path":[start_url],"last_reason":"","time":0,"error":""}
                     for mid in mids}
    with runs_lock:
        runs[run_id] = {"start":start,"target":target,"model_results":model_results,
                        "cancelled":False,"created":datetime.now().isoformat()}
    for mid in mids:
        threading.Thread(target=run_model, args=(run_id,mid,start_url,target,cfg), daemon=True).start()
    return jsonify({"run_id": run_id})

@app.route("/api/status/<run_id>")
def api_status(run_id):
    with runs_lock:
        run = runs.get(run_id)
        if not run: return jsonify({"error":"Not found"}), 404
        return jsonify({"run_id":run_id,"start":run["start"],"target":run["target"],
                        "model_results":run["model_results"]})

@app.route("/api/cancel/<run_id>", methods=["POST"])
def api_cancel(run_id):
    with runs_lock:
        if run_id in runs: runs[run_id]["cancelled"] = True
    return jsonify({"ok": True})

@app.route("/api/leaderboard")
def api_leaderboard():
    results = load_results()
    stats = {}
    for r in results:
        mid = r.get("model_id","")
        if mid not in stats:
            stats[mid] = {"model_id":mid,"model_name":r.get("model_name",mid),
                          "runs":0,"wins":0,"total_score":0,"total_steps":0,"total_time":0}
        s = stats[mid]; s["runs"]+=1
        if r.get("success"): s["wins"]+=1
        s["total_score"]+=r.get("score",0); s["total_steps"]+=r.get("steps",0); s["total_time"]+=r.get("time",0)
    board = []
    for s in stats.values():
        n = s["runs"]
        board.append({**s,"avg_score":round(s["total_score"]/n,1),"avg_steps":round(s["total_steps"]/n,1),
                      "avg_time":round(s["total_time"]/n,1),"win_rate":round(s["wins"]/n*100,1)})
    board.sort(key=lambda x: -x["avg_score"])
    return jsonify(board)

@app.route("/api/clear_results", methods=["POST"])
def api_clear():
    with open(RESULTS_FILE,"w") as f: json.dump([], f)
    return jsonify({"ok":True})

if __name__ == "__main__":
    print("\n  WikiRace AI Benchmark")
    print("   Open http://localhost:5050\n")
    app.run(host="0.0.0.0", port=5050, debug=False, threaded=True)
