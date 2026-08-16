"""Focused unit tests for migrated OpenCode integration Pydantic models.

Tests construction, defaults, optional fields, enum fields, nested models,
properties, serialization, deserialization, frozen immutability, and backward compatibility.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
import pytest
from pydantic import ValidationError

from seo_agent.integrations.opencode.models import (
    OpenCodeAction,
    OpenCodeActionRequest,
    OpenCodeActionResult,
    OpenCodeExecutionContext,
    OpenCodeFileChange,
    OpenCodeFileEdit,
    OpenCodeFileRead,
    OpenCodeModel,
    OpenCodeRequest,
    OpenCodeResponse,
    OpenCodeSearchQuery,
    OpenCodeStatus,
)


def test_opencode_file_edit_and_read():
    """Test OpenCodeFileEdit and OpenCodeFileRead construction and defaults."""
    edit = OpenCodeFileEdit(file_path="src/app.py", content="print('hello')")
    assert edit.file_path == "src/app.py"
    assert edit.content == "print('hello')"
    assert edit.old_content is None
    assert edit.is_new is False

    read = OpenCodeFileRead(file_path="src/app.py", line_start=1, line_end=10)
    assert read.file_path == "src/app.py"
    assert read.line_start == 1
    assert read.line_end == 10


def test_opencode_search_query_and_action_request():
    """Test OpenCodeSearchQuery and OpenCodeActionRequest nested models."""
    query = OpenCodeSearchQuery(pattern="import", file_pattern="*.py")
    action_req = OpenCodeActionRequest(
        action=OpenCodeAction.SEARCH_FILES,
        search_query=query,
    )

    assert action_req.action == OpenCodeAction.SEARCH_FILES
    assert action_req.search_query is not None
    assert action_req.search_query.pattern == "import"
    assert action_req.max_results == 100


def test_opencode_request_defaults_and_frozen_immutability():
    """Test OpenCodeRequest defaults and frozen immutability constraint."""
    action_req = OpenCodeActionRequest(
        action=OpenCodeAction.WRITE_FILE,
        file_path="seo.html",
        content="<h1>Title</h1>",
    )
    req = OpenCodeRequest(
        request_id="req_123",
        instructions="Create SEO landing page",
        actions=(action_req,),
    )

    assert req.request_id == "req_123"
    assert req.model == OpenCodeModel.CLAUDE_3_5_SONNET
    assert req.max_iterations == 10
    assert len(req.actions) == 1

    with pytest.raises(ValidationError):
        req.instructions = "Changed instructions"


def test_opencode_response_properties():
    """Test OpenCodeResponse calculated properties: is_success, duration_seconds, all_file_changes."""
    change1 = OpenCodeFileChange(file_path="page1.html", change_type="created")
    change2 = OpenCodeFileChange(file_path="page2.html", change_type="modified")

    result1 = OpenCodeActionResult(
        action=OpenCodeAction.WRITE_FILE,
        success=True,
        file_changes=(change1,),
    )
    result2 = OpenCodeActionResult(
        action=OpenCodeAction.EDIT_FILE,
        success=True,
        file_changes=(change2,),
    )

    start_time = datetime(2026, 1, 1, 12, 0, 0)
    end_time = datetime(2026, 1, 1, 12, 0, 5)

    resp = OpenCodeResponse(
        request_id="resp_456",
        status=OpenCodeStatus.COMPLETED,
        results=(result1, result2),
        started_at=start_time,
        completed_at=end_time,
    )

    assert resp.is_success is True
    assert resp.duration_seconds == 5.0
    assert len(resp.all_file_changes) == 2
    assert resp.all_file_changes[0].file_path == "page1.html"


def test_opencode_execution_context_path_coercion():
    """Test OpenCodeExecutionContext workspace_path handling."""
    ctx = OpenCodeExecutionContext(workspace_path=Path("/tmp/workspace"))
    assert isinstance(ctx.workspace_path, Path)
    assert str(ctx.workspace_path) == "/tmp/workspace"


def test_dataclasses_asdict_and_is_dataclass_compatibility():
    """Test dataclasses.asdict() and is_dataclass() compatibility helpers on OpenCode models."""
    change = OpenCodeFileChange(file_path="test.py", change_type="modified")
    assert is_dataclass(change)

    d = asdict(change)
    assert isinstance(d, dict)
    assert d["file_path"] == "test.py"
    assert d["change_type"] == "modified"


def test_json_payload_serialization_structure():
    """Test serialization of OpenCode models to verify JSON structure compatibility."""
    action_req = OpenCodeActionRequest(
        action=OpenCodeAction.WRITE_FILE,
        file_path="index.html",
        content="<p>Test</p>",
    )
    req = OpenCodeRequest(
        request_id="req_test",
        instructions="Write file",
        actions=(action_req,),
        model=OpenCodeModel.CLAUDE_3_5_SONNET,
    )

    d = req.to_dict(mode="json")
    assert d["request_id"] == "req_test"
    assert d["instructions"] == "Write file"
    assert d["model"] == "claude-3-5-sonnet-20241022"
    assert len(d["actions"]) == 1
    assert d["actions"][0]["action"] == "write_file"
