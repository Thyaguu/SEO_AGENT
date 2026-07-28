"""Unit tests for ApprovedChangesApplier."""

from pathlib import Path
import pytest

from seo_agent.models.task import ExecutionResult, PhaseResult, TaskResult
from seo_agent.seo.applier import ApprovedChangesApplier, ApplicationSummary


class TestApprovedChangesApplier:
    def test_apply_changes_writes_files_successfully(self, tmp_path: Path):
        applier = ApprovedChangesApplier()

        task_res = TaskResult(
            task_id="task-0001",
            success=True,
            output={
                "file_edits": [
                    {
                        "file_path": "about.html",
                        "success": True,
                        "content": "<h1>Updated About Page</h1>",
                    }
                ]
            },
        )
        phase_res = PhaseResult(
            phase_id="phase-1",
            success=True,
            task_results=(task_res,),
        )
        exec_res = ExecutionResult(
            request_id="req-123",
            success=True,
            plan=None,
            phase_results=(phase_res,),
        )

        res = applier.apply_changes(exec_res, tmp_path)
        assert res.is_success()
        summary = res.unwrap()
        assert summary.total_written == 1
        assert (tmp_path / "about.html").exists()
        assert (tmp_path / "about.html").read_text() == "<h1>Updated About Page</h1>"

    def test_apply_changes_skips_none_content(self, tmp_path: Path):
        applier = ApprovedChangesApplier()

        task_res = TaskResult(
            task_id="task-0002",
            success=True,
            output={
                "file_edits": [
                    {
                        "file_path": "contact.html",
                        "success": True,
                        "content": None,
                    }
                ]
            },
        )
        phase_res = PhaseResult(
            phase_id="phase-1",
            success=True,
            task_results=(task_res,),
        )
        exec_res = ExecutionResult(
            request_id="req-123",
            success=True,
            plan=None,
            phase_results=(phase_res,),
        )

        res = applier.apply_changes(exec_res, tmp_path)
        assert res.is_success()
        summary = res.unwrap()
        assert summary.total_written == 0
        assert "contact.html" in summary.skipped_files
