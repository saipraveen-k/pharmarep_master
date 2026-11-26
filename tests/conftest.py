"""Make backend modules importable both as `backend.x` and as `x`.

The backend uses flat imports (e.g. `from prompts import ...`) because it
is started from inside the backend folder (`cd backend && python main.py`).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for path in (ROOT, os.path.join(ROOT, "backend")):
    if path not in sys.path:
        sys.path.insert(0, path)
