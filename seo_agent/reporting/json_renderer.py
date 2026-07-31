"""JSON Renderer for AI Execution Intelligence Report.

Serializes ExecutionIntelligenceReportModel to machine-readable JSON format.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from seo_agent.reporting.models import ExecutionIntelligenceReportModel


class JSONRenderer:
    """Renders ExecutionIntelligenceReportModel to machine-readable JSON."""

    def render(self, report: ExecutionIntelligenceReportModel) -> str:
        data_dict = asdict(report)
        return json.dumps(data_dict, indent=2, default=str)
