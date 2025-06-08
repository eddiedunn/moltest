import sys
from pathlib import Path

# Ensure src directory is on the path for tests
SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if SRC_PATH.exists():
    sys.path.insert(0, str(SRC_PATH))
