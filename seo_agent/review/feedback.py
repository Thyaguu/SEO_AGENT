"""Review feedback aggregation.

This module provides functionality for aggregating validation results
and diff analysis into a final review decision.

The feedback aggregator is completely read-only and never modifies repository files.

Usage:
    aggregator = FeedbackAggregator()
    result = aggregator.aggregate(validation_result, diff_analysis)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from seo_agent.review.diff_analyzer import DiffAnalysis
    from seo_agent.review.validator import ValidationResult

logger = logging.getLogger(__name__)


class ReviewDecision(Enum):
    """Final decision for a review.

    APPROVED: Changes are approved as-is.
    APPROVED_WITH_WARNINGS: Changes are approved but with warnings to address.
    REJECTED: Changes are rejected and must be revised.
    """

    APPROVED = "approved"
    APPROVED_WITH_WARNINGS = "approved_with_warnings"
    REJECTED = "rejected"


@dataclass
class ReviewResult:
    """Final result of the review process.

    This aggregates validation results and diff analysis to produce
    a final decision with detailed feedback.

    Attributes:
        decision: The final review decision.
        validation_result: The validation result.
        diff_analysis: The diff analysis result.
        total_issues: Total number of issues found.
        blocking_issues: Number of blocking issues.
        warning_issues: Number of warning issues.
        approved_files: List of approved file changes.
        rejected_files: List of rejected file changes.
        feedback_messages: List of feedback messages for the user.
        review_duration_seconds: Time taken for the review.
        is_approved: Whether the changes are approved.
    """

    decision: ReviewDecision
    validation_result: ValidationResult | None = None
    diff_analysis: DiffAnalysis | None = None
    total_issues: int = 0
    blocking_issues: int = 0
    warning_issues: int = 0
    approved_files: list[str] = field(default_factory=list)
    rejected_files: list[str] = field(default_factory=list)
    feedback_messages: list[str] = field(default_factory=list)
    review_duration_seconds: float = 0.0

    @property
    def is_approved(self) -> bool:
        """Check if the changes are approved."""
        return self.decision in (ReviewDecision.APPROVED, ReviewDecision.APPROVED_WITH_WARNINGS)

    @property
    def is_rejected(self) -> bool:
        """Check if the changes are rejected."""
        return self.decision == ReviewDecision.REJECTED

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return self.decision == ReviewDecision.APPROVED_WITH_WARNINGS

    @property
    def summary(self) -> str:
        """Get a human-readable summary of the review."""
        if self.decision == ReviewDecision.APPROVED:
            return "All changes approved. No issues found."
        elif self.decision == ReviewDecision.APPROVED_WITH_WARNINGS:
            return f"Approved with {self.warning_issues} warning(s). Please address when convenient."
        else:
            return f"Changes rejected. {self.blocking_issues} blocking issue(s) must be resolved."

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "decision": self.decision.value,
            "is_approved": self.is_approved,
            "is_rejected": self.is_rejected,
            "has_warnings": self.has_warnings,
            "total_issues": self.total_issues,
            "blocking_issues": self.blocking_issues,
            "warning_issues": self.warning_issues,
            "approved_files": self.approved_files,
            "rejected_files": self.rejected_files,
            "feedback_messages": self.feedback_messages,
            "review_duration_seconds": self.review_duration_seconds,
            "summary": self.summary,
            "validation_result": self.validation_result.to_dict() if self.validation_result else None,
            "diff_analysis": self.diff_analysis.to_dict() if self.diff_analysis else None,
        }


class FeedbackAggregator:
    """Aggregates validation results and diff analysis into review decisions.

    This class combines the results from the validator and diff analyzer
    to produce a final ReviewResult with a clear decision and feedback.
    """

    def __init__(self) -> None:
        """Initialize the feedback aggregator."""
        self._feedback_messages: list[str] = []

    def aggregate(
        self,
        validation_result: ValidationResult | None = None,
        diff_analysis: DiffAnalysis | None = None,
    ) -> ReviewResult:
        """Aggregate validation and diff results into a final review result.

        Args:
            validation_result: Result from the validator.
            diff_analysis: Result from the diff analyzer.

        Returns:
            ReviewResult with the final decision and feedback.
        """
        import time

        start_time = time.time()
        self._feedback_messages = []

        # Count issues from validation
        blocking_issues = 0
        warning_issues = 0
        total_issues = 0

        if validation_result:
            blocking_issues += len(validation_result.critical_issues)
            blocking_issues += len(validation_result.error_issues)
            warning_issues += len(validation_result.warning_issues)
            total_issues += len(validation_result.issues)

        # Count issues from diff analysis
        if diff_analysis:
            blocking_issues += len(diff_analysis.blocking_changes)
            warning_issues += len(diff_analysis.warning_changes)
            total_issues += diff_analysis.total_files_changed

        # Determine the decision
        decision = self._determine_decision(
            blocking_issues=blocking_issues,
            warning_issues=warning_issues,
            validation_result=validation_result,
            diff_analysis=diff_analysis,
        )

        # Collect approved and rejected files
        approved_files, rejected_files = self._collect_files(
            validation_result=validation_result,
            diff_analysis=diff_analysis,
        )

        # Generate feedback messages
        self._generate_feedback(
            decision=decision,
            blocking_issues=blocking_issues,
            warning_issues=warning_issues,
            validation_result=validation_result,
            diff_analysis=diff_analysis,
        )

        review_duration = time.time() - start_time

        return ReviewResult(
            decision=decision,
            validation_result=validation_result,
            diff_analysis=diff_analysis,
            total_issues=total_issues,
            blocking_issues=blocking_issues,
            warning_issues=warning_issues,
            approved_files=approved_files,
            rejected_files=rejected_files,
            feedback_messages=self._feedback_messages.copy(),
            review_duration_seconds=review_duration,
        )

    def _determine_decision(
        self,
        blocking_issues: int,
        warning_issues: int,
        validation_result: ValidationResult | None,
        diff_analysis: DiffAnalysis | None,
    ) -> ReviewDecision:
        """Determine the review decision based on issues found.

        Args:
            blocking_issues: Number of blocking issues.
            warning_issues: Number of warning issues.
            validation_result: The validation result.
            diff_analysis: The diff analysis result.

        Returns:
            The appropriate ReviewDecision.
        """
        # Reject if there are blocking issues
        if blocking_issues > 0:
            return ReviewDecision.REJECTED

        # Check for safety bounds violations
        if diff_analysis and not diff_analysis.is_within_safety_bounds:
            return ReviewDecision.REJECTED

        # Check for validation failures
        if validation_result and not validation_result.is_valid:
            return ReviewDecision.REJECTED

        # Approve with warnings if there are warnings
        if warning_issues > 0:
            return ReviewDecision.APPROVED_WITH_WARNINGS

        # Otherwise, approve
        return ReviewDecision.APPROVED

    def _collect_files(
        self,
        validation_result: ValidationResult | None,
        diff_analysis: DiffAnalysis | None,
    ) -> tuple[list[str], list[str]]:
        """Collect approved and rejected files from results.

        Args:
            validation_result: The validation result.
            diff_analysis: The diff analysis result.

        Returns:
            Tuple of (approved_files, rejected_files).
        """
        approved_files: list[str] = []
        rejected_files: list[str] = []

        # Collect from diff analysis
        if diff_analysis:
            for change in diff_analysis.all_changes:
                file_path = change.file_path
                if change.severity.value in ("safe", "acceptable"):
                    if file_path not in approved_files:
                        approved_files.append(file_path)
                elif change.severity.value in ("warning", "blocking"):
                    if file_path not in rejected_files:
                        rejected_files.append(file_path)

        # Collect from validation (files with issues)
        if validation_result:
            for issue in validation_result.issues:
                if issue.file_path:
                    if issue.severity.value in ("critical", "error"):
                        if issue.file_path not in rejected_files:
                            rejected_files.append(issue.file_path)
                    elif issue.severity.value == "warning":
                        if issue.file_path not in approved_files:
                            approved_files.append(issue.file_path)

        return approved_files, rejected_files

    def _generate_feedback(
        self,
        decision: ReviewDecision,
        blocking_issues: int,
        warning_issues: int,
        validation_result: ValidationResult | None,
        diff_analysis: DiffAnalysis | None,
    ) -> None:
        """Generate feedback messages based on the review results.

        Args:
            decision: The final decision.
            blocking_issues: Number of blocking issues.
            warning_issues: Number of warning issues.
            validation_result: The validation result.
            diff_analysis: The diff analysis result.
        """
        # Add decision message
        if decision == ReviewDecision.APPROVED:
            self._feedback_messages.append(
                "All changes approved. The changes are ready for deployment."
            )
        elif decision == ReviewDecision.APPROVED_WITH_WARNINGS:
            self._feedback_messages.append(
                f"Changes approved with {warning_issues} warning(s). "
                "Please review and address when convenient."
            )
        else:
            self._feedback_messages.append(
                f"Changes rejected. {blocking_issues} blocking issue(s) must be resolved."
            )

        # Add validation feedback
        if validation_result:
            self._add_validation_feedback(validation_result)

        # Add diff analysis feedback
        if diff_analysis:
            self._add_diff_feedback(diff_analysis)

    def _add_validation_feedback(self, validation_result: ValidationResult) -> None:
        """Add feedback messages from validation results.

        Args:
            validation_result: The validation result.
        """
        # Critical issues
        if validation_result.critical_issues:
            self._feedback_messages.append(
                f"Critical issues ({len(validation_result.critical_issues)}):"
            )
            for issue in validation_result.critical_issues[:5]:  # Limit to first 5
                self._feedback_messages.append(f"  - {issue.message}")
            if len(validation_result.critical_issues) > 5:
                self._feedback_messages.append(
                    f"  ... and {len(validation_result.critical_issues) - 5} more"
                )

        # Error issues
        if validation_result.error_issues:
            self._feedback_messages.append(
                f"Error issues ({len(validation_result.error_issues)}):"
            )
            for issue in validation_result.error_issues[:5]:  # Limit to first 5
                self._feedback_messages.append(f"  - {issue.message}")
            if len(validation_result.error_issues) > 5:
                self._feedback_messages.append(
                    f"  ... and {len(validation_result.error_issues) - 5} more"
                )

        # Warning issues
        if validation_result.warning_issues:
            self._feedback_messages.append(
                f"Warning issues ({len(validation_result.warning_issues)}):"
            )
            for issue in validation_result.warning_issues[:5]:  # Limit to first 5
                self._feedback_messages.append(f"  - {issue.message}")
            if len(validation_result.warning_issues) > 5:
                self._feedback_messages.append(
                    f"  ... and {len(validation_result.warning_issues) - 5} more"
                )

    def _add_diff_feedback(self, diff_analysis: DiffAnalysis) -> None:
        """Add feedback messages from diff analysis.

        Args:
            diff_analysis: The diff analysis result.
        """
        # Summary
        self._feedback_messages.append(
            f"Files changed: {diff_analysis.total_files_changed} "
            f"(created: {len(diff_analysis.created_files)}, "
            f"modified: {len(diff_analysis.modified_files)}, "
            f"deleted: {len(diff_analysis.deleted_files)})"
        )

        # SEO pages
        if diff_analysis.seo_page_changes:
            self._feedback_messages.append(
                f"SEO pages modified: {len(diff_analysis.seo_page_changes)}"
            )

        # Blocking changes
        if diff_analysis.blocking_changes:
            self._feedback_messages.append(
                f"Blocking changes ({len(diff_analysis.blocking_changes)}):"
            )
            for change in diff_analysis.blocking_changes[:5]:  # Limit to first 5
                self._feedback_messages.append(f"  - {change.description}")
            if len(diff_analysis.blocking_changes) > 5:
                self._feedback_messages.append(
                    f"  ... and {len(diff_analysis.blocking_changes) - 5} more"
                )

        # Warning changes
        if diff_analysis.warning_changes:
            self._feedback_messages.append(
                f"Warning changes ({len(diff_analysis.warning_changes)}):"
            )
            for change in diff_analysis.warning_changes[:5]:  # Limit to first 5
                self._feedback_messages.append(f"  - {change.description}")
            if len(diff_analysis.warning_changes) > 5:
                self._feedback_messages.append(
                    f"  ... and {len(diff_analysis.warning_changes) - 5} more"
                )

        # Safety bounds
        if not diff_analysis.is_within_safety_bounds:
            self._feedback_messages.append(
                "Warning: Changes exceed safety bounds. Manual review recommended."
            )


class ReviewEngine:
    """Main review engine that orchestrates the review process.

    This class provides a unified interface for reviewing execution results,
    combining validation and diff analysis into a single review result.
    """

    def __init__(self) -> None:
        """Initialize the review engine."""
        self._feedback_aggregator = FeedbackAggregator()

    def review(
        self,
        validation_result: ValidationResult | None = None,
        diff_analysis: DiffAnalysis | None = None,
    ) -> ReviewResult:
        """Perform a complete review of the execution results.

        Args:
            validation_result: Result from the validator.
            diff_analysis: Result from the diff analyzer.

        Returns:
            ReviewResult with the final decision and feedback.
        """
        return self._feedback_aggregator.aggregate(
            validation_result=validation_result,
            diff_analysis=diff_analysis,
        )

    def is_approved(
        self,
        validation_result: ValidationResult | None = None,
        diff_analysis: DiffAnalysis | None = None,
    ) -> bool:
        """Check if the review is approved.

        Args:
            validation_result: Result from the validator.
            diff_analysis: Result from the diff analyzer.

        Returns:
            True if approved, False otherwise.
        """
        result = self.review(
            validation_result=validation_result,
            diff_analysis=diff_analysis,
        )
        return result.is_approved

    def get_decision(
        self,
        validation_result: ValidationResult | None = None,
        diff_analysis: DiffAnalysis | None = None,
    ) -> ReviewDecision:
        """Get the review decision.

        Args:
            validation_result: Result from the validator.
            diff_analysis: Result from the diff analyzer.

        Returns:
            The ReviewDecision.
        """
        result = self.review(
            validation_result=validation_result,
            diff_analysis=diff_analysis,
        )
        return result.decision