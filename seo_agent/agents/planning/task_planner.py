"""Execution plan generation.

This module generates an ExecutionPlan with Task objects from the analysis results.
Each Task specifies task type, target files, inputs, outputs, dependencies, priority, and complexity.

It MUST NOT:
- Modify files
- Communicate with OpenCode
- Perform Git operations
- Review generated code
- Make AI/LLM calls

It ONLY generates task definitions for the execution agent.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from pathlib import Path

from seo_agent.core.logging import get_logger
from seo_agent.models.repository import PageInfo
from seo_agent.models.seo import Keyword, Metadata, SEOPage
from seo_agent.models.task import (
    Complexity,
    ExecutionPlan,
    Phase,
    Task,
    TaskDependency,
    TaskPriority,
    TaskStatus,
    TaskType,
)

from .keyword_selector import KeywordSelectionResult, KeywordSelector
from .repository_analyzer import RepositoryAnalysis, RepositoryAnalyzer

if TYPE_CHECKING:
    from seo_agent.models.repository import RepositoryInfo
    from seo_agent.models.seo_input import SEOInputCollection

logger = get_logger(__name__)


class TaskGroup(Enum):
    """Logical grouping for related tasks."""

    METADATA = "metadata"
    CONTENT = "content"
    TECHNICAL = "technical"
    STRUCTURE = "structure"


@dataclass(frozen=True)
class TaskTemplate:
    """Template for generating tasks.

    Attributes:
        task_type: Type of task to create.
        target_files: Files to operate on.
        inputs: Required inputs for the task.
        outputs: Expected outputs from the task.
        priority: Task priority.
        complexity: Task complexity.
        phase: Phase in which task should execute.
        group: Logical grouping.
        description: Human-readable description.
    """

    task_type: TaskType
    target_files: tuple[str, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    priority: TaskPriority
    complexity: Complexity
    phase: str
    group: TaskGroup
    description: str


class TaskPlanner:
    """Generates execution plans from analysis results.

    This planner consumes:
    - RepositoryAnalysis from RepositoryAnalyzer
    - KeywordSelectionResult from KeywordSelector

    And produces an ExecutionPlan with Task objects for the execution agent.

    It performs analysis only - no file modifications, no AI calls,
    no Git operations, no code review.
    """

    def __init__(
        self,
        max_tasks_per_phase: int = 20,
        enable_parallel_execution: bool = True,
    ) -> None:
        """Initialize the task planner.

        Args:
            max_tasks_per_phase: Maximum tasks per phase.
            enable_parallel_execution: Whether to enable parallel task execution.
        """
        self._logger = get_logger(__name__)
        self._max_tasks_per_phase = max_tasks_per_phase
        self._enable_parallel_execution = enable_parallel_execution

    def plan(
        self,
        request_id: str,
        repository_analysis: RepositoryAnalysis,
        keyword_selection: KeywordSelectionResult,
        repository_path: Path,
        seo_input: Any | None = None,
        matching_result: Any | None = None,
    ) -> ExecutionPlan:
        """Generate an ExecutionPlan with Task objects from analysis.

        Args:
            request_id: Request identifier for tracking.
            repository_analysis: Repository analysis results.
            keyword_selection: Keyword selection results.
            repository_path: Path to the repository.
            seo_input: Optional normalized SEO input collection.
            matching_result: Optional AI Page-Keyword matching results.

        Returns:
            ExecutionPlan ready for the execution agent.
        """
        self._logger.debug(
            f"generating_execution_plan: opportunities={len(repository_analysis.seo_opportunities)}, "
            f"selected_keywords={keyword_selection.total_selected_count}"
        )

        # Generate task templates
        templates = self._generate_task_templates(
            repository_analysis,
            keyword_selection,
        )

        # Convert templates to tasks
        tasks = self._create_tasks(templates, repository_path, seo_input=seo_input, matching_result=matching_result)

        # Create dependencies
        tasks = self._create_dependencies(tasks)

        # Create phases
        phases = self._create_phases(tasks)

        # Build execution plan
        plan = ExecutionPlan(
            request_id=request_id,
            phases=tuple(phases),
            estimated_duration_seconds=self._estimate_duration(tasks) * 60,
        )

        self._logger.debug(
            f"execution_plan_generated: total_tasks={len(tasks)}, phases={len(phases)}"
        )

        return plan

    def _generate_task_templates(
        self,
        analysis: RepositoryAnalysis,
        keywords: KeywordSelectionResult,
    ) -> list[TaskTemplate]:
        """Generate task templates from analysis.

        Args:
            analysis: Repository analysis results.
            keywords: Keyword selection results.

        Returns:
            List of task templates.
        """
        templates: list[TaskTemplate] = []

        # Metadata optimization tasks
        templates.extend(self._generate_metadata_tasks(analysis, keywords))

        # Page generation tasks
        templates.extend(self._generate_page_tasks(analysis, keywords))

        # Technical SEO tasks
        templates.extend(self._generate_technical_tasks(analysis))

        # Structure tasks
        templates.extend(self._generate_structure_tasks(analysis))

        return templates

    def _generate_metadata_tasks(
        self,
        analysis: RepositoryAnalysis,
        keywords: KeywordSelectionResult,
    ) -> list[TaskTemplate]:
        """Generate metadata optimization tasks.

        Args:
            analysis: Repository analysis.
            keywords: Keyword selection.

        Returns:
            List of metadata task templates.
        """
        templates: list[TaskTemplate] = []

        self._logger.debug(
            f"planning_trace_metadata: missing_metadata_count={len(analysis.missing_metadata)}, "
            f"existing_seo_assets_count={len(analysis.existing_seo_assets)}"
        )

        processed_targets: set[tuple[str, str]] = set()

        # Tasks for pages with missing metadata
        for missing in analysis.missing_metadata:
            key = (missing.page_route, TaskType.METADATA_UPDATE.value)
            if key in processed_targets:
                continue
            processed_targets.add(key)

            templates.append(TaskTemplate(
                task_type=TaskType.METADATA_UPDATE,
                target_files=(missing.page_route,),
                inputs=(
                    f"page:{missing.page_route}",
                    f"keywords:{','.join(kw.keyword.term for kw in keywords.selected_keywords[:5])}",
                ),
                outputs=(
                    f"metadata:{missing.page_route}",
                    f"optimized_keywords:{missing.page_route}",
                ),
                priority=TaskPriority.HIGH,
                complexity=Complexity.LOW,
                phase="metadata",
                group=TaskGroup.METADATA,
                description=f"Optimize metadata for {missing.page_route}",
            ))

        # Tasks for metadata opportunities identified by RepositoryAnalyzer
        metadata_opp_types = {
            "missing_title",
            "missing_description",
            "missing_og_tags",
            "missing_structured_data",
            "no_faq_schema",
            "no_article_schema",
            "missing_alt_tags",
        }
        for opportunity in analysis.seo_opportunities:
            if opportunity.opportunity_type.value in metadata_opp_types:
                key = (opportunity.page_route, TaskType.METADATA_UPDATE.value)
                if key in processed_targets:
                    continue
                processed_targets.add(key)

                templates.append(TaskTemplate(
                    task_type=TaskType.METADATA_UPDATE,
                    target_files=(opportunity.page_route,),
                    inputs=(
                        f"page:{opportunity.page_route}",
                        f"keywords:{','.join(kw.keyword.term for kw in keywords.selected_keywords[:5])}",
                        f"opportunity:{opportunity.opportunity_type.value}",
                    ),
                    outputs=(
                        f"metadata:{opportunity.page_route}",
                        f"optimized_keywords:{opportunity.page_route}",
                    ),
                    priority=self._map_opportunity_priority(opportunity.priority),
                    complexity=Complexity.LOW,
                    phase="metadata",
                    group=TaskGroup.METADATA,
                    description=f"Fix {opportunity.opportunity_type.value} on {opportunity.page_route}",
                ))

        self._logger.debug(f"metadata_tasks_created: count={len(templates)}")
        return templates

    def _resolve_target_file(self, route_or_path: str, repository_path: Path) -> str:
        """Resolve a URL route or relative path to an existing physical relative file path.

        Args:
            route_or_path: URL route (e.g. "/about") or relative path.
            repository_path: Path to the repository root.

        Returns:
            Relative physical file path (e.g. "about.html").
        """
        cleaned = route_or_path.lstrip("/")
        if not cleaned or cleaned == "/":
            return "index.html"

        direct_path = repository_path / cleaned
        if direct_path.is_file():
            return cleaned

        html_path = repository_path / f"{cleaned}.html"
        if html_path.is_file():
            return f"{cleaned}.html"

        index_path = repository_path / cleaned / "index.html"
        if index_path.is_file():
            return f"{cleaned}/index.html"

        return cleaned if "." in cleaned else f"{cleaned}.html"

    def _generate_page_tasks(
        self,
        analysis: RepositoryAnalysis,
        keywords: KeywordSelectionResult,
    ) -> list[TaskTemplate]:
        """Generate page generation tasks.

        Args:
            analysis: Repository analysis.
            keywords: Keyword selection.

        Returns:
            List of page task templates.
        """
        templates: list[TaskTemplate] = []

        self._logger.debug(
            f"planning_trace_page_tasks: seo_opportunities_count={len(analysis.seo_opportunities)}, "
            f"critical_keywords_count={len(keywords.critical_keywords)}"
        )

        # Tasks for LOW_CONTENT_QUALITY opportunities
        for opportunity in analysis.seo_opportunities:
            if opportunity.opportunity_type.value in ("low_content_quality", "new_page", "content_gap"):
                # NOTE / TODO: "new_page" and "content_gap" are legacy strings preserved for future content gap analyzers.
                templates.append(TaskTemplate(
                    task_type=TaskType.SEO_PAGE_GENERATION,
                    target_files=(opportunity.page_route,),
                    inputs=(
                        f"route:{opportunity.page_route}",
                        f"keywords:{opportunity.description}",
                        f"intent:informational",
                    ),
                    outputs=(
                        f"generated_page:{opportunity.page_route}",
                        f"metadata:{opportunity.page_route}",
                    ),
                    priority=self._map_opportunity_priority(opportunity.priority),
                    complexity=Complexity.HIGH,
                    phase="content",
                    group=TaskGroup.CONTENT,
                    description=f"Generate page for: {opportunity.description}",
                ))

        # Tasks for keyword-targeted pages
        for kw_score in keywords.critical_keywords[:10]:
            route = self._keyword_to_route(kw_score.keyword.term)
            templates.append(TaskTemplate(
                task_type=TaskType.SEO_PAGE_GENERATION,
                target_files=(route,),
                inputs=(
                    f"route:{route}",
                    f"keyword:{kw_score.keyword.term}",
                    f"intent:{kw_score.keyword.intent or 'informational'}",
                ),
                outputs=(
                    f"generated_page:{route}",
                    f"metadata:{route}",
                ),
                priority=TaskPriority.HIGH,
                complexity=Complexity.MEDIUM,
                phase="content",
                group=TaskGroup.CONTENT,
                description=f"Generate page for keyword: {kw_score.keyword.term}",
            ))

        self._logger.debug(f"page_tasks_created: count={len(templates)}")
        return templates

    def _generate_technical_tasks(
        self,
        analysis: RepositoryAnalysis,
    ) -> list[TaskTemplate]:
        """Generate technical SEO tasks.

        Args:
            analysis: Repository analysis.

        Returns:
            List of technical task templates.
        """
        templates: list[TaskTemplate] = []

        has_sitemap = any(a.asset_type == "sitemap" for a in analysis.existing_seo_assets)
        has_robots = any(a.asset_type == "robots" for a in analysis.existing_seo_assets)
        self._logger.debug(
            f"planning_trace_technical_tasks: has_sitemap={has_sitemap}, has_robots={has_robots}"
        )

        # Sitemap tasks
        if not has_sitemap:
            templates.append(TaskTemplate(
                task_type=TaskType.SITEMAP_UPDATE,
                target_files=("sitemap.xml",),
                inputs=("repository:pages",),
                outputs=("sitemap.xml",),
                priority=TaskPriority.HIGH,
                complexity=Complexity.LOW,
                phase="technical",
                group=TaskGroup.TECHNICAL,
                description="Generate sitemap.xml",
            ))

        # Robots.txt tasks
        if not has_robots:
            templates.append(TaskTemplate(
                task_type=TaskType.ROBOTS_UPDATE,
                target_files=("robots.txt",),
                inputs=("repository:config",),
                outputs=("robots.txt",),
                priority=TaskPriority.NORMAL,
                complexity=Complexity.LOW,
                phase="technical",
                group=TaskGroup.TECHNICAL,
                description="Generate robots.txt",
            ))

        # Internal linking tasks (check both 'missing_internal_links' and legacy 'internal_linking')
        for opportunity in analysis.seo_opportunities:
            if opportunity.opportunity_type.value in ("missing_internal_links", "internal_linking"):
                templates.append(TaskTemplate(
                    task_type=TaskType.INTERNAL_LINKING,
                    target_files=(opportunity.page_route,),
                    inputs=(
                        f"source:{opportunity.page_route}",
                        f"targets:{opportunity.page_route}",
                    ),
                    outputs=("updated_links",),
                    priority=TaskPriority.NORMAL,
                    complexity=Complexity.LOW,
                    phase="technical",
                    group=TaskGroup.TECHNICAL,
                    description=f"Add internal links for {opportunity.page_route}",
                ))

        self._logger.debug(f"technical_tasks_created: count={len(templates)}")
        return templates

    def _generate_structure_tasks(
        self,
        analysis: RepositoryAnalysis,
    ) -> list[TaskTemplate]:
        """Generate structure-related tasks.

        Args:
            analysis: Repository analysis.

        Returns:
            List of structure task templates.
        """
        templates: list[TaskTemplate] = []

        # URL structure optimization (preserved for future URL structure analyzer)
        # TODO: Connect to future UrlStructureAnalyzer when opportunity type 'url_structure' is produced.
        for opportunity in analysis.seo_opportunities:
            if opportunity.opportunity_type.value == "url_structure":
                templates.append(TaskTemplate(
                    task_type=TaskType.VALIDATION,
                    target_files=(opportunity.page_route,),
                    inputs=(
                        f"current_urls:{opportunity.page_route}",
                        f"recommended:{opportunity.page_route}",
                    ),
                    outputs=("redirect_map",),
                    priority=TaskPriority.NORMAL,
                    complexity=Complexity.MEDIUM,
                    phase="structure",
                    group=TaskGroup.STRUCTURE,
                    description=f"Optimize URL structure: {opportunity.description}",
                ))

        return templates

    def _create_tasks(
        self,
        templates: list[TaskTemplate],
        repository_path: Path,
        seo_input: Any | None = None,
        matching_result: Any | None = None,
    ) -> list[Task]:
        """Convert templates to Task objects.

        Args:
            templates: Task templates.
            repository_path: Repository path.
            seo_input: Optional SEO input collection.
            matching_result: Optional AI Page-Keyword matching results.

        Returns:
            List of Task objects.
        """
        tasks: list[Task] = []
        task_id = 1

        for template in templates:
            if len(tasks) >= self._max_tasks_per_phase:
                self._logger.warning(
                    f"max_tasks_reached: max_tasks={self._max_tasks_per_phase}, "
                    f"skipped={len(templates) - len(tasks)}"
                )
                break

            # Build input_data in the schema the executor expects
            input_data = self._build_input_data(template, repository_path, seo_input=seo_input, matching_result=matching_result)

            desc = template.description
            if "primary_keyword" in input_data:
                target_file = input_data.get("target_files", [resolved_file if 'resolved_file' in locals() else ""])[0]
                sec_kws = input_data.get("secondary_keywords", [])
                desc = f"Phase 1: Optimize {target_file} for primary keyword '{input_data['primary_keyword']}' and secondary keywords [{', '.join(sec_kws)}]"

            task = Task(
                task_id=f"task-{task_id:04d}",
                task_type=template.task_type,
                description=desc,
                status=TaskStatus.PENDING,
                priority=template.priority,
                dependencies=tuple(),
                input_data=input_data,
                output_data={"outputs": list(template.outputs)},
            )
            tasks.append(task)
            task_id += 1

        # Add tasks for unassigned keyword actions if generate_seo_page requested
        if matching_result and getattr(matching_result, "unassigned_actions", None):
            for action in matching_result.unassigned_actions:
                if action.action == "generate_seo_page" and action.target_slug:
                    target_file = action.target_slug
                    abs_path = str(repository_path / target_file)
                    gen_input = {
                        "target_files": [target_file],
                        "file_path": abs_path,
                        "workspace_path": str(repository_path),
                        "complexity": "medium",
                        "phase": "page_generation",
                        "primary_keyword": action.keyword_record.keyword,
                        "instructions": (
                            f"Generate a new SEO landing page '{target_file}' for keyword '{action.keyword_record.keyword}'. "
                            f"Reasoning: {action.reasoning}"
                        ),
                    }
                    gen_task = Task(
                        task_id=f"task-{task_id:04d}",
                        task_type=TaskType.SEO_PAGE_GENERATION,
                        description=f"Generate new SEO landing page {target_file} for '{action.keyword_record.keyword}'",
                        status=TaskStatus.PENDING,
                        priority=TaskPriority.HIGH,
                        dependencies=tuple(),
                        input_data=gen_input,
                        output_data={"outputs": [target_file]},
                    )
                    tasks.append(gen_task)
                    task_id += 1

        return tasks

    def _parse_inputs(
        self,
        inputs: tuple[str, ...],
    ) -> dict[str, str]:
        """Parse input strings into dict.

        Args:
            inputs: Input strings like "key:value".

        Returns:
            Dict of inputs.
        """
        result = {}
        for inp in inputs:
            if ":" in inp:
                key, value = inp.split(":", 1)
                result[key] = value
            else:
                result[inp] = ""
        return result

    def _build_input_data(
        self,
        template: TaskTemplate,
        repository_path: Path,
        seo_input: Any | None = None,
        matching_result: Any | None = None,
    ) -> dict[str, Any]:
        """Build executor-compatible input_data from a TaskTemplate.

        Different task types require different input_data schemas:
        - METADATA_UPDATE: needs 'instructions' (content is AI-generated
          at execution time; the planner cannot make LLM calls).
        - SITEMAP/ROBOTS/LINKING: needs 'edits' (pre-computed content).
        - SEO_PAGE_GENERATION: needs 'file_path' + 'content'.
        - Others: needs 'instructions' (generic).

        Args:
            template: The task template to convert.
            repository_path: Path to the repository.
            seo_input: Optional SEO input collection.
            matching_result: Optional AI Page-Keyword matching results.

        Returns:
            Dictionary of input data for the executor.
        """
        target_raw = template.target_files[0] if template.target_files else ""
        resolved_file = self._resolve_target_file(target_raw, repository_path)
        abs_file_path = str(repository_path / resolved_file)

        # Common planner metadata (always included)
        base: dict[str, Any] = {
            "target_files": [resolved_file],
            "file_path": abs_file_path,
            "workspace_path": str(repository_path),
            "complexity": template.complexity.value,
            "phase": template.phase,
        }

        # Check for AI Page-Keyword assignment match
        assignment_match = None
        if matching_result and getattr(matching_result, "assignments", None):
            def norm(p: str) -> tuple[str, str]:
                c = str(p).lower().strip("/")
                if not c or c in ("index", "index.html"):
                    return ("index.html", "index")
                return (c, Path(c).stem)

            target_norm, target_stem = norm(resolved_file)
            for ass in matching_result.assignments:
                p_norm, p_stem = norm(ass.page_route)
                if target_norm == p_norm or target_stem == p_stem:
                    assignment_match = ass
                    break

        if assignment_match:
            prim = assignment_match.primary_keyword
            sec_kw_objs = assignment_match.secondary_keywords or []
            sec_kw_terms = [s.keyword for s in sec_kw_objs]
            sec1_term = sec_kw_terms[0] if len(sec_kw_terms) > 0 else prim.keyword
            sec2_term = sec_kw_terms[1] if len(sec_kw_terms) > 1 else sec1_term

            base["primary_keyword"] = prim.keyword
            base["secondary_keywords"] = sec_kw_terms
            base["confidence_score"] = assignment_match.confidence_score
            base["ai_reasoning"] = assignment_match.ai_reasoning

            title_val = prim.meta_title or f"{prim.keyword} | {sec1_term} Solutions"
            desc_val = prim.meta_description or f"Leading {prim.keyword} services. Specialized in {sec1_term} and {sec2_term}."
            h2_val = prim.h2_outlines or ([sec1_term, sec2_term, "Key Benefits & Features"] if sec_kw_terms else ["Overview", "Key Features"])

            base["target_metadata"] = {
                "primary_keyword": prim.keyword,
                "secondary_keywords": sec_kw_terms,
                "title": title_val,
                "description": desc_val,
                "h1": prim.keyword,
                "h2_outlines": h2_val,
                "canonical": prim.canonical,
                "og_title": prim.og_title or title_val,
                "og_description": prim.og_description or desc_val,
                "twitter_card": prim.twitter_card or "summary_large_image",
                "structured_data": prim.structured_data,
                "internal_links": prim.lsi_keywords,
            }

            sec_kws_str = ", ".join(f'"{kw}"' for kw in sec_kw_terms)
            base["instructions"] = (
                f"Update the SEO metadata in the HTML file '{resolved_file}' (located at '{abs_file_path}') "
                f"using the AI Page-Keyword Semantic Matching assignments:\n"
                f"- Target Page: {resolved_file}\n"
                f"- Primary Keyword: \"{prim.keyword}\"\n"
                f"- Secondary Keywords: [{sec_kws_str}]\n"
                f"- Confidence Score: {int(assignment_match.confidence_score * 100)}%\n"
                f"- Assignment Reasoning: {assignment_match.ai_reasoning}\n"
                f"- Title Tag: \"{title_val}\"\n"
                f"- Meta Description: \"{desc_val}\"\n"
                f"- Primary H1 Heading: \"{prim.keyword}\"\n"
                f"- H2 Outlines: {', '.join(h2_val)}\n"
                f"- Canonical URL: \"{prim.canonical or ''}\"\n"
                f"- Social Metadata: OpenGraph (og:title, og:description) & Twitter Cards\n"
                f"- Structured Data Schema: Organization / Product Schema\n"
                f"- Image Alt Tags: Optimized for '{prim.keyword}' and '{sec1_term}'"
            )
            return base

        # Match entry from seo_input if present
        entry_match = None
        if seo_input and getattr(seo_input, "records", None):
            clean_target = str(resolved_file).lower().strip("/")
            target_base = Path(clean_target).name
            for rec in seo_input.records:
                cand = getattr(rec, "page_path", None) or getattr(rec, "url", None)
                if not cand:
                    continue
                clean_cand = str(cand).lower().strip("/")
                cand_base = Path(clean_cand).name
                if clean_target == clean_cand or target_base == cand_base or clean_target.endswith(clean_cand) or clean_cand.endswith(clean_target):
                    entry_match = rec
                    break

        if entry_match:
            base["target_metadata"] = {
                "title": entry_match.title,
                "description": entry_match.description,
                "canonical": entry_match.canonical,
                "keywords": entry_match.keywords,
                "h1": entry_match.h1,
                "og_title": entry_match.og_title,
                "og_description": entry_match.og_description,
                "og_image": entry_match.og_image,
                "twitter_card": entry_match.twitter_card,
                "twitter_title": entry_match.twitter_title,
                "twitter_description": entry_match.twitter_description,
                "twitter_image": entry_match.twitter_image,
                "structured_data": entry_match.structured_data,
                "internal_links": entry_match.internal_link_suggestions,
            }

        # Parse template inputs for planning context
        parsed = self._parse_inputs(template.inputs)

        if template.task_type == TaskType.METADATA_UPDATE:
            keywords = parsed.get("keywords", "")
            if entry_match:
                details = []
                if entry_match.title:
                    details.append(f"- Title Tag: \"{entry_match.title}\"")
                if entry_match.description:
                    details.append(f"- Meta Description: \"{entry_match.description}\"")
                if entry_match.canonical:
                    details.append(f"- Canonical URL: \"{entry_match.canonical}\"")
                if entry_match.h1:
                    details.append(f"- H1 Heading: \"{entry_match.h1}\"")
                if entry_match.og_title:
                    details.append(f"- OpenGraph Title: \"{entry_match.og_title}\"")
                if entry_match.og_image:
                    details.append(f"- OpenGraph Image: \"{entry_match.og_image}\"")
                if entry_match.twitter_card:
                    details.append(f"- Twitter Card: \"{entry_match.twitter_card}\"")
                if entry_match.keywords:
                    details.append(f"- Target Keywords: {', '.join(entry_match.keywords)}")
                if entry_match.internal_link_suggestions:
                    details.append(f"- Internal Link Suggestions: {', '.join(entry_match.internal_link_suggestions)}")

                base["instructions"] = (
                    f"Update the SEO metadata in the HTML file '{resolved_file}' (located at '{abs_file_path}') "
                    f"using the following explicit target CSV/input values:\n" + "\n".join(details)
                )
            else:
                base["instructions"] = (
                    f"Update the SEO metadata in the HTML file '{resolved_file}' (located at '{abs_file_path}'). "
                    f"Target keywords: {keywords}. "
                    f"Ensure the file has an optimized title tag, meta description, "
                    f"Open Graph tags (og:title, og:description, og:image), Twitter Card tags, "
                    f"canonical link tag (<link rel=\"canonical\">), and structured data as appropriate for this page."
                )

        elif template.task_type == TaskType.SITEMAP_UPDATE:
            base["instructions"] = (
                f"Generate or update sitemap.xml in '{repository_path}' to include all discoverable pages and SEO routes."
            )

        elif template.task_type == TaskType.ROBOTS_UPDATE:
            base["instructions"] = (
                f"Generate or update robots.txt in '{repository_path}' with appropriate crawl rules and a sitemap link."
            )

        elif template.task_type == TaskType.INTERNAL_LINKING:
            import os
            source = parsed.get("source", target_raw)
            resolved_source = self._resolve_target_file(source, repository_path)
            abs_source_path = str(repository_path / resolved_source)
            base["target_files"] = [resolved_source]
            base["file_path"] = abs_source_path

            # Define standard candidate pages and anchor text
            standard_candidates = [
                ("solutions.html", "AI Recruitment Solutions"),
                ("pricing.html", "Pricing & Plans"),
                ("about.html", "About Us"),
                ("contact.html", "Contact Us"),
                ("index.html", "Home"),
            ]

            source_dir = os.path.dirname(resolved_source)
            norm_source = os.path.normpath(resolved_source)

            # Build pre-computed HTML link tags in Python
            link_tags: list[str] = []
            for target_rel, anchor in standard_candidates:
                if os.path.normpath(target_rel) == norm_source:
                    continue
                rel_url = os.path.relpath(target_rel, source_dir) if source_dir else target_rel
                link_tags.append(f'<a href="{rel_url}">{anchor}</a>')
                if len(link_tags) >= 2:
                    break

            base["precomputed_links"] = link_tags
            links_formatted = "\n".join(f"- {link}" for link in link_tags)

            base["instructions"] = (
                f"Insert the following pre-computed internal links into the HTML file '{resolved_source}' (located at '{abs_source_path}'):\n\n"
                f"Supplied Links to Insert:\n{links_formatted}\n\n"
                f"Strict Execution Rules:\n"
                f"1. Modify ONLY the file '{resolved_source}'. Do NOT search, list, inspect, or read any other files in the workspace.\n"
                f"2. Insert the supplied link tags into appropriate text paragraphs within the <body> of '{resolved_source}'.\n"
                f"3. Do NOT search for target pages or determine relevant pages; use ONLY the exact supplied links above.\n"
                f"4. Do NOT rewrite or remove existing page layout, CSS, or tags.\n"
                f"5. Apply the edit and stop execution immediately."
            )

        elif template.task_type == TaskType.SEO_PAGE_GENERATION:
            base["file_path"] = abs_file_path
            base["content"] = ""
            base["instructions"] = template.description

        else:
            base.update(parsed)
            base["instructions"] = template.description

        return base

    def _create_dependencies(
        self,
        tasks: list[Task],
    ) -> list[Task]:
        """Create dependencies between tasks.

        Args:
            tasks: Tasks to add dependencies to.

        Returns:
            New list of Tasks with dependencies (Task is immutable).
        """
        if not self._enable_parallel_execution:
            return tasks

        # Group tasks by description prefix (part before ":")
        groups: dict[str, list[Task]] = {}
        for task in tasks:
            group_key = task.description.split(":")[0] if ":" in task.description else "default"
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(task)

        # Build new tasks with dependencies using dataclasses.replace
        new_tasks: list[Task] = []
        task_index: dict[str, int] = {}  # Map task_id to index in new_tasks

        for task in tasks:
            task_index[task.task_id] = len(new_tasks)
            new_tasks.append(task)

        # Update dependencies for tasks that depend on previous in group
        for group_tasks in groups.values():
            for i, task in enumerate(group_tasks):
                if i > 0:
                    prev_task = group_tasks[i - 1]
                    idx = task_index[task.task_id]
                    new_tasks[idx] = replace(
                        new_tasks[idx],
                        dependencies=(TaskDependency(
                            task_id=prev_task.task_id,
                            dependency_type="sequential",
                        ),)
                    )

        return new_tasks

    def _create_phases(
        self,
        tasks: list[Task],
    ) -> tuple[Phase, ...]:
        """Create phases from tasks.

        Args:
            tasks: All tasks.

        Returns:
            Tuple of phases in execution order.
        """
        # Define the four ordered phases
        phase_order = ["metadata", "content", "technical", "structure"]
        phase_names = {
            "metadata": "Metadata",
            "content": "Content",
            "technical": "Technical",
            "structure": "Structure",
        }
        phase_descriptions = {
            "metadata": "Metadata optimization tasks",
            "content": "Content creation and optimization tasks",
            "technical": "Technical SEO tasks",
            "structure": "Site structure and navigation tasks",
        }

        # Group tasks by phase from input_data
        phase_tasks: dict[str, list[Task]] = {phase: [] for phase in phase_order}
        for task in tasks:
            phase_key = task.input_data.get("phase", "metadata")
            if phase_key in phase_tasks:
                phase_tasks[phase_key].append(task)
            else:
                # Default to metadata for unknown phases
                phase_tasks["metadata"].append(task)

        # Create Phase objects in order
        phases: list[Phase] = []
        for i, phase_key in enumerate(phase_order):
            phase = Phase(
                phase_id=f"phase-{i + 1:04d}",
                name=phase_names[phase_key],
                description=phase_descriptions[phase_key],
                tasks=tuple(phase_tasks[phase_key]),
            )
            phases.append(phase)

        return tuple(phases)

    def _estimate_duration(
        self,
        tasks: list[Task],
    ) -> int:
        """Estimate total duration in minutes.

        Args:
            tasks: All tasks.

        Returns:
            Estimated duration in minutes.
        """
        duration_map = {
            Complexity.LOW: 5,
            Complexity.MEDIUM: 15,
            Complexity.HIGH: 30,
        }

        total = 0
        for task in tasks:
            # Read complexity from input_data (Task has no complexity field)
            complexity = task.input_data.get("complexity")
            total += duration_map.get(complexity, 15)

        return total

    def _map_classification_to_priority(
        self,
        classification: str,
    ) -> TaskPriority:
        """Map page classification to task priority.

        Args:
            classification: Page classification.

        Returns:
            Task priority.
        """
        mapping = {
            "critical": TaskPriority.CRITICAL,
            "high": TaskPriority.HIGH,
            "medium": TaskPriority.MEDIUM,
            "low": TaskPriority.LOW,
        }
        return mapping.get(classification.lower(), TaskPriority.MEDIUM)

    def _map_opportunity_priority(
        self,
        priority: int,
    ) -> TaskPriority:
        """Map opportunity priority to task priority.

        Args:
            priority: Priority value (1=CRITICAL, 2=HIGH, 3=NORMAL, 4=LOW).

        Returns:
            Task priority.
        """
        mapping = {
            1: TaskPriority.CRITICAL,
            2: TaskPriority.HIGH,
            3: TaskPriority.NORMAL,
            4: TaskPriority.LOW,
        }
        return mapping.get(priority, TaskPriority.NORMAL)

    def _keyword_to_route(self, keyword: str) -> str:
        """Convert keyword to URL route.

        Args:
            keyword: Keyword term.

        Returns:
            URL route.
        """
        # Simple slug generation
        slug = keyword.lower().replace(" ", "-")
        return f"/{slug}"