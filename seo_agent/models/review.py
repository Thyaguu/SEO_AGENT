"""Review result models.

This module contains domain models for the review phase including
validation results, review decisions, and feedback.

All models follow SOLID principles with single responsibility.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from pydantic import ConfigDict, Field

from seo_agent.models.base import BasePydanticModel

if TYPE_CHECKING:
    from seo_agent.models.seo import SEOPage, Metadata
    from seo_agent.models.repository import PageInfo


class ReviewDecision(Enum):
    """Outcome of a review phase."""

    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"


class ValidationSeverity(Enum):
    """Severity level for validation issues."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationCategory(Enum):
    """Category of validation being performed."""

    SEO_QUALITY = "seo_quality"
    CONTENT_QUALITY = "content_quality"
    TECHNICAL_SEO = "technical_seo"
    ACCESSIBILITY = "accessibility"
    CODE_QUALITY = "code_quality"
    STRUCTURE = "structure"


class ValidationIssue(BasePydanticModel):
    """A single validation issue found during review.

    Attributes:
        category: Category of the validation issue.
        severity: How severe this issue is.
        message: Human-readable issue description.
        location: Where the issue was found (file path, line number, etc.).
        suggestion: How to fix the issue.
        rule_id: Identifier of the rule that was violated.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    category: ValidationCategory
    severity: ValidationSeverity
    message: str
    location: str | None = None
    suggestion: str | None = None
    rule_id: str | None = None


class ValidationResult(BasePydanticModel):
    """Result of validating a single item.

    Attributes:
        item_id: Identifier of the item being validated.
        item_type: Type of item (page, file, etc.).
        passed: Whether validation passed.
        issues: List of validation issues found.
        validated_at: When validation was performed.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    item_id: str
    item_type: str
    passed: bool = True
    issues: tuple[ValidationIssue, ...] = ()
    validated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def critical_issues(self) -> tuple[ValidationIssue, ...]:
        """Get only critical severity issues."""
        return tuple(i for i in self.issues if i.severity == ValidationSeverity.CRITICAL)

    @property
    def error_count(self) -> int:
        """Count of error and critical issues."""
        return sum(
            1 for i in self.issues
            if i.severity in (ValidationSeverity.CRITICAL, ValidationSeverity.ERROR)
        )

    @property
    def warning_count(self) -> int:
        """Count of warning issues."""
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)


class SEOQualityCheck(BasePydanticModel):
    """SEO quality check result.

    Attributes:
        check_name: Name of the quality check.
        passed: Whether the check passed.
        score: Quality score (0-100).
        details: Additional details about the check.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    check_name: str
    passed: bool
    score: int = 100
    details: str | None = None


class ContentQualityCheck(BasePydanticModel):
    """Content quality check result.

    Attributes:
        check_name: Name of the quality check.
        passed: Whether the check passed.
        score: Quality score (0-100).
        word_count: Total word count.
        reading_time_minutes: Estimated reading time.
        details: Additional details about the check.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    check_name: str
    passed: bool
    score: int = 100
    word_count: int = 0
    reading_time_minutes: float = 0.0
    details: str | None = None


class ReviewFeedback(BasePydanticModel):
    """Feedback for a rejected review.

    Attributes:
        decision: The review decision.
        summary: Summary of the review.
        issues: List of issues found.
        seo_checks: SEO quality check results.
        content_checks: Content quality check results.
        recommendations: Suggested improvements.
        reviewer_notes: Additional notes from reviewer.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    decision: ReviewDecision
    summary: str
    issues: tuple[ValidationIssue, ...] = ()
    seo_checks: tuple[SEOQualityCheck, ...] = ()
    content_checks: tuple[ContentQualityCheck, ...] = ()
    recommendations: tuple[str, ...] = ()
    reviewer_notes: str | None = None


class ReviewResult(BasePydanticModel):
    """Complete result of a review phase.

    Attributes:
        request_id: Associated request ID.
        attempt_number: Which review attempt this is.
        decision: Final decision.
        feedback: Detailed feedback if rejected.
        validation_results: Results of all validations.
        overall_score: Overall quality score (0-100).
        seo_score: SEO-specific score.
        content_score: Content-specific score.
        reviewed_at: When review was performed.
        reviewed_by: Who/what performed the review.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    request_id: str
    attempt_number: int
    decision: ReviewDecision
    feedback: ReviewFeedback | None = None
    validation_results: tuple[ValidationResult, ...] = ()
    overall_score: int = 100
    seo_score: int = 100
    content_score: int = 100
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_by: str = "automated"

    @property
    def is_approved(self) -> bool:
        """Check if review was approved."""
        return self.decision == ReviewDecision.APPROVED

    @property
    def is_valid(self) -> bool:
        """Check if review was valid/approved."""
        return self.is_approved

    @property
    def total_issues(self) -> int:
        """Count total validation issues."""
        return sum(len(v.issues) for v in self.validation_results)

    @property
    def critical_issues_count(self) -> int:
        """Count critical issues across all validations."""
        return sum(len(v.critical_issues) for v in self.validation_results)


class ReviewSummary(BasePydanticModel):
    """Summary of all review attempts.

    Attributes:
        total_attempts: Total number of review attempts.
        approved_attempts: Number of approved attempts.
        rejected_attempts: Number of rejected attempts.
        final_decision: Final decision after all attempts.
        average_score: Average overall score.
        improvement_trend: Whether scores improved over attempts.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    total_attempts: int
    approved_attempts: int
    rejected_attempts: int
    final_decision: ReviewDecision
    average_score: float = 100.0
    improvement_trend: bool = True


class ReviewCriteria(BasePydanticModel):
    """Criteria for automated review.

    Attributes:
        min_seo_score: Minimum required SEO score (0-100).
        min_content_score: Minimum required content score (0-100).
        max_critical_issues: Maximum allowed critical issues.
        max_total_issues: Maximum allowed total issues.
        require_keyword_usage: Whether keywords must be used.
        require_structured_data: Whether structured data is required.
        require_og_tags: Whether Open Graph tags are required.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    min_seo_score: int = 70
    min_content_score: int = 70
    max_critical_issues: int = 0
    max_total_issues: int = 10
    require_keyword_usage: bool = True
    require_structured_data: bool = True
    require_og_tags: bool = True


class PageReviewContext(BasePydanticModel):
    """Context for reviewing a specific page.

    Attributes:
        page: The page being reviewed.
        seo_page: Associated SEO page if applicable.
        metadata: Current metadata on the page.
        keywords: Keywords that should be used.
        competitors: Competitor information for comparison.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    page: PageInfo | None = None
    seo_page: SEOPage | None = None
    metadata: Metadata | None = None
    keywords: tuple[str, ...] = ()
    competitors: tuple[str, ...] = ()