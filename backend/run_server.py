#!/usr/bin/env python3
"""
Start the backend with the same Python that runs this script, so anthropic and other
deps are available. Run from repo root: python backend/run_server.py
Or from backend/: python run_server.py
"""
import argparse
import os
import signal
import subprocess
import sys
import time

# Run from backend directory so uvicorn finds main:app
backend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)


def free_port(port: int = 8000) -> None:
    """Kill any process listening on the given port so we can bind to it."""
    try:
        out = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            for pid in out.stdout.strip().split():
                try:
                    os.kill(int(pid), signal.SIGKILL)
                except (ProcessLookupError, ValueError):
                    pass
            time.sleep(2)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the backend server")
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable reload (single process; use if you get 'Address already in use')",
    )
    parser.add_argument(
        "--free-port",
        action="store_true",
        help="Kill any process on port 8000 before starting",
    )
    args = parser.parse_args()
    if args.free_port:
        free_port(8000)
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=not args.no_reload,
    )


if __name__ == "__main__":
    main()
