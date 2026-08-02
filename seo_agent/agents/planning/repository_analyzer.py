"""Repository analysis for planning.

This module analyzes repository information to identify SEO opportunities,
missing metadata, existing SEO assets, and implementation constraints.

It MUST NOT:
- Modify files
- Communicate with OpenCode
- Perform Git operations
- Review generated code
- Make AI/LLM calls

It ONLY analyzes and produces analysis data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from seo_agent.core.logging import get_logger
from seo_agent.models.repository import (
    FrameworkInfo,
    FrameworkType,
    PageInfo,
    RepositoryInfo,
)

if TYPE_CHECKING:
    from seo_agent.models.seo import Metadata

logger = get_logger(__name__)


class PageClassification(Enum):
    """Classification of a page for SEO purposes."""

    HOME = "home"
    LANDING = "landing"
    BLOG = "blog"
    PRODUCT = "product"
    CATEGORY = "category"
    CONTACT = "contact"
    ABOUT = "about"
    PRICING = "pricing"
    DOCUMENTATION = "documentation"
    SEO_PAGE = "seo_page"
    UNKNOWN = "unknown"


class SEOOpportunityType(Enum):
    """Types of SEO opportunities."""

    MISSING_TITLE = "missing_title"
    MISSING_DESCRIPTION = "missing_description"
    MISSING_OG_TAGS = "missing_og_tags"
    MISSING_STRUCTURED_DATA = "missing_structured_data"
    LOW_CONTENT_QUALITY = "low_content_quality"
    MISSING_INTERNAL_LINKS = "missing_internal_links"
    NO_FAQ_SCHEMA = "no_faq_schema"
    NO_ARTICLE_SCHEMA = "no_article_schema"
    DUPLICATE_CONTENT = "duplicate_content"
    MISSING_ALT_TAGS = "missing_alt_tags"


class ImplementationConstraint(Enum):
    """Constraints that affect SEO implementation."""

    STATIC_SITE = "static_site"
    DYNAMIC_ROUTING = "dynamic_routing"
    NO_SERVER_SIDE_RENDERING = "no_server_side_rendering"
    LIMITED_FILE_ACCESS = "limited_file_access"
    FRAMEWORK_SPECIFIC_SYNTAX = "framework_specific_syntax"
    READ_ONLY_REPOSITORY = "read_only_repository"


@dataclass(frozen=True)
class SEOOpportunity:
    """Represents an SEO opportunity on a page.

    Attributes:
        opportunity_type: Type of opportunity.
        page_route: Route of the affected page.
        description: Human-readable description.
        priority: Priority level (1-5, 1 being highest).
        estimated_effort: Estimated effort (low, medium, high).
    """

    opportunity_type: SEOOpportunityType
    page_route: str
    description: str
    priority: int = 3
    estimated_effort: str = "medium"


@dataclass(frozen=True)
class MissingMetadata:
    """Represents missing metadata on a page.

    Attributes:
        page_route: Route of the affected page.
        missing_fields: List of missing metadata fields.
        current_values: Current values for existing fields.
    """

    page_route: str
    missing_fields: tuple[str, ...]
    current_values: dict[str, str | None] = field(default_factory=dict)


@dataclass(frozen=True)
class ExistingSEOAsset:
    """Represents an existing SEO asset in the repository.

    Attributes:
        asset_type: Type of asset (sitemap, robots, etc.).
        file_path: Path to the asset file.
        is_valid: Whether the asset is valid.
        last_modified: Last modification timestamp.
        issues: List of issues with the asset.
    """

    asset_type: str
    file_path: str
    is_valid: bool = True
    last_modified: datetime | None = None
    issues: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PageClassificationResult:
    """Classification result for a single page.

    Attributes:
        page_route: Route of the page.
        classification: Classification type.
        confidence: Confidence score (0.0-1.0).
        reasoning: Explanation of classification.
    """

    page_route: str
    classification: PageClassification
    confidence: float = 0.5
    reasoning: str | None = None


@dataclass(frozen=True)
class RepositoryAnalysis:
    """Complete repository analysis for SEO planning.

    This is the output of the repository analyzer and serves as input
    for the task planner.

    Attributes:
        repository_path: Path to the repository.
        detected_framework: Framework information.
        seo_opportunities: All identified SEO opportunities.
        missing_metadata: Pages with missing metadata.
        existing_seo_assets: Existing SEO assets found.
        page_classifications: Classification of each page.
        implementation_constraints: Constraints affecting implementation.
        total_pages: Total number of pages analyzed.
        pages_needing_work: Number of pages requiring SEO work.
        analyzed_at: Timestamp of analysis.
    """

    repository_path: str
    detected_framework: FrameworkInfo
    seo_opportunities: tuple[SEOOpportunity, ...] = field(default_factory=tuple)
    missing_metadata: tuple[MissingMetadata, ...] = field(default_factory=tuple)
    existing_seo_assets: tuple[ExistingSEOAsset, ...] = field(default_factory=tuple)
    page_classifications: tuple[PageClassificationResult, ...] = field(default_factory=tuple)
    implementation_constraints: tuple[ImplementationConstraint, ...] = field(default_factory=tuple)
    total_pages: int = 0
    pages_needing_work: int = 0
    analyzed_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def high_priority_opportunities(self) -> tuple[SEOOpportunity, ...]:
        """Get high priority opportunities (priority 1-2)."""
        return tuple(o for o in self.seo_opportunities if o.priority <= 2)

    @property
    def opportunity_count_by_type(self) -> dict[SEOOpportunityType, int]:
        """Count opportunities by type."""
        counts: dict[SEOOpportunityType, int] = {}
        for opp in self.seo_opportunities:
            counts[opp.opportunity_type] = counts.get(opp.opportunity_type, 0) + 1
        return counts


class RepositoryAnalyzer:
    """Analyzes repository information for SEO planning.

    This analyzer consumes repository, framework, page, and metadata information
    to produce a comprehensive analysis used by the task planner.

    It performs analysis only - no file modifications, no AI calls,
    no Git operations, no code review.
    """

    def __init__(self) -> None:
        """Initialize the repository analyzer."""
        self._logger = get_logger(__name__)

    def analyze(
        self,
        repository_info: RepositoryInfo,
        page_info: tuple[PageInfo, ...] = field(default_factory=tuple),
        additional_metadata: dict[str, Metadata] | None = None,
    ) -> RepositoryAnalysis:
        """Analyze repository for SEO opportunities.

        Args:
            repository_info: Complete repository information.
            page_info: Extracted page information with metadata from METADATA_EXTRACTION stage.
            additional_metadata: Optional additional metadata by page route.

        Returns:
            RepositoryAnalysis with identified opportunities and constraints.
        """
        # Use page_info from METADATA_EXTRACTION stage if available,
        # otherwise fall back to repository_info.pages
        pages = page_info if page_info else repository_info.pages

        self._logger.debug(
            f"analyzing_repository: path={repository_info.root_path}, page_count={len(pages)}"
        )

        # Analyze pages for opportunities and missing metadata
        seo_opportunities = self._analyze_seo_opportunities(
            pages,
            additional_metadata or {},
        )

        missing_metadata = self._analyze_missing_metadata(
            pages,
            additional_metadata or {},
        )

        # Classify pages
        page_classifications = self._classify_pages(pages)

        # Identify existing SEO assets
        existing_assets = self._identify_seo_assets(repository_info)

        # Determine implementation constraints
        constraints = self._determine_constraints(repository_info)

        # Count pages needing work
        pages_needing_work = len(missing_metadata)

        analysis = RepositoryAnalysis(
            repository_path=repository_info.root_path,
            detected_framework=repository_info.framework,
            seo_opportunities=seo_opportunities,
            missing_metadata=missing_metadata,
            existing_seo_assets=existing_assets,
            page_classifications=page_classifications,
            implementation_constraints=constraints,
            total_pages=len(pages),
            pages_needing_work=pages_needing_work,
        )

        self._logger.debug(
            f"repository_analysis_complete: opportunities={len(seo_opportunities)}, "
            f"missing_metadata={len(missing_metadata)}, constraints={len(constraints)}"
        )

        return analysis

    def _analyze_seo_opportunities(
        self,
        pages: tuple[PageInfo, ...],
        additional_metadata: dict[str, Metadata],
    ) -> tuple[SEOOpportunity, ...]:
        """Analyze pages for SEO opportunities.

        Args:
            pages: All discovered pages.
            additional_metadata: Additional metadata by route.

        Returns:
            Tuple of identified SEO opportunities.
        """
        opportunities: list[SEOOpportunity] = []

        for page in pages:
            page_opportunities = self._find_page_opportunities(page, additional_metadata)
            opportunities.extend(page_opportunities)

        # Sort by priority (1 = highest)
        opportunities.sort(key=lambda o: (o.priority, o.opportunity_type.value))

        return tuple(opportunities)

    def _find_page_opportunities(
        self,
        page: PageInfo,
        additional_metadata: dict[str, Metadata],
    ) -> list[SEOOpportunity]:
        """Find SEO opportunities for a single page.

        Args:
            page: Page to analyze.
            additional_metadata: Additional metadata by route.

        Returns:
            List of opportunities for the page.
        """
        opportunities: list[SEOOpportunity] = []
        metadata = page.metadata or additional_metadata.get(page.route)

        # Check for missing title
        if not page.title and not (metadata and metadata.title):
            opportunities.append(SEOOpportunity(
                opportunity_type=SEOOpportunityType.MISSING_TITLE,
                page_route=page.route,
                description=f"Page '{page.route}' is missing a title",
                priority=2,
                estimated_effort="low",
            ))

        # Check for missing description
        if not metadata or not metadata.description:
            opportunities.append(SEOOpportunity(
                opportunity_type=SEOOpportunityType.MISSING_DESCRIPTION,
                page_route=page.route,
                description=f"Page '{page.route}' is missing meta description",
                priority=2,
                estimated_effort="low",
            ))

        # Check for missing OG tags
        og_tags = getattr(metadata, "og_tags", None) or getattr(metadata, "og", None)
        if not metadata or not og_tags:
            opportunities.append(SEOOpportunity(
                opportunity_type=SEOOpportunityType.MISSING_OG_TAGS,
                page_route=page.route,
                description=f"Page '{page.route}' is missing Open Graph tags",
                priority=3,
                estimated_effort="low",
            ))

        # Check for missing structured data
        if not metadata or not metadata.structured_data:
            # Only flag for important page types
            if page.page_type.value in ("landing", "blog", "product"):
                opportunities.append(SEOOpportunity(
                    opportunity_type=SEOOpportunityType.MISSING_STRUCTURED_DATA,
                    page_route=page.route,
                    description=f"Page '{page.route}' is missing structured data",
                    priority=3,
                    estimated_effort="medium",
                ))

        # Check for missing internal links
        if not page.links:
            opportunities.append(SEOOpportunity(
                opportunity_type=SEOOpportunityType.MISSING_INTERNAL_LINKS,
                page_route=page.route,
                description=f"Page '{page.route}' has no internal links",
                priority=4,
                estimated_effort="medium",
            ))

        return opportunities

    def _analyze_missing_metadata(
        self,
        pages: tuple[PageInfo, ...],
        additional_metadata: dict[str, Metadata],
    ) -> tuple[MissingMetadata, ...]:
        """Analyze pages for missing metadata.

        Args:
            pages: All discovered pages.
            additional_metadata: Additional metadata by route.

        Returns:
            Tuple of pages with missing metadata.
        """
        missing: list[MissingMetadata] = []

        for page in pages:
            metadata = page.metadata or additional_metadata.get(page.route)

            canonical_val = getattr(metadata, "canonical", None) or getattr(metadata, "canonical_url", None)
            og_val = getattr(metadata, "og_tags", None) or getattr(metadata, "og", None)
            twitter_val = getattr(metadata, "twitter_tags", None) or getattr(metadata, "twitter", None)

            # Page is missing metadata if title or description is empty
            missing_fields: list[str] = []
            if not page.title and not (metadata and metadata.title):
                missing_fields.append("title")
            if not metadata or not metadata.description:
                missing_fields.append("description")
            if not metadata or not canonical_val:
                missing_fields.append("canonical_url")
            if not metadata or not og_val:
                missing_fields.append("og_tags")
            if not metadata or not twitter_val:
                missing_fields.append("twitter_tags")

            if missing_fields:
                current_values = {
                    "title": page.title or (metadata.title if metadata else None),
                    "description": metadata.description if metadata else None,
                    "canonical": canonical_val,
                }
                missing.append(MissingMetadata(
                    page_route=page.route,
                    missing_fields=tuple(missing_fields),
                    current_values=current_values,
                ))

        return tuple(missing)

    def _classify_pages(
        self,
        pages: tuple[PageInfo, ...],
    ) -> tuple[PageClassificationResult, ...]:
        """Classify pages by type.

        Args:
            pages: All discovered pages.

        Returns:
            Tuple of page classifications.
        """
        classifications: list[PageClassificationResult] = []

        for page in pages:
            classification = self._classify_single_page(page)
            classifications.append(classification)

        return tuple(classifications)

    def _classify_single_page(self, page: PageInfo) -> PageClassificationResult:
        """Classify a single page.

        Args:
            page: Page to classify.

        Returns:
            Classification result.
        """
        route = page.route.lower()
        page_type = page.page_type.value.lower()

        # Check for SEO page
        if page.is_seo_page or "/seo/" in route:
            return PageClassificationResult(
                page_route=page.route,
                classification=PageClassification.SEO_PAGE,
                confidence=0.95,
                reasoning="Page is in /seo/ directory or marked as SEO page",
            )

        # Check route patterns
        if route == "/" or route == "" or route == "/home":
            return PageClassificationResult(
                page_route=page.route,
                classification=PageClassification.HOME,
                confidence=0.9,
                reasoning="Page is the home page",
            )

        if "/blog" in route or page_type == "blog":
            return PageClassificationResult(
                page_route=page.route,
                classification=PageClassification.BLOG,
                confidence=0.85,
                reasoning="Page is in blog section",
            )

        if "/product" in route or page_type == "product":
            return PageClassificationResult(
                page_route=page.route,
                classification=PageClassification.PRODUCT,
                confidence=0.85,
                reasoning="Page is a product page",
            )

        if "/pricing" in route:
            return PageClassificationResult(
                page_route=page.route,
                classification=PageClassification.PRICING,
                confidence=0.9,
                reasoning="Page is a pricing page",
            )

        if "/contact" in route:
            return PageClassificationResult(
                page_route=page.route,
                classification=PageClassification.CONTACT,
                confidence=0.9,
                reasoning="Page is a contact page",
            )

        if "/about" in route:
            return PageClassificationResult(
                page_route=page.route,
                classification=PageClassification.ABOUT,
                confidence=0.9,
                reasoning="Page is an about page",
            )

        if "/docs" in route or "/documentation" in route:
            return PageClassificationResult(
                page_route=page.route,
                classification=PageClassification.DOCUMENTATION,
                confidence=0.85,
                reasoning="Page is documentation",
            )

        if page_type == "landing":
            return PageClassificationResult(
                page_route=page.route,
                classification=PageClassification.LANDING,
                confidence=0.8,
                reasoning="Page is classified as landing page type",
            )

        # Default to unknown
        return PageClassificationResult(
            page_route=page.route,
            classification=PageClassification.UNKNOWN,
            confidence=0.5,
            reasoning="Could not determine page type",
        )

    def _identify_seo_assets(
        self,
        repository_info: RepositoryInfo,
    ) -> tuple[ExistingSEOAsset, ...]:
        """Identify existing SEO assets in the repository.

        Args:
            repository_info: Repository information.

        Returns:
            Tuple of existing SEO assets.
        """
        assets: list[ExistingSEOAsset] = []

        # Check sitemap
        if repository_info.sitemap:
            assets.append(ExistingSEOAsset(
                asset_type="sitemap",
                file_path=repository_info.sitemap.file_path,
                is_valid=repository_info.sitemap.exists,
                last_modified=None,
                issues=() if repository_info.sitemap.exists else ("sitemap not found",),
            ))

        # Check robots.txt
        if repository_info.robots:
            assets.append(ExistingSEOAsset(
                asset_type="robots",
                file_path=repository_info.robots.file_path,
                is_valid=repository_info.robots.exists,
                last_modified=None,
                issues=() if repository_info.robots.exists else ("robots.txt not found",),
            ))

        # Check for SEO pages directory
        seo_page_count = len(repository_info.seo_pages)
        if seo_page_count > 0:
            assets.append(ExistingSEOAsset(
                asset_type="seo_pages_directory",
                file_path="/seo/",
                is_valid=True,
                issues=(),
            ))

        return tuple(assets)

    def _determine_constraints(
        self,
        repository_info: RepositoryInfo,
    ) -> tuple[ImplementationConstraint, ...]:
        """Determine implementation constraints from repository.

        Args:
            repository_info: Repository information.

        Returns:
            Tuple of implementation constraints.
        """
        constraints: list[ImplementationConstraint] = []
        framework = repository_info.framework

        # Check framework type for constraints
        # is_static check: STATIC_HTML is the only truly static type
        if framework.framework_type == FrameworkType.STATIC_HTML:
            constraints.append(ImplementationConstraint.STATIC_SITE)

        # is_spa check: these frameworks are SPAs without server-side rendering
        if framework.framework_type in (
            FrameworkType.REACT,
            FrameworkType.NEXT_JS,
            FrameworkType.VUE,
            FrameworkType.ANGULAR,
            FrameworkType.SVELTE,
            FrameworkType.REMIX,
        ):
            constraints.append(ImplementationConstraint.NO_SERVER_SIDE_RENDERING)

        if framework.routing_strategy.value == "dynamic":
            constraints.append(ImplementationConstraint.DYNAMIC_ROUTING)

        # Check for read-only indicators
        if not repository_info.build_config:
            constraints.append(ImplementationConstraint.LIMITED_FILE_ACCESS)

        # Add framework-specific constraint
        constraints.append(ImplementationConstraint.FRAMEWORK_SPECIFIC_SYNTAX)

        return tuple(constraints)