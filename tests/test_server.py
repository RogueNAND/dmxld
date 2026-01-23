"""Unit tests for HTTP server."""

import json
import threading
import time
import urllib.request
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from fcld.server import ShowRunner, discover_shows, run_server


class TestDiscoverShows:
    """Tests for show discovery."""

    def test_discovers_valid_shows(self, tmp_path: Path) -> None:
        """Valid show files are discovered."""
        show_file = tmp_path / "my_show.py"
        show_file.write_text(
            "def create_rig(): pass\ndef create_show(): pass"
        )
        shows = discover_shows(str(tmp_path))
        assert "my_show" in shows
        assert shows["my_show"] == show_file

    def test_ignores_files_without_create_rig(self, tmp_path: Path) -> None:
        """Files missing create_rig are ignored."""
        show_file = tmp_path / "incomplete.py"
        show_file.write_text("def create_show(): pass")
        shows = discover_shows(str(tmp_path))
        assert "incomplete" not in shows

    def test_ignores_files_without_create_show(self, tmp_path: Path) -> None:
        """Files missing create_show are ignored."""
        show_file = tmp_path / "incomplete.py"
        show_file.write_text("def create_rig(): pass")
        shows = discover_shows(str(tmp_path))
        assert "incomplete" not in shows

    def test_ignores_underscore_files(self, tmp_path: Path) -> None:
        """Files starting with underscore are ignored."""
        show_file = tmp_path / "_private.py"
        show_file.write_text(
            "def create_rig(): pass\ndef create_show(): pass"
        )
        shows = discover_shows(str(tmp_path))
        assert "_private" not in shows

    def test_ignores_syntax_errors(self, tmp_path: Path) -> None:
        """Files with syntax errors are ignored."""
        show_file = tmp_path / "broken.py"
        show_file.write_text("def create_rig( invalid syntax")
        shows = discover_shows(str(tmp_path))
        assert "broken" not in shows

    def test_returns_empty_for_missing_directory(self) -> None:
        """Returns empty dict for non-existent directory."""
        shows = discover_shows("/nonexistent/path/12345")
        assert shows == {}

    def test_discovers_multiple_shows(self, tmp_path: Path) -> None:
        """Multiple valid shows are discovered."""
        for name in ["show_a", "show_b", "show_c"]:
            (tmp_path / f"{name}.py").write_text(
                "def create_rig(): pass\ndef create_show(): pass"
            )
        shows = discover_shows(str(tmp_path))
        assert len(shows) == 3
        assert all(name in shows for name in ["show_a", "show_b", "show_c"])


class TestShowRunner:
    """Tests for ShowRunner lifecycle management."""

    def test_initial_status_not_running(self, tmp_path: Path) -> None:
        """Initial status shows not running."""
        runner = ShowRunner(str(tmp_path))
        status = runner.status()
        assert status["running"] is False

    def test_get_shows_returns_discovered(self, tmp_path: Path) -> None:
        """get_shows returns discovered shows."""
        (tmp_path / "test_show.py").write_text(
            "def create_rig(): pass\ndef create_show(): pass"
        )
        runner = ShowRunner(str(tmp_path))
        shows = runner.get_shows()
        assert "test_show" in shows

    def test_play_nonexistent_show_returns_error(self, tmp_path: Path) -> None:
        """Playing non-existent show returns error."""
        runner = ShowRunner(str(tmp_path))
        success, message = runner.play("nonexistent")
        assert success is False
        assert "not found" in message

    def test_stop_when_not_running_returns_false(self, tmp_path: Path) -> None:
        """Stopping when nothing running returns was_running=False."""
        runner = ShowRunner(str(tmp_path))
        was_running, message = runner.stop()
        assert was_running is False
        assert "No show running" in message


class TestShowRunnerWithMockEngine:
    """Tests for ShowRunner with mocked DMXEngine."""

    @pytest.fixture
    def mock_show_dir(self, tmp_path: Path) -> Path:
        """Create a directory with a mock show."""
        show_content = '''
from fcld.model import Rig, Fixture, FixtureType, Vec3, FixtureState
from fcld.clips import TimelineClip

class MockType(FixtureType):
    channel_count = 4
    def encode(self, state: FixtureState) -> dict[int, int]:
        return {1: int(state.dimmer * 255)}

def create_rig():
    return Rig([Fixture("f1", MockType(), 1, 1, Vec3(0,0,0), set())])

def create_show():
    return TimelineClip()
'''
        (tmp_path / "mock_show.py").write_text(show_content)
        return tmp_path

    def test_play_starts_show(self, mock_show_dir: Path) -> None:
        """Playing a show starts it."""
        runner = ShowRunner(str(mock_show_dir))

        with patch("fcld.server.DMXEngine") as MockEngine:
            mock_engine = MagicMock()
            MockEngine.return_value = mock_engine

            success, message = runner.play("mock_show")

            assert success is True
            assert "Started" in message
            assert runner._current_show == "mock_show"

    def test_play_sets_current_show(self, mock_show_dir: Path) -> None:
        """Playing a show sets the current show name."""
        runner = ShowRunner(str(mock_show_dir))

        with patch("fcld.server.DMXEngine") as MockEngine:
            mock_engine = MagicMock()
            MockEngine.return_value = mock_engine

            runner.play("mock_show")

            # Current show should be set
            assert runner._current_show == "mock_show"


class TestServerIntegration:
    """Integration tests for HTTP server."""

    @pytest.fixture
    def server_with_show(self, tmp_path: Path) -> Generator[tuple[str, ShowRunner], None, None]:
        """Start a test server with a mock show."""
        show_content = '''
from fcld.model import Rig, Fixture, FixtureType, Vec3, FixtureState
from fcld.clips import TimelineClip

class MockType(FixtureType):
    channel_count = 4
    def encode(self, state: FixtureState) -> dict[int, int]:
        return {1: int(state.dimmer * 255)}

def create_rig():
    return Rig([Fixture("f1", MockType(), 1, 1, Vec3(0,0,0), set())])

def create_show():
    return TimelineClip()
'''
        (tmp_path / "test_show.py").write_text(show_content)

        # Find an available port
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]

        runner = ShowRunner(str(tmp_path))

        from http.server import HTTPServer
        from fcld.server import FCLDHandler

        class Handler(FCLDHandler):
            pass
        Handler.runner = runner

        server = HTTPServer(('127.0.0.1', port), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        time.sleep(0.1)  # Wait for server to start

        yield f"http://127.0.0.1:{port}", runner

        server.shutdown()

    def _fetch(self, url: str) -> dict:
        """Fetch JSON from URL."""
        req = urllib.request.urlopen(url, timeout=5)
        return json.loads(req.read())

    def test_health_endpoint(self, server_with_show: tuple[str, ShowRunner]) -> None:
        """Health endpoint returns ok."""
        base_url, _ = server_with_show
        result = self._fetch(f"{base_url}/")
        assert result["status"] == "ok"
        assert result["service"] == "fcld"

    def test_shows_endpoint(self, server_with_show: tuple[str, ShowRunner]) -> None:
        """Shows endpoint lists available shows."""
        base_url, _ = server_with_show
        result = self._fetch(f"{base_url}/shows")
        assert "test_show" in result["shows"]

    def test_status_endpoint_not_running(self, server_with_show: tuple[str, ShowRunner]) -> None:
        """Status shows not running initially."""
        base_url, _ = server_with_show
        result = self._fetch(f"{base_url}/status")
        assert result["running"] is False

    def test_play_nonexistent_returns_404(self, server_with_show: tuple[str, ShowRunner]) -> None:
        """Playing non-existent show returns 404."""
        base_url, _ = server_with_show
        try:
            self._fetch(f"{base_url}/play/nonexistent")
            assert False, "Should have raised HTTPError"
        except urllib.request.HTTPError as e:
            assert e.code == 404

    def test_stop_endpoint(self, server_with_show: tuple[str, ShowRunner]) -> None:
        """Stop endpoint works when nothing running."""
        base_url, _ = server_with_show
        result = self._fetch(f"{base_url}/stop")
        assert result["was_running"] is False

    def test_404_for_unknown_path(self, server_with_show: tuple[str, ShowRunner]) -> None:
        """Unknown paths return 404."""
        base_url, _ = server_with_show
        try:
            self._fetch(f"{base_url}/unknown/path")
            assert False, "Should have raised HTTPError"
        except urllib.request.HTTPError as e:
            assert e.code == 404
