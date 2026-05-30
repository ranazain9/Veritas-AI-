"""Streamlit entry at repo root — runs frontend/app.py (for `streamlit run app.py`)."""

import sys
from pathlib import Path

_FRONTEND = Path(__file__).resolve().parent / "frontend"
if str(_FRONTEND) not in sys.path:
    sys.path.insert(0, str(_FRONTEND))

_APP = _FRONTEND / "app.py"
exec(compile(_APP.read_text(encoding="utf-8"), str(_APP), "exec"))
