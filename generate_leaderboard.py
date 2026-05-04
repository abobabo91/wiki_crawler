"""Compatibility entry point for generating the HTML leaderboard."""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from wiki_race.reporting import main


if __name__ == "__main__":
    main()
