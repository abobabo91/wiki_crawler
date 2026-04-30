"""Smoke test: run ONE race, replace that result in results.json, regenerate HTML."""
import json, os, sys, subprocess
from datetime import datetime

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR)

from wiki_evaluator import load_config, WIKI_BASE
from run_tests import run_race

RESULTS_FILE = os.path.join(DIR, "results.json")
TESTS_FILE   = os.path.join(DIR, "test_sets.json")

MODEL_ID   = "anthropic/claude-haiku-4-5-20251001"
MODEL_NAME = "Claude Haiku 4.5"
TEST_ID    = 8   # Penguin -> United States [easy]

with open(TESTS_FILE) as f:
    tests = json.load(f)
test = next(t for t in tests if t["id"] == TEST_ID)

print(f"Running: {MODEL_NAME}  |  {test['start']} -> {test['target']}  [{test['difficulty']}]")

cfg       = load_config()
start_url = f"{WIKI_BASE}/wiki/{test['start'].replace(' ', '_')}"
result    = run_race(MODEL_ID, start_url, test["target"], cfg)

print(f"\nResult : {'SUCCESS' if result['success'] else 'FAILED'}")
print(f"Steps  : {result['steps']}")
print(f"Score  : {result.get('score', 0)}")
print(f"Path   : {result.get('path', [])}")
print(f"Reasons: {result.get('reasons', [])}")

# Replace the old record for this model+test in results.json
with open(RESULTS_FILE) as f:
    data = json.load(f)

data = [r for r in data if not (r["model_id"] == MODEL_ID and r["test_id"] == TEST_ID)]
data.append({
    "model_id":   MODEL_ID,
    "model_name": MODEL_NAME,
    "start":      start_url,
    "target":     test["target"],
    "steps":      result.get("steps", 0),
    "time":       result.get("time", 0),
    "score":      result.get("score", 0),
    "success":    result.get("success", False),
    "timestamp":  datetime.now().isoformat(),
    "test_id":    TEST_ID,
    "difficulty": test["difficulty"],
    "path":       result.get("path", []),
    "reasons":    result.get("reasons", []),
})

with open(RESULTS_FILE, "w") as f:
    json.dump(data, f)
print(f"\nSaved. results.json now has {len(data)} records.")

# Regenerate leaderboard
subprocess.run([sys.executable, os.path.join(DIR, "generate_leaderboard.py")], check=True)
print("Leaderboard regenerated.")
