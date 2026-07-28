"""SEO Planning Agent - Orchestrator.

The planning agent is an intelligence-only layer that decides WHAT should be done
but does NOT execute anything. It coordinates three components:

1. RepositoryAnalyzer - analyzes the repository structure and content
2. KeywordSelector - selects and prioritizes keywords from n8n payload
3. TaskPlanner - generates execution plan with Task objects

Pipeline:
    RepositoryInfo + SEOPayload -> Planner.plan() -> ExecutionPlan

It MUST NOT:
- Modify files
- Communicate with OpenCode
- Perform Git operations
- Review generated code
- Make AI/LLM calls
"""

from seo_agent.agents.planning.keyword_selector import (
    KeywordPriority,
    KeywordScore,
    KeywordSelectionResult,
    KeywordSelector,
    KeywordSource,
)
from seo_agent.agents.planning.planner import (
    PlanningInput,
    PlanningResult,
    Planner,
)
from seo_agent.agents.planning.repository_analyzer import (
    ExistingSEOAsset,
    MissingMetadata,
    PageClassification,
    PageClassificationResult,
    RepositoryAnalysis,
    RepositoryAnalyzer,
    SEOOpportunity,
    SEOOpportunityType,
)
from seo_agent.agents.planning.task_planner import (
    Complexity,
    TaskGroup,
    TaskPlanner,
    TaskTemplate,
)

__all__ = [
    # Repository Analyzer
    "RepositoryAnalyzer",
    "RepositoryAnalysis",
    "SEOOpportunity",
    "SEOOpportunityType",
    "MissingMetadata",
    "ExistingSEOAsset",
    "PageClassification",
    "PageClassificationResult",
    # Keyword Selector
    "KeywordSelector",
    "KeywordSelectionResult",
    "KeywordScore",
    "KeywordPriority",
    "KeywordSource",
    # Task Planner
    "TaskPlanner",
    "TaskTemplate",
    "TaskGroup",
    # Planner
    "Planner",
    "PlanningInput",
    "PlanningResult",
]