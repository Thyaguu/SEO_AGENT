"""Markdown Renderer for AI Execution Intelligence Report.

Renders all 14 report sections into clean, GitHub-flavored Markdown.
"""

from __future__ import annotations

from seo_agent.reporting.models import ExecutionIntelligenceReportModel


class MarkdownRenderer:
    """Renders ExecutionIntelligenceReportModel to GitHub-Flavored Markdown."""

    def render(self, report: ExecutionIntelligenceReportModel) -> str:
        lines: list[str] = []

        # Header
        lines.append("# AI Execution Intelligence Report")
        lines.append(f"**Workflow ID:** `{report.executive_summary.workflow_id}`  ")
        lines.append(f"**Generated:** {report.executive_summary.finished_at}  ")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Section 1: Executive Summary
        s1 = report.executive_summary
        lines.append("## 1. Executive Summary")
        lines.append("")
        lines.append(f"- **Workflow ID:** `{s1.workflow_id}`")
        lines.append(f"- **Repository Path:** `{s1.repository_path}`")
        lines.append(f"- **Started:** {s1.started_at}")
        lines.append(f"- **Finished:** {s1.finished_at}")
        lines.append(f"- **Duration:** {s1.duration_seconds}s")
        lines.append(f"- **Status:** `{s1.status}`")
        lines.append(f"- **AI Model:** {s1.ai_model}")
        lines.append(f"- **OpenCode Version:** {s1.opencode_version}")
        lines.append(f"- **Framework Detected:** {s1.framework}")
        lines.append(f"- **Pages Found:** {s1.pages_found}")
        lines.append(f"- **Files Scanned:** {s1.files_scanned}")
        lines.append(f"- **Execution Time:** {s1.execution_time_seconds}s")
        lines.append("")

        # Section 2: Repository Analysis
        s2 = report.repository_analysis
        lines.append("## 2. Repository Analysis")
        lines.append("")
        lines.append(f"- **Repository Path:** `{s2.repository_path}`")
        lines.append(f"- **Framework Detected:** {s2.framework}")
        lines.append(f"- **Routing Strategy:** {s2.routing_type}")
        lines.append(f"- **Files Discovered:** {s2.files_discovered}")
        lines.append(f"- **Pages Discovered:** {s2.pages_discovered}")
        lines.append(f"- **Existing Sitemap Present:** {'Yes' if s2.has_sitemap else 'No'}")
        lines.append(f"- **Existing Robots.txt Present:** {'Yes' if s2.has_robots else 'No'}")
        lines.append(f"- **Repository Health Score:** {s2.health_score}/100")
        if report.seo_input_summary:
            si = report.seo_input_summary
            lines.append("")
            lines.append("### External SEO Input Data")
            lines.append(f"- **Input Source:** `{si.input_source}`")
            lines.append(f"- **SEO Records Loaded:** {si.records_loaded}")
            lines.append(f"- **Matched Pages:** {si.matched_pages}")
            lines.append(f"- **Unmatched Records:** {si.unmatched_records}")
            lines.append(f"- **Skipped Records:** {si.skipped_records}")
        if report.page_keyword_assignments:
            lines.append("")
            lines.append("### AI Page-Keyword Semantic Assignments")
            lines.append("| Page Route | Primary Keyword | Secondary Keywords | Confidence | AI Reasoning |")
            lines.append("|---|---|---|---|---|")
            for ass in report.page_keyword_assignments:
                sec_str = ", ".join(ass.secondary_keywords)
                lines.append(f"| `{ass.page_route}` | **{ass.primary_keyword}** | {sec_str} | {int(ass.confidence_score * 100)}% | {ass.ai_reasoning} |")
        if report.unassigned_keyword_actions:
            lines.append("")
            lines.append("### Unassigned Keyword Strategy")
            lines.append("| Keyword | Action | Target Slug | Reasoning |")
            lines.append("|---|---|---|---|")
            for unass in report.unassigned_keyword_actions:
                lines.append(f"| **{unass.keyword}** | `{unass.action.upper()}` | `{unass.target_slug or 'N/A'}` | {unass.reasoning} |")
        lines.append("")

        # Section 3: AI Understanding
        s3 = report.ai_understanding
        lines.append("## 3. AI Understanding")
        lines.append("")
        lines.append(s3.summary_narrative)
        lines.append("")
        lines.append("### Key Analysis Findings")
        for finding in s3.key_findings:
            lines.append(f"- {finding}")
        lines.append("")

        # Section 4: Planning Decisions
        lines.append("## 4. Planning Decisions")
        lines.append("")
        if report.planning_decisions:
            lines.append("| Task ID | Priority | Description | Problem Detected | Expected Impact | Confidence |")
            lines.append("|---|---|---|---|---|---|")
            for pd in report.planning_decisions:
                lines.append(f"| `{pd.task_id}` | `{pd.priority}` | {pd.description} | {pd.problem_detected} | {pd.expected_impact} | {int(pd.confidence * 100)}% |")
        else:
            lines.append("_No planning tasks recorded._")
        lines.append("")

        # Section 5: File-by-File Changes
        lines.append("## 5. File-by-File Changes")
        lines.append("")
        for fc in report.file_changes:
            lines.append(f"### `{fc.file_name}`")
            lines.append(f"- **Path:** `{fc.file_path}`")
            lines.append(f"- **Reason Selected:** {fc.reason_selected}")
            lines.append(f"- **Why Modified:** {fc.why_modified}")
            lines.append("- **Applied Changes:**")
            for change in fc.changes_applied:
                lines.append(f"  - ✓ {change}")
            lines.append("")

        # Section 6: Before vs After
        lines.append("## 6. Before vs After Comparisons")
        lines.append("")
        for page_comp in report.before_after_comparisons:
            lines.append(f"### `{page_comp.file_name}` (`{page_comp.route}`)")
            lines.append("")
            for item in page_comp.comparisons:
                lines.append(f"#### {item.field_name}")
                lines.append("")
                lines.append("**Before**")
                lines.append("")
                lines.append(item.before)
                lines.append("")
                lines.append("↓")
                lines.append("")
                lines.append("**After**")
                lines.append("")
                lines.append(item.after)
                lines.append("")
                lines.append("---")
                lines.append("")

        # Section 7: AI Reasoning
        lines.append("## 7. AI Reasoning & Decisions")
        lines.append("")
        for r in report.ai_reasoning:
            lines.append(f"### Decision: {r.decision_title}")
            lines.append(f"- **Why Needed:** {r.why_needed}")
            lines.append(f"- **Alternatives Considered:** {r.alternatives_considered}")
            lines.append(f"- **Chosen Approach Rationale:** {r.chosen_approach_rationale}")
            lines.append(f"- **Expected SEO Benefit:** {r.expected_seo_benefit}")
            lines.append(f"- **Confidence Score:** {int(r.confidence_score * 100)}%")
            lines.append("")

        # Section 8: Execution Summary
        s8 = report.execution_summary
        lines.append("## 8. Execution Summary")
        lines.append("")
        lines.append(f"- **Tasks Generated:** {s8.tasks_generated}")
        lines.append(f"- **Tasks Executed:** {s8.tasks_executed}")
        lines.append(f"- **Tasks Failed:** {s8.tasks_failed}")
        lines.append(f"- **Tasks Skipped:** {s8.tasks_skipped}")
        lines.append(f"- **Execution Duration:** {s8.duration_seconds}s")
        lines.append(f"- **OpenCode API Requests:** {s8.opencode_requests}")
        lines.append(f"- **OpenCode API Responses:** {s8.opencode_responses}")
        lines.append(f"- **Files Modified:** {', '.join(s8.files_modified) if s8.files_modified else 'None'}")
        lines.append(f"- **Files Skipped:** {', '.join(s8.files_skipped) if s8.files_skipped else 'None'}")
        lines.append(f"- **Files Failed:** {', '.join(s8.files_failed) if s8.files_failed else 'None'}")
        if s8.failure_reasons:
            lines.append("")
            lines.append("### Failure Diagnostics & Classification")
            lines.append(f"- **Classification:** `{s8.failure_classification}`")
            lines.append(f"- **Exception Type:** `{s8.exception_type}`")
            lines.append(f"- **Failed Stage:** `{s8.failed_stage}`")
            lines.append(f"- **Failed Task ID:** `{s8.failed_task_id}`")
            lines.append(f"- **Retry Count:** {s8.retry_count}")
            lines.append(f"- **Root Cause:** {s8.root_cause}")
            lines.append(f"- **Recommended Fix:** {s8.recommended_fix}")
            lines.append("")
            lines.append("#### Failure Reasons")
            for err in s8.failure_reasons:
                lines.append(f"- {err}")
        lines.append("")

        # Section 9: Review Summary
        s9 = report.review_summary
        lines.append("## 9. Review & Validation Summary")
        lines.append("")
        lines.append(f"- **Validation Status:** `{s9.validation_status}`")
        lines.append(f"- **Validation Score:** {s9.validation_score}/100")
        lines.append(f"- **Checks Passed:** {s9.checks_passed}")
        lines.append(f"- **Checks Failed:** {s9.checks_failed}")
        if s9.warnings:
            lines.append("- **Warnings:**")
            for w in s9.warnings:
                lines.append(f"  - ⚠️ {w}")
        lines.append("- **Recommendations:**")
        for rec in s9.recommendations:
            lines.append(f"  - 💡 {rec}")
        lines.append("")

        # Section 10: Generated Assets
        lines.append("## 10. Generated Technical Assets")
        lines.append("")
        for asset in report.generated_assets:
            lines.append(f"### Asset: `{asset.asset_name}`")
            lines.append(f"- **Action:** {asset.action}")
            lines.append(f"- **File Path:** `{asset.file_path}`")
            lines.append(f"- **Validation Status:** `{asset.validation_status}`")
            if asset.urls_included:
                lines.append(f"- **URLs Included:** {', '.join(asset.urls_included[:5])}")
            lines.append("")

        # Section 11: Git Summary
        s11 = report.git_summary
        lines.append("## 11. Git Summary")
        lines.append("")
        if s11.is_skipped:
            lines.append("_Git operations skipped per workflow context configuration._")
        else:
            lines.append(f"- **Branch:** `{s11.branch}`")
            lines.append(f"- **Commit Hash:** `{s11.commit_hash}`")
            lines.append(f"- **Files Changed:** {s11.files_changed}")
            lines.append(f"- **Insertions:** +{s11.insertions}")
            lines.append(f"- **Deletions:** -{s11.deletions}")
        lines.append("")

        # Section 12: Metrics
        s12 = report.metrics
        lines.append("## 12. Workflow Performance Metrics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|---|---|")
        lines.append(f"| **Files Scanned** | {s12.files_scanned} |")
        lines.append(f"| **Pages Discovered** | {s12.pages_discovered} |")
        lines.append(f"| **Files Modified** | {s12.files_modified} |")
        lines.append(f"| **Tasks Executed** | {s12.tasks_executed} |")
        lines.append(f"| **Execution Time** | {s12.execution_time_seconds}s |")
        lines.append(f"| **Warnings** | {s12.warning_count} |")
        lines.append(f"| **Errors** | {s12.error_count} |")
        lines.append(f"| **Success Rate** | {s12.success_rate_pct}% |")
        lines.append("")

        # Section 13: Timeline
        lines.append("## 13. Execution Timeline")
        lines.append("")
        lines.append("| Time | Stage | Status | Duration |")
        lines.append("|---|---|---|---|")
        for item in report.timeline:
            lines.append(f"| `{item.timestamp}` | **{item.stage_name}** | `{item.status}` | {item.duration_seconds}s |")
        lines.append("")

        # Section 14: Final AI Summary
        lines.append("## 14. Final AI Executive Conclusion")
        lines.append("")
        lines.append(f"> {report.final_summary}")
        lines.append("")

        return "\n".join(lines)
