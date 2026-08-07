"""Unit tests for OpenCodeClient session lifecycle and recovery management."""

import pytest
from unittest.mock import MagicMock, patch
from seo_agent.integrations.opencode.client import OpenCodeClient, OpenCodeClientError
from seo_agent.integrations.opencode.models import OpenCodeRequest, OpenCodeModel


class TestOpenCodeClientSession:
    @pytest.fixture
    def client(self):
        return OpenCodeClient(
            base_url="http://127.0.0.1:4096",
            api_key="test_key",
            timeout=10,
        )

    def test_create_session_success(self, client):
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value.read.return_value = b'{"id": "ses_12345"}'

        with patch("urllib.request.urlopen", return_value=mock_cm):
            session_id = client._create_session("/path/to/repo")
            assert session_id == "ses_12345"

    def test_get_or_create_session_creates_when_none(self, client):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"id": "ses_new"}'

        with patch.object(client, "_create_session", return_value="ses_new") as mock_create:
            session_id = client.get_or_create_session("/path/to/repo")
            assert session_id == "ses_new"
            mock_create.assert_called_once_with("/path/to/repo")

    def test_get_or_create_session_reuses_when_valid(self, client):
        client._session_id = "ses_valid"
        client._session_workspace_path = "/path/to/repo"

        with patch.object(client, "_is_session_valid", return_value=True), \
             patch.object(client, "_create_session") as mock_create:
            session_id = client.get_or_create_session("/path/to/repo")
            assert session_id == "ses_valid"
            mock_create.assert_not_called()

    def test_get_or_create_session_recreates_when_path_changes(self, client):
        client._session_id = "ses_old"
        client._session_workspace_path = "/path/to/old_repo"

        with patch.object(client, "_create_session", return_value="ses_new") as mock_create:
            session_id = client.get_or_create_session("/path/to/new_repo")
            assert session_id == "ses_new"
            assert client._session_workspace_path == "/path/to/new_repo"
            mock_create.assert_called_once_with("/path/to/new_repo")

    def test_execute_retries_on_session_not_found(self, client):
        request = OpenCodeRequest(
            request_id="req_001",
            instructions="Add SEO title",
            workspace_path="/path/to/repo",
            model=OpenCodeModel.CLAUDE_3_5_SONNET,
        )

        proc_fail = MagicMock()
        proc_fail.returncode = 1
        proc_fail.stderr = "Error: Session not found"
        proc_fail.stdout = ""

        proc_success = MagicMock()
        proc_success.returncode = 0
        proc_success.stderr = ""
        proc_success.stdout = '{"type": "step_finish"}'

        with patch.object(client, "get_or_create_session", side_effect=["ses_expired", "ses_fresh"]), \
             patch("subprocess.run", side_effect=[proc_fail, proc_success]) as mock_sub:
            result = client.execute(request)
            assert result.is_success
            assert mock_sub.call_count == 2
