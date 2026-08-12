"""Report Manager for saving and indexing Execution Intelligence Reports.

Handles creation of repository_root/reports/ directory, saving .md, .html, .json
reports with timestamped filenames, and maintaining reports/index.json execution history.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from seo_agent.reporting.html_renderer import HTMLRenderer
from seo_agent.reporting.json_renderer import JSONRenderer
from seo_agent.reporting.markdown_renderer import MarkdownRenderer
from seo_agent.reporting.report_generator import ReportGenerator

if TYPE_CHECKING:
    from seo_agent.workflow.context import WorkflowContext

logger = logging.getLogger(__name__)


class ReportManager:
    """Orchestrates report generation, file output writing, and index.json maintenance."""

    def __init__(self) -> None:
        self.generator = ReportGenerator()
        self.md_renderer = MarkdownRenderer()
        self.html_renderer = HTMLRenderer()
        self.json_renderer = JSONRenderer()

    def generate_and_save(self, context: WorkflowContext) -> dict[str, str]:
        """Generate and save Markdown, HTML, and JSON execution reports into repository_root/reports/.

        Args:
            context: The workflow context after workflow completion.

        Returns:
            Dictionary containing absolute file paths of generated report artifacts.
        """
        repo_path = Path(context.repository_path)
        reports_dir = repo_path / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        timestamp_str = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
        prefix = f"{timestamp_str}_execution_report"

        md_path = reports_dir / f"{prefix}.md"
        json_path = reports_dir / f"{prefix}.json"
        index_path = reports_dir / "index.json"

        # Generate report model from context
        report_model = self.generator.generate(context)

        # Render formats
        md_content = self.md_renderer.render(report_model)
        json_content = self.json_renderer.render(report_model)

        # Write files
        md_path.write_text(md_content, encoding="utf-8")
        json_path.write_text(json_content, encoding="utf-8")

        logger.info(f"Execution Intelligence Reports saved to: {reports_dir}")

        # Update index.json
        self._update_index(
            index_path=index_path,
            execution_id=report_model.executive_summary.workflow_id,
            timestamp=report_model.executive_summary.finished_at,
            repo_path=str(repo_path),
            status=report_model.executive_summary.status,
            duration=report_model.executive_summary.duration_seconds,
            md_rel=md_path.name,
            json_rel=json_path.name,
        )

        return {
            "markdown": str(md_path),
            "json": str(json_path),
            "index": str(index_path),
        }

    def _update_index(
        self,
        index_path: Path,
        execution_id: str,
        timestamp: str,
        repo_path: str,
        status: str,
        duration: float,
        md_rel: str,
        json_rel: str,
        html_rel: str | None = None,
    ) -> None:
        """Maintain and update the reports/index.json history file."""
        entries: list[dict[str, Any]] = []
        if index_path.exists():
            try:
                raw = index_path.read_text(encoding="utf-8")
                data = json.loads(raw)
                if isinstance(data, list):
                    entries = data
                elif isinstance(data, dict) and "executions" in data:
                    entries = data["executions"]
            except Exception as e:
                logger.warning(f"Failed to parse existing reports/index.json: {e}")

        new_entry = {
            "execution_id": execution_id,
            "timestamp": timestamp,
            "repository_path": repo_path,
            "status": status,
            "duration_seconds": duration,
            "markdown_report": md_rel,
            "json_report": json_rel,
        }
        if html_rel:
            new_entry["html_report"] = html_rel

        entries.insert(0, new_entry)

        index_payload = {
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "total_executions": len(entries),
            "executions": entries,
        }

        index_path.write_text(json.dumps(index_payload, indent=2), encoding="utf-8")
        logger.info(f"Updated execution history index: {index_path}")
