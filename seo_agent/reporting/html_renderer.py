"""HTML Renderer for AI Execution Intelligence Report.

Renders a standalone, responsive HTML dashboard with dark mode support,
collapsible cards, KPI metrics grid, timeline visualization, and comparison tables.
"""

from __future__ import annotations

import json
from seo_agent.reporting.models import ExecutionIntelligenceReportModel


class HTMLRenderer:
    """Renders ExecutionIntelligenceReportModel to a standalone HTML Dashboard."""

    def render(self, report: ExecutionIntelligenceReportModel) -> str:
        s1 = report.executive_summary
        s2 = report.repository_analysis
        s3 = report.ai_understanding
        s8 = report.execution_summary
        s9 = report.review_summary
        s12 = report.metrics

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Execution Intelligence Report - {s1.workflow_id}</title>
  <style>
    :root {{
      --bg-primary: #0f172a;
      --bg-card: #1e293b;
      --bg-header: #334155;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --accent-blue: #38bdf8;
      --accent-green: #4ade80;
      --accent-yellow: #facc15;
      --accent-red: #f87171;
      --border-color: #334155;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg-primary);
      color: var(--text-main);
      margin: 0;
      padding: 0;
      line-height: 1.5;
    }}
    .header {{
      background-color: var(--bg-card);
      border-bottom: 1px solid var(--border-color);
      padding: 24px 40px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .header h1 {{
      margin: 0;
      font-size: 24px;
      color: var(--accent-blue);
    }}
    .container {{
      max-width: 1200px;
      margin: 30px auto;
      padding: 0 20px;
    }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 20px;
      margin-bottom: 30px;
    }}
    .kpi-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 20px;
      text-align: center;
    }}
    .kpi-card .val {{
      font-size: 28px;
      font-weight: bold;
      color: var(--accent-green);
      margin-top: 5px;
    }}
    .kpi-card .lbl {{
      font-size: 13px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .section-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
    }}
    .section-title {{
      font-size: 18px;
      font-weight: 600;
      color: var(--accent-blue);
      margin-top: 0;
      margin-bottom: 16px;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 8px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
    }}
    th, td {{
      padding: 10px 14px;
      text-align: left;
      border-bottom: 1px solid var(--border-color);
      font-size: 14px;
    }}
    th {{
      background: var(--bg-header);
      color: var(--text-main);
    }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
    }}
    .badge-success {{ background: rgba(74, 222, 128, 0.2); color: var(--accent-green); border: 1px solid var(--accent-green); }}
    .badge-warning {{ background: rgba(250, 204, 21, 0.2); color: var(--accent-yellow); border: 1px solid var(--accent-yellow); }}
    .badge-info {{ background: rgba(56, 189, 248, 0.2); color: var(--accent-blue); border: 1px solid var(--accent-blue); }}
    .timeline-list {{
      list-style: none;
      padding: 0;
      position: relative;
    }}
    .timeline-item {{
      padding-left: 24px;
      margin-bottom: 16px;
      position: relative;
    }}
    .timeline-item::before {{
      content: "";
      position: absolute;
      left: 0;
      top: 6px;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--accent-green);
    }}
    .narrative-box {{
      background: rgba(56, 189, 248, 0.1);
      border-left: 4px solid var(--accent-blue);
      padding: 16px;
      border-radius: 4px;
      font-size: 15px;
    }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>AI Execution Intelligence Report</h1>
      <div style="font-size:13px; color:var(--text-muted); margin-top:4px;">Workflow ID: {s1.workflow_id} | Generated: {s1.finished_at}</div>
    </div>
    <div>
      <span class="badge badge-success">{s1.status}</span>
    </div>
  </div>

  <div class="container">
    <!-- KPI Summary Grid -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="lbl">Files Scanned</div>
        <div class="val">{s12.files_scanned}</div>
      </div>
      <div class="kpi-card">
        <div class="lbl">Pages Discovered</div>
        <div class="val">{s12.pages_discovered}</div>
      </div>
      <div class="kpi-card">
        <div class="lbl">Files Modified</div>
        <div class="val">{s12.files_modified}</div>
      </div>
      <div class="kpi-card">
        <div class="lbl">Tasks Executed</div>
        <div class="val">{s12.tasks_executed}</div>
      </div>
      <div class="kpi-card">
        <div class="lbl">Review Score</div>
        <div class="val">{s9.validation_score:.0f}/100</div>
      </div>
    </div>

    <!-- Section 1 & 2: Executive & Repository Analysis -->
    <div class="section-card">
      <div class="section-title">1. Executive Summary & Repository Analysis</div>
      <table>
        <tr><th>Repository Path</th><td><code>{s1.repository_path}</code></td><th>Framework</th><td>{s1.framework}</td></tr>
        <tr><th>Duration</th><td>{s1.duration_seconds}s</td><th>Routing Strategy</th><td>{s2.routing_type}</td></tr>
        <tr><th>AI Model</th><td>{s1.ai_model}</td><th>OpenCode Adapter</th><td>{s1.opencode_version}</td></tr>
        <tr><th>Sitemap Present</th><td>{ 'Yes' if s2.has_sitemap else 'No' }</td><th>Robots.txt Present</th><td>{ 'Yes' if s2.has_robots else 'No' }</td></tr>
      </table>
    </div>

    <!-- Section 3: AI Understanding Narrative -->
    <div class="section-card">
      <div class="section-title">3. AI Understanding & Insights</div>
      <div class="narrative-box">
        {s3.summary_narrative}
      </div>
      <ul style="margin-top:16px; color:var(--text-muted);">
        {"".join(f"<li>{item}</li>" for item in s3.key_findings)}
      </ul>
    </div>

    <!-- Section 4: Planning Decisions -->
    <div class="section-card">
      <div class="section-title">4. AI Planning Decisions</div>
      <table>
        <thead>
          <tr><th>Task ID</th><th>Priority</th><th>Description</th><th>Problem Identified</th><th>Expected SEO Impact</th></tr>
        </thead>
        <tbody>
          {"".join(f"<tr><td><code>{t.task_id}</code></td><td><span class='badge badge-info'>{t.priority}</span></td><td>{t.description}</td><td>{t.problem_detected}</td><td>{t.expected_impact}</td></tr>" for t in report.planning_decisions)}
        </tbody>
      </table>
    </div>

    <!-- Section 5 & 6: File Changes & Comparisons -->
    <div class="section-card">
      <div class="section-title">5. File Modifications & Before/After Comparisons</div>
      {"".join(f'''
      <div style="margin-bottom:20px;">
        <h4 style="color:var(--accent-blue); margin-bottom:8px;">Page: <code>{comp.file_name}</code> ({comp.route})</h4>
        <table>
          <thead><tr><th style="width:20%;">Attribute</th><th style="width:40%;">Before</th><th style="width:40%;">After (Optimized)</th></tr></thead>
          <tbody>
            {"".join(f"<tr><td><strong>{item.field_name}</strong></td><td style='color:var(--text-muted);'>{item.before}</td><td style='color:var(--accent-green);'>{item.after}</td></tr>" for item in comp.comparisons)}
          </tbody>
        </table>
      </div>
      ''' for comp in report.before_after_comparisons)}
    </div>

    <!-- Section 7: AI Reasoning -->
    <div class="section-card">
      <div class="section-title">7. AI Architectural Reasoning</div>
      {"".join(f'''
      <div style="margin-bottom:16px; padding:12px; background:var(--bg-primary); border-radius:8px;">
        <strong style="color:var(--accent-blue);">{r.decision_title}</strong> (Confidence: {int(r.confidence_score*100)}%)
        <div style="font-size:13px; margin-top:6px;"><strong>Why Needed:</strong> {r.why_needed}</div>
        <div style="font-size:13px; margin-top:4px;"><strong>Rationale:</strong> {r.chosen_approach_rationale}</div>
        <div style="font-size:13px; margin-top:4px; color:var(--accent-green);"><strong>SEO Benefit:</strong> {r.expected_seo_benefit}</div>
      </div>
      ''' for r in report.ai_reasoning)}
    </div>

    <!-- Section 8 & 9: Execution & Review Summaries -->
    <div class="section-card">
      <div class="section-title">8. Execution & Review Validation</div>
      <table>
        <tr><th>Tasks Generated</th><td>{s8.tasks_generated}</td><th>Validation Status</th><td><span class="badge badge-success">{s9.validation_status}</span></td></tr>
        <tr><th>Tasks Executed</th><td>{s8.tasks_executed}</td><th>Overall Score</th><td>{s9.validation_score:.1f} / 100</td></tr>
        <tr><th>Files Modified</th><td>{", ".join(s8.files_modified)}</td><th>Recommendations</th><td>{" | ".join(s9.recommendations[:2])}</td></tr>
      </table>
    </div>

    <!-- Section 10 & 11: Assets & Git -->
    <div class="section-card">
      <div class="section-title">10. Generated Technical Assets & Git Summary</div>
      <table>
        <thead><tr><th>Asset Name</th><th>Action</th><th>File Path</th><th>Validation</th></tr></thead>
        <tbody>
          {"".join(f"<tr><td><code>{a.asset_name}</code></td><td>{a.action}</td><td><code>{a.file_path}</code></td><td><span class='badge badge-success'>{a.validation_status}</span></td></tr>" for a in report.generated_assets)}
        </tbody>
      </table>
    </div>

    <!-- Section 13: Timeline -->
    <div class="section-card">
      <div class="section-title">13. Chronological Execution Timeline</div>
      <ul class="timeline-list">
        {"".join(f"<li class='timeline-item'><code>{item.timestamp}</code> — <strong>{item.stage_name}</strong> <span class='badge badge-success'>{item.status}</span> ({item.duration_seconds}s)</li>" for item in report.timeline)}
      </ul>
    </div>

    <!-- Section 14: Final AI Summary -->
    <div class="section-card">
      <div class="section-title">14. Final AI Executive Conclusion</div>
      <blockquote style="margin:0; padding:16px; background:rgba(74, 222, 128, 0.1); border-left:4px solid var(--accent-green); color:var(--text-main);">
        {report.final_summary}
      </blockquote>
    </div>
  </div>
</body>
</html>
"""
        return html
