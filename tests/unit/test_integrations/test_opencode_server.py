"""Unit tests for OpenCode server management functionality."""

from unittest.mock import MagicMock, patch
import pytest

from seo_agent.integrations.opencode.server import (
    check_opencode_health,
    ensure_opencode_server,
    start_opencode_server,
)


class TestOpenCodeServer:
    """Test suite for OpenCode server management."""

    @patch("urllib.request.urlopen")
    def test_check_opencode_health_success(self, mock_urlopen: MagicMock) -> None:
        """Test health check succeeds when server returns <500 status."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        assert check_opencode_health("http://127.0.0.1:4096") is True
        mock_urlopen.assert_called_once()

    @patch("urllib.request.urlopen", side_effect=Exception("Connection refused"))
    def test_check_opencode_health_failure(self, mock_urlopen: MagicMock) -> None:
        """Test health check fails when server raises exception."""
        assert check_opencode_health("http://127.0.0.1:4096") is False

    @patch("seo_agent.integrations.opencode.client.OpenCodeClient._resolve_opencode_binary", return_value="/usr/local/bin/opencode")
    @patch("os.path.isfile", return_value=True)
    @patch("subprocess.Popen")
    def test_start_opencode_server_success(
        self, mock_popen: MagicMock, mock_isfile: MagicMock, mock_resolve: MagicMock
    ) -> None:
        """Test start_opencode_server launches opencode serve with port."""
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc

        proc = start_opencode_server("http://127.0.0.1:4096")

        assert proc == mock_proc
        mock_popen.assert_called_once_with(
            ["/usr/local/bin/opencode", "serve", "--port", "4096"],
            stdout=-3,  # DEVNULL
            stderr=-3,  # DEVNULL
            start_new_session=True,
        )

    @patch("seo_agent.integrations.opencode.server.check_opencode_health", return_value=True)
    def test_ensure_opencode_server_already_running(self, mock_health: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
        """Test ensure_opencode_server skips startup when server is already healthy."""
        res = ensure_opencode_server(base_url="http://127.0.0.1:4096")

        assert res is True
        captured = capsys.readouterr()
        assert "Checking OpenCode server..." in captured.out
        assert "✓ OpenCode server detected." in captured.out

    @patch("seo_agent.integrations.opencode.server.check_opencode_health", side_effect=[False, True])
    @patch("seo_agent.integrations.opencode.server.start_opencode_server")
    @patch("time.sleep", return_value=None)
    def test_ensure_opencode_server_auto_starts(
        self, mock_sleep: MagicMock, mock_start: MagicMock, mock_health: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test ensure_opencode_server automatically starts server and succeeds."""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_start.return_value = mock_proc

        res = ensure_opencode_server(base_url="http://127.0.0.1:4096", startup_timeout=5, check_interval=0.1)

        assert res is True
        captured = capsys.readouterr()
        assert "Checking OpenCode server..." in captured.out
        assert "Starting OpenCode server..." in captured.out
        assert "Waiting for OpenCode..." in captured.out
        assert "OpenCode is ready." in captured.out

    @patch("seo_agent.integrations.opencode.server.check_opencode_health", return_value=False)
    @patch("seo_agent.integrations.opencode.server.start_opencode_server")
    @patch("time.sleep", return_value=None)
    def test_ensure_opencode_server_startup_timeout_fails(
        self, mock_sleep: MagicMock, mock_start: MagicMock, mock_health: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test ensure_opencode_server prints error and fails when server cannot be started."""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_start.return_value = mock_proc

        res = ensure_opencode_server(base_url="http://127.0.0.1:4096", startup_timeout=0.1, check_interval=0.05)

        assert res is False
        captured = capsys.readouterr()
        assert "Checking OpenCode server..." in captured.out
        assert "Starting OpenCode server..." in captured.out
        assert "Waiting for OpenCode..." in captured.out
        assert "OpenCode server is not running." in captured.out
        assert "opencode serve --port 4096" in captured.out
        assert "Workflow aborted." in captured.out
