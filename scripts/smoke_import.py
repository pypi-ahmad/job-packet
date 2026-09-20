"""Import the Streamlit entrypoint and all application modules."""

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MODULES = (
    "src.config",
    "src.agnes_client",
    "src.parse",
    "src.match",
    "src.generate",
    "src.leakcheck",
    "app",
)

for module_name in MODULES:
    importlib.import_module(module_name)

print("IMPORT SMOKE PASSED")
