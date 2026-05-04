# WikiRace AI Benchmark

This project is a small research-style benchmark for evaluating how AI models navigate a real knowledge network.

Instead of measuring only question answering or static reasoning, the benchmark asks models to move through Wikipedia as a graph: start from one article, choose links step by step, and reach a target page as efficiently as possible. That makes the project part AI evaluation, part benchmark design, and part network-science experiment.

## Research framing

Wikipedia is treated here as a large directed network of concepts. Each article is a node, each article link is an edge, and the model acts as an agent trying to traverse that graph under partial information.

The benchmark is meant to probe questions like:

- How well can a model reason over local graph structure without seeing the whole network?
- Can it make efficient pathfinding decisions in a semantic network?
- Does stronger language modeling translate into better navigation strategy?
- Which models are fast, robust, or sample-efficient on multi-step search tasks?

In that sense, the project sits at the intersection of:

- AI agent evaluation
- benchmark engineering
- semantic navigation
- graph search
- network science

## What the benchmark measures

Each run starts from a source Wikipedia article and tries to reach a target article in as few clicks as possible.

The system records:

- success or failure
- number of steps
- elapsed time
- score
- chosen path
- per-step reasoning text

The final leaderboard aggregates those runs across a shared test set so models can be compared on the same navigation problems.

## Project structure

- `wiki_evaluator.py`: Flask app and core benchmark logic
- `run_tests.py`: batch runner for the predefined benchmark set
- `generate_leaderboard.py`: static HTML leaderboard generator
- `smoke_test.py`: one-off regression run for a single model/test case
- `test_sets.json`: benchmark scenarios
- `results.json`: recorded evaluation results
- `leaderboard.html`: generated report
- `ai_bot.py`: earlier standalone prototype

## How it works

For each benchmark run, the evaluator:

1. Loads the current Wikipedia article and extracts valid outgoing article links.
2. Builds a prompt that includes the current page, path history, target, and candidate links.
3. Asks the selected model to choose the next step.
4. Repeats until the target is reached or the maximum step count is exceeded.
5. Stores the outcome for later aggregation and visualization.

To keep the task meaningful, the benchmark blocks obvious hub or meta pages that would trivialize navigation.

## Setup

Install the Python dependencies required for the providers you want to evaluate.

Core dependencies:

- `flask`
- `requests`
- `beautifulsoup4`
- `openai`

Optional provider dependencies:

- `google-genai` for Gemini
- `anthropic` for Claude

Provider keys are stored in `config.json` through the web UI or loaded by the scripts at runtime.

## Run the web app

```bash
python wiki_evaluator.py
```

Then open:

```text
http://localhost:5050
```

## Run the benchmark suite

```bash
python run_tests.py openai/gpt-4o
python run_tests.py openai/gpt-4o gemini/gemini-3.1-flash-lite-preview
```

## Generate the report

```bash
python generate_leaderboard.py
```

This writes `leaderboard.html` in the project root.

## Notes

- `results.json` is the source data for the leaderboard.
- The benchmark is intentionally lightweight and exploratory rather than a formal academic evaluation suite.
- The current codebase focuses on practical cross-model comparison, but the same setup could be extended with stronger graph metrics, difficulty calibration, or repeated-trial analysis.
