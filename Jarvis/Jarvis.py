"""Start Jarvis:  python Jarvis.py   (same options as jarvis.bat, e.g. --calibrate)"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV_PY = HERE / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

# Use Jarvis's own Python environment (made by setup.ps1) if we're not already in it.
if VENV_PY.exists() and Path(sys.executable).resolve() != VENV_PY.resolve():
    sys.exit(subprocess.call([str(VENV_PY), str(Path(__file__).resolve()), *sys.argv[1:]]))

try:
    import numpy, sounddevice, faster_whisper, edge_tts  # noqa: F401
except ImportError as e:
    sys.exit(
        f"Jarvis isn't set up yet ({e.name} is missing).\n"
        "Run this once in PowerShell from the Jarvis folder:\n"
        "  powershell -ExecutionPolicy Bypass -File setup.ps1\n"
        "or just double-click jarvis.bat."
    )

sys.path.insert(0, str(HERE))
from jarvis.__main__ import main  # noqa: E402

main()
