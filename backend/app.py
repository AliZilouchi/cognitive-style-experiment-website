"""Vercel FastAPI entrypoint.

The application itself stays in ``src/sepid_rag`` so local, Docker, Colab, and
Vercel deployments all execute the same research code.
"""

from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from sepid_rag.api import app  # noqa: E402,F401
