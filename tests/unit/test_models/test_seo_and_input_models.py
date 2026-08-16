"""Focused unit tests for migrated SEO and SEO input Pydantic models.

Tests normal construction, defaults, optional fields, enum fields, serialization,
deserialization, frozen immutability, properties, and backward compatibility features.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import pytest
from pydantic import ValidationError

from seo_agent.models.enums import ChangeFrequency, KeywordType
from seo_agent.models.seo import (
    CompetitorInfo,
    ContentRecommendation,
    FAQItem,
    InternalLink,
    JsonLdData,
    Keyword,
    Metadata,
    OpenGraphData,
    RobotsConfig,
    RobotsRule,
    SEOPage,
    SitemapEntry,
    StructuredData,
    TwitterCardData,
)
from seo_agent.models.seo_input import NormalizedSEOEntry, SEOInputCollection


# --- NormalizedSEOEntry Tests ---

def test_normalized_seo_entry_construction_and_defaults():
    """Test NormalizedSEOEntry default construction and compatibility properties."""
    entry = NormalizedSEOEntry(
        keyword="Recruitment Software",
        search_volume=10000,
        meta_title="Best Recruitment Software",
        meta_description="Enterprise recruitment software.",
        raw_data={
            "canonical": "https://example.com/ats",
            "h1": "Top ATS Platform",
            "og_title": "Social ATS",
            "twitter_card": "summary_large_image",
        },
    )

    assert entry.keyword == "Recruitment Software"
    assert entry.search_volume == 10000
    assert entry.competition == 0.0
    assert entry.search_intent == "informational"
    # Legacy property accessors
    assert entry.title == "Best Recruitment Software"
    assert entry.description == "Enterprise recruitment software."
    assert entry.canonical == "https://example.com/ats"
    assert entry.h1 == "Top ATS Platform"
    assert entry.og_title == "Social ATS"
    assert entry.twitter_card == "summary_large_image"


def test_normalized_seo_entry_positional_args():
    """Test positional arguments support for NormalizedSEOEntry."""
    entry = NormalizedSEOEntry("Talent Acquisition", 5000)
    assert entry.keyword == "Talent Acquisition"
    assert entry.search_volume == 5000


def test_seo_input_collection_serialization():
    """Test SEOInputCollection to_dict and from_dict roundtrip."""
    entry = NormalizedSEOEntry(keyword="Hiring Software", search_volume=3000)
    collection = SEOInputCollection(
        source_type="csv",
        source_path="/tmp/seo.csv",
        records=[entry],
        records_loaded=1,
    )

    data = collection.to_dict(mode="python")
    assert data["source_type"] == "csv"
    assert len(data["records"]) == 1

    restored = SEOInputCollection.from_dict(data)
    assert restored.source_type == "csv"
    assert restored.records[0].keyword == "Hiring Software"


# --- Keyword & Metadata Tests ---

def test_keyword_construction_and_frozen_immutability():
    """Test Keyword construction and frozen immutability."""
    kw = Keyword(term="SEO Tool", keyword_type=KeywordType.PRIMARY, search_volume=2000)
    assert kw.term == "SEO Tool"
    assert kw.keyword_type == KeywordType.PRIMARY

    with pytest.raises(ValidationError):
        kw.term = "Modified"  # Frozen constraint check


def test_metadata_nested_models_and_defaults():
    """Test Metadata model construction with default nested OpenGraph and TwitterCard models."""
    meta = Metadata(
        title="Page Title",
        description="Meta description text.",
        canonical_url="https://example.com/page",
    )

    assert meta.title == "Page Title"
    assert meta.description == "Meta description text."
    assert meta.robots == "index, follow"
    assert isinstance(meta.og, OpenGraphData)
    assert isinstance(meta.twitter, TwitterCardData)
    assert meta.og.type == "website"
    assert meta.twitter.card == "summary"


def test_metadata_null_og_twitter_fallback_validator():
    """Test that passing og=None or twitter=None falls back cleanly to default instances."""
    meta = Metadata(
        title="Fallback Title",
        description="Fallback Description",
        canonical_url="https://example.com/fallback",
        og=None,
        twitter=None,
    )
    assert meta.og is not None
    assert meta.og.type == "website"
    assert meta.twitter is not None
    assert meta.twitter.card == "summary"


# --- SEOPage & Sitemap Entry Tests ---

def test_seo_page_construction_and_dataclass_asdict_compat():
    """Test SEOPage model construction and dataclasses.asdict() compatibility."""
    meta = Metadata(
        title="SEO Landing Page",
        description="Description",
        canonical_url="https://example.com/seo/page",
    )
    page = SEOPage(
        slug="seo-page",
        title="SEO Landing Page",
        description="Description",
        h1="Main Heading",
        metadata=meta,
        route_path="/seo/page.html",
        file_path="/repo/seo/page.html",
    )

    assert page.slug == "seo-page"
    assert page.metadata.canonical_url == "https://example.com/seo/page"
    assert isinstance(page.created_at, datetime)

    # Verify dataclasses.asdict() compatibility helper
    import dataclasses
    print("FIELDS PAGE:", dataclasses.fields(page))
    print("FIELDS META:", dataclasses.fields(meta))
    d = asdict(page)
    print("D DICT:", d)
    assert isinstance(d, dict)
    assert d["slug"] == "seo-page"
    assert d["h1"] == "Main Heading"


def test_sitemap_and_robots_rules():
    """Test SitemapEntry and RobotsRule model defaults."""
    entry = SitemapEntry(url="https://example.com/index.html", priority=0.8)
    assert entry.change_frequency == ChangeFrequency.WEEKLY
    assert entry.priority == 0.8

    rule = RobotsRule(user_agent="Googlebot", disallow=("/admin", "/private"))
    assert rule.user_agent == "Googlebot"
    assert "/admin" in rule.disallow


def test_pagemetadata_to_metadata_conversion_and_seopage_boundary():
    """Test explicit PageMetadata to Metadata domain boundary conversion."""
    from seo_agent.models.repository import PageMetadata

    pm = PageMetadata(
        title="Page Title",
        description="Page Description",
        canonical="https://example.com/page",
        og_tags={"og:title": "OG Title", "og:description": "OG Desc"},
        twitter_tags={"twitter:card": "summary_large_image"},
        keywords=("seo", "test"),
    )

    meta = pm.to_metadata()
    assert isinstance(meta, Metadata)
    assert meta.title == "Page Title"
    assert meta.description == "Page Description"
    assert meta.canonical_url == "https://example.com/page"
    assert meta.og.title == "OG Title"
    assert meta.twitter.card == "summary_large_image"
    assert meta.keywords == ("seo", "test")

    page = SEOPage(
        slug="page-slug",
        title="Page Title",
        description="Page Description",
        h1="H1 Header",
        metadata=meta,
        route_path="/page",
        file_path="/repo/page.html",
    )
    assert page.metadata.canonical_url == "https://example.com/page"


def test_metadata_from_page_metadata_factory():
    """Test Metadata.from_page_metadata factory for PageMetadata, Metadata, and dict inputs."""
    from seo_agent.models.repository import PageMetadata

    pm = PageMetadata(title="Sample Page", description="Sample Desc")
    m1 = Metadata.from_page_metadata(pm)
    assert isinstance(m1, Metadata)
    assert m1.title == "Sample Page"

    m2 = Metadata.from_page_metadata(m1)
    assert m2 is m1

    m3 = Metadata.from_page_metadata({"title": "Dict Title", "description": "Dict Desc", "canonical_url": "https://ex.com"})
    assert isinstance(m3, Metadata)
    assert m3.title == "Dict Title"


def test_seopage_rejects_invalid_metadata_types():
    """Test that SEOPage rejects invalid raw types without explicit conversion."""
    from seo_agent.models.repository import PageMetadata

    pm = PageMetadata(title="Unconverted", description="Unconverted")
    with pytest.raises(ValidationError):
        SEOPage(
            slug="test",
            title="Test",
            description="Test",
            h1="Test",
            metadata=pm,  # Must fail Pydantic validation until explicitly converted
            route_path="/test",
            file_path="/repo/test.html",
        )

