"""Main workflow orchestrator.

This module provides the WorkflowOrchestrator class that coordinates the
entire SEO agent workflow. It executes stages in order, manages transitions,
handles failures, and coordinates with external agents.

The orchestrator does NOT contain business logic. It delegates to:
- Repository services for scanning, framework detection, page discovery
- Planning agent for execution planning
- Execution agent for file operations
- Review engine for validation
- Git service for version control

The orchestrator ONLY orchestrates - it decides WHAT to do and WHEN,
while actual HOW is handled by specialized services.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Union
import asyncio
import time
import traceback

from seo_agent.core.logging import get_logger, log_stage_banner, log_stage_report
from seo_agent.core.result import Failure, Result, Success
from seo_agent.models.api import KeywordPayload, SEOPayload
from seo_agent.models.repository import PageInfo
from seo_agent.models.seo import SEOPage
from seo_agent.agents.planning.planner import PlanningInput
from seo_agent.workflow.context import WorkflowContext
from seo_agent.workflow.stages import (
    WorkflowStage,
    can_transition,
    get_next_stage,
    get_stage_info,
    get_stage_order,
)

if TYPE_CHECKING:
    from seo_agent.models.workflow import WorkflowResult

logger = get_logger(__name__)


# Stage handler type - supports both sync and async handlers
StageHandler = Callable[[WorkflowContext], Result[Any, str]]
AsyncStageHandler = Callable[[WorkflowContext], Any]  # Awaitable that returns Result
HandlerType = Union[StageHandler, AsyncStageHandler]


@dataclass
class OrchestratorConfig:
    """Configuration for the workflow orchestrator.

    Attributes:
        max_retries: Maximum retries per stage on failure.
        continue_on_review_failure: Whether to continue if review fails.
        enable_checkpoints: Whether to save workflow checkpoints.
        checkpoint_interval: Stages between checkpoints.
    """

    max_retries: int = 3
    continue_on_review_failure: bool = False
    enable_checkpoints: bool = True
    checkpoint_interval: int = 3


class WorkflowOrchestrator:
    """Main workflow orchestrator.

    This class coordinates the entire SEO agent workflow by executing
    stages in order. It manages stage transitions, handles failures,
    and coordinates with external services.

    The orchestrator does NOT:
    - Contain business logic
    - Communicate with AI agents directly
    - Modify repositories
    - Make planning decisions

    The orchestrator ONLY:
    - Executes stages in order
    - Manages stage transitions
    - Handles failures and retries
    - Coordinates with external services
    - Reports workflow status

    Example:
        >>> config = OrchestratorConfig(max_retries=3)
        >>> orchestrator = WorkflowOrchestrator(config)
        >>> context = WorkflowContext(repository_path=Path("/repo"))
        >>> result = await orchestrator.run(context)
    """

    def __init__(
        self,
        config: OrchestratorConfig | None = None,
        stage_handlers: dict[WorkflowStage, HandlerType] | None = None,
    ) -> None:
        """Initialize the orchestrator.

        Args:
            config: Orchestrator configuration.
            stage_handlers: Optional handlers for stages. If not provided,
                stages must be registered before running.
        """
        self.config = config or OrchestratorConfig()
        self._stage_handlers: dict[WorkflowStage, HandlerType] = (
            stage_handlers or {}
        )
        self._retry_counts: dict[WorkflowStage, int] = {}

    def register_stage_handler(
        self,
        stage: WorkflowStage,
        handler: HandlerType,
    ) -> None:
        """Register a handler for a stage.

        Args:
            stage: The stage to handle.
            handler: Function that executes the stage (sync or async).
        """
        self._stage_handlers[stage] = handler
        logger.debug(f"Registered handler for stage: {stage.value}")

    def register_handlers(
        self,
        handlers: dict[WorkflowStage, HandlerType],
    ) -> None:
        """Register multiple stage handlers.

        Args:
            handlers: Dictionary mapping stages to handlers.
        """
        for stage, handler in handlers.items():
            self.register_stage_handler(stage, handler)

    async def run(self, context: WorkflowContext) -> Result[WorkflowContext, str]:
        """Run the workflow.

        Executes stages in order until completion or failure.

        Args:
            context: Workflow context with initial state.

        Returns:
            Success with updated context if workflow completes.
            Failure with error message if workflow fails.
        """
        logger.info(
            f"Starting workflow for repository: {context.repository_path}"
        )

        # Execute stages in order
        for stage in get_stage_order():
            if context.is_complete():
                break

            result = await self._execute_stage(context, stage)
            if result.is_failure():
                logger.error(f"Stage {stage.value} failed: {result.get_error_or_none()}")
                return result

        # Mark workflow completed if all stages succeeded
        context.update_stage(WorkflowStage.COMPLETED)

        # Check final state
        if context.is_successful():
            log_stage_banner(logger, "Workflow Completed")
            logger.info("Workflow completed successfully")
            return Success(context)
        elif context.has_errors():
            error_summary = context.get_error_summary()
            logger.error(f"Workflow failed: {error_summary}")
            return Failure(error_summary or "Workflow failed")
        else:
            logger.warning("Workflow ended in unexpected state")
            return Failure("Workflow ended in unexpected state")

    async def _execute_stage(
        self,
        context: WorkflowContext,
        stage: WorkflowStage,
    ) -> Result[WorkflowContext, str]:
        """Execute a single stage.

        Args:
            context: Workflow context.
            stage: Stage to execute.

        Returns:
            Success with updated context, or failure with error.
        """
        stage_info = get_stage_info(stage)
        log_stage_banner(logger, stage_info.name)
        logger.info(f"Executing stage: {stage_info.name}")
        start_time = time.time()

        # Get handler
        handler = self._stage_handlers.get(stage)
        if handler is None:
            error = f"No handler registered for stage: {stage.value}"
            logger.error(error)
            context.record_failure(error)
            return Failure(error)

        # Execute with retries
        retry_count = 0
        max_retries = self.config.max_retries if stage_info.can_retry else 0

        while retry_count <= max_retries:
            # Update to this stage
            context.update_stage(stage)

            # Execute handler - handle both sync and async handlers
            result = handler(context)
            
            # Await if it's a coroutine (async handler)
            if asyncio.iscoroutine(result):
                result = await result

            duration = time.time() - start_time
            if result.is_success():
                self._print_stage_report(context, stage, "SUCCESS", duration)
                logger.info(f"Stage {stage_info.name} completed successfully")
                return Success(context)

            self._print_stage_report(context, stage, "FAILED", duration)

            # Handle failure
            error = result.get_error_or_none() or "Unknown error"
            retry_count += 1

            if retry_count <= max_retries:
                logger.warning(
                    f"Stage {stage_info.name} failed (attempt {retry_count}/"
                    f"{max_retries + 1}): {error}"
                )
                self._retry_counts[stage] = retry_count
            else:
                logger.error(
                    f"Stage {stage_info.name} failed after {max_retries + 1} "
                    f"attempts: {error}"
                )
                context.record_failure(error)
                return Failure(error)

        # Should not reach here
        return Failure("Max retries exceeded")

    def _print_stage_report(
        self,
        context: WorkflowContext,
        stage: WorkflowStage,
        status: str,
        duration_sec: float,
    ) -> None:
        """Format and print a structured report for the completed stage using runtime information."""
        try:
            stage_info = get_stage_info(stage)
            stage_name = stage_info.name

            input_data: list[tuple[str, str]] = []
            processing_steps: list[str] = []
            output_data: list[tuple[str, str]] = []
            extra_sections: list[tuple[str, list[str]]] = []

            if stage == WorkflowStage.REPOSITORY_SCAN:
                input_data.append(("Repository Path", str(context.repository_path)))
                processing_steps = [
                    "Scanning repository...",
                    "Detecting supported HTML pages...",
                    "Identifying project structure...",
                ]
                if context.repository_info:
                    fw = context.framework_info.framework if context.framework_info else "static_html"
                    output_data.append(("Framework", str(fw)))
                    html_files = [Path(p.path).name if hasattr(p, "path") else str(p) for p in context.repository_info.html_pages]
                    if html_files:
                        extra_sections.append(("Files Found", html_files))
                    output_data.append(("Total HTML Pages", str(len(context.repository_info.html_pages))))

            elif stage == WorkflowStage.FRAMEWORK_DETECTION:
                input_data.append(("Repository Path", str(context.repository_path)))
                processing_steps = [
                    "Analyzing file structure...",
                    "Detecting web framework...",
                    "Identifying routing architecture...",
                ]
                if context.framework_info:
                    output_data.append(("Framework", str(context.framework_info.framework)))
                    output_data.append(("Routing Type", str(context.framework_info.routing_type)))

            elif stage == WorkflowStage.PAGE_DISCOVERY:
                input_data.append(("Repository Path", str(context.repository_path)))
                if context.framework_info:
                    input_data.append(("Framework", str(context.framework_info.framework)))
                processing_steps = [
                    "Discovering static routes...",
                    "Mapping page paths...",
                ]
                if context.pages:
                    page_items = [f"{Path(p.path).name} ({p.route})" if hasattr(p, "path") else str(p.route) for p in context.pages]
                    extra_sections.append(("Pages Discovered", page_items))
                output_data.append(("Total Pages Discovered", str(len(context.pages))))

            elif stage == WorkflowStage.METADATA_EXTRACTION:
                input_data.append(("Discovered Pages Count", str(len(context.page_info))))
                processing_steps = [
                    "Parsing HTML head tags...",
                    "Extracting title, description, canonical, OpenGraph, JSON-LD...",
                ]
                if context.page_info:
                    meta_items = []
                    for p in context.page_info:
                        title_str = f'"{p.title}"' if p.title else "None"
                        desc_str = f'"{p.metadata.description[:60]}..."' if p.metadata and p.metadata.description else "None"
                        meta_items.append(f"{p.route} -> Title: {title_str} | Meta Description: {desc_str}")
                    extra_sections.append(("Extracted Page Metadata", meta_items))
                output_data.append(("Pages Parsed", str(len(context.page_info))))

            elif stage == WorkflowStage.PLANNING:
                input_data.append(("Repository Path", str(context.repository_path)))
                if context.keywords:
                    input_data.append(("Seed Keywords", ", ".join(context.keywords)))
                processing_steps = [
                    "Analyzing repository opportunities...",
                    "Selecting target keywords...",
                    "Generating multi-phase execution tasks...",
                ]
                if context.execution_plan:
                    task_items = []
                    for t in context.execution_plan.tasks:
                        task_id = getattr(t, "id", getattr(t, "task_id", "task"))
                        phase = getattr(t, "phase", 1)
                        desc = getattr(t, "description", getattr(t, "title", "Task"))
                        target = getattr(t, "target_file", "")
                        task_items.append(f"[{task_id}] Phase {phase}: {desc} ({target})")
                    if task_items:
                        extra_sections.append(("Planned Tasks", task_items))
                    output_data.append(("Total Tasks Planned", str(len(context.execution_plan.tasks))))
                    output_data.append(("Execution Phases", str(len(context.execution_plan.phases))))

            elif stage == WorkflowStage.EXECUTION:
                input_data.append(("Planned Tasks Count", str(len(context.execution_plan.tasks)) if context.execution_plan else "0"))
                processing_steps = [
                    "Executing task modifications...",
                    "Invoking OpenCode client...",
                    "Applying SEO changes...",
                ]
                if context.execution_result:
                    if context.execution_result.executed_tasks:
                        extra_sections.append(("Executed Tasks", [str(getattr(t, "task_id", t)) for t in context.execution_result.executed_tasks]))
                    if context.execution_result.files_modified:
                        extra_sections.append(("Files Modified", [str(f) for f in context.execution_result.files_modified]))
                    output_data.append(("Executed Tasks Count", str(len(context.execution_result.executed_tasks))))
                    output_data.append(("Files Modified Count", str(len(context.execution_result.files_modified))))

            elif stage == WorkflowStage.REVIEW:
                input_data.append(("Execution Results", "Passed from Execution Stage"))
                processing_steps = [
                    "Validating HTML rules...",
                    "Checking title & meta description lengths...",
                    "Verifying h1 hierarchy...",
                ]
                if context.review_result:
                    output_data.append(("Approved", str(context.review_result.approved)))
                    output_data.append(("Quality Score", f"{context.review_result.score:.1f}" if hasattr(context.review_result, "score") else "1.0"))
                    if hasattr(context.review_result, "issues") and context.review_result.issues:
                        extra_sections.append(("Validation Issues", [str(i) for i in context.review_result.issues]))

            elif stage == WorkflowStage.SEO_UPDATE:
                input_data.append(("Repository Path", str(context.repository_path)))
                processing_steps = [
                    "Applying approved changes...",
                    "Generating sitemap.xml...",
                    "Generating robots.txt...",
                ]
                if "sitemap_path" in context.metadata:
                    output_data.append(("Sitemap Path", str(context.metadata["sitemap_path"])))
                if "robots_path" in context.metadata:
                    output_data.append(("Robots Path", str(context.metadata["robots_path"])))

            elif stage == WorkflowStage.GIT_OPERATIONS:
                input_data.append(("Repository Path", str(context.repository_path)))
                processing_steps = [
                    "Checking git configuration...",
                    "Performing version control operations...",
                ]
                output_data.append(("Git Status", "Skipped per context configuration" if context.config.get("skip_git") else "Completed"))

            log_stage_report(
                logger=logger,
                stage_name=stage_name,
                input_data=input_data,
                processing_steps=processing_steps,
                output_data=output_data,
                status=status,
                duration_sec=duration_sec,
                extra_sections=extra_sections if extra_sections else None,
            )
        except Exception as e:
            logger.debug(f"Failed to format stage report: {e}")

    def get_stage_status(
        self,
        context: WorkflowContext,
    ) -> dict[str, Any]:
        """Get status of all stages.

        Args:
            context: Current workflow context.

        Returns:
            Dictionary with stage status information.
        """
        stages = []
        for stage in get_stage_order():
            stage_info = get_stage_info(stage)
            retry_count = self._retry_counts.get(stage, 0)

            stages.append({
                "stage": stage.value,
                "name": stage_info.name,
                "description": stage_info.description,
                "can_retry": stage_info.can_retry,
                "retry_count": retry_count,
                "is_current": context.stage == stage,
                "is_complete": context.stage.is_terminal,
            })

        return {
            "current_stage": context.stage.value,
            "stages": stages,
            "is_complete": context.is_complete(),
            "is_successful": context.is_successful(),
            "has_errors": context.has_errors(),
            "error_count": len(context.errors),
            "transition_count": len(context.transitions),
        }

    def reset(self) -> None:
        """Reset orchestrator state.

        Clears retry counts and any temporary state.
        """
        self._retry_counts.clear()
        logger.debug("Orchestrator state reset")


def create_orchestrator(
    config: OrchestratorConfig | None = None,
    repository_scanner: Any = None,
    framework_detector: Any = None,
    page_discovery: Any = None,
    metadata_parser: Any = None,
    planning_agent: Any = None,
    execution_agent: Any = None,
    review_engine: Any = None,
    git_service: Any = None,
    seo_service: Any = None,
    sitemap_service: Any = None,
    robots_service: Any = None,
) -> WorkflowOrchestrator:
    """Create and configure a workflow orchestrator.

    This factory function wires up all the service dependencies
    and registers the appropriate stage handlers.

    Args:
        config: Orchestrator configuration.
        repository_scanner: Service for repository scanning.
        framework_detector: Service for framework detection.
        page_discovery: Service for page discovery.
        metadata_parser: Service for metadata extraction.
        planning_agent: AI planning agent.
        execution_agent: AI execution agent.
        review_engine: Review/validation engine.
        git_service: Git operations service.
        seo_service: SEO operations service.
        sitemap_service: Service for sitemap operations.
        robots_service: Service for robots operations.

    Returns:
        Configured WorkflowOrchestrator instance.
    """
    orchestrator = WorkflowOrchestrator(config)

    # Register repository stages
    if repository_scanner:
        orchestrator.register_stage_handler(
            WorkflowStage.SCANNING,
            _create_scanning_handler(repository_scanner),
        )

    if framework_detector:
        orchestrator.register_stage_handler(
            WorkflowStage.FRAMEWORK_DETECTION,
            _create_framework_detection_handler(framework_detector),
        )

    if page_discovery:
        orchestrator.register_stage_handler(
            WorkflowStage.PAGE_DISCOVERY,
            _create_page_discovery_handler(page_discovery),
        )

    if metadata_parser:
        orchestrator.register_stage_handler(
            WorkflowStage.METADATA_EXTRACTION,
            _create_metadata_extraction_handler(metadata_parser),
        )

    # Register planning stage
    if planning_agent:
        orchestrator.register_stage_handler(
            WorkflowStage.PLANNING,
            _create_planning_handler(planning_agent),
        )

    # Register execution stage
    if execution_agent:
        orchestrator.register_stage_handler(
            WorkflowStage.EXECUTION,
            _create_execution_handler(execution_agent),
        )

    # Register review stage
    if review_engine:
        orchestrator.register_stage_handler(
            WorkflowStage.REVIEW,
            _create_review_handler(
                review_engine,
                execution_agent=execution_agent,
                max_review_attempts=config.max_retries,
            ),
        )

    # Register SEO update stage
    if seo_service or sitemap_service or robots_service:
        orchestrator.register_stage_handler(
            WorkflowStage.SEO_UPDATE,
            _create_seo_update_handler(
                seo_service=seo_service,
                sitemap_service=sitemap_service,
                robots_service=robots_service,
            ),
        )

    # Register git stage
    if git_service:
        orchestrator.register_stage_handler(
            WorkflowStage.GIT,
            _create_git_handler(git_service),
        )

    return orchestrator


# Handler factory functions
# These create handlers that delegate to services

def _create_scanning_handler(
    repository_service: Any,
) -> StageHandler:
    """Create handler for SCANNING stage."""

    def handler(context: WorkflowContext) -> Result[WorkflowContext, str]:
        try:
            result = repository_service.scan(context.repository_path)

            if result.is_success():
                context.set_repository_info(result.get_or_none())
                return Success(context)

            logger.error(f"Scan failure: {result.get_error_or_none()}")
            return result

        except Exception as e:
            logger.exception(f"Scanning handler exception: {e}")
            return Failure(str(e))

    return handler

def _create_framework_detection_handler(
    framework_detector: Any,
) -> StageHandler:
    """Create handler for FRAMEWORK_DETECTION stage."""
    async def handler(context: WorkflowContext) -> Result[WorkflowContext, str]:
        try:
            result = framework_detector.detect(
                context.repository_path,
                context.repository_info,
            )
            if result.is_success():
                context.set_framework_info(result.get_or_none())
            if result.is_success():
                return Success(context)
            else:
                return Failure(result.get_error_or_none() or "Framework detection failed")
        except Exception as e:
                return Failure(str(e))
    return handler


def _create_page_discovery_handler(
    repository_service: Any,
) -> StageHandler:
    """Create handler for PAGE_DISCOVERY stage."""
    def handler(context: WorkflowContext) -> Result[WorkflowContext, str]:
        try:
            result = repository_service.discover_pages(
                context.repository_path,
                context.framework_info,
            )
            if result.is_success():
                context.set_pages(result.get_or_none() or [])
                return Success(context)
            return result
        except Exception as e:
            traceback.print_exc()
            return Failure(str(e))
    return handler


def _create_metadata_extraction_handler(
    metadata_parser: Any,
) -> StageHandler:
    """Create handler for METADATA_EXTRACTION stage."""
    async def handler(context: WorkflowContext) -> Result[WorkflowContext, str]:
        try:
            page_info_list = []
            for page in context.pages:
                result = metadata_parser.parse_file(page.file_path)
                if result.is_success():
                    page_metadata = result.get_or_none()
                    # Construct PageInfo from DiscoveredPage (route, file_path) + PageMetadata
                    page_info = PageInfo(
                        route=page.url_path,
                        file_path=page.file_path,
                        page_type=page.page_type,
                        title=page_metadata.title if page_metadata else None,
                        metadata=page_metadata,
                    )
                    page_info_list.append(page_info)
                else:
                    return Failure(f"Failed to parse metadata for {page.file_path}: {result.get_or_none()}")
            context.set_page_info(page_info_list)

            return Success(context)
        except Exception as e:
            return Failure(str(e))
    return handler


def _create_planning_handler(
    planning_agent: Any,
) -> StageHandler:
    """Create handler for PLANNING stage."""
    def handler(context: WorkflowContext) -> Result[WorkflowContext, str]:
        try:
            # Convert keyword strings to KeywordPayload instances
            seed_keywords = [
                KeywordPayload(term=kw) for kw in context.keywords
            ]
            seo_payload = SEOPayload(
                target_urls=[str(context.repository_path)],
                seed_keywords=seed_keywords,
            )
            input_data = PlanningInput(
                request_id=context.metadata.get("request_id", ""),
                repository_info=context.repository_info,
                seo_payload=seo_payload,
                repository_path=context.repository_path,
                page_info=tuple(context.page_info) if context.page_info else (),
            )
            result = planning_agent.plan(input_data)
            # PlanningResult is a plain dataclass, not a Result type.
            # Exceptions are caught by the try/except below.
            context.set_execution_plan(result.execution_plan)
            return Success(context)
        except Exception as e:
            logger.exception("Planning stage failed: %s", str(e))
            return Failure(str(e))
    return handler


def _create_execution_handler(
    execution_agent: Any,
) -> StageHandler:
    """Create handler for EXECUTION stage."""
    async def handler(context: WorkflowContext) -> Result[WorkflowContext, str]:
        try:
            # Handle no-op execution: if the plan has zero tasks, produce an
            # empty ExecutionResult and succeed immediately.
            if context.execution_plan is None or context.execution_plan.total_tasks == 0:
                from seo_agent.models.task import ExecutionPlan, ExecutionResult
                logger.info("Execution plan has 0 tasks — repository already optimized")
                noop_result = ExecutionResult(
                    request_id=context.metadata.get("request_id", ""),
                    success=True,
                    plan=context.execution_plan or ExecutionPlan(request_id=""),
                )
                context.set_execution_result(noop_result)
                return Success(context)

            result = execution_agent.execute(context.execution_plan)
            if result.is_success():
                context.set_execution_result(result.get_or_none())
                return Success(context)
            return result
        except Exception as e:
            return Failure(str(e))
    return handler


def _extract_proposed_contents(execution_result: Any | None) -> dict[str, str]:
    """Extract proposed file contents from the active execution result in memory."""
    contents: dict[str, str] = {}
    if not execution_result or not hasattr(execution_result, "phase_results"):
        return contents

    for phase_res in execution_result.phase_results:
        for task_res in getattr(phase_res, "task_results", []):
            output = getattr(task_res, "output", {}) or {}
            for key in ("file_edits", "page_generations"):
                entries = output.get(key, [])
                if isinstance(entries, list):
                    for entry in entries:
                        if isinstance(entry, dict):
                            fp = entry.get("file_path")
                            cnt = entry.get("content")
                            if fp and cnt is not None:
                                contents[fp] = cnt
    return contents


def _build_fix_plan_from_review(
    context: WorkflowContext,
    validation_result: Any,
    proposed_contents: dict[str, str],
) -> Any | None:
    """Construct an ExecutionPlan with structured FixTask objects derived from review feedback."""
    if not hasattr(validation_result, "issues") or not validation_result.issues:
        return None

    from seo_agent.models.execution_session import FixTask
    from seo_agent.models.task import ExecutionPlan, Phase, Task, TaskPriority, TaskStatus, TaskType

    tasks: list[Task] = []
    for idx, issue in enumerate(validation_result.issues, 1):
        file_path = getattr(issue, "file_path", None) or "repository"
        msg = getattr(issue, "message", "Resolve issue")
        suggestion = getattr(issue, "suggestion", None)
        prev_content = proposed_contents.get(file_path)

        fix_task_model = FixTask(
            task_id=f"fix-{idx:04d}",
            file_path=file_path,
            current_proposed_content=prev_content,
            review_feedback=msg,
            suggestions=suggestion,
            repository_context={"repository_path": str(context.repository_path)},
        )

        description = f"Fix review issue: {msg}"
        if suggestion:
            description += f" (Suggestion: {suggestion})"

        input_data = {
            "fix_task": {
                "task_id": fix_task_model.task_id,
                "file_path": fix_task_model.file_path,
                "current_proposed_content": fix_task_model.current_proposed_content,
                "review_feedback": fix_task_model.review_feedback,
                "suggestions": fix_task_model.suggestions,
                "repository_context": fix_task_model.repository_context,
            },
            "instructions": (
                f"Fix the review failure issue in '{file_path}': {msg}. "
                f"Suggestion: {suggestion or 'Ensure compliance'}."
            ),
            "file_path": file_path,
            "target_files": [file_path] if getattr(issue, "file_path", None) else [],
            "phase": "fix",
        }

        task = Task(
            task_id=fix_task_model.task_id,
            task_type=TaskType.METADATA_UPDATE,
            description=description,
            status=TaskStatus.PENDING,
            priority=TaskPriority.HIGH,
            input_data=input_data,
        )
        tasks.append(task)

    if not tasks:
        return None

    phase = Phase(
        phase_id=f"fix-phase-{len(proposed_contents) + 1}",
        name="Review Fix Phase",
        description="Execution phase to resolve issues identified by ReviewValidator",
        tasks=tuple(tasks),
    )

    request_id = context.metadata.get("request_id", "req")
    return ExecutionPlan(
        request_id=f"fix_{request_id}",
        phases=(phase,),
    )


def _create_review_handler(
    review_engine: Any,
    execution_agent: Any = None,
    max_review_attempts: int = 3,
) -> StageHandler:
    """Create handler for REVIEW stage with Review -> Fix Task -> Execution retry loop using ExecutionSession."""
    async def handler(context: WorkflowContext) -> Result[WorkflowContext, str]:
        try:
            from seo_agent.models.execution_session import ExecutionSession

            # Retrieve or initialize ExecutionSession on WorkflowContext metadata
            session: ExecutionSession = context.metadata.get("execution_session")
            if not session:
                session = ExecutionSession()
                context.metadata["execution_session"] = session

            attempt = 0
            while attempt < max_review_attempts:
                attempt += 1

                # Validate active single execution result
                result = review_engine.validate_execution_result(
                    context.execution_result,
                    context.repository_path,
                )
                context.set_review_result(result)

                # Record attempt in history and update active session current result
                session.record_attempt(context.execution_result, result)

                if result.is_valid:
                    logger.info(f"Review validation passed on attempt {attempt}/{max_review_attempts}")
                    # Ensure context.execution_result is strictly the single active current result
                    context.set_execution_result(session.current_execution_result)
                    return Success(context)

                logger.warning(
                    f"Review failed (attempt {attempt}/{max_review_attempts}) "
                    f"with {len(result.issues)} issue(s)"
                )

                if attempt >= max_review_attempts or not execution_agent:
                    return Failure(
                        f"Validation failed after {attempt} attempt(s) with {len(result.issues)} issue(s)"
                    )

                # Extract in-memory proposed file contents from the active current result
                proposed_contents = _extract_proposed_contents(session.current_execution_result)

                # Generate a fix plan from review feedback issues & structured FixTask objects
                fix_plan = _build_fix_plan_from_review(context, result, proposed_contents)
                if not fix_plan:
                    return Failure(
                        f"Validation failed with {len(result.issues)} issue(s), unable to generate fix plan"
                    )

                logger.info(
                    f"Re-executing {fix_plan.total_tasks} fix task(s) for review feedback "
                    f"(attempt {attempt + 1}/{max_review_attempts})"
                )
                exec_res = execution_agent.execute(fix_plan)

                if not exec_res.is_success():
                    return Failure(
                        f"Fix task execution failed: {exec_res.get_error_or_none()}"
                    )

                # Replace current_execution_result with ONLY the latest single ExecutionResult
                new_exec_result = exec_res.get_or_none()
                context.set_execution_result(new_exec_result)

            return Failure(
                f"Validation failed after {max_review_attempts} attempt(s)"
            )

        except Exception as e:
            return Failure(str(e))
    return handler


def _create_seo_update_handler(
    seo_service: Any = None,
    sitemap_service: Any = None,
    robots_service: Any = None,
) -> StageHandler:
    """Create handler for SEO_UPDATE stage."""
    async def handler(context: WorkflowContext) -> Result[WorkflowContext, str]:
        try:
            if context.execution_result is None:
                return Failure("No execution result available for SEO update")

            # Apply approved file changes (metadata updates, code edits, page generations) to disk
            from seo_agent.seo.applier import ApprovedChangesApplier
            applier = ApprovedChangesApplier()
            apply_res = applier.apply_changes(
                context.execution_result,
                context.repository_path,
            )
            if not apply_res.is_success():
                return Failure(apply_res.get_error_or_none() or "Failed to apply approved changes")

            # Generate SEO pages (if required)
            if seo_service and context.execution_result.seo_pages_created:
                result = seo_service.generate_pages(
                    [context.execution_result],
                    context.repository_path,
                )
                if not result.is_success():
                    return Failure(result.get_error_or_none() or "SEO page generation failed")

            # Invoke SitemapService
            if sitemap_service:
                log_stage_banner(logger, "Sitemap Generation", char="-")
                logger.info("Starting sitemap generation")
                sitemap_path = context.repository_path / "sitemap.xml"
                sitemap_service.set_sitemap_path(sitemap_path)

                seo_pages: list[SEOPage] = []
                for p_info in (context.page_info or []):
                    if p_info.metadata:
                        seo_pages.append(
                            SEOPage(
                                slug=p_info.route.strip("/").replace(".html", "") or "home",
                                title=p_info.title or "",
                                description=p_info.metadata.description or "",
                                h1=p_info.title or "",
                                metadata=p_info.metadata,
                                route_path=p_info.route,
                                file_path=str(p_info.file_path),
                            )
                        )

                sitemap_res = sitemap_service.update_sitemap(seo_pages, preserve_existing=True)
                if not sitemap_res.is_success():
                    err_msg = sitemap_res.get_error_or_none() or "Sitemap generation failed"
                    logger.error(f"Sitemap generation failed: {err_msg}")
                    return Failure(err_msg)

                context.metadata["sitemap_path"] = str(sitemap_path)
                logger.info(f"sitemap generated: {sitemap_path}")

            # Invoke RobotsService
            if robots_service:
                log_stage_banner(logger, "Robots.txt Generation", char="-")
                logger.info("Starting robots generation")
                robots_path = context.repository_path / "robots.txt"
                robots_service.set_robots_path(robots_path)

                sitemap_url = "https://example.com/sitemap.xml"
                robots_res = robots_service.update_robots(sitemap_url=sitemap_url, preserve_existing=True)
                if not robots_res.is_success():
                    err_msg = robots_res.get_error_or_none() or "Robots generation failed"
                    logger.error(f"Robots generation failed: {err_msg}")
                    return Failure(err_msg)

                context.metadata["robots_path"] = str(robots_path)
                logger.info(f"robots generated: {robots_path}")

            return Success(context)
        except Exception as e:
            return Failure(str(e))
    return handler


def _create_git_handler(
    git_service: Any,
) -> StageHandler:
    """Create handler for GIT stage."""
    async def handler(context: WorkflowContext) -> Result[WorkflowContext, str]:
        try:
            if context.config.get("skip_git"):
                logger.info("Git operations skipped per workflow context configuration")
                return Success(context)

            result = git_service.commit_seo_changes(
                context.repository_path,
            )
            if result.is_success():
                # Store git result in metadata (WorkflowContext has no
                # dedicated git_result field).
                context.metadata["git_result"] = result.get_or_none()
                return Success(context)
            return Failure(
                str(result.get_error_or_none())
                if result.get_error_or_none() is not None
                else "Git commit failed"
            )
        except Exception as e:
            return Failure(str(e))
    return handler