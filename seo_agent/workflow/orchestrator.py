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

from seo_agent.core.logging import ConsoleFormatter, get_logger, log_stage_banner, log_stage_report
from seo_agent.core.result import Failure, Result, Success
from seo_agent.models.api import KeywordPayload, SEOPayload
from seo_agent.models.repository import PageInfo
from seo_agent.models.seo import SEOPage
from seo_agent.agents.planning.planner import PlanningInput
from seo_agent.inputs import CSVSEOInputReader, JSONSEOInputReader
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

        # Process initial SEO input (CSV / JSON) during workflow initialization
        self._process_initial_seo_input(context)

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

        # Check final state using get_workflow_status()
        wf_status = context.get_workflow_status()

        # Build and log Workflow Execution Summary
        repo_name = Path(context.repository_path).name or str(context.repository_path)
        fw_type = context.framework_info.framework_type.value if context.framework_info else "static_html"
        pages_cnt = len(context.pages) if context.pages else len(context.page_info)
        kw_cnt = context.seo_input.records_loaded if (context.seo_input and getattr(context.seo_input, "records_loaded", None)) else len(context.keywords)
        tasks_pl = context.execution_plan.total_tasks if context.execution_plan else 0
        tasks_ex = context.execution_result.completed_tasks if context.execution_result else 0
        tasks_fa = context.execution_result.failed_tasks if context.execution_result else 0
        unique_mod_files = context.get_modified_file_paths()
        files_mod_cnt = len(unique_mod_files)
        rev_score = f"{int(context.review_result.overall_score)}/100" if (context.review_result and hasattr(context.review_result, "overall_score")) else "100/100"
        sm_status = "Generated" if "sitemap_path" in context.metadata else "Skipped"
        rb_status = "Generated" if "robots_path" in context.metadata else "Skipped"
        rep_status = "Markdown | JSON" if "report_paths" in context.metadata else "Generated"
        tot_dur = context.get_total_duration()

        summary_text = ConsoleFormatter.print_summary(
            repository=repo_name,
            framework=fw_type,
            pages=pages_cnt,
            keywords=kw_cnt,
            tasks_planned=tasks_pl,
            tasks_executed=tasks_ex,
            tasks_failed=tasks_fa,
            files_modified=files_mod_cnt,
            review_score=rev_score,
            sitemap=sm_status,
            robots=rb_status,
            reports=rep_status,
            overall_status=wf_status,
            total_duration=tot_dur,
        )
        logger.info(f"\n{summary_text}\n")

        if wf_status in ("SUCCESS", "PARTIAL SUCCESS"):
            return Success(context)
        else:
            error_summary = context.get_error_summary()
            return Failure(error_summary or "Workflow failed due to task failures")

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

            # Handle failure with Smart Retry Policy
            error = result.get_error_or_none() or "Unknown error"

            # Failure classification
            is_retryable = True
            classification = "RETRYABLE"
            reason = "Transient Error"
            exc_type = "Runtime Exception"

            non_retryable_terms = (
                "AttributeError", "NameError", "ImportError", "TypeError", "ValueError",
                "AssertionError", "SyntaxError", "KeyError", "IndexError",
                "has no attribute", "not defined", "cannot import", "missing 1 required",
                "unexpected keyword argument", "unsupported operand", "object is not callable",
                "rejected review", "Rejected review", "Validation failed", "validation failed",
                "Planning validation failed", "Missing approval", "skipped due to rejected review",
                "skipped due to execution task failures"
            )

            for term in non_retryable_terms:
                if term in error:
                    is_retryable = False
                    classification = "NON-RETRYABLE"
                    reason = "Programming Error" if any(p in error for p in ("Error", "attribute", "defined", "import", "operand", "callable", "argument")) else "Business Logic Failure"
                    exc_type = term if term in ("AttributeError", "NameError", "ImportError", "TypeError", "ValueError", "AssertionError", "SyntaxError", "KeyError") else "Logic Exception"
                    break

            if not is_retryable:
                logger.error(
                    f"Stage {stage_info.name} failed\n"
                    f"Classification:\n{classification}\n"
                    f"Reason:\n{reason}\n"
                    f"Exception:\n{exc_type}\n"
                    f"Retry:\nNO"
                )
                context.record_failure(error)
                return Failure(error)

            retry_count += 1

            if retry_count <= max_retries:
                logger.warning(
                    f"Stage {stage_info.name} transient failure (attempt {retry_count}/"
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

    def _process_initial_seo_input(self, context: WorkflowContext) -> None:
        """Parse and normalize CSV/JSON input files during context initialization."""
        if context.seo_input is not None:
            return

        csv_path = context.config.get("csv_path") or context.config.get("seo_input_path") or context.metadata.get("csv_path")
        csv_content = context.config.get("csv_content") or context.metadata.get("csv_content")
        json_path = context.config.get("json_path") or context.metadata.get("json_path")

        # Search default filenames in repo root if not explicitly provided
        if not csv_path and not csv_content and not json_path:
            repo_root = Path(context.repository_path)
            if repo_root.exists():
                for default_name in ("seo_input.csv", "seo.csv", "keywords.csv"):
                    candidate = repo_root / default_name
                    if candidate.exists() and candidate.is_file():
                        csv_path = str(candidate)
                        break

        if csv_path or csv_content:
            reader = CSVSEOInputReader()
            source = csv_path or csv_content
            res = reader.read(source)
            if res.is_success():
                context.seo_input = res.get_or_none()
            else:
                logger.error(f"Failed to read CSV input: {res.get_error_or_none()}")

        elif json_path:
            reader = JSONSEOInputReader()
            res = reader.read(json_path)
            if res.is_success():
                context.seo_input = res.get_or_none()
            else:
                logger.error(f"Failed to read JSON input: {res.get_error_or_none()}")

        if context.seo_input and context.seo_input.records:
            b1 = ConsoleFormatter.print_banner("SEO INTELLIGENCE LOADING")
            kv1 = ConsoleFormatter.print_key_value("Keywords Loaded", context.seo_input.records_loaded)
            st1 = ConsoleFormatter.print_status("SUCCESS")
            logger.info(f"\n{b1}\n\n{kv1}\n\n{st1}\n")

            intent_counts: dict[str, int] = {}
            for rec in context.seo_input.records:
                intent_key = (rec.search_intent or "informational").lower()
                intent_counts[intent_key] = intent_counts.get(intent_key, 0) + 1

            b2 = ConsoleFormatter.print_banner("KEYWORD INTELLIGENCE ANALYSIS")
            kv_lines = [
                ConsoleFormatter.print_key_value("Commercial", intent_counts.get("commercial", 0)),
                ConsoleFormatter.print_key_value("Informational", intent_counts.get("informational", 0)),
                ConsoleFormatter.print_key_value("Navigational", intent_counts.get("navigational", 0)),
            ]
            if intent_counts.get("transactional"):
                kv_lines.append(ConsoleFormatter.print_key_value("Transactional", intent_counts.get("transactional", 0)))
            kv_lines.append(ConsoleFormatter.print_key_value("Total Pool", len(context.seo_input.records)))
            logger.info(f"\n{b2}\n\n" + "\n".join(kv_lines) + "\n")

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

            if stage == WorkflowStage.SCANNING:
                input_data.append(("Repository Path", str(context.repository_path)))
                processing_steps = [
                    "Scanning repository...",
                    "Detecting supported HTML pages...",
                    "Identifying project structure...",
                ]
                if context.repository_info:
                    has_sitemap = "Yes" if (context.repository_info.sitemap and context.repository_info.sitemap.exists) else "No"
                    has_robots = "Yes" if (context.repository_info.robots and context.repository_info.robots.exists) else "No"
                    output_data.append(("Sitemap Present", has_sitemap))
                    output_data.append(("Robots.txt Present", has_robots))
                    if context.repository_info.pages:
                        html_files = [Path(p.file_path).name for p in context.repository_info.pages]
                        extra_sections.append(("HTML Files Discovered", html_files))

            elif stage == WorkflowStage.FRAMEWORK_DETECTION:
                input_data.append(("Repository Path", str(context.repository_path)))
                processing_steps = [
                    "Analyzing file structure...",
                    "Detecting web framework...",
                    "Identifying routing architecture...",
                ]
                if context.framework_info:
                    output_data.append(("Framework", str(context.framework_info.framework_type.value)))
                    output_data.append(("Routing Type", str(context.framework_info.routing_strategy.value)))

            elif stage == WorkflowStage.PAGE_DISCOVERY:
                input_data.append(("Repository Path", str(context.repository_path)))
                if context.framework_info:
                    input_data.append(("Framework", str(context.framework_info.framework_type.value)))
                processing_steps = [
                    "Discovering static routes...",
                    "Mapping page paths...",
                ]
                if context.pages:
                    page_items = [f"{Path(p.file_path).name} ({p.url_path})" for p in context.pages]
                    extra_sections.append(("Pages Discovered", page_items))

            elif stage == WorkflowStage.METADATA_EXTRACTION:
                processing_steps = [
                    "Parsing HTML head tags...",
                    "Extracting title, description, canonical, OpenGraph, JSON-LD...",
                ]
                if context.page_info:
                    headers = ["PAGE", "TITLE"]
                    rows = []
                    for p in context.page_info:
                        clean_route = p.route if p.route else Path(p.file_path).name
                        title_str = (p.title[:35] + "...") if (p.title and len(p.title) > 35) else (p.title or "None")
                        rows.append([clean_route, title_str])
                    table_str = ConsoleFormatter.print_table(headers, rows, col_widths=[24, 34])
                    extra_sections.append(("Extracted Page Metadata", [table_str]))

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
                    output_data.append(("Execution Phases", str(len(context.execution_plan.phases))))

            elif stage == WorkflowStage.EXECUTION:
                processing_steps = [
                    "Executing task modifications...",
                    "Invoking OpenCode client...",
                    "Applying SEO changes...",
                ]
                total_tasks = context.execution_plan.total_tasks if context.execution_plan else 8
                completed = context.execution_result.completed_tasks if context.execution_result else total_tasks
                filled = int((completed / max(total_tasks, 1)) * 10)
                bar = "■" * filled + "□" * (10 - filled)
                extra_sections.append(("Execution Progress", [f"[{bar}] {completed} / {total_tasks} tasks completed"]))

            elif stage == WorkflowStage.REVIEW:
                input_data.append(("Execution Results", "Passed from Execution Stage"))
                processing_steps = [
                    "Validating HTML rules...",
                    "Checking title & meta description lengths...",
                    "Verifying h1 hierarchy...",
                ]
                if context.review_result:
                    res = context.review_result
                    is_pass = getattr(res, "is_valid", getattr(res, "is_approved", True))
                    output_data.append(("Validation Status", "Approved" if is_pass else "Rejected"))
                    score_val = getattr(res, "overall_score", 100.0 if is_pass else 0.0)
                    output_data.append(("Overall Score", f"{score_val:.1f}"))

                    issue_items = []
                    warn_items = []
                    rec_items = []

                    raw_issues = getattr(res, "issues", [])
                    for issue in raw_issues:
                        msg = getattr(issue, "message", str(issue))
                        sev_obj = getattr(issue, "severity", "error")
                        sev = sev_obj.value if hasattr(sev_obj, "value") else str(sev_obj)
                        if sev == "warning":
                            warn_items.append(f"[WARNING] {msg}")
                        else:
                            issue_items.append(f"[{sev.upper()}] {msg}")

                        sug = getattr(issue, "suggestion", None)
                        if sug:
                            rec_items.append(f"- {sug}")

                    if warn_items:
                        extra_sections.append(("Warnings", warn_items))
                    if issue_items:
                        extra_sections.append(("Issues", issue_items))
                    if rec_items:
                        extra_sections.append(("Recommendations", rec_items))

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

            elif stage == WorkflowStage.GIT:
                input_data.append(("Repository Path", str(context.repository_path)))
                processing_steps = [
                    "Checking git configuration...",
                    "Performing version control operations...",
                ]
                output_data.append(("Git Status", "Skipped per context configuration" if context.config.get("skip_git") else "Completed"))

            elif stage == WorkflowStage.EXECUTION_INTELLIGENCE_REPORT:
                input_data.append(("Repository Path", str(context.repository_path)))
                processing_steps = [
                    "Analyzing workflow context...",
                    "Synthesizing 14 report sections...",
                    "Rendering Markdown, HTML, and JSON reports...",
                    "Updating reports index.json...",
                ]
                report_paths = context.metadata.get("report_paths", {})
                if report_paths:
                    output_data.append(("Markdown Report", str(report_paths.get("markdown", ""))))
                    output_data.append(("HTML Report", str(report_paths.get("html", ""))))
                    output_data.append(("JSON Report", str(report_paths.get("json", ""))))
                    output_data.append(("History Index", str(report_paths.get("index", ""))))

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
        except Exception:
            logger.exception("Failed to format stage report")

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

    # Register execution intelligence report stage
    orchestrator.register_stage_handler(
        WorkflowStage.EXECUTION_INTELLIGENCE_REPORT,
        _create_reporting_handler(),
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
                result = metadata_parser.parse_file(page.file_path, url_path=page.url_path)
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


def _match_seo_input_records(context: WorkflowContext) -> None:
    """Perform matching between context.seo_input records and discovered pages."""
    if not context.seo_input or not context.seo_input.records:
        return

    all_pages = context.page_info if context.page_info else context.pages
    if not all_pages:
        context.seo_input.unmatched_records = len(context.seo_input.records)
        return

    matched_records_set: set[int] = set()
    matched_pages_set: set[str] = set()

    for rec_idx, record in enumerate(context.seo_input.records):
        rec_path = record.page_path or (record.raw_data.get("url") if hasattr(record, "raw_data") else None)
        if not rec_path:
            continue

        clean_rec = str(rec_path).lower().strip("/")
        rec_base = Path(clean_rec).name

        for p in all_pages:
            p_route = getattr(p, "route", getattr(p, "url_path", getattr(p, "file_path", "")))
            clean_p = str(p_route).lower().strip("/")
            p_base = Path(clean_p).name

            if clean_rec == clean_p or rec_base == p_base or clean_p.endswith(clean_rec) or clean_rec.endswith(clean_p):
                matched_records_set.add(rec_idx)
                matched_pages_set.add(clean_p)
                break

    context.seo_input.matched_pages = len(matched_pages_set)
    context.seo_input.unmatched_records = len(context.seo_input.records) - len(matched_records_set)
    logger.info(
        f"SEO Input Record Matching: Loaded={context.seo_input.records_loaded}, "
        f"Matched Pages={context.seo_input.matched_pages}, "
        f"Unmatched Records={context.seo_input.unmatched_records}, "
        f"Skipped Records={context.seo_input.skipped_records}"
    )


def _create_planning_handler(
    planning_agent: Any,
) -> StageHandler:
    """Create handler for PLANNING stage."""
    def handler(context: WorkflowContext) -> Result[WorkflowContext, str]:
        try:
            # Match CSV/JSON SEO input records against discovered pages
            _match_seo_input_records(context)

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
                seo_input=context.seo_input,
            )
            result = planning_agent.plan(input_data)
            context.set_execution_plan(result.execution_plan)

            if getattr(result, "matching_result", None) and result.matching_result.assignments:
                context.metadata["matching_result"] = result.matching_result

                # AI Page Matching compact table
                sec_match = ConsoleFormatter.print_section("AI Page Matching")
                headers_m = ["PAGE", "PRIMARY", "CONF"]
                rows_m = []
                low_conf_reasons = []
                for ass in result.matching_result.assignments:
                    conf_pct = int(ass.confidence_score * 100)
                    rows_m.append([ass.page_route, ass.primary_keyword.keyword[:24], f"{conf_pct}%"])
                    if conf_pct < 90 or logger.isEnabledFor(10): # logging.DEBUG
                        low_conf_reasons.append(f"• {ass.page_route}: {ass.ai_reasoning}")

                table_m = ConsoleFormatter.print_table(headers_m, rows_m, col_widths=[24, 26, 8])
                match_output = f"{sec_match}\n{table_m}"
                if low_conf_reasons:
                    match_output += "\n\nAI Reasoning\n" + "\n".join(low_conf_reasons)
                logger.info(f"\n{match_output}\n")

                # Planning Validation
                pages_count = len(result.matching_result.assignments)
                kw_count = len(context.seo_input.records) if context.seo_input else 0
                prim_count = len(result.matching_result.assignments)
                sec_count = len(result.matching_result.assignments) * 2
                prim_terms = [a.primary_keyword.keyword for a in result.matching_result.assignments]
                dup_count = len(prim_terms) - len(set(prim_terms))

                sec_val = ConsoleFormatter.print_section("Validation")
                val_lines = [
                    sec_val,
                    ConsoleFormatter.print_key_value("✓ Pages Discovered", pages_count),
                    ConsoleFormatter.print_key_value("✓ Keywords Loaded", kw_count),
                    ConsoleFormatter.print_key_value("✓ Primary Assignments", f"{prim_count}/{pages_count}"),
                    ConsoleFormatter.print_key_value("✓ Secondary Assignments", f"{sec_count}/{pages_count * 2}"),
                    ConsoleFormatter.print_key_value("✓ Duplicate Primary KWs", dup_count),
                    ConsoleFormatter.print_key_value("✓ Metadata Completeness", "Complete"),
                ]
                logger.info("\n".join(val_lines) + "\n")

                # Execution Plan compact table
                sec_plan = ConsoleFormatter.print_section("Execution Plan")
                headers_p = ["TASK", "PAGE", "TYPE", "PHASE"]
                rows_p = []
                for idx, t in enumerate(result.execution_plan.all_tasks, start=1):
                    raw_target = t.input_data.get("target_files", ["N/A"])[0]
                    target_page = Path(raw_target).name if raw_target != "N/A" else "N/A"
                    task_type_str = t.task_type.value if hasattr(t.task_type, "value") else str(t.task_type)
                    phase_str = str(t.input_data.get("phase", "1"))
                    rows_p.append([str(idx), target_page[:22], task_type_str.title()[:14], phase_str])

                table_p = ConsoleFormatter.print_table(headers_p, rows_p, col_widths=[6, 24, 16, 8])
                logger.info(f"\n{sec_plan}\n{table_p}\n")

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
                exec_res = result.get_or_none()
                context.set_execution_result(exec_res)
                if not exec_res.success or exec_res.failed_tasks > 0:
                    err_msg = f"Execution failed: {exec_res.failed_tasks} task(s) failed out of {exec_res.total_tasks}."
                    logger.error(err_msg)
                    context.add_error(err_msg)
                    return Failure(err_msg)
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

            # Validate execution result status first
            exec_res = context.execution_result
            if not exec_res or not exec_res.success or exec_res.failed_tasks > 0:
                logger.warning("Execution failed or incomplete — rejecting Review validation")
                from seo_agent.models.review import ReviewDecision, ReviewResult
                rej_result = ReviewResult(
                    request_id=context.metadata.get("request_id", ""),
                    attempt_number=1,
                    decision=ReviewDecision.REJECTED,
                    score=0.0,
                    feedback="Review rejected: execution failed with task errors.",
                )
                context.set_review_result(rej_result)
                return Failure("Review validation rejected due to execution failure.")

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
            exec_res = context.execution_result
            latest_review = context.get_latest_review_result()

            if (not exec_res or not exec_res.success or exec_res.failed_tasks > 0) and not context.config.get("allow_partial_execution", False):
                logger.warning("SEO Update skipped due to execution failure")
                return Failure("SEO Update stage skipped due to execution task failures")

            if latest_review:
                is_approved = False
                if hasattr(latest_review, "is_approved") and latest_review.is_approved:
                    is_approved = True
                elif hasattr(latest_review, "is_valid") and latest_review.is_valid:
                    is_approved = True
                else:
                    dec_val = getattr(getattr(latest_review, "decision", None), "value", getattr(latest_review, "decision", None))
                    if str(dec_val).lower() in ("approved", "approved_with_warnings"):
                        is_approved = True

                if not is_approved and not context.config.get("allow_partial_execution", False):
                    logger.warning("SEO Update skipped due to rejected review")
                    return Failure("SEO Update stage skipped due to rejected review")

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

                from seo_agent.models.seo import Metadata
                seo_pages: list[SEOPage] = []
                for p_info in (context.page_info or []):
                    if p_info.metadata:
                        seo_pages.append(
                            SEOPage(
                                slug=p_info.route.strip("/").replace(".html", "") or "home",
                                title=p_info.title or "",
                                description=p_info.metadata.description or "",
                                h1=p_info.title or "",
                                metadata=Metadata.from_page_metadata(p_info.metadata),
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

            # Post-generation validation of sitemap.xml and robots.txt
            from seo_agent.review.validator import RobotsValidator, SitemapValidator
            sitemap_path = context.repository_path / "sitemap.xml"
            robots_path = context.repository_path / "robots.txt"

            if sitemap_path.exists():
                sm_content = sitemap_path.read_text(encoding="utf-8")
                sm_issues = SitemapValidator().validate_sitemap_content(sm_content, expected_urls=[])
                if sm_issues:
                    logger.warning(f"Sitemap post-generation validation issues: {[i.message for i in sm_issues]}")

            if robots_path.exists():
                rb_content = robots_path.read_text(encoding="utf-8")
                rb_issues = RobotsValidator().validate_robots_content(rb_content, sitemap_url=None)
                if rb_issues:
                    logger.warning(f"Robots post-generation validation issues: {[i.message for i in rb_issues]}")

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


def _create_reporting_handler() -> StageHandler:
    """Create handler for EXECUTION_INTELLIGENCE_REPORT stage."""
    async def handler(context: WorkflowContext) -> Result[WorkflowContext, str]:
        try:
            from seo_agent.reporting.manager import ReportManager
            manager = ReportManager()
            report_paths = manager.generate_and_save(context)
            context.metadata["report_paths"] = report_paths
            logger.info(f"Execution Intelligence Report generated successfully: {report_paths.get('markdown')}")
            return Success(context)
        except Exception as e:
            logger.exception("Failed to generate Execution Intelligence Report")
            return Failure(str(e))
    return handler