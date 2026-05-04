from __future__ import annotations

import sys
from pathlib import Path

from .constants import MODEL_MAP
from .race import make_result_record, run_single_race
from .storage import append_result, load_config, load_results, load_test_sets, overwrite_results
from .wikipedia import article_url


def run_benchmark_suite(model_ids: list[str]) -> None:
    if not model_ids:
        print("Usage: python run_tests.py <model_id> [model_id2 ...]")
        print("Available models:")
        for model in MODEL_MAP.values():
            print(f"  {model['id']}")
        raise SystemExit(1)

    config = load_config()
    tests = load_test_sets()

    for model_id in model_ids:
        name = MODEL_MAP.get(model_id, {}).get("name", model_id)
        print(f"\n{'=' * 70}")
        print(f"  {name}  ({model_id})")
        print(f"{'=' * 70}")

        for index, test in enumerate(tests, 1):
            start = test["start"]
            target = test["target"]
            difficulty = test.get("difficulty", "?")
            start_url = article_url(start)

            print(f"\n[{index:2d}/{len(tests)}] {start} -> {target}  [{difficulty}]")
            result = run_single_race(model_id, start_url, target, config)
            append_result(
                make_result_record(
                    model_id,
                    start_url,
                    target,
                    result,
                    test_id=test["id"],
                    difficulty=difficulty,
                )
            )

            if result["success"]:
                print(f"  SUCCESS  steps={result['steps']}  score={result['score']}  time={result['time']}s")
            else:
                print(f"  FAILED   {result.get('error', '?')}")

    print_leaderboard()
    print("\nResults saved to data/results.json")


def print_leaderboard() -> None:
    results = load_results()
    stats: dict[str, dict] = {}
    for result in results:
        model_id = result.get("model_id", "")
        if model_id not in stats:
            stats[model_id] = {
                "name": result.get("model_name", model_id),
                "wins": 0,
                "runs": 0,
                "score": 0,
                "steps": 0,
            }
        row = stats[model_id]
        row["runs"] += 1
        row["score"] += result.get("score", 0)
        row["steps"] += result.get("steps", 0)
        if result.get("success"):
            row["wins"] += 1

    ranked = sorted(
        stats.items(),
        key=lambda item: item[1]["wins"] / item[1]["runs"] if item[1]["runs"] else 0,
        reverse=True,
    )

    print("\n" + "=" * 72)
    print("FULL LEADERBOARD")
    print("=" * 72)
    print(f"{'Model':<32} {'Wins':>5} {'Win%':>5} {'AvgScore':>9} {'AvgSteps':>9}")
    print("-" * 72)
    for _, row in ranked:
        runs = row["runs"]
        print(
            f"{row['name']:<32} {row['wins']:>3}/{runs:<3} "
            f"{row['wins'] / runs * 100:>4.0f}% {row['score'] / runs:>9.1f} {row['steps'] / runs:>9.1f}"
        )
    print("=" * 72)


def run_smoke_test(
    model_id: str = "anthropic/claude-haiku-4-5-20251001",
    test_id: int = 8,
) -> dict:
    tests = load_test_sets()
    test = next(item for item in tests if item["id"] == test_id)
    model_name = MODEL_MAP.get(model_id, {}).get("name", model_id)
    start_url = article_url(test["start"])
    config = load_config()

    print(f"Running: {model_name}  |  {test['start']} -> {test['target']}  [{test['difficulty']}]")
    result = run_single_race(model_id, start_url, test["target"], config)

    print(f"\nResult : {'SUCCESS' if result['success'] else 'FAILED'}")
    print(f"Steps  : {result['steps']}")
    print(f"Score  : {result.get('score', 0)}")
    print(f"Path   : {result.get('path_urls', [])}")
    print(f"Reasons: {result.get('reasons', [])}")

    records = load_results()
    records = [record for record in records if not (record["model_id"] == model_id and record.get("test_id") == test_id)]
    records.append(
        make_result_record(
            model_id,
            start_url,
            test["target"],
            result,
            test_id=test_id,
            difficulty=test["difficulty"],
        )
    )
    overwrite_results(records)
    print(f"\nSaved. data/results.json now has {len(records)} records.")
    return result


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> None:
    run_benchmark_suite(list(sys.argv[1:] if argv is None else argv))
