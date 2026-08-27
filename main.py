"""Backward-compatible entrypoint forwarding execution to src.main."""

import sys
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.main import main  # noqa: E402

if __name__ == "__main__":
    main()
