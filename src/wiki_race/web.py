from __future__ import annotations

import threading
import uuid

from flask import Flask, jsonify, render_template, request

from .constants import MODELS, MODEL_MAP, PROVIDER_KEY_MAP, WIKI_BASE
from .paths import TEMPLATES_DIR
from .race import make_result_record, run_single_race
from .storage import append_result, clear_results, load_config, load_results, load_test_sets, overwrite_results, save_config
from .wikipedia import article_url


def build_leaderboard_rows() -> list[dict]:
    stats: dict[str, dict] = {}
    for result in load_results():
        model_id = result.get("model_id", "")
        if model_id not in stats:
            stats[model_id] = {
                "model_id": model_id,
                "model_name": result.get("model_name", model_id),
                "runs": 0,
                "wins": 0,
                "total_score": 0,
                "total_steps": 0,
                "total_time": 0,
            }

        row = stats[model_id]
        row["runs"] += 1
        row["wins"] += 1 if result.get("success") else 0
        row["total_score"] += result.get("score", 0)
        row["total_steps"] += result.get("steps", 0) if result.get("success") else 20
        row["total_time"] += result.get("time", 0)

    leaderboard = []
    for row in stats.values():
        runs = row["runs"] or 1
        leaderboard.append(
            {
                **row,
                "avg_score": round(row["total_score"] / runs, 1),
                "avg_steps": round(row["total_steps"] / runs, 1),
                "avg_time": round(row["total_time"] / runs, 1),
                "win_rate": round(row["wins"] / runs * 100, 1),
            }
        )

    leaderboard.sort(key=lambda item: (item["avg_steps"], -item["win_rate"]))
    return leaderboard


def create_app() -> Flask:
    app = Flask(__name__, template_folder=str(TEMPLATES_DIR))
    runs: dict[str, dict] = {}
    runs_lock = threading.Lock()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/models")
    def api_models():
        config = load_config()
        return jsonify(
            [
                {
                    **model,
                    "available": bool(config.get(PROVIDER_KEY_MAP[model["provider"]], "").strip()),
                }
                for model in MODELS
            ]
        )

    @app.route("/api/test_sets")
    def api_tests():
        return jsonify(load_test_sets())

    @app.route("/api/config", methods=["GET", "POST"])
    def api_config():
        if request.method == "POST":
            config = load_config()
            config.update(request.json or {})
            save_config(config)
            return jsonify({"ok": True})

        config = load_config()
        return jsonify(
            {
                "has_key": {key: bool(value) for key, value in config.items()},
                "masked": {
                    key: (value[:8] + "..." + value[-4:] if len(value) > 12 else ("set" if value else ""))
                    for key, value in config.items()
                },
            }
        )

    @app.route("/api/run", methods=["POST"])
    def api_run():
        payload = request.json or {}
        start = payload.get("start", "").strip()
        target = payload.get("target", "").strip()
        model_ids = payload.get("models", [])

        if not start or not target or not model_ids:
            return jsonify({"error": "Missing start, target, or models"}), 400

        start_url = f"{WIKI_BASE}/wiki/{start.replace(' ', '_')}"
        config = load_config()
        run_id = str(uuid.uuid4())[:8]
        model_results = {
            model_id: {
                "status": "pending",
                "steps": 0,
                "score": 0,
                "current_page": start,
                "path": [start_url],
                "last_reason": "",
                "time": 0,
                "error": "",
            }
            for model_id in model_ids
        }

        with runs_lock:
            runs[run_id] = {
                "start": start,
                "target": target,
                "model_results": model_results,
                "cancelled": False,
            }

        def worker(model_id: str) -> None:
            def update_lane(delta: dict) -> None:
                with runs_lock:
                    runs[run_id]["model_results"][model_id].update(delta)

            def is_cancelled() -> bool:
                with runs_lock:
                    return bool(runs[run_id].get("cancelled"))

            result = run_single_race(
                model_id,
                start_url,
                target,
                config,
                progress_callback=update_lane,
                cancel_callback=is_cancelled,
            )

            if result["status"] != "cancelled":
                append_result(make_result_record(model_id, start_url, target, result))

        for model_id in model_ids:
            thread = threading.Thread(target=worker, args=(model_id,), daemon=True)
            thread.start()

        return jsonify({"run_id": run_id})

    @app.route("/api/status/<run_id>")
    def api_status(run_id: str):
        with runs_lock:
            run = runs.get(run_id)
            if not run:
                return jsonify({"error": "Not found"}), 404

            return jsonify(
                {
                    "run_id": run_id,
                    "start": run["start"],
                    "target": run["target"],
                    "model_results": run["model_results"],
                }
            )

    @app.route("/api/cancel/<run_id>", methods=["POST"])
    def api_cancel(run_id: str):
        with runs_lock:
            if run_id in runs:
                runs[run_id]["cancelled"] = True
        return jsonify({"ok": True})

    @app.route("/api/leaderboard")
    def api_leaderboard():
        return jsonify(build_leaderboard_rows())

    @app.route("/api/clear_results", methods=["POST"])
    def api_clear():
        clear_results()
        return jsonify({"ok": True})

    @app.route("/api/results")
    def api_results():
        return jsonify(load_results())

    @app.route("/api/benchmark", methods=["POST"])
    def api_benchmark():
        payload = request.json or {}
        model_ids = payload.get("models", [])
        if not model_ids:
            return jsonify({"error": "No models selected"}), 400

        config = load_config()
        tests = load_test_sets()
        bench_id = str(uuid.uuid4())[:8]

        with runs_lock:
            runs[bench_id] = {
                "type": "benchmark",
                "total": len(tests) * len(model_ids),
                "completed": 0,
                "results": [],
                "cancelled": False,
            }

        def bench_worker():
            for model_id in model_ids:
                for test in tests:
                    with runs_lock:
                        if runs[bench_id].get("cancelled"):
                            return
                    start_url = article_url(test["start"])
                    result = run_single_race(model_id, start_url, test["target"], config)
                    record = make_result_record(
                        model_id, start_url, test["target"], result,
                        test_id=test["id"], difficulty=test.get("difficulty"),
                    )
                    append_result(record)
                    with runs_lock:
                        runs[bench_id]["completed"] += 1
                        runs[bench_id]["results"].append(record)

        thread = threading.Thread(target=bench_worker, daemon=True)
        thread.start()
        return jsonify({"bench_id": bench_id})

    @app.route("/api/benchmark/<bench_id>")
    def api_benchmark_status(bench_id: str):
        with runs_lock:
            bench = runs.get(bench_id)
            if not bench or bench.get("type") != "benchmark":
                return jsonify({"error": "Not found"}), 404
            return jsonify({
                "total": bench["total"],
                "completed": bench["completed"],
                "results": bench["results"],
                "cancelled": bench.get("cancelled", False),
            })

    @app.route("/api/cancel_benchmark/<bench_id>", methods=["POST"])
    def api_cancel_benchmark(bench_id: str):
        with runs_lock:
            if bench_id in runs:
                runs[bench_id]["cancelled"] = True
        return jsonify({"ok": True})

    return app


app = create_app()


def main() -> None:
    print("\n  WikiRace AI Benchmark")
    print("   Open http://localhost:5050\n")
    app.run(host="0.0.0.0", port=5050, debug=False, threaded=True)


if __name__ == "__main__":
    main()
