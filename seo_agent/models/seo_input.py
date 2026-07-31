"""SEO input models for external data ingestion (CSV / JSON).

This module provides normalized domain models for external SEO data sources.
Downstream pipeline components consume these models without being coupled
to CSV or JSON schemas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NormalizedSEOEntry:
    """Normalized SEO data entry for a single page.

    Attributes:
        url: Target page URL (e.g., "https://example.com/about").
        page_path: Target relative path or route (e.g., "/about", "about.html").
        title: Optimized page title tag.
        description: Optimized meta description tag.
        canonical: Canonical URL string.
        keywords: List of target keywords.
        h1: Primary H1 heading text.
        og_title: OpenGraph title tag.
        og_description: OpenGraph description tag.
        og_image: OpenGraph image URL.
        twitter_card: Twitter card type (e.g., "summary_large_image").
        twitter_title: Twitter card title.
        twitter_description: Twitter card description.
        twitter_image: Twitter card image URL.
        structured_data: JSON-LD structured data payload or schema name.
        internal_link_suggestions: Target anchor links or routes to include.
        raw_data: Original dictionary record for auditing.
    """

    url: str | None = None
    page_path: str | None = None
    title: str | None = None
    description: str | None = None
    canonical: str | None = None
    keywords: list[str] = field(default_factory=list)
    h1: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    og_image: str | None = None
    twitter_card: str | None = None
    twitter_title: str | None = None
    twitter_description: str | None = None
    twitter_image: str | None = None
    structured_data: Any | None = None
    internal_link_suggestions: list[str] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class SEOInputCollection:
    """Collection of normalized SEO records loaded from an external source.

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
    records: list[NormalizedSEOEntry] = field(default_factory=list)
    records_loaded: int = 0
    matched_pages: int = 0
    unmatched_records: int = 0
    skipped_records: int = 0
