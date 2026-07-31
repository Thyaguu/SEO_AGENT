"""Data models for the Execution Intelligence Report.

This module defines the structured data representations for all 14 sections
of the AI Execution Intelligence Report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ExecutiveSummaryData:
    workflow_id: str
    repository_path: str
    started_at: str
    finished_at: str
    duration_seconds: float
    status: str
    ai_model: str
    opencode_version: str
    framework: str
    pages_found: int
    files_scanned: int
    execution_time_seconds: float


@dataclass
class RepositoryAnalysisData:
    repository_path: str
    framework: str
    routing_type: str
    files_discovered: int
    pages_discovered: int
    has_sitemap: bool
    has_robots: bool
    health_score: int


@dataclass
class AIUnderstandingData:
    summary_narrative: str
    key_findings: list[str] = field(default_factory=list)


@dataclass
class PlanningDecisionData:
    task_id: str
    description: str
    problem_detected: str
    reason: str
    priority: str
    expected_impact: str
    confidence: float


@dataclass
class FileChangeData:
    file_name: str
    file_path: str
    reason_selected: str
    why_modified: str
    changes_applied: list[str] = field(default_factory=list)


@dataclass
class BeforeAfterItem:
    field_name: str
    before: str
    after: str


@dataclass
class PageComparisonData:
    file_name: str
    route: str
    comparisons: list[BeforeAfterItem] = field(default_factory=list)


@dataclass
class AIReasoningData:
    decision_title: str
    why_needed: str
    alternatives_considered: str
    chosen_approach_rationale: str
    expected_seo_benefit: str
    confidence_score: float


@dataclass
class ExecutionSummaryData:
    tasks_generated: int
    tasks_executed: int
    tasks_skipped: int
    duration_seconds: float
    opencode_requests: int
    opencode_responses: int
    files_modified: list[str] = field(default_factory=list)
    files_skipped: list[str] = field(default_factory=list)
    files_failed: list[str] = field(default_factory=list)


@dataclass
class ReviewSummaryData:
    validation_score: float
    validation_status: str
    checks_passed: int
    checks_failed: int
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class GeneratedAssetData:
    asset_name: str
    action: str
    file_path: str
    validation_status: str
    urls_included: list[str] = field(default_factory=list)


@dataclass
class GitSummaryData:
    branch: str
    commit_hash: str
    files_changed: int
    insertions: int
    deletions: int
    is_skipped: bool


@dataclass
class MetricsData:
    files_scanned: int
    pages_discovered: int
    files_modified: int
    tasks_executed: int
    execution_time_seconds: float
    warning_count: int
    error_count: int
    success_rate_pct: float


@dataclass
class TimelineItem:
    timestamp: str
    stage_name: str
    status: str
    duration_seconds: float


@dataclass
class SEOInputSummaryData:
    input_source: str  # "CSV", "JSON", "None"
    records_loaded: int = 0
    matched_pages: int = 0
    unmatched_records: int = 0
    skipped_records: int = 0


@dataclass
class PageKeywordAssignmentData:
    page_route: str
    primary_keyword: str
    secondary_keywords: list[str]
    confidence_score: float
    ai_reasoning: str


@dataclass
class UnassignedKeywordActionData:
    keyword: str
    action: str
    target_slug: str | None
    reasoning: str


@dataclass
class ExecutionIntelligenceReportModel:
    executive_summary: ExecutiveSummaryData
    repository_analysis: RepositoryAnalysisData
    ai_understanding: AIUnderstandingData
    seo_input_summary: SEOInputSummaryData | None = None
    page_keyword_assignments: list[PageKeywordAssignmentData] = field(default_factory=list)
    unassigned_keyword_actions: list[UnassignedKeywordActionData] = field(default_factory=list)
    planning_decisions: list[PlanningDecisionData] = field(default_factory=list)
    file_changes: list[FileChangeData] = field(default_factory=list)
    before_after_comparisons: list[PageComparisonData] = field(default_factory=list)
    ai_reasoning: list[AIReasoningData] = field(default_factory=list)
    execution_summary: ExecutionSummaryData = field(default_factory=lambda: ExecutionSummaryData(0, 0, 0, 0.0, 0, 0))
    review_summary: ReviewSummaryData = field(default_factory=lambda: ReviewSummaryData(100.0, "Approved", 0, 0))
    generated_assets: list[GeneratedAssetData] = field(default_factory=list)
    git_summary: GitSummaryData = field(default_factory=lambda: GitSummaryData("N/A", "N/A", 0, 0, 0, True))
    metrics: MetricsData = field(default_factory=lambda: MetricsData(0, 0, 0, 0, 0.0, 0, 0, 100.0))
    timeline: list[TimelineItem] = field(default_factory=list)
    final_summary: str = ""
