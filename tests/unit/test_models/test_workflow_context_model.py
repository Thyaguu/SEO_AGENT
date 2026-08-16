"""Focused unit tests for migrated WorkflowContext Pydantic model.

Tests construction, defaults, Path coercion, mutable state updates, stage transitions,
error recording, duration calculation, status evaluation, file path extraction, summary,
and backward compatibility.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
import pytest

from seo_agent.models.repository import RepositoryInfo
from seo_agent.models.seo_input import NormalizedSEOEntry, SEOInputCollection
from seo_agent.workflow.context import WorkflowContext
from seo_agent.workflow.stages import WorkflowStage


def test_workflow_context_initialization():
    """Test WorkflowContext default initialization and Path coercion."""
    ctx = WorkflowContext(repository_path="/tmp/repo")
    assert isinstance(ctx.repository_path, Path)
    assert str(ctx.repository_path) == "/tmp/repo"
    assert ctx.stage == WorkflowStage.INITIALIZED
    assert ctx.errors == []
    assert ctx.transitions == []
    assert ctx.metadata == {}
    assert ctx.config == {}
    assert ctx.is_complete() is False


def test_workflow_context_mutable_state_updates():
    """Test mutating WorkflowContext stage, errors, and metadata."""
    ctx = WorkflowContext(repository_path=Path("/tmp/repo"))

    # Stage update
    ctx.update_stage(WorkflowStage.SCANNING)
    assert ctx.stage == WorkflowStage.SCANNING
    assert len(ctx.transitions) == 1
    assert ctx.transitions[0].from_stage == WorkflowStage.INITIALIZED
    assert ctx.transitions[0].to_stage == WorkflowStage.SCANNING

    # Error recording
    ctx.add_error("Minor warning error")
    assert ctx.has_errors() is True
    assert ctx.get_error_summary() == "Minor warning error"

    # Metadata mutation
    ctx.metadata["test_key"] = "test_val"
    assert ctx.metadata["test_key"] == "test_val"

    # Record failure
    ctx.record_failure("Critical failure")
    assert ctx.stage == WorkflowStage.FAILED
    assert ctx.is_complete() is True
    assert ctx.is_successful() is False


def test_workflow_context_seo_input_lookup():
    """Test get_seo_entry_for_page helper."""
    entry = NormalizedSEOEntry(
        keyword="Recruitment Software",
        page_path="/index.html",
    )
    seo_coll = SEOInputCollection(records=[entry])
    ctx = WorkflowContext(repository_path=Path("/tmp/repo"), seo_input=seo_coll)

    found = ctx.get_seo_entry_for_page("index.html")
    assert found is not None
    assert found.keyword == "Recruitment Software"


def test_workflow_context_summary_and_dataclass_compat():
    """Test get_summary() dictionary and dataclasses compatibility."""
    ctx = WorkflowContext(repository_path=Path("/tmp/repo"))
    summary = ctx.get_summary()

    assert summary["repository_path"] == "/tmp/repo"
    assert summary["current_stage"] == "initialized"
    assert summary["is_complete"] is False

    assert is_dataclass(ctx)
    d = asdict(ctx)
    assert isinstance(d, dict)
    assert str(d["repository_path"]) == "/tmp/repo"


def test_workflow_context_repository_path_remains_path_after_mutations():
    """Regression test: repository_path MUST remain pathlib.Path after field mutations."""
    from seo_agent.models.enums import FrameworkType
    from seo_agent.models.repository import FrameworkInfo, PageInfo, RepositoryInfo

    repo_path = Path("/tmp/repo")
    ctx = WorkflowContext(repository_path=repo_path)

    assert isinstance(ctx.repository_path, Path)

    # Perform assignment / mutations
    fw = FrameworkInfo(framework_type=FrameworkType.STATIC_HTML, confidence=1.0)
    p_info = PageInfo(file_path=Path("/tmp/repo/index.html"), route="/index.html", title="Home")
    repo_info = RepositoryInfo(root_path=repo_path, framework=fw, pages=(p_info,))

    ctx.set_repository_info(repo_info)
    assert isinstance(ctx.repository_path, Path)
    assert isinstance(p_info.file_path, str)

    ctx.update_stage(WorkflowStage.SCANNING)
    assert isinstance(ctx.repository_path, Path)

    ctx.metadata["test"] = "value"
    assert isinstance(ctx.repository_path, Path)

    # Verify path concatenation operator / works cleanly
    target_file = ctx.repository_path / "about.html"
    assert isinstance(target_file, Path)
    assert str(target_file) == "/tmp/repo/about.html"

