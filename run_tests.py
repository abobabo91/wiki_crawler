#!/usr/bin/env python3
"""
Batch test runner for WikiRace AI Benchmark.
Runs selected models against all 20 test sets and prints a leaderboard.

Usage:
    python run_tests.py openai/gpt-4o-mini
    python run_tests.py openai/gpt-4o-mini gemini/gemini-3.1-flash-lite-preview
"""

import re, sys, time, os
from datetime import datetime
from urllib.parse import unquote

def _path(history):
    return [unquote(u.split("/wiki/")[-1]).replace("_", " ") for u in history]
from wiki_evaluator import (
    get_wiki_page, build_prompt, parse_response, call_ai,
    load_config, append_result, load_results,
    WIKI_BASE, MAX_STEPS, MODEL_MAP,
)

TESTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_sets.json")


def run_race(model_id, start_url, target, cfg):
    import json
    target_slug = target.replace(" ", "_")
    target_url  = f"{WIKI_BASE}/wiki/{target_slug}"
    cur     = start_url
    history = [cur]
    reasons = [""]   # reasons[i] = why we navigated to history[i]; "" for the start page
    steps   = 0
    t0      = time.time()

    for _ in range(MAX_STEPS):
        # Already on target
        if target_slug.lower() in cur.lower().split("/wiki/")[-1]:
            elapsed = round(time.time() - t0, 1)
            score   = max(0, 1000 - steps * 50 - int(elapsed * 2))
            return {"success": True, "steps": steps, "time": elapsed, "score": score, "path": _path(history), "reasons": reasons}

        text, links = get_wiki_page(cur)
        if not links:
            return {"success": False, "error": "No links found", "steps": steps, "path": _path(history), "reasons": reasons}

        # Direct link to target on current page
        if target_url in links:
            history.append(target_url)
            reasons.append("Direct link to target found on this page.")
            steps += 1
            elapsed = round(time.time() - t0, 1)
            score   = max(0, 1000 - steps * 50 - int(elapsed * 2))
            return {"success": True, "steps": steps, "time": elapsed, "score": score, "path": _path(history), "reasons": reasons}

        prompt = build_prompt(cur, text, links, history, target)
        try:
            resp = call_ai(model_id, prompt, cfg)
        except Exception as e:
            return {"success": False, "error": f"AI error: {str(e)[:120]}", "steps": steps, "path": _path(history), "reasons": reasons}

        chosen = parse_response(resp, links)
        if not chosen:
            fresh  = [l for l in links if l not in history]
            chosen = fresh[0] if fresh else (links[0] if links else None)
        if not chosen:
            return {"success": False, "error": "No valid link", "steps": steps, "path": _path(history), "reasons": reasons}
        if history.count(chosen) >= 2:
            return {"success": False, "error": "Loop detected", "steps": steps, "path": _path(history), "reasons": reasons}

        reason_m = re.search(r"REASON:\s*(.+)", resp, re.DOTALL)
        reason   = reason_m.group(1).strip()[:120] if reason_m else ""
        slug     = chosen.split("/wiki/")[-1].replace("_", " ")
        print(f"    step {steps+1:2d}: {slug[:50]:<50}  {reason[:60]}")

        cur = chosen
        history.append(cur)
        reasons.append(reason)
        steps += 1
        time.sleep(1.2)

    elapsed = round(time.time() - t0, 1)
    return {"success": False, "error": f"Reached max {MAX_STEPS} steps", "steps": steps, "time": elapsed, "path": _path(history), "reasons": reasons}


def print_leaderboard():
    results = load_results()
    stats = {}
    for r in results:
        mid = r.get("model_id", "")
        if mid not in stats:
            stats[mid] = {"name": r.get("model_name", mid), "wins": 0, "n": 0, "score": 0, "steps": 0}
        s = stats[mid]
        s["n"] += 1
        s["score"] += r.get("score", 0)
        s["steps"] += r.get("steps", 0)
        if r.get("success"):
            s["wins"] += 1
    ranked = sorted(stats.items(), key=lambda x: x[1]["wins"]/x[1]["n"] if x[1]["n"] else 0, reverse=True)
    print("\n" + "=" * 72)
    print("FULL LEADERBOARD")
    print("=" * 72)
    print(f"{'Model':<32} {'Wins':>5} {'Win%':>5} {'AvgScore':>9} {'AvgSteps':>9}")
    print("-" * 72)
    for mid, s in ranked:
        n = s["n"]
        print(f"{s['name']:<32} {s['wins']:>3}/{n:<3} {s['wins']/n*100:>4.0f}% {s['score']/n:>9.1f} {s['steps']/n:>9.1f}")
    print("=" * 72)


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_tests.py <model_id> [model_id2 ...]")
        print("Available models:")
        for m in MODEL_MAP.values():
            print(f"  {m['id']}")
        sys.exit(1)

    import json
    model_ids = sys.argv[1:]
    cfg = load_config()

    with open(TESTS_FILE) as f:
        tests = json.load(f)

    for model_id in model_ids:
        name = MODEL_MAP.get(model_id, {}).get("name", model_id)
        print(f"\n{'='*70}")
        print(f"  {name}  ({model_id})")
        print(f"{'='*70}")

        for i, test in enumerate(tests, 1):
            start      = test["start"]
            target     = test["target"]
            difficulty = test.get("difficulty", "?")
            start_url  = f"{WIKI_BASE}/wiki/{start.replace(' ', '_')}"

            if i > 1:
                time.sleep(5)
            print(f"\n[{i:2d}/20] {start} -> {target}  [{difficulty}]")
            result = run_race(model_id, start_url, target, cfg)

            rec = {
                "model_id":   model_id,
                "model_name": name,
                "start":      start_url,
                "target":     target,
                "steps":      result.get("steps", 0),
                "time":       result.get("time", 0),
                "score":      result.get("score", 0),
                "success":    result.get("success", False),
                "timestamp":  datetime.now().isoformat(),
                "test_id":    test["id"],
                "difficulty": difficulty,
                "path":       result.get("path", []),
                "reasons":    result.get("reasons", []),
            }
            append_result(rec)

            if result["success"]:
                print(f"  SUCCESS  steps={result['steps']}  score={result['score']}  time={result['time']}s")
            else:
                print(f"  FAILED   {result.get('error', '?')}")

    print_leaderboard()
    print("\nResults saved to results.json")
    print("Run `python wiki_evaluator.py` and open http://localhost:5050 for the full UI leaderboard.")


if __name__ == "__main__":
    main()
