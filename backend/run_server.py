#!/usr/bin/env python3
"""
Start the backend with the same Python that runs this script, so anthropic and other
deps are available. Run from repo root: python backend/run_server.py
Or from backend/: python run_server.py
"""
import sys
import os

# Run from backend directory so uvicorn finds main:app
backend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

# Use this Python's uvicorn
import uvicorn
uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
