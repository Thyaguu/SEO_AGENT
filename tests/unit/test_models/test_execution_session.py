"""Unit tests for ExecutionSession, ExecutionIteration, and FixTask."""

from datetime import datetime
import pytest

from seo_agent.models.execution_session import (
    ExecutionIteration,
    ExecutionSession,
    FixTask,
)
from seo_agent.models.task import ExecutionResult


class TestExecutionSession:
    def test_session_records_attempt_and_replaces_current(self):
        session = ExecutionSession()
        assert session.current_execution_result is None
        assert len(session.history) == 0

        res1 = ExecutionResult(request_id="req-1", success=False, plan=None)
        session.record_attempt(res1, review_result="Failed")

        assert session.current_execution_result == res1
        assert len(session.history) == 1
        assert session.history[0].iteration_number == 1
        assert session.history[0].execution_result == res1
        assert session.history[0].review_result == "Failed"

        res2 = ExecutionResult(request_id="req-1", success=True, plan=None)
        session.record_attempt(res2, review_result="Passed")

        assert session.current_execution_result == res2
        assert len(session.history) == 2
        assert session.history[1].iteration_number == 2
        assert session.history[1].execution_result == res2

    def test_fix_task_model_initialization(self):
        task = FixTask(
            task_id="fix-0001",
            file_path="index.html",
            current_proposed_content="<h1>New Title</h1>",
            review_feedback="Title missing brand keyword",
            suggestions="Add 'Acme' to title",
            repository_context={"repo": "/tmp/test"},
        )

        assert task.task_id == "fix-0001"
        assert task.file_path == "index.html"
        assert task.current_proposed_content == "<h1>New Title</h1>"
        assert task.review_feedback == "Title missing brand keyword"
        assert task.suggestions == "Add 'Acme' to title"
