"""Metadata extraction service.

This module provides functionality to extract SEO metadata from HTML files,
including titles, meta descriptions, Open Graph tags, Twitter Cards,
structured data, and JSON-LD.

Usage:
    from seo_agent.repository.metadata_parser import MetadataParser

    parser = MetadataParser()
    result = parser.parse_file("/path/to/page.html")
    if result.is_success():
        metadata = result.value
        print(f"Title: {metadata.title}")
        print(f"Description: {metadata.description}")
"""

import dataclasses
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from seo_agent.core.logging import get_logger
from seo_agent.core.result import Result, success, Failure
from seo_agent.models.repository import Heading, PageMetadata
from seo_agent.models.seo import (
    OpenGraphData,
    TwitterCardData,
    StructuredData,
    JsonLdData,
)

if TYPE_CHECKING:
    from seo_agent.models.seo import DiscoveredPage


class MetadataParser:
    """Extracts SEO metadata from HTML files.

    This class parses HTML files to extract various SEO-related metadata
    including title, meta tags, Open Graph, Twitter Cards, and structured data.

    Attributes:
        _logger: Logger instance for the parser.

    Example:
        parser = MetadataParser()
        result = parser.parse_file("/path/to/page.html")
        if result.is_success():
            print(result.value.title)
    """

    def __init__(self) -> None:
        """Initialize the metadata parser."""
        self._logger = get_logger(__name__)

    def parse_file(
        self,
        file_path: str | Path,
        url_path: str | None = None,
    ) -> Result[PageMetadata, str]:
        """Parse SEO metadata from an HTML file.

        Args:
            file_path: Path to the HTML file.
            url_path: Optional URL path for the page.

        Returns:
            Result containing PageMetadata on success.
        """
        path = Path(file_path)

        if not path.exists():
            return Result.failure(f"File does not exist: {path}")

        if not path.is_file():
            return Result.failure(f"Not a file: {path}")

        self._logger.debug(f"parsing_metadata: file={path}")

        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                content = f.read()

            return self.parse_content(content, url_path or str(path))

        except OSError as e:
            self._logger.error(f"file_read_failed: {path} — {e}", exc_info=e)
            return Result.failure(f"Failed to read file: {e}")

    def parse_content(
        self,
        html_content: str,
        url_path: str,
    ) -> Result[PageMetadata, str]:
        """Parse SEO metadata from HTML content.

        Args:
            html_content: Raw HTML content.
            url_path: URL path for the page.

        Returns:
            Result containing PageMetadata on success.
        """
        try:
            # Extract basic metadata
            title = self._extract_title(html_content)
            meta_description = self._extract_meta_description(html_content)
            canonical = self._extract_canonical(html_content)
            robots = self._extract_robots(html_content)

            # Extract Open Graph data
            og_data = self._extract_open_graph(html_content)

            # Extract Twitter Cards
            twitter_card = self._extract_twitter_cards(html_content)

            # Extract structured data
            structured_data = self._extract_structured_data(html_content)

            # Extract JSON-LD
            json_ld = self._extract_json_ld(html_content)

            # Extract headings
            h1_tags = self._extract_headings(html_content, "h1")
            h2_tags = self._extract_headings(html_content, "h2")

            # Extract images for alt text analysis
            images = self._extract_images(html_content)
            metadata = PageMetadata(
                title=title,
                description=meta_description,
                canonical=canonical,
                og_tags=vars(og_data) if og_data else {},
                twitter_tags=asdict(twitter_card) if twitter_card else {},
                structured_data=tuple(s.schema_type for s in structured_data),
                h1=h1_tags[0] if h1_tags else None,
                headings=tuple(Heading(level=1, text=tag, id=None) for tag in h1_tags)
                + tuple(Heading(level=2, text=tag, id=None) for tag in h2_tags),
            )

            self._logger.debug(
                f"metadata_parsed: path={url_path}, has_title={bool(title)}, has_description={bool(meta_description)}"
            )

            return success(metadata)

        except Exception as e:
            self._logger.error(f"metadata_parse_failed: {url_path} — {e}", exc_info=e)
            return Result.failure(f"Failed to parse metadata: {e}")

    def parse_batch(
        self,
        file_paths: list[str | Path],
    ) -> Result[list[PageMetadata], str]:
        """Parse metadata from multiple files.

        Args:
            file_paths: List of file paths to parse.

        Returns:
            Result containing list of PageMetadata.
        """
        results: list[PageMetadata] = []
        errors: list[str] = []

        for file_path in file_paths:
            result = self.parse_file(file_path)
            if result.is_success():
                results.append(result.value)
            else:
                errors.append(f"{file_path}: {result.error}")

        if errors:
            self._logger.warning(f"batch_parse_partial: errors={errors}")

        return success(results)

    def _extract_title(self, html: str) -> str | None:
        """Extract page title from HTML.

        Args:
            html: HTML content.

        Returns:
            Page title or None.
        """
        match = re.search(
            r"<title[^>]*>([^<]+)</title>",
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            return self._clean_text(match.group(1).strip())
        return None

    def _extract_meta_description(self, html: str) -> str | None:
        """Extract meta description from HTML.

        Args:
            html: HTML content.

        Returns:
            Meta description or None.
        """
        match = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            return self._clean_text(match.group(1).strip())

        # Try alternate attribute order
        match = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            return self._clean_text(match.group(1).strip())

        return None

    def _extract_canonical(self, html: str) -> str | None:
        """Extract canonical URL from HTML.

        Args:
            html: HTML content.

        Returns:
            Canonical URL or None.
        """
        match = re.search(
            r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        # Try alternate attribute order
        match = re.search(
            r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']canonical["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        return None

    def _extract_robots(self, html: str) -> str | None:
        """Extract robots meta directive from HTML.

        Args:
            html: HTML content.

        Returns:
            Robots directive or None.
        """
        match = re.search(
            r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        # Try alternate order
        match = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']robots["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        return None

    def _extract_open_graph(self, html: str) -> OpenGraphData | None:
        """Extract Open Graph data from HTML.

        Args:
            html: HTML content.

        Returns:
            OpenGraphData or None.
        """
        og_properties = {
            "og:title": "title",
            "og:description": "description",
            "og:image": "image",
            "og:url": "url",
            "og:type": "type",
            "og:site_name": "site_name",
            "og:locale": "locale",
            "og:video": "video",
            "og:audio": "audio",
        }

        data: dict[str, str] = {}

        for property_name, key in og_properties.items():
            # Try property attribute
            pattern = rf'<meta[^>]+property=["\'{re.escape(property_name)}["\'][^>]+content=["\']([^"\']+)["\']'
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                data[key] = match.group(1).strip()
                continue

            # Try alternate order
            pattern = rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\'{re.escape(property_name)}["\']'
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                data[key] = match.group(1).strip()

        if not data:
            return None

        return OpenGraphData(**data)

    def _extract_twitter_cards(self, html: str) -> TwitterCardData | None:
        """Extract Twitter Card data from HTML.

        Args:
            html: HTML content.

        Returns:
            TwitterCardData or None.
        """
        twitter_properties = {
            "twitter:card": "card",
            "twitter:title": "title",
            "twitter:description": "description",
            "twitter:image": "image",
            "twitter:site": "site",
        }

        data: dict[str, str] = {}

        for property_name, key in twitter_properties.items():
            # Try name attribute (Twitter uses name, not property)
            pattern = rf'<meta[^>]+name=["\'{re.escape(property_name)}["\'][^>]+content=["\']([^"\']+)["\']'
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                data[key] = match.group(1).strip()
                continue

            # Try alternate order
            pattern = rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\'{re.escape(property_name)}["\']'
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                data[key] = match.group(1).strip()

        if not data:
            return None

        return TwitterCardData(**data)

    def _extract_structured_data(self, html: str) -> list[StructuredData]:
        """Extract structured data (JSON-LD) from HTML.

        Args:
            html: HTML content.

        Returns:
            List of StructuredData objects.
        """
        structured_data_list: list[StructuredData] = []

        # Find all script tags with type="application/ld+json"
        pattern = r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>([^<]+)</script>'
        matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)

        for match in matches:
            try:
                json_content = match.group(1).strip()
                data = json.loads(json_content)

                # Handle @graph array
                if isinstance(data, dict) and "@graph" in data:
                    items = data["@graph"]
                elif isinstance(data, list):
                    items = data
                else:
                    items = [data]

                for item in items:
                    if isinstance(item, dict):
                        schema_type = str(item.get("@type", "Unknown"))
                        structured_data_list.append(
                            StructuredData(
                                schema_type=schema_type,
                                properties=item,
                            )
                        )

            except json.JSONDecodeError:
                self._logger.warning(f"invalid_json_ld: content={match.group(1)[:100]}")

        return structured_data_list

    def _extract_json_ld(self, html: str) -> list[JsonLdData]:
        """Extract JSON-LD data from HTML.

        Args:
            html: HTML content.

        Returns:
            List of JsonLdData objects.
        """
        json_ld_list: list[JsonLdData] = []

        pattern = r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>([^<]+)</script>'
        matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)

        for match in matches:
            try:
                json_content = match.group(1).strip()
                data = json.loads(json_content)

                # Determine context
                context = data.get("@context", "unknown")

                json_ld_list.append(
                    JsonLdData(
                        context=str(context),
                        type=data.get("@type"),
                        data=data,
                    )
                )

            except json.JSONDecodeError:
                pass

        return json_ld_list

    def _extract_headings(self, html: str, tag: str) -> list[str]:
        """Extract heading text from HTML.

        Args:
            html: HTML content.
            tag: Heading tag (h1, h2, h3, etc.).

        Returns:
            List of heading texts.
        """
        pattern = rf"<{tag}[^>]*>([^<]+)</{tag}>"
        matches = re.finditer(pattern, html, re.IGNORECASE)
        return [self._clean_text(m.group(1).strip()) for m in matches]

    def _extract_images(self, html: str) -> list[dict[str, str]]:
        """Extract image information from HTML.

        Args:
            html: HTML content.

        Returns:
            List of image data dictionaries.
        """
        images: list[dict[str, str]] = []

        # Find img tags
        img_pattern = r"<img[^>]+>"
        for img_match in re.finditer(img_pattern, html, re.IGNORECASE):
            img_tag = img_match.group(0)

            image_data: dict[str, str] = {}

            # Extract src
            src_match = re.search(r'src=["\']([^"\']+)["\']', img_tag)
            if src_match:
                image_data["src"] = src_match.group(1)

            # Extract alt
            alt_match = re.search(r'alt=["\']([^"\']*)["\']', img_tag)
            if alt_match:
                image_data["alt"] = alt_match.group(1)

            # Extract title
            title_match = re.search(r'title=["\']([^"\']*)["\']', img_tag)
            if title_match:
                image_data["title"] = title_match.group(1)

            # Extract loading attribute
            loading_match = re.search(r'loading=["\']([^"\']+)["\']', img_tag)
            if loading_match:
                image_data["loading"] = loading_match.group(1)

            if image_data:
                images.append(image_data)

        return images

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content.

        Args:
            text: Raw text content.

        Returns:
            Cleaned text.
        """
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def validate_metadata(
        self,
        metadata: PageMetadata,
    ) -> Result[dict[str, list[str]], str]:
        """Validate SEO metadata and return issues.

        Args:
            metadata: PageMetadata to validate.

        Returns:
            Result containing dictionary of validation issues.
        """
        issues: dict[str, list[str]] = {
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        # Check title
        if not metadata.title:
            issues["errors"].append("Missing page title")
        elif len(metadata.title) < 30:
            issues["warnings"].append(f"Title too short ({len(metadata.title)} chars, recommended: 50-60)")
        elif len(metadata.title) > 60:
            issues["warnings"].append(f"Title too long ({len(metadata.title)} chars, recommended: 50-60)")

        # Check meta description
        if not metadata.description:
            issues["errors"].append("Missing meta description")
        elif len(metadata.description) < 120:
            issues["warnings"].append(f"Description too short ({len(metadata.description)} chars, recommended: 150-160)")
        elif len(metadata.description) > 160:
            issues["warnings"].append(f"Description too long ({len(metadata.description)} chars, recommended: 150-160)")

        # Check canonical
        if not metadata.canonical:
            issues["suggestions"].append("Missing canonical URL")

        # Check Open Graph
        if not metadata.og_tags:
            issues["suggestions"].append("Missing Open Graph tags")
        else:
            if not metadata.og_tags.get("og:title"):
                issues["warnings"].append("Open Graph title missing")
            if not metadata.og_tags.get("og:description"):
                issues["warnings"].append("Open Graph description missing")
            if not metadata.og_tags.get("og:image"):
                issues["warnings"].append("Open Graph image missing")

        # Check Twitter Cards
        if not metadata.twitter_tags:
            issues["suggestions"].append("Missing Twitter Card tags")

        # Check H1 tag
        if not metadata.h1:
            issues["errors"].append("No H1 tag found")

        return success(issues)