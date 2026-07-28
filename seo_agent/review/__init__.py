"""Review engine package - validation only, no execution.

This package provides the review engine for validating execution results
and producing review decisions. It consists of three main components:

- validator: Validates execution output against project rules, SEO best practices,
             and safety constraints
- diff_analyzer: Compares original repository with ExecutionResult to produce
                  classified changes
- feedback: Aggregates validation and diff results into final review decisions

Usage:
    from seo_agent.review import ReviewEngine, ReviewResult, ReviewDecision

    engine = ReviewEngine()
    result = engine.review(validation_result, diff_analysis)
    if result.is_approved:
        print("Changes approved!")
"""

from seo_agent.review.validator import (
    ValidationSeverity,
    ValidationCategory,
    ValidationIssue,
    ValidationResult,
    ReviewValidator,
)

from seo_agent.review.diff_analyzer import (
    ChangeType,
    ChangeCategory,
    ChangeSeverity,
    FileChange,
    DiffAnalysis,
    DiffAnalyzer,
)

from seo_agent.review.feedback import (
    ReviewDecision,
    ReviewResult,
    FeedbackAggregator,
    ReviewEngine,
)

__all__ = [
    # Validator
    "ValidationSeverity",
    "ValidationCategory",
    "ValidationIssue",
    "ValidationResult",
    "ReviewValidator",
    # Diff Analyzer
    "ChangeType",
    "ChangeCategory",
    "ChangeSeverity",
    "FileChange",
    "DiffAnalysis",
    "DiffAnalyzer",
    # Feedback
    "ReviewDecision",
    "ReviewResult",
    "FeedbackAggregator",
    "ReviewEngine",
]