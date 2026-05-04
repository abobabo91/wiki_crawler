"""Compatibility entry point for the earlier standalone prototype."""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

from prototype_bot import main


if __name__ == "__main__":
    main()
