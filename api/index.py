"""
API Index for Vercel function.
"""
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app import create_app

app = create_app()
