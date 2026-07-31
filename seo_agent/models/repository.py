"""Repository analysis models.

This module contains domain models for repository analysis including
framework detection, page discovery, and file information.

All models follow SOLID principles with single responsibility and are
designed for immutability where appropriate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from seo_agent.core.types import StrDict

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


@dataclass(frozen=True)
class DiscoveredPage:
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

    url_path: str
    file_path: str
    page_type: PageType = PageType.UNKNOWN
    title: str | None = None
    has_dynamic_params: bool = False


@dataclass(frozen=True)
class FrameworkInfo:
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

    framework_type: FrameworkType
    routing_strategy: RoutingStrategy = RoutingStrategy.UNKNOWN
    package_manager: str | None = None
    build_command: str | None = None
    dev_command: str | None = None
    output_directory: str | None = None
    config_files: tuple[str, ...] = field(default_factory=tuple)
    version: str | None = None


@dataclass(frozen=True)
class FileInfo:
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

    path: str
    absolute_path: str
    size_bytes: int = 0
    modified_at: datetime | None = None
    is_text: bool = True
    extension: str = ""
    encoding: str | None = None


@dataclass(frozen=True)
class Heading:
    """HTML heading information.

    Attributes:
        level: Heading level (1-6).
        text: Heading text content.
        id: Optional element ID for anchor links.
    """

    level: int
    text: str
    id: str | None = None


@dataclass(frozen=True)
class PageMetadata:
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

    title: str | None = None
    description: str | None = None
    keywords: tuple[str, ...] = field(default_factory=tuple)
    canonical: str | None = None
    og_tags: StrDict = field(default_factory=dict)
    twitter_tags: StrDict = field(default_factory=dict)
    structured_data: tuple[str, ...] = field(default_factory=tuple)
    h1: str | None = None
    headings: tuple[Heading, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PageInfo:
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

    route: str
    file_path: str
    page_type: PageType = PageType.UNKNOWN
    title: str | None = None
    metadata: PageMetadata | None = None
    keywords: tuple[str, ...] = field(default_factory=tuple)
    purpose: str | None = None
    links: tuple[str, ...] = field(default_factory=tuple)
    last_modified: datetime | None = None
    is_seo_page: bool = False


@dataclass(frozen=True)
class SitemapInfo:
    """Information about existing sitemap.xml.

    Attributes:
        file_path: Path to sitemap.xml.
        exists: Whether the file exists.
        entries: Parsed sitemap entries.
        format: Sitemap format (xml, json, etc.).
    """

    file_path: str
    exists: bool = False
    entries: tuple[str, ...] = field(default_factory=tuple)
    format: str = "xml"


@dataclass(frozen=True)
class RobotsInfo:
    """Information about existing robots.txt.

    Attributes:
        file_path: Path to robots.txt.
        exists: Whether the file exists.
        rules: Parsed robots rules.
    """

    file_path: str
    exists: bool = False
    rules: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RepositoryInfo:
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

    root_path: str
    framework: FrameworkInfo
    pages: tuple[PageInfo, ...] = field(default_factory=tuple)
    seo_pages: tuple[PageInfo, ...] = field(default_factory=tuple)
    sitemap: SitemapInfo | None = None
    robots: RobotsInfo | None = None
    public_assets: tuple[str, ...] = field(default_factory=tuple)
    build_config: StrDict = field(default_factory=dict)
    analyzed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class RepositoryScanOptions:
    """Options for repository scanning.

    Attributes:
        include_hidden: Include hidden files/directories.
        max_depth: Maximum directory depth to scan.
        extensions: File extensions to include.
        exclude_patterns: Glob patterns to exclude.
        follow_symlinks: Follow symbolic links.
    """

    include_hidden: bool = False
    max_depth: int | None = None
    extensions: tuple[str, ...] = field(default_factory=tuple)
    exclude_patterns: tuple[str, ...] = field(default_factory=lambda: ("node_modules", ".git", "__pycache__", "reports"))
    follow_symlinks: bool = False


@dataclass(frozen=True)
class PageAnalysisResult:
    """Result of analyzing a single page.

    Attributes:
        page: The page information.
        success: Whether analysis succeeded.
        error: Error message if analysis failed.
        extracted_keywords: Keywords extracted from page content.
    """

    page: PageInfo
    success: bool = True
    error: str | None = None
    extracted_keywords: tuple[str, ...] = field(default_factory=tuple)