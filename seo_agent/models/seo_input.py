"""SEO keyword intelligence input models for external data ingestion (CSV / JSON).

Represents keyword intelligence datasets (search volume, intent, priority scores,
H2 outlines, LSI keywords, and proposed metadata).
"""

from __future__ import annotations

from typing import Any
from pydantic import Field
from seo_agent.models.base import BasePydanticModel


class NormalizedSEOEntry(BasePydanticModel):
    """Normalized keyword intelligence record.

    Attributes:
        keyword: Target keyword or term (e.g., "Recruitment Software").
        search_volume: Monthly search volume.
        competition: Competition or difficulty score (0.0 to 1.0 or 0-100).
        search_intent: Search intent classification (informational, commercial, navigational, transactional).
        content_type: Recommended content type (page, blog, guide, product).
        content_priority_score: Priority score for SEO optimization.
        ai_opportunity_score: AI opportunity ranking score.
        ranking_feasibility: Ranking feasibility score.
        meta_title: Recommended or target meta title.
        meta_description: Recommended or target meta description.
        h2_outlines: List of recommended H2 section headings.
        lsi_keywords: List of Latent Semantic Indexing (LSI) / secondary keywords.
        page_path: Optional page path or URL hint if provided in CSV.
        raw_data: Original dictionary record for auditing.
    """

    keyword: str
    search_volume: int = 0
    competition: float = 0.0
    search_intent: str = "informational"
    content_type: str = "page"
    content_priority_score: float = 0.0
    ai_opportunity_score: float = 0.0
    ranking_feasibility: float = 0.0
    meta_title: str | None = None
    meta_description: str | None = None
    h2_outlines: list[str] = Field(default_factory=list)
    lsi_keywords: list[str] = Field(default_factory=list)
    page_path: str | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)

    # Legacy compatibility fields
    @property
    def title(self) -> str | None:
        return self.meta_title

    @property
    def description(self) -> str | None:
        return self.meta_description

    @property
    def canonical(self) -> str | None:
        return self.raw_data.get("canonical") or self.raw_data.get("canonical_url")

    @property
    def h1(self) -> str | None:
        return self.raw_data.get("h1")

    @property
    def og_title(self) -> str | None:
        return self.raw_data.get("og_title")

    @property
    def og_description(self) -> str | None:
        return self.raw_data.get("og_description")

    @property
    def og_image(self) -> str | None:
        return self.raw_data.get("og_image")

    @property
    def twitter_card(self) -> str | None:
        return self.raw_data.get("twitter_card")

    @property
    def twitter_title(self) -> str | None:
        return self.raw_data.get("twitter_title")

    @property
    def twitter_description(self) -> str | None:
        return self.raw_data.get("twitter_description")

    @property
    def twitter_image(self) -> str | None:
        return self.raw_data.get("twitter_image")

    @property
    def structured_data(self) -> Any | None:
        return self.raw_data.get("structured_data")

    @property
    def internal_link_suggestions(self) -> list[str]:
        return self.lsi_keywords or self.raw_data.get("internal_link_suggestions", [])


class SEOInputCollection(BasePydanticModel):
    """Collection of keyword intelligence records loaded from CSV/JSON.

    Attributes:
        source_type: Type of source ("csv", "json", "none").
        source_path: File path or source identifier if available.
        records: List of parsed NormalizedSEOEntry objects.
        records_loaded: Total records parsed successfully.
        matched_pages: Count of records successfully matched to repository pages.
        unmatched_records: Count of records that could not be matched to any discovered page.
        skipped_records: Count of records skipped during parsing/validation.
    """

    source_type: str = "none"
    source_path: str | None = None
    records: list[NormalizedSEOEntry] = Field(default_factory=list)
    records_loaded: int = 0
    matched_pages: int = 0
    unmatched_records: int = 0
    skipped_records: int = 0
