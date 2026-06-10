"""Parse-only validation for the Streamlit dashboard.

This avoids Python bytecode writes, which can fail in restricted environments
where creating __pycache__ is denied.
"""

from pathlib import Path
import ast


source = Path("dashboard.py").read_text(encoding="utf-8")
ast.parse(source, filename="dashboard.py")
print("dashboard.py syntax ok")
