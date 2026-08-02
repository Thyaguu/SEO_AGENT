"""Main planning orchestrator.

This module coordinates the three planning components:
1. RepositoryAnalyzer - analyzes the repository
2. KeywordSelector - selects and prioritizes keywords
3. TaskPlanner - generates execution plan

It MUST NOT:
- Modify files
- Communicate with OpenCode
- Perform Git operations
- Review generated code
- Make AI/LLM calls

It ONLY orchestrates the planning pipeline and returns an ExecutionPlan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from seo_agent.core.logging import get_logger
from seo_agent.models.api import SEOPayload
from seo_agent.models.repository import PageInfo, RepositoryInfo
from seo_agent.models.task import ExecutionPlan

from .keyword_selector import KeywordSelectionResult, KeywordSelector
from .repository_analyzer import RepositoryAnalysis, RepositoryAnalyzer
from .task_planner import TaskPlanner

if TYPE_CHECKING:
    from seo_agent.core.dependency_injection import Container

logger = get_logger(__name__)


from seo_agent.models.seo_input import SEOInputCollection


@dataclass(frozen=True)
class PlanningInput:
    """Input data for the planning pipeline.

    Attributes:
        request_id: Request identifier for tracking.
        repository_info: Repository information from scanner.
        seo_payload: SEO payload from n8n.
        repository_path: Path to the repository.
        page_info: Extracted page information with metadata from METADATA_EXTRACTION stage.
        seo_input: Optional normalized SEO input collection from CSV/JSON.
    """

    request_id: str
    repository_info: RepositoryInfo
    seo_payload: SEOPayload
    repository_path: Path
    page_info: tuple[PageInfo, ...] = field(default_factory=tuple)
    seo_input: SEOInputCollection | None = None


from seo_agent.models.page_keyword_mapping import KeywordMatchingResult
from seo_agent.agents.planning.page_keyword_matcher import PageKeywordMatcher


@dataclass(frozen=True)
class PlanningResult:
    """Result of the planning process.

    Attributes:
        execution_plan: Generated execution plan.
        repository_analysis: Repository analysis results.
        keyword_selection: Keyword selection results.
        matching_result: AI Page-Keyword matching results.
        planned_at: Timestamp of planning.
        duration_seconds: Time taken for planning.
    """

    execution_plan: ExecutionPlan
    repository_analysis: RepositoryAnalysis
    keyword_selection: KeywordSelectionResult
    matching_result: KeywordMatchingResult | None = None
    planned_at: datetime = field(default_factory=datetime.utcnow)
    duration_seconds: float = 0.0


class Planner:
    """Main planning orchestrator.

    This planner coordinates the three planning components to produce
    an ExecutionPlan from repository analysis and n8n payload.

    Pipeline:
    1. RepositoryAnalyzer.analyze() -> RepositoryAnalysis
    2. KeywordSelector.select() -> KeywordSelectionResult
    3. TaskPlanner.plan() -> ExecutionPlan

    It performs analysis only - no file modifications, no AI calls,
    no Git operations, no code review.
    """

    def __init__(
        self,
        repository_analyzer: RepositoryAnalyzer | None = None,
        keyword_selector: KeywordSelector | None = None,
        task_planner: TaskPlanner | None = None,
    ) -> None:
        """Initialize the planner.

        Args:
            repository_analyzer: Repository analyzer instance.
            keyword_selector: Keyword selector instance.
            task_planner: Task planner instance.
        """
        self._logger = get_logger(__name__)

        # Use provided instances or create new ones
        self._repository_analyzer = repository_analyzer or RepositoryAnalyzer()
        self._keyword_selector = keyword_selector or KeywordSelector()
        self._task_planner = task_planner or TaskPlanner()

        self._logger.debug("planner_initialized")

    @classmethod
    def from_container(cls, container: Container) -> Planner:
        """Create planner from dependency injection container.

        Args:
            container: DI container.

        Returns:
            Configured Planner instance.
        """
        return cls()

    def plan(self, input_data: PlanningInput) -> PlanningResult:
        """Execute the planning pipeline.

        Args:
            input_data: Planning input data.

        Returns:
            PlanningResult with execution plan and intermediate results.
        """
        start_time = datetime.utcnow()
        self._logger.debug(
            f"planning_started: repository={input_data.repository_path}, "
            f"seed_keywords={len(input_data.seo_payload.seed_keywords)}"
        )

        # Step 1: Analyze repository
        self._logger.debug("step_1_analyzing_repository")
        repository_analysis = self._repository_analyzer.analyze(
            input_data.repository_info,
            page_info=input_data.page_info,
        )

        # Step 2: Select keywords
        self._logger.debug("step_2_selecting_keywords")
        keyword_selection = self._keyword_selector.select(
            input_data.seo_payload,
            existing_pages=input_data.page_info,
        )

        # Step 2.5: Perform AI Page-Keyword Semantic Matching if SEO Input Pool is present
        matching_result = None
        if input_data.seo_input and input_data.seo_input.records:
            self._logger.debug("step_2_5_ai_page_keyword_matching")
            matcher = PageKeywordMatcher()
            pages_list = list(input_data.page_info) if input_data.page_info else []
            matching_result = matcher.match_pages(pages_list, input_data.seo_input.records)

        # Step 3: Generate execution plan
        self._logger.debug("step_3_generating_execution_plan")
        execution_plan = self._task_planner.plan(
            request_id=input_data.request_id,
            repository_analysis=repository_analysis,
            keyword_selection=keyword_selection,
            repository_path=input_data.repository_path,
            seo_input=input_data.seo_input,
            matching_result=matching_result,
        )

        # Calculate duration
        duration = (datetime.utcnow() - start_time).total_seconds()

        result = PlanningResult(
            execution_plan=execution_plan,
            repository_analysis=repository_analysis,
            keyword_selection=keyword_selection,
            matching_result=matching_result,
            planned_at=start_time,
            duration_seconds=duration,
        )

        self._logger.debug(
            f"planning_completed: duration_seconds={duration}, "
            f"total_tasks={execution_plan.total_tasks}, "
            f"phases={len(execution_plan.phases)}, "
            f"selected_keywords={keyword_selection.total_selected_count}, "
            f"opportunities={len(repository_analysis.seo_opportunities)}"
        )

        return result

    def plan_simple(
        self,
        repository_info: RepositoryInfo,
        seo_payload: SEOPayload,
        repository_path: Path,
    ) -> ExecutionPlan:
        """Simple planning interface.

        Args:
            repository_info: Repository information.
            seo_payload: SEO payload from n8n.
            repository_path: Path to repository.

        Returns:
            ExecutionPlan for the execution agent.
        """
        input_data = PlanningInput(
            repository_info=repository_info,
            seo_payload=seo_payload,
            repository_path=repository_path,
        )

        result = self.plan(input_data)
        return result.execution_plan