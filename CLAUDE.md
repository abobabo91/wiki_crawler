# WikiRace AI Benchmark

Multi-provider benchmark: models navigate Wikipedia as a graph (start article → target article in fewest clicks). Records success / steps / time / score / path / per-step reasoning. Aggregated into a public leaderboard. Web UI + Docker deploy.

## Critical rules

- The model sees **only the current article's outgoing links** at each step — never the global graph. Don't surface graph structure into the prompt; that breaks the "partial information" property the benchmark exists to measure.
- Each run uses the **shared test set** in `data/test_sets.json`. Don't compare results across different test sets — leaderboard is only valid within the same source/target pairs.
- NEVER commit API keys. Users supply keys per-run in the UI or via env vars; nothing persisted.
- `data/results.json` is the leaderboard source of truth. Only commit runs that are honest (real model, real navigation, no hand-tuning).

## Stack & run

- Python + Flask web UI + per-provider AI SDKs (similar to euler_benchmark)
- Local: `python ai_bot.py` (or the relevant entry — see `scripts/` for orchestration)
- Smoke test: `python smoke_test.py`
- Generate leaderboard: `python generate_leaderboard.py`
- Tests: `python run_tests.py`
- Docker: `Dockerfile` present for containerized runs

## Where things live

- Bot logic (agent loop, prompt, navigation): `ai_bot.py`
- Evaluator (scoring, path validation): `wiki_evaluator.py`
- Leaderboard generation: `generate_leaderboard.py` → outputs `docs/leaderboard.html`
- Test set + results: `data/test_sets.json`, `data/results.json`
- Package source: `src/wiki_race/`
- Smoke test: `smoke_test.py`
- Run tests: `run_tests.py`
- Public leaderboard (rendered): `docs/leaderboard.html`
- Orchestration scripts: `scripts/`

## Common workflows

**To benchmark a new model:**
1. Add provider routing in `ai_bot.py` (or wherever the model dispatch lives)
2. Smoke test with `python smoke_test.py` to verify auth + 1 run
3. Run the full test set; results stream into `data/results.json`
4. Regenerate the leaderboard: `python generate_leaderboard.py`
5. Commit `data/results.json` + `docs/leaderboard.html`

**To add a new source/target pair to the test set:**
1. Edit `data/test_sets.json` (pick articles with a known short path for difficulty calibration)
2. Note: adding to the test set invalidates direct leaderboard comparison with prior runs — flag the version explicitly

## Gotchas

- Wikipedia article slugs change occasionally (renames, merges). A test set entry that worked yesterday can break today — handle 404s gracefully.
- The Wikipedia API has soft rate limits (no auth needed but throttling kicks in). Don't burst-fetch across many concurrent runs without coordinating.
- Different models reveal vastly different navigation strategies. The "per-step reasoning text" is the most interesting artifact — preserve it in logs even if the path itself succeeds.
- For cross-project model selection / agentic-benchmark patterns: `tools/knowledge base/llms 2026.md`. Sister project: `euler_benchmark` (same agentic harness pattern).
