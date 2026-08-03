"""Vercel Serverless entrypoint for the Flask backend.

The existing backend package was originally designed to run from
`backend/app.py` under Gunicorn or the desktop EXE.  Vercel loads Python
functions from the root `api/` directory, so this small adapter places the
backend folder on `sys.path` and exposes the Flask WSGI app as `app`.
"""
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'backend'
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app import create_app  # noqa: E402


app = create_app()
