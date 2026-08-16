"""Unit tests for foundational BasePydanticModel and consolidated enums.

Ensures that BasePydanticModel handles serialization, deserialization, type coercion,
extra parameter tolerance, and that consolidated enums match original definitions exactly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from pydantic import Field

from seo_agent.models.base import BasePydanticModel
import seo_agent.models.enums as consolidated_enums
from seo_agent.models.repository import FrameworkType, PageType, RoutingStrategy
from seo_agent.models.review import ReviewDecision, ValidationCategory, ValidationSeverity
from seo_agent.models.seo import ChangeFrequency, KeywordType
from seo_agent.models.task import Complexity, TaskPriority, TaskStatus, TaskType
from seo_agent.models.workflow import WorkflowEvent, WorkflowStatus
from seo_agent.workflow.stages import WorkflowStage


class SampleModel(BasePydanticModel):
    """Sample derived model for testing BasePydanticModel features."""

    name: str
    count: int = Field(default=0, ge=0)
    file_path: Path | None = None
    stage: WorkflowStage = WorkflowStage.INITIALIZED


def test_base_pydantic_model_instantiation():
    """Test model instantiation with default and valid parameters."""
    model = SampleModel(name="test_run", count=5, file_path=Path("/tmp/test.txt"))
    assert model.name == "test_run"
    assert model.count == 5
    assert model.file_path == Path("/tmp/test.txt")
    assert model.stage == WorkflowStage.INITIALIZED


def test_base_pydantic_model_to_dict_python():
    """Test to_dict method in python mode (preserves Path and Enum objects)."""
    model = SampleModel(name="test", file_path=Path("/repo"))
    data = model.to_dict(mode="python")
    assert data["name"] == "test"
    assert data["file_path"] == Path("/repo")
    assert data["stage"] == WorkflowStage.INITIALIZED


def test_base_pydantic_model_to_json_and_from_dict():
    """Test to_json serialization and from_dict deserialization."""
    model = SampleModel(name="json_test", count=42, stage=WorkflowStage.PLANNING)
    json_str = model.to_json()
    assert '"name":"json_test"' in json_str or '"name": "json_test"' in json_str

    raw_dict: dict[str, Any] = {
        "name": "from_dict_test",
        "count": 100,
        "stage": "execution",
        "extra_field_to_ignore": "should_be_ignored",
    }
    reconstructed = SampleModel.from_dict(raw_dict)
    assert reconstructed.name == "from_dict_test"
    assert reconstructed.count == 100
    assert reconstructed.stage == WorkflowStage.EXECUTION


def test_consolidated_enums_identity_and_values():
    """Verify consolidated enums retain exact values, types, and identity."""
    assert consolidated_enums.WorkflowStage is WorkflowStage
    assert consolidated_enums.WorkflowStatus is WorkflowStatus
    assert consolidated_enums.WorkflowEvent is WorkflowEvent
    assert consolidated_enums.FrameworkType is FrameworkType
    assert consolidated_enums.RoutingStrategy is RoutingStrategy
    assert consolidated_enums.PageType is PageType
    assert consolidated_enums.TaskStatus is TaskStatus
    assert consolidated_enums.TaskPriority is TaskPriority
    assert consolidated_enums.Complexity is Complexity
    assert consolidated_enums.TaskType is TaskType
    assert consolidated_enums.ReviewDecision is ReviewDecision
    assert consolidated_enums.ValidationSeverity is ValidationSeverity
    assert consolidated_enums.ValidationCategory is ValidationCategory
    assert consolidated_enums.KeywordType is KeywordType
    assert consolidated_enums.ChangeFrequency is ChangeFrequency


def test_enum_string_values_unchanged():
    """Verify specific enum string values match exact historical definitions."""
    assert WorkflowStage.INITIALIZED.value == "initialized"
    assert WorkflowStage.EXECUTION.value == "execution"
    assert FrameworkType.STATIC_HTML.value == "static_html"
    assert FrameworkType.NEXT_JS.value == "next_js"
    assert TaskType.SEO_PAGE_GENERATION.value == "seo_page_generation"
    assert ReviewDecision.APPROVED.value == "approved"
    assert ReviewDecision.REJECTED.value == "rejected"
    assert KeywordType.PRIMARY.value == "primary"
    assert KeywordType.SECONDARY.value == "secondary"
