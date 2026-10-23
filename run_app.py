"""
Datrics Text2SQL Application Launcher
Run with either:
    python run_app.py
OR:
    streamlit run app/ui/streamlit_app.py
"""
import sys
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# When launched via `streamlit run run_app.py`, import the UI directly
try:
    import streamlit as st
    # If running inside streamlit runtime, execute UI directly
    from app.ui.streamlit_app import *
except Exception:
    pass

if __name__ == "__main__":
    # If executed as a script via `python run_app.py`, invoke streamlit runner
    app_script = ROOT_DIR / "app" / "ui" / "streamlit_app.py"
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_script)]
    print(f"Starting Datrics Text2SQL Studio at http://localhost:8501 ...")
    subprocess.run(cmd)
