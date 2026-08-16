"""Focused unit tests for API boundary request and response Pydantic v2 schemas.

Tests construction, field validation, defaults, bounds, nested models,
and JSON serialization/deserialization compatibility.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from seo_agent.api.schemas import (
    CompetitorPayload,
    ErrorResponse,
    ExecutionStatus,
    FileChange,
    HealthResponse,
    KeywordPayload,
    PageAnalysisResult,
    PagePayload,
    ReviewStatus,
    SEOAgentRequest,
    SEOPageResult,
    SEOPayload,
    SEOResponse,
    StageResult,
    VersionResponse,
)


def test_keyword_payload_validation():
    """Test KeywordPayload validation rules and defaults."""
    kw = KeywordPayload(term="recruitment software", type="primary", search_volume=5000, difficulty=45.5)
    assert kw.term == "recruitment software"
    assert kw.type == "primary"
    assert kw.search_volume == 5000
    assert kw.difficulty == 45.5

    with pytest.raises(ValidationError):
        KeywordPayload(term="", type="invalid_type")


def test_seo_payload_and_agent_request_validation():
    """Test SEOPayload and SEOAgentRequest model validation."""
    kw = KeywordPayload(term="applicant tracking", type="primary")
    comp = CompetitorPayload(name="Competitor A", strengths=["Fast UI"])

    payload = SEOPayload(
        target_urls=["https://example.com/ats"],
        seed_keywords=[kw],
        competitors=[comp],
    )

    request = SEOAgentRequest(
        request_id="req_api_100",
        repository_path="/tmp/repo",
        seo_payload=payload,
        max_seo_pages=5,
    )

    assert request.request_id == "req_api_100"
    assert request.repository_path == "/tmp/repo"
    assert request.max_seo_pages == 5
    assert request.skip_git is False

    with pytest.raises(ValidationError):
        SEOAgentRequest(
            request_id="req_empty",
            repository_path="   ",
            seo_payload=payload,
        )


def test_seo_response_serialization():
    """Test SEOResponse model_dump mode='json' structure compatibility."""
    change = FileChange(file_path="seo/page1.html", change_type="created", description="Generated landing page")
    stage_res = StageResult(
        stage="seo_page_generation",
        status="completed",
        started_at="2026-01-01T12:00:00Z",
        completed_at="2026-01-01T12:00:05Z",
        duration_seconds=5.0,
        file_changes=[change],
    )

    resp = SEOResponse(
        request_id="req_api_100",
        status=ExecutionStatus.COMPLETED,
        review_status=ReviewStatus.APPROVED,
        started_at="2026-01-01T12:00:00Z",
        completed_at="2026-01-01T12:00:05Z",
        duration_seconds=5.0,
        stages=[stage_res],
        file_changes=[change],
    )

    dumped = resp.model_dump(mode="json")
    assert dumped["request_id"] == "req_api_100"
    assert dumped["status"] == "completed"
    assert dumped["review_status"] == "approved"
    assert len(dumped["stages"]) == 1
    assert dumped["stages"][0]["file_changes"][0]["change_type"] == "created"


def test_health_and_version_responses():
    """Test HealthResponse and VersionResponse models."""
    health = HealthResponse(status="healthy", version="1.0.0")
    assert health.status == "healthy"
    assert health.version == "1.0.0"

    version = VersionResponse(name="SEO_AGENT", version="1.0.0")
    assert version.name == "SEO_AGENT"
    assert version.version == "1.0.0"
