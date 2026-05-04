from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_DIR.parent
ROOT_DIR = SRC_DIR.parent
DATA_DIR = ROOT_DIR / "data"
DOCS_DIR = ROOT_DIR / "docs"
SCREENSHOTS_DIR = DOCS_DIR / "screenshots"
ARCHIVE_DIR = DOCS_DIR / "archive"
TEMPLATES_DIR = PACKAGE_DIR / "templates"

RESULTS_FILE = DATA_DIR / "results.json"
TESTS_FILE = DATA_DIR / "test_sets.json"
CONFIG_FILE = DATA_DIR / "config.json"
LEADERBOARD_FILE = DOCS_DIR / "leaderboard.html"
