"""Focused unit tests for migrated repository analysis Pydantic models.

Tests construction, defaults, optional fields, enum fields, nested models,
serialization, deserialization, frozen immutability, and backward compatibility.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
import pytest
from pydantic import ValidationError

from seo_agent.models.enums import FrameworkType, PageType, RoutingStrategy
from seo_agent.models.repository import (
    DiscoveredPage,
    FileInfo,
    FrameworkInfo,
    Heading,
    PageAnalysisResult,
    PageInfo,
    PageMetadata,
    RepositoryInfo,
    RepositoryScanOptions,
    RobotsInfo,
    SitemapInfo,
)


def test_discovered_page_construction_and_defaults():
    """Test DiscoveredPage construction, defaults, and frozen immutability."""
    page = DiscoveredPage(
        url_path="/about",
        file_path="/repo/about.html",
        page_type=PageType.PAGE,
        title="About Us",
    )

    assert page.url_path == "/about"
    assert page.file_path == "/repo/about.html"
    assert page.page_type == PageType.PAGE
    assert page.title == "About Us"
    assert page.has_dynamic_params is False

    with pytest.raises(ValidationError):
        page.title = "New Title"


def test_framework_info_defaults_and_positional_args():
    """Test FrameworkInfo positional construction and default values."""
    framework = FrameworkInfo(FrameworkType.NEXT_JS, RoutingStrategy.FILE_BASED)
    assert framework.framework_type == FrameworkType.NEXT_JS
    assert framework.routing_strategy == RoutingStrategy.FILE_BASED
    assert framework.package_manager is None
    assert framework.config_files == ()


def test_file_info_and_heading():
    """Test FileInfo and Heading models construction and serialization."""
    file_info = FileInfo(
        path="src/index.tsx",
        absolute_path="/app/src/index.tsx",
        size_bytes=1024,
        extension=".tsx",
    )
    assert file_info.path == "src/index.tsx"
    assert file_info.is_text is True

    heading = Heading(level=1, text="Welcome", id="hero")
    assert heading.level == 1
    assert heading.text == "Welcome"
    assert heading.id == "hero"


def test_page_metadata_and_page_info_nesting():
    """Test nested PageMetadata inside PageInfo model."""
    heading = Heading(level=1, text="Header 1")
    metadata = PageMetadata(
        title="Page Title",
        description="Meta description.",
        h1="Header 1",
        headings=(heading,),
    )
    page_info = PageInfo(
        route="/products",
        file_path="/repo/products.html",
        page_type=PageType.PRODUCT,
        metadata=metadata,
    )

    assert page_info.route == "/products"
    assert page_info.metadata is not None
    assert page_info.metadata.title == "Page Title"
    assert page_info.metadata.headings[0].text == "Header 1"


def test_repository_info_serialization_roundtrip():
    """Test RepositoryInfo complete serialization and deserialization roundtrip."""
    framework = FrameworkInfo(framework_type=FrameworkType.REACT)
    page = PageInfo(route="/index.html", file_path="/repo/index.html")
    sitemap = SitemapInfo(file_path="/repo/sitemap.xml", exists=True)
    robots = RobotsInfo(file_path="/repo/robots.txt", exists=True)

    repo_info = RepositoryInfo(
        root_path="/repo",
        framework=framework,
        pages=(page,),
        sitemap=sitemap,
        robots=robots,
    )

    assert repo_info.root_path == "/repo"
    assert repo_info.framework.framework_type == FrameworkType.REACT
    assert len(repo_info.pages) == 1

    d = repo_info.to_dict(mode="python")
    assert d["root_path"] == "/repo"

    restored = RepositoryInfo.from_dict(d)
    assert restored.root_path == "/repo"
    assert restored.framework.framework_type == FrameworkType.REACT


def test_repository_scan_options_and_page_analysis_result():
    """Test RepositoryScanOptions defaults and PageAnalysisResult wrapper."""
    opts = RepositoryScanOptions(max_depth=3)
    assert opts.max_depth == 3
    assert "node_modules" in opts.exclude_patterns

    page = PageInfo(route="/contact", file_path="/repo/contact.html")
    result = PageAnalysisResult(page=page, extracted_keywords=("contact", "support"))
    assert result.success is True
    assert result.extracted_keywords == ("contact", "support")


def test_dataclasses_asdict_and_is_dataclass_backward_compatibility():
    """Test dataclasses.asdict() and is_dataclass() compatibility helpers on repository models."""
    heading = Heading(level=2, text="Subheading")
    assert is_dataclass(heading)

    d = asdict(heading)
    assert isinstance(d, dict)
    assert d["level"] == 2
    assert d["text"] == "Subheading"


def test_model_replace_helper():
    """Test replace() dataclass-style immutability update helper."""
    orig = PageInfo(route="/old", file_path="/repo/old.html")
    updated = orig.replace(route="/new", file_path="/repo/new.html")

    assert orig.route == "/old"
    assert updated.route == "/new"
    assert updated.file_path == "/repo/new.html"
