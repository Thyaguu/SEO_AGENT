"""SEO data models.

This module contains domain models for SEO-related data structures including
keywords, metadata, SEO pages, sitemap entries, and robots.txt rules.

All models follow SOLID principles with single responsibility and are
designed for immutability where appropriate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from seo_agent.core.types import StrDict


class KeywordType(Enum):
    """Types of keywords in SEO optimization."""

    PRIMARY = "primary"
    SECONDARY = "secondary"


class ChangeFrequency(Enum):
    """Sitemap change frequency values."""

    ALWAYS = "always"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    NEVER = "never"


@dataclass(frozen=True)
class Keyword:
    """Represents an SEO keyword with associated metadata.

    Attributes:
        term: The actual keyword or phrase.
        keyword_type: Whether this is a primary or secondary keyword.
        search_volume: Optional monthly search volume estimate.
        difficulty: Optional keyword difficulty score (0-100).
        intent: Optional search intent description.
        reason: Optional reasoning for keyword selection.
    """

    term: str
    keyword_type: KeywordType
    search_volume: int | None = None
    difficulty: float | None = None
    intent: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class OpenGraphData:
    """Open Graph meta tag data for social sharing.

    Attributes:
        title: OG title (defaults to page title if not set).
        description: OG description.
        image: URL to image for social cards.
        url: Canonical URL for the page.
        type: Content type (website, article, etc.).
        site_name: Name of the website.
    """

    title: str | None = None
    description: str | None = None
    image: str | None = None
    url: str | None = None
    type: str = "website"
    site_name: str | None = None
    locale: str | None = None
    video: str | None = None
    audio: str | None = None


@dataclass(frozen=True)
class TwitterCardData:
    """Twitter Card meta tag data.

    Attributes:
        card: Card type (summary, summary_large_image, etc.).
        title: Card title.
        description: Card description.
        image: URL to image for card.
        site: Twitter handle of content creator.
    """

    card: str = "summary"
    title: str | None = None
    description: str | None = None
    image: str | None = None
    site: str | None = None


@dataclass(frozen=True)
class StructuredData:
    """Schema.org structured data for rich search results.

    Attributes:
        schema_type: The schema.org type (e.g., Article, FAQPage).
        properties: Key-value pairs of schema properties.
        raw_json: Optional raw JSON-LD string if pre-formatted.
    """

    schema_type: str
    properties: StrDict = field(default_factory=dict)
    raw_json: str | None = None


@dataclass(frozen=True)
class JsonLdData:
    """JSON-LD structured data extracted from HTML.

    Attributes:
        context: The @context value (e.g., "https://schema.org").
        type: The @type value (e.g., "Article", "WebPage").
        data: The full JSON-LD data dictionary.
    """

    context: str
    type: str | None = None
    data: StrDict = field(default_factory=dict)


@dataclass(frozen=True)
class Metadata:
    """Complete SEO metadata for a page.

    This model contains all SEO-related meta tags and structured data
    that can be applied to HTML pages.

    Attributes:
        title: HTML title tag (max 60 characters recommended).
        description: Meta description (max 160 characters recommended).
        keywords: List of meta keywords (optional, rarely used).
        canonical_url: Canonical URL to prevent duplicate content issues.
        robots: Robots meta directive (e.g., "index, follow").
        primary_keyword: The main target keyword for the page.
        secondary_keywords: Additional target keywords.
        og: Open Graph social sharing data.
        twitter: Twitter Card data.
        structured_data: List of schema.org structured data entries.
        language: HTML language code (e.g., "en", "en-US").
    """

    title: str
    description: str
    canonical_url: str
    robots: str = "index, follow"
    keywords: tuple[str, ...] = field(default_factory=tuple)
    primary_keyword: Keyword | None = None
    secondary_keywords: tuple[Keyword, ...] = field(default_factory=tuple)
    og: OpenGraphData = field(default_factory=OpenGraphData)
    twitter: TwitterCardData = field(default_factory=TwitterCardData)
    structured_data: tuple[StructuredData, ...] = field(default_factory=tuple)
    language: str = "en"


@dataclass(frozen=True)
class SEOPage:
    """Represents a generated SEO landing page.

    SEO landing pages are generated under the /seo directory based on
    keyword research from the n8n payload.

    Attributes:
        slug: URL-friendly identifier (e.g., "applicant-tracking-system").
        title: Page title for HTML.
        description: Meta description.
        h1: Main heading text.
        content_sections: List of content section titles (H2-H3).
        keywords: Associated keywords.
        metadata: Complete SEO metadata.
        route_path: Framework-specific route path.
        file_path: Physical file path in repository.
        created_at: Timestamp when page was created.
        modified_at: Timestamp when page was last modified.
    """

    slug: str
    title: str
    description: str
    h1: str
    metadata: Metadata
    route_path: str
    file_path: str
    content_sections: tuple[str, ...] = field(default_factory=tuple)
    keywords: tuple[Keyword, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class SitemapEntry:
    """Entry in sitemap.xml.

    Attributes:
        url: The page URL.
        last_modified: Last modification date.
        change_frequency: How often the page is likely to change.
        priority: Relative priority of this URL (0.0-1.0).
    """

    url: str
    last_modified: datetime | None = None
    change_frequency: ChangeFrequency = ChangeFrequency.WEEKLY
    priority: float = 0.5


@dataclass(frozen=True)
class RobotsRule:
    """Rule in robots.txt file.

    Attributes:
        user_agent: Target user agent (e.g., "*", "Googlebot").
        allow: List of allowed paths. If empty, all paths are disallowed.
        disallow: List of disallowed paths.
        crawl_delay: Optional delay between requests in seconds.
    """

    user_agent: str
    allow: tuple[str, ...] = field(default_factory=tuple)
    disallow: tuple[str, ...] = field(default_factory=tuple)
    crawl_delay: float | None = None


@dataclass(frozen=True)
class RobotsConfig:
    """Complete robots.txt configuration.

    Attributes:
        rules: List of robots rules for different user agents.
        sitemap_urls: List of sitemap URLs referenced in the file.
    """

    rules: tuple[RobotsRule, ...] = field(default_factory=tuple)
    sitemap_urls: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CompetitorInfo:
    """Information about a competitor for comparison sections.

    Attributes:
        name: Competitor name.
        strengths: List of competitor strengths.
        comparison_notes: Notes for comparison section.
    """

    name: str
    strengths: tuple[str, ...] = field(default_factory=tuple)
    comparison_notes: str | None = None


@dataclass(frozen=True)
class FAQItem:
    """FAQ item for structured data and page content.

    Attributes:
        question: The FAQ question.
        answer: The FAQ answer.
    """

    question: str
    answer: str


@dataclass(frozen=True)
class InternalLink:
    """Internal link for cross-referencing SEO pages.

    Attributes:
        target_url: The URL to link to.
        anchor_text: The clickable text.
        context: Optional surrounding context.
    """

    target_url: str
    anchor_text: str
    context: str | None = None


@dataclass(frozen=True)
class ContentRecommendation:
    """Content optimization recommendation.

    Attributes:
        recommendation_type: Type of recommendation.
        description: Detailed recommendation.
        priority: Priority level (1-5, 1 being highest).
    """

    recommendation_type: str
    description: str
    priority: int = 3


# Type aliases for common patterns
KeywordSelection = Annotated[tuple[Keyword, ...], "Primary + up to 2 secondary"]
ContentSections = Annotated[tuple[str, ...], "H2 and H3 section headings"]