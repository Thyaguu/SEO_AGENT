"""Repository analysis models.

This module contains domain models for repository analysis including
framework detection, page discovery, and file information.

All models follow SOLID principles with single responsibility and are
designed for immutability where appropriate.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from pydantic import ConfigDict, Field

from seo_agent.core.types import StrDict
from seo_agent.models.base import BasePydanticModel

if TYPE_CHECKING:
    from seo_agent.models.seo import Metadata


class FrameworkType(Enum):
    """Supported framework types for repository detection."""

    STATIC_HTML = "static_html"
    REACT = "react"
    NEXT_JS = "next_js"
    VUE = "vue"
    NUXT = "nuxt"
    ANGULAR = "angular"
    ASTRO = "astro"
    SVELTE = "svelte"
    REMIX = "remix"
    GATSBY = "gatsby"
    LARAVEL_BLADE = "laravel_blade"
    DJANGO = "django"
    FLASK = "flask"
    EXPRESS = "express"
    VITE = "vite"
    UNKNOWN = "unknown"


class RoutingStrategy(Enum):
    """Routing strategy used by the framework."""

    FILE_BASED = "file_based"
    CONFIG_BASED = "config_based"
    STATIC = "static"
    DYNAMIC = "dynamic"
    API_ROUTES = "api_routes"
    UNKNOWN = "unknown"


class PageType(Enum):
    """Type of page discovered in repository."""

    HOMEPAGE = "homepage"
    INDEX = "index"
    PAGE = "page"
    BLOG = "blog"
    BLOG_POST = "blog_post"
    PRODUCT = "product"
    CATEGORY = "category"
    TAG = "tag"
    AUTH = "auth"
    ADMIN = "admin"
    DASHBOARD = "dashboard"
    CHECKOUT = "checkout"
    ACCOUNT = "account"
    SEARCH = "search"
    API_ROUTE = "api_route"
    SEO_LANDING = "seo_landing"
    ERROR = "error"
    REDIRECT = "redirect"
    GENERAL = "general"
    UNKNOWN = "unknown"


class DiscoveredPage(BasePydanticModel):
    """A page discovered during repository scanning.

    This is a lightweight model used during the discovery phase before
    full metadata extraction.

    Attributes:
        url_path: The URL path for this page (e.g., "/about", "/blog/post-123").
        file_path: Physical file path in the repository.
        page_type: Classification of the page type.
        title: Page title if discoverable, None otherwise.
        has_dynamic_params: Whether the route contains dynamic parameters.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    url_path: str
    file_path: str
    page_type: PageType = PageType.UNKNOWN
    title: str | None = None
    has_dynamic_params: bool = False


class FrameworkInfo(BasePydanticModel):
    """Information about the detected framework.

    Attributes:
        framework_type: The type of framework detected.
        routing_strategy: How the framework handles routing.
        package_manager: Detected package manager (npm, yarn, pnpm, etc.).
        build_command: Build command if detected.
        dev_command: Development server command if detected.
        output_directory: Build output directory if applicable.
        config_files: List of detected configuration files.
        version: Detected framework version if available.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    framework_type: FrameworkType
    routing_strategy: RoutingStrategy = RoutingStrategy.UNKNOWN
    package_manager: str | None = None
    build_command: str | None = None
    dev_command: str | None = None
    output_directory: str | None = None
    config_files: tuple[str, ...] = ()
    version: str | None = None


class FileInfo(BasePydanticModel):
    """Information about a file in the repository.

    Attributes:
        path: Relative path from repository root.
        absolute_path: Full absolute path.
        size_bytes: File size in bytes.
        modified_at: Last modification timestamp.
        is_text: Whether file is text (True) or binary (False).
        extension: File extension (e.g., ".html", ".tsx").
        encoding: Text encoding if applicable.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    path: str
    absolute_path: str
    size_bytes: int = 0
    modified_at: datetime | None = None
    is_text: bool = True
    extension: str = ""
    encoding: str | None = None


class Heading(BasePydanticModel):
    """HTML heading information.

    Attributes:
        level: Heading level (1-6).
        text: Heading text content.
        id: Optional element ID for anchor links.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    level: int
    text: str
    id: str | None = None


class PageMetadata(BasePydanticModel):
    """Existing metadata found on a page.

    Attributes:
        title: Current page title.
        description: Current meta description.
        keywords: Current meta keywords.
        canonical: Current canonical URL.
        og_tags: Current Open Graph tags.
        twitter_tags: Current Twitter Card tags.
        structured_data: Current structured data.
        h1: Current H1 heading.
        headings: All headings on the page.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    title: str | None = None
    description: str | None = None
    keywords: tuple[str, ...] = ()
    canonical: str | None = None
    og_tags: StrDict = Field(default_factory=dict)
    twitter_tags: StrDict = Field(default_factory=dict)
    structured_data: tuple[str, ...] = ()
    h1: str | None = None
    headings: tuple[Heading, ...] = ()

    def to_metadata(self) -> Any:
        """Convert repository PageMetadata into SEO Metadata model."""
        from seo_agent.models.seo import Metadata, OpenGraphData, TwitterCardData

        og_title = self.og_tags.get("og:title") or self.og_tags.get("title")
        og_desc = self.og_tags.get("og:description") or self.og_tags.get("description")
        og_img = self.og_tags.get("og:image") or self.og_tags.get("image")
        og_url = self.og_tags.get("og:url") or self.og_tags.get("url")
        og_type = self.og_tags.get("og:type") or "website"
        og_site = self.og_tags.get("og:site_name") or self.og_tags.get("site_name")

        og_data = OpenGraphData(
            title=og_title,
            description=og_desc,
            image=og_img,
            url=og_url,
            type=og_type,
            site_name=og_site,
        )

        tw_card = self.twitter_tags.get("twitter:card") or self.twitter_tags.get("card") or "summary"
        tw_title = self.twitter_tags.get("twitter:title") or self.twitter_tags.get("title")
        tw_desc = self.twitter_tags.get("twitter:description") or self.twitter_tags.get("description")
        tw_img = self.twitter_tags.get("twitter:image") or self.twitter_tags.get("image")
        tw_site = self.twitter_tags.get("twitter:site") or self.twitter_tags.get("site")

        twitter_data = TwitterCardData(
            card=tw_card,
            title=tw_title,
            description=tw_desc,
            image=tw_img,
            site=tw_site,
        )

        return Metadata(
            title=self.title or "",
            description=self.description or "",
            canonical_url=self.canonical or "",
            keywords=self.keywords,
            og=og_data,
            twitter=twitter_data,
        )



class PageInfo(BasePydanticModel):
    """Information about a discovered page in the repository.

    Attributes:
        route: URL route path (e.g., "/about", "/products/123").
        file_path: Physical file path in repository.
        page_type: Type classification of the page.
        title: Page title if discoverable.
        metadata: Existing SEO metadata on the page.
        keywords: Keywords currently associated with the page.
        purpose: Inferred purpose of the page.
        links: Internal links found on the page.
        last_modified: Last modification timestamp.
        is_seo_page: Whether this is a generated SEO landing page.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    route: str
    file_path: str
    page_type: PageType = PageType.UNKNOWN
    title: str | None = None
    metadata: PageMetadata | None = None
    keywords: tuple[str, ...] = ()
    purpose: str | None = None
    links: tuple[str, ...] = ()
    last_modified: datetime | None = None
    is_seo_page: bool = False


class SitemapInfo(BasePydanticModel):
    """Information about existing sitemap.xml.

    Attributes:
        file_path: Path to sitemap.xml.
        exists: Whether the file exists.
        entries: Parsed sitemap entries.
        format: Sitemap format (xml, json, etc.).
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    file_path: str
    exists: bool = False
    entries: tuple[str, ...] = ()
    format: str = "xml"


class RobotsInfo(BasePydanticModel):
    """Information about existing robots.txt.

    Attributes:
        file_path: Path to robots.txt.
        exists: Whether the file exists.
        rules: Parsed robots rules.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    file_path: str
    exists: bool = False
    rules: tuple[str, ...] = ()


class RepositoryInfo(BasePydanticModel):
    """Complete repository analysis results.

    This is the main output of the repository analysis phase and contains
    all information needed for SEO planning.

    Attributes:
        root_path: Absolute path to repository root.
        framework: Detected framework information.
        pages: All discovered pages.
        seo_pages: Only SEO landing pages (subset of pages).
        sitemap: Existing sitemap information.
        robots: Existing robots.txt information.
        public_assets: Public asset locations.
        build_config: Build configuration if detected.
        analyzed_at: Timestamp of analysis.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    root_path: str
    framework: FrameworkInfo
    pages: tuple[PageInfo, ...] = ()
    seo_pages: tuple[PageInfo, ...] = ()
    sitemap: SitemapInfo | None = None
    robots: RobotsInfo | None = None
    public_assets: tuple[str, ...] = ()
    build_config: StrDict = Field(default_factory=dict)
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class RepositoryScanOptions(BasePydanticModel):
    """Options for repository scanning.

    Attributes:
        include_hidden: Include hidden files/directories.
        max_depth: Maximum directory depth to scan.
        extensions: File extensions to include.
        exclude_patterns: Glob patterns to exclude.
        follow_symlinks: Follow symbolic links.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    include_hidden: bool = False
    max_depth: int | None = None
    extensions: tuple[str, ...] = ()
    exclude_patterns: tuple[str, ...] = ("node_modules", ".git", "__pycache__", "reports")
    follow_symlinks: bool = False


class PageAnalysisResult(BasePydanticModel):
    """Result of analyzing a single page.

    Attributes:
        page: The page information.
        success: Whether analysis succeeded.
        error: Error message if analysis failed.
        extracted_keywords: Keywords extracted from page content.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    page: PageInfo
    success: bool = True
    error: str | None = None
    extracted_keywords: tuple[str, ...] = ()