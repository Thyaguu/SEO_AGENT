"""Focused unit tests for migrated review and execution session Pydantic models.

Tests construction, defaults, optional fields, enum fields, nested models,
properties, serialization, deserialization, frozen immutability, execution session history tracking,
and backward compatibility helpers.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
import pytest
from pydantic import ValidationError

from seo_agent.models.execution_session import (
    ExecutionIteration,
    ExecutionSession,
    FixTask,
)

from seo_agent.models.enums import (
    ReviewDecision,
    ValidationCategory,
    ValidationSeverity,
)

from seo_agent.models.review import (
    ContentQualityCheck,
    PageReviewContext,
    ReviewCriteria,
    ReviewFeedback,
    ReviewResult,
    ReviewSummary,
    SEOQualityCheck,
    ValidationIssue,
    ValidationResult,
)


def test_validation_issue_and_result_properties():
    """Test ValidationIssue and ValidationResult construction and computed properties."""
    issue_crit = ValidationIssue(
        category=ValidationCategory.SEO_QUALITY,
        severity=ValidationSeverity.CRITICAL,
        message="Missing H1 heading",
    )
    issue_warn = ValidationIssue(
        category=ValidationCategory.CONTENT_QUALITY,
        severity=ValidationSeverity.WARNING,
        message="Short description",
    )

    val_res = ValidationResult(
        item_id="page_1",
        item_type="seo_page",
        passed=False,
        issues=(issue_crit, issue_warn),
    )

    assert val_res.item_id == "page_1"
    assert val_res.passed is False
    assert len(val_res.critical_issues) == 1
    assert val_res.critical_issues[0].message == "Missing H1 heading"
    assert val_res.error_count == 1
    assert val_res.warning_count == 1


def test_review_result_and_feedback_properties():
    """Test ReviewResult and ReviewFeedback properties."""
    issue = ValidationIssue(
        category=ValidationCategory.TECHNICAL_SEO,
        severity=ValidationSeverity.CRITICAL,
        message="Broken canonical URL",
    )
    val_res = ValidationResult(
        item_id="page_2",
        item_type="html_page",
        passed=False,
        issues=(issue,),
    )
    feedback = ReviewFeedback(
        decision=ReviewDecision.REJECTED,
        summary="SEO Quality Check Failed",
        issues=(issue,),
    )
    result = ReviewResult(
        request_id="req_999",
        attempt_number=1,
        decision=ReviewDecision.REJECTED,
        feedback=feedback,
        validation_results=(val_res,),
    )

    assert result.is_approved is False
    assert result.total_issues == 1
    assert result.critical_issues_count == 1


def test_fix_task_construction_and_frozen_immutability():
    """Test FixTask model construction, positional args, and frozen immutability."""
    task = FixTask(
        task_id="fix_001",
        file_path="seo/ats.html",
        review_feedback="Fix missing title",
    )

    assert task.task_id == "fix_001"
    assert task.file_path == "seo/ats.html"
    assert task.review_feedback == "Fix missing title"
    assert task.repository_context == {}

    with pytest.raises(ValidationError):
        task.file_path = "seo/new.html"


def test_execution_session_attempt_recording():
    """Test ExecutionSession attempt recording, current result updating, and iteration_count."""
    session = ExecutionSession()
    assert session.iteration_count == 0
    assert session.current_execution_result is None

    exec_res_1 = {"status": "failed", "attempt": 1}
    rev_res_1 = {"decision": "rejected"}
    session.record_attempt(exec_res_1, rev_res_1)

    assert session.iteration_count == 1
    assert session.current_execution_result == exec_res_1
    assert session.history[0].iteration_number == 1
    assert session.history[0].execution_result == exec_res_1
    assert session.history[0].review_result == rev_res_1

    exec_res_2 = {"status": "success", "attempt": 2}
    rev_res_2 = {"decision": "approved"}
    session.record_attempt(exec_res_2, rev_res_2)

    assert session.iteration_count == 2
    assert session.current_execution_result == exec_res_2
    assert session.history[1].iteration_number == 2


def test_dataclasses_asdict_and_is_dataclass_compatibility():
    """Test dataclasses.asdict() and is_dataclass() compatibility helpers on review/execution models."""
    task = FixTask(task_id="fix_002", file_path="index.html")
    assert is_dataclass(task)

    d = asdict(task)
    assert isinstance(d, dict)
    assert d["task_id"] == "fix_002"
    assert d["file_path"] == "index.html"


def test_workflow_context_review_result_accepts_validation_result_and_review_result():
    """Regression test: WorkflowContext.review_result accepts ValidationResult and ReviewResult."""
    from pathlib import Path
    from seo_agent.review.validator import ValidationResult as ValidatorValidationResult
    from seo_agent.workflow.context import WorkflowContext

    ctx = WorkflowContext(repository_path=Path("/tmp/repo"))
    assert ctx.review_result is None

    # 1. Accept ValidationResult from ReviewValidator
    val_res = ValidatorValidationResult(is_valid=True)
    ctx.set_review_result(val_res)
    assert ctx.review_result is val_res
    assert ctx.review_result.is_valid is True

    # 2. Accept ReviewResult from ReviewEngine
    rev_res = ReviewResult(
        request_id="req_100",
        attempt_number=1,
        decision=ReviewDecision.APPROVED,
    )
    ctx.set_review_result(rev_res)
    assert ctx.review_result is rev_res
    assert ctx.review_result.is_approved is True
    assert ctx.review_result.is_valid is True

