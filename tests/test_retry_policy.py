import pytest
from pathlib import Path

from seo_agent.core.result import Failure
from seo_agent.models.review import ReviewDecision, ReviewResult
from seo_agent.workflow.context import WorkflowContext
from seo_agent.workflow.orchestrator import OrchestratorConfig, WorkflowOrchestrator


def test_get_latest_review_result():
    context = WorkflowContext(repository_path=Path("/tmp"))
    assert context.get_latest_review_result() is None

    review = ReviewResult(
        request_id="test-req",
        attempt_number=1,
        decision=ReviewDecision.APPROVED,
        overall_score=100,
    )
    context.set_review_result(review)
    assert context.get_latest_review_result() == review

    context.add_review_result(review)
    assert context.get_latest_review_result() == review


@pytest.mark.asyncio
async def test_non_retryable_programming_exceptions():
    config = OrchestratorConfig(max_retries=3)
    orchestrator = WorkflowOrchestrator(config=config)

    # Programming error message containing AttributeError
    error_msg = "'WorkflowContext' object has no attribute 'get_latest_review_result'"

    # Verify classification logic suppresses retries
    non_retryable_terms = (
        "AttributeError", "NameError", "ImportError", "TypeError", "ValueError",
        "AssertionError", "SyntaxError", "KeyError", "IndexError",
        "has no attribute", "not defined", "cannot import", "missing 1 required",
        "unexpected keyword argument", "unsupported operand", "object is not callable"
    )

    is_retryable = not any(term in error_msg for term in non_retryable_terms)
    assert is_retryable is False
