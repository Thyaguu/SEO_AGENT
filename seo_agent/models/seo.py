"""SEO data models.

This module contains domain models for SEO-related data structures including
keywords, metadata, SEO pages, sitemap entries, and robots.txt rules.

All models follow SOLID principles with single responsibility and are
designed for immutability where appropriate.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from pydantic import ConfigDict, Field, field_validator

from enum import Enum
from seo_agent.core.types import StrDict
from seo_agent.models.base import BasePydanticModel


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



class Keyword(BasePydanticModel):
    """Represents an SEO keyword with associated metadata.

    Attributes:
        term: The actual keyword or phrase.
        keyword_type: Whether this is a primary or secondary keyword.
        search_volume: Optional monthly search volume estimate.
        difficulty: Optional keyword difficulty score (0-100).
        intent: Optional search intent description.
        reason: Optional reasoning for keyword selection.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    term: str
    keyword_type: KeywordType
    search_volume: int | None = None
    difficulty: float | None = None
    intent: str | None = None
    reason: str | None = None


class OpenGraphData(BasePydanticModel):
    """Open Graph meta tag data for social sharing.

    Attributes:
        title: OG title (defaults to page title if not set).
        description: OG description.
        image: URL to image for social cards.
        url: Canonical URL for the page.
        type: Content type (website, article, etc.).
        site_name: Name of the website.
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
    image: str | None = None
    url: str | None = None
    type: str = "website"
    site_name: str | None = None
    locale: str | None = None
    video: str | None = None
    audio: str | None = None


class TwitterCardData(BasePydanticModel):
    """Twitter Card meta tag data.

    Attributes:
        card: Card type (summary, summary_large_image, etc.).
        title: Card title.
        description: Card description.
        image: URL to image for card.
        site: Twitter handle of content creator.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    card: str = "summary"
    title: str | None = None
    description: str | None = None
    image: str | None = None
    site: str | None = None


class StructuredData(BasePydanticModel):
    """Schema.org structured data for rich search results.

    Attributes:
        schema_type: The schema.org type (e.g., Article, FAQPage).
        properties: Key-value pairs of schema properties.
        raw_json: Optional raw JSON-LD string if pre-formatted.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    schema_type: str
    properties: StrDict = Field(default_factory=dict)
    raw_json: str | None = None


class JsonLdData(BasePydanticModel):
    """JSON-LD structured data extracted from HTML.

    Attributes:
        context: The @context value (e.g., "https://schema.org").
        type: The @type value (e.g., "Article", "WebPage").
        data: The full JSON-LD data dictionary.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    context: str
    type: str | None = None
    data: StrDict = Field(default_factory=dict)


class Metadata(BasePydanticModel):
    """Complete SEO metadata for a page.

    This model contains all SEO-related meta tags and structured data
    that can be applied to HTML pages.

    Attributes:
        title: HTML title tag (max 60 characters recommended).
        description: Meta description (max 160 characters recommended).
        canonical_url: Canonical URL to prevent duplicate content issues.
        robots: Robots meta directive (e.g., "index, follow").
        keywords: List of meta keywords (optional, rarely used).
        primary_keyword: The main target keyword for the page.
        secondary_keywords: Additional target keywords.
        og: Open Graph social sharing data.
        twitter: Twitter Card data.
        structured_data: List of schema.org structured data entries.
        language: HTML language code (e.g., "en", "en-US").
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    title: str
    description: str
    canonical_url: str
    robots: str = "index, follow"
    keywords: tuple[str, ...] = ()
    primary_keyword: Keyword | None = None
    secondary_keywords: tuple[Keyword, ...] = ()
    og: OpenGraphData = Field(default_factory=OpenGraphData)
    twitter: TwitterCardData = Field(default_factory=TwitterCardData)
    structured_data: tuple[StructuredData, ...] = ()
    language: str = "en"

    @field_validator("og", mode="before")
    @classmethod
    def _validate_og(cls, v: Any) -> Any:
        if v is None:
            return OpenGraphData()
        return v

    @field_validator("twitter", mode="before")
    @classmethod
    def _validate_twitter(cls, v: Any) -> Any:
        if v is None:
            return TwitterCardData()
        return v

    @classmethod
    def from_page_metadata(cls, page_meta: Any) -> Metadata:
        """Create a Metadata instance from a PageMetadata instance or dict."""
        if hasattr(page_meta, "to_metadata"):
            return page_meta.to_metadata()
        if isinstance(page_meta, cls):
            return page_meta
        if isinstance(page_meta, dict):
            return cls(**page_meta)
        raise TypeError(f"Cannot convert {type(page_meta)} to Metadata")



class SEOPage(BasePydanticModel):
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

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    slug: str
    title: str
    description: str
    h1: str
    metadata: Metadata
    route_path: str
    file_path: str
    content_sections: tuple[str, ...] = ()
    keywords: tuple[Keyword, ...] = ()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    modified_at: datetime = Field(default_factory=datetime.utcnow)


class SitemapEntry(BasePydanticModel):
    """Entry in sitemap.xml.

    Attributes:
        url: The page URL.
        last_modified: Last modification date.
        change_frequency: How often the page is likely to change.
        priority: Relative priority of this URL (0.0-1.0).
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    url: str
    last_modified: datetime | None = None
    change_frequency: ChangeFrequency = ChangeFrequency.WEEKLY
    priority: float = 0.5


class RobotsRule(BasePydanticModel):
    """Rule in robots.txt file.

    Attributes:
        user_agent: Target user agent (e.g., "*", "Googlebot").
        allow: List of allowed paths. If empty, all paths are disallowed.
        disallow: List of disallowed paths.
        crawl_delay: Optional delay between requests in seconds.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    user_agent: str
    allow: tuple[str, ...] = ()
    disallow: tuple[str, ...] = ()
    crawl_delay: float | None = None


class RobotsConfig(BasePydanticModel):
    """Complete robots.txt configuration.

    Attributes:
        rules: List of robots rules for different user agents.
        sitemap_urls: List of sitemap URLs referenced in the file.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    rules: tuple[RobotsRule, ...] = ()
    sitemap_urls: tuple[str, ...] = ()


class CompetitorInfo(BasePydanticModel):
    """Information about a competitor for comparison sections.

    Attributes:
        name: Competitor name.
        strengths: List of competitor strengths.
        comparison_notes: Notes for comparison section.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    name: str
    strengths: tuple[str, ...] = ()
    comparison_notes: str | None = None


class FAQItem(BasePydanticModel):
    """FAQ item for structured data and page content.

    Attributes:
        question: The FAQ question.
        answer: The FAQ answer.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    question: str
    answer: str


class InternalLink(BasePydanticModel):
    """Internal link for cross-referencing SEO pages.

    Attributes:
        target_url: The URL to link to.
        anchor_text: The clickable text.
        context: Optional surrounding context.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    target_url: str
    anchor_text: str
    context: str | None = None


class ContentRecommendation(BasePydanticModel):
    """Content optimization recommendation.

    Attributes:
        recommendation_type: Type of recommendation.
        description: Detailed recommendation.
        priority: Priority level (1-5, 1 being highest).
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    recommendation_type: str
    description: str
    priority: int = 3


# Type aliases for common patterns
KeywordSelection = Annotated[tuple[Keyword, ...], "Primary + up to 2 secondary"]
ContentSections = Annotated[tuple[str, ...], "H2 and H3 section headings"]