"""HTTP server for triggering shows via GET requests."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from fcld.engine import DMXEngine
from fcld.model import FixtureContext, Rig


def discover_shows(shows_dir: str) -> dict[str, Path]:
    """Scan directory for valid show modules with run() function."""
    shows: dict[str, Path] = {}
    shows_path = Path(shows_dir)

    if not shows_path.exists():
        return shows

    for py_file in shows_path.glob("*.py"):
        if py_file.name.startswith("_"):
            continue

        try:
            spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "run"):
                shows[py_file.stem] = py_file
        except Exception:
            continue

    return shows


def load_show_module(show_path: Path) -> Any:
    """Load a show module from path."""
    spec = importlib.util.spec_from_file_location(show_path.stem, show_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {show_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[show_path.stem] = module
    spec.loader.exec_module(module)
    return module


class ShowRunner:
    """Manages show lifecycle with thread safety."""

    def __init__(self, shows_dir: str) -> None:
        self.shows_dir = shows_dir
        self._lock = threading.Lock()
        self._engine: DMXEngine | None = None
        self._thread: threading.Thread | None = None
        self._current_show: str | None = None
        self._start_time: float | None = None

    def get_shows(self) -> dict[str, Path]:
        """Get available shows."""
        return discover_shows(self.shows_dir)

    def play(self, show_name: str, start_at: float = 0.0) -> tuple[bool, str]:
        """Start a show. Returns (success, message)."""
        shows = self.get_shows()
        if show_name not in shows:
            return False, f"Show '{show_name}' not found"

        self.stop()

        show_path = shows[show_name]
        try:
            module = load_show_module(show_path)
            with FixtureContext() as ctx:
                clip = module.run()
            rig = Rig(ctx.fixtures)
        except Exception as e:
            return False, f"Error loading show: {e}"

        with self._lock:
            self._engine = DMXEngine(rig=rig, fps=40.0)
            self._current_show = show_name
            self._start_time = time.monotonic() - start_at

            self._thread = threading.Thread(
                target=self._run_show,
                args=(clip, start_at),
                daemon=True,
            )
            self._thread.start()

        return True, f"Started show '{show_name}'"

    def _run_show(self, clip: Any, start_at: float) -> None:
        """Run show in background thread."""
        engine = self._engine
        if engine is None:
            return

        try:
            engine.play(clip, start_at=start_at)
        except Exception as e:
            print(f"Show error: {e}")
        finally:
            with self._lock:
                if self._engine is engine:
                    self._current_show = None
                    self._start_time = None
                    self._engine = None

    def stop(self) -> tuple[bool, str]:
        """Stop current show. Returns (was_running, message)."""
        with self._lock:
            if self._engine is None:
                return False, "No show running"

            show_name = self._current_show
            self._engine.stop()
            self._engine = None
            self._current_show = None
            self._start_time = None

        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

        return True, f"Stopped show '{show_name}'"

    def status(self) -> dict[str, Any]:
        """Get current status."""
        with self._lock:
            if self._engine is None or self._current_show is None:
                return {"running": False}

            elapsed = 0.0
            if self._start_time is not None:
                elapsed = time.monotonic() - self._start_time

            return {
                "running": True,
                "show": self._current_show,
                "elapsed": round(elapsed, 2),
            }


class FCLDHandler(BaseHTTPRequestHandler):
    """HTTP request handler for FCLD."""

    runner: ShowRunner

    def log_message(self, format: str, *args: Any) -> None:
        """Log HTTP requests."""
        print(f"[HTTP] {args[0]}")

    def _send_json(self, data: dict[str, Any], status: int = 200) -> None:
        """Send JSON response."""
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        if path == "/":
            self._send_json({"status": "ok", "service": "fcld"})

        elif path == "/shows":
            shows = self.runner.get_shows()
            self._send_json({"shows": list(shows.keys())})

        elif path.startswith("/play/"):
            show_name = path[6:]
            start_at = 0.0
            if "start_at" in query:
                try:
                    start_at = float(query["start_at"][0])
                except (ValueError, IndexError):
                    pass

            success, message = self.runner.play(show_name, start_at)
            status = 200 if success else 404
            self._send_json({"success": success, "message": message}, status)

        elif path == "/stop":
            was_running, message = self.runner.stop()
            self._send_json({"was_running": was_running, "message": message})

        elif path == "/status":
            self._send_json(self.runner.status())

        else:
            self._send_json({"error": "Not found"}, 404)


def run_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    shows_dir: str = "/app/shows",
) -> None:
    """Run the HTTP server."""
    runner = ShowRunner(shows_dir)
    FCLDHandler.runner = runner

    server = HTTPServer((host, port), FCLDHandler)
    print(f"FCLD Server starting on http://{host}:{port}")
    print(f"Shows directory: {shows_dir}")

    shows = runner.get_shows()
    if shows:
        print(f"Available shows: {', '.join(shows.keys())}")
    else:
        print("No shows found")

    print()
    print("Endpoints:")
    print("  GET /         - Health check")
    print("  GET /shows    - List available shows")
    print("  GET /play/<n> - Start show (optional ?start_at=5.0)")
    print("  GET /stop     - Stop current show")
    print("  GET /status   - Current status")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        runner.stop()
        server.shutdown()
