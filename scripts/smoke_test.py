"""Script entry point for a single benchmark smoke test."""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wiki_race.benchmark import run_smoke_test
from wiki_race.reporting import main as generate_report


if __name__ == "__main__":
    run_smoke_test()
    generate_report()
