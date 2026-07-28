"""Metadata optimization service.

This module provides functionality for optimizing SEO metadata on existing
pages. It updates title tags, meta descriptions, canonical URLs, robots
directives, Open Graph tags, Twitter Cards, and JSON-LD structured data.

The optimizer follows the Zero Disturbance Policy: it only modifies SEO-
related metadata and never touches content, styling, or functionality.

Usage:
    optimizer = MetadataOptimizer(container)
    result = await optimizer.optimize_page(page_path, metadata_updates)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from seo_agent.core.exceptions import SEOAgentError, ValidationError
from seo_agent.core.logging import get_logger
from seo_agent.core.result import Failure, Result, Success
from seo_agent.models.seo import Metadata

if TYPE_CHECKING:
    from seo_agent.core.dependency_injection import Container

logger = get_logger(__name__)


class MetadataOptimizationError(SEOAgentError):
    """Raised when metadata optimization fails."""
    pass


class MetadataOptimizer:
    """Service for optimizing SEO metadata on existing pages.

    This service updates existing pages with optimized SEO metadata
    including title, description, canonical URL, Open Graph, Twitter
    Cards, and structured data.

    Attributes:
        container: Dependency injection container.
        _repository_path: Path to the repository being optimized.
    """

    def __init__(
        self,
        container: Container,
        repository_path: Path | None = None,
    ) -> None:
        """Initialize the metadata optimizer.

        Args:
            container: Dependency injection container.
            repository_path: Optional path to the repository.
        """
        self._container = container
        self._repository_path = repository_path

    def set_repository_path(self, repository_path: Path) -> None:
        """Set the repository path for optimization.

        Args:
            repository_path: Path to the repository.
        """
        self._repository_path = repository_path

    def optimize_page(
        self,
        page_path: Path,
        metadata: Metadata,
        preserve_existing: bool = True,
    ) -> Result[Path, str]:
        """Optimize metadata for a single page.

        Args:
            page_path: Path to the HTML page to optimize.
            metadata: New metadata to apply.
            preserve_existing: If True, preserve existing non-SEO content.

        Returns:
            Success with updated page path if optimization succeeds.
            Failure with error message if optimization fails.
        """
        try:
            if not page_path.exists():
                return Failure(f"Page not found: {page_path}")

            if not page_path.suffix in (".html", ".htm", ".jsx", ".tsx", ".vue"):
                return Failure(f"Unsupported file type: {page_path.suffix}")

            content = page_path.read_text(encoding="utf-8")
            updated_content = self._apply_metadata(content, metadata)
            page_path.write_text(updated_content, encoding="utf-8")

            logger.info(f"Optimized metadata for: {page_path}")
            return Success(page_path)

        except Exception as e:
            error_msg = f"Failed to optimize metadata: {e}"
            logger.error(error_msg)
            return Failure(error_msg)

    def optimize_pages(
        self,
        page_paths: list[Path],
        metadata_updates: dict[str, Metadata],
        preserve_existing: bool = True,
    ) -> Result[list[Path], str]:
        """Optimize metadata for multiple pages.

        Args:
            page_paths: List of page paths to optimize.
            metadata_updates: Dictionary mapping page paths to metadata.
            preserve_existing: If True, preserve existing non-SEO content.

        Returns:
            Success with list of updated page paths.
            Failure with error message if optimization fails.
        """
        updated_paths: list[Path] = []
        errors: list[str] = []

        for page_path in page_paths:
            metadata = metadata_updates.get(str(page_path))
            if metadata:
                result = self.optimize_page(
                    page_path, metadata, preserve_existing
                )
                if result.is_success():
                    updated_paths.append(result.value)
                else:
                    errors.append(f"{page_path}: {result.error}")

        if errors:
            logger.warning(f"Errors during batch optimization: {errors}")

        return Success(updated_paths)

    def _apply_metadata(self, content: str, metadata: Metadata) -> str:
        """Apply metadata to HTML content.

        This method updates or inserts SEO-related meta tags while
        preserving all other content (Zero Disturbance Policy).

        Args:
            content: Original HTML content.
            metadata: Metadata to apply.

        Returns:
            Updated HTML content with optimized metadata.
        """
        result = content

        # Update title tag
        result = self._update_title_tag(result, metadata.title)

        # Update meta description
        result = self._update_meta_tag(
            result, "name", "description", metadata.description
        )

        # Update canonical URL
        result = self._update_canonical(result, metadata.canonical)

        # Update robots meta tag
        result = self._update_meta_tag(result, "name", "robots", metadata.robots)

        # Update keywords meta tag
        if metadata.keywords:
            keywords_str = ", ".join(metadata.keywords)
            result = self._update_meta_tag(
                result, "name", "keywords", keywords_str
            )

        # Update Open Graph tags
        result = self._update_og_tags(result, metadata)

        # Update Twitter Card tags
        result = self._update_twitter_tags(result, metadata)

        # Update JSON-LD structured data
        result = self._update_structured_data(result, metadata)

        return result

    def _update_title_tag(self, content: str, title: str) -> str:
        """Update or insert title tag.

        Args:
            content: HTML content.
            title: New title value.

        Returns:
            Updated HTML content.
        """
        import re

        # Check for existing title tag
        title_pattern = re.compile(
            r"<title[^>]*>(.*?)</title>",
            re.IGNORECASE | re.DOTALL
        )
        match = title_pattern.search(content)

        if match:
            # Update existing title
            new_title_tag = f"<title>{title}</title>"
            content = content[:match.start()] + new_title_tag + content[match.end():]
        else:
            # Insert title tag in head
            head_end = content.find("</head>")
            if head_end != -1:
                title_tag = f"<title>{title}</title>\n"
                content = content[:head_end] + title_tag + content[head_end:]

        return content

    def _update_meta_tag(
        self,
        content: str,
        attr_type: str,
        attr_name: str,
        value: str,
    ) -> str:
        """Update or insert a meta tag.

        Args:
            content: HTML content.
            attr_type: Attribute type (e.g., "name", "property").
            attr_name: Attribute name (e.g., "description").
            value: Meta tag content value.

        Returns:
            Updated HTML content.
        """
        import re

        # Pattern for meta tag with name or property attribute
        pattern = re.compile(
            rf'<meta\s+(?:[^>]*?\s+)?{attr_type}=["\'](?:{attr_name})["\'][^>]*>',
            re.IGNORECASE
        )
        new_tag = f'<meta {attr_type}="{attr_name}" content="{value}">'

        match = pattern.search(content)
        if match:
            # Update existing tag
            content = content[:match.start()] + new_tag + content[match.end():]
        else:
            # Insert new tag before </head>
            head_end = content.find("</head>")
            if head_end != -1:
                content = content[:head_end] + f"    {new_tag}\n" + content[head_end:]

        return content

    def _update_canonical(self, content: str, canonical_url: str) -> str:
        """Update or insert canonical URL link tag.

        Args:
            content: HTML content.
            canonical_url: Canonical URL value.

        Returns:
            Updated HTML content.
        """
        import re

        # Check for existing canonical link
        pattern = re.compile(
            r'<link\s+(?:[^>]*?\s+)?rel=["\']canonical["\'][^>]*>',
            re.IGNORECASE
        )
        new_tag = f'<link rel="canonical" href="{canonical_url}">'

        match = pattern.search(content)
        if match:
            # Update existing tag
            content = content[:match.start()] + new_tag + content[match.end():]
        else:
            # Insert new tag before </head>
            head_end = content.find("</head>")
            if head_end != -1:
                content = content[:head_end] + f"    {new_tag}\n" + content[head_end:]

        return content

    def _update_og_tags(self, content: str, metadata: Metadata) -> str:
        """Update Open Graph meta tags.

        Args:
            content: HTML content.
            metadata: Metadata containing OG data.

        Returns:
            Updated HTML content.
        """
        og = metadata.og
        if not og:
            return content

        # OG title
        if og.title:
            content = self._update_meta_tag(content, "property", "og:title", og.title)

        # OG description
        if og.description:
            content = self._update_meta_tag(
                content, "property", "og:description", og.description
            )

        # OG image
        if og.image:
            content = self._update_meta_tag(content, "property", "og:image", og.image)

        # OG URL
        if og.url:
            content = self._update_meta_tag(content, "property", "og:url", og.url)

        # OG type
        if og.type:
            content = self._update_meta_tag(content, "property", "og:type", og.type)

        # OG site name
        if og.site_name:
            content = self._update_meta_tag(
                content, "property", "og:site_name", og.site_name
            )

        return content

    def _update_twitter_tags(self, content: str, metadata: Metadata) -> str:
        """Update Twitter Card meta tags.

        Args:
            content: HTML content.
            metadata: Metadata containing Twitter Card data.

        Returns:
            Updated HTML content.
        """
        twitter = metadata.twitter
        if not twitter:
            return content

        # Twitter card type
        content = self._update_meta_tag(
            content, "name", "twitter:card", twitter.card
        )

        # Twitter title
        if twitter.title:
            content = self._update_meta_tag(
                content, "name", "twitter:title", twitter.title
            )

        # Twitter description
        if twitter.description:
            content = self._update_meta_tag(
                content, "name", "twitter:description", twitter.description
            )

        # Twitter image
        if twitter.image:
            content = self._update_meta_tag(
                content, "name", "twitter:image", twitter.image
            )

        # Twitter site
        if twitter.site:
            content = self._update_meta_tag(
                content, "name", "twitter:site", twitter.site
            )

        return content

    def _update_structured_data(
        self,
        content: str,
        metadata: Metadata,
    ) -> str:
        """Update JSON-LD structured data.

        Args:
            content: HTML content.
            metadata: Metadata containing structured data.

        Returns:
            Updated HTML content.
        """
        import json
        import re

        structured_data = metadata.structured_data
        if not structured_data:
            return content

        # Remove existing JSON-LD script tags
        jsonld_pattern = re.compile(
            r'<script\s+(?:[^>]*?\s+)?type=["\']application/ld\+json["\'][^>]*>.*?</script>',
            re.IGNORECASE | re.DOTALL
        )
        content = jsonld_pattern.sub("", content)

        # Insert new JSON-LD scripts before </head>
        for sd in structured_data:
            if sd.raw_json:
                jsonld_script = (
                    f'<script type="application/ld+json">\n'
                    f'{sd.raw_json}\n'
                    f'</script>\n'
                )
            else:
                jsonld_data = {
                    "@context": "https://schema.org",
                    "@type": sd.schema_type,
                    **sd.properties,
                }
                jsonld_script = (
                    f'<script type="application/ld+json">\n'
                    f'{json.dumps(jsonld_data, indent=2)}\n'
                    f'</script>\n'
                )

            head_end = content.find("</head>")
            if head_end != -1:
                content = content[:head_end] + jsonld_script + content[head_end:]

        return content

    def validate_metadata(self, metadata: Metadata) -> Result[Metadata, str]:
        """Validate metadata before applying.

        Args:
            metadata: Metadata to validate.

        Returns:
            Success with validated metadata if valid.
            Failure with validation error if invalid.
        """
        errors: list[str] = []

        # Validate title length
        if len(metadata.title) > 60:
            errors.append(
                f"Title exceeds 60 characters ({len(metadata.title)})"
            )

        # Validate description length
        if len(metadata.description) > 160:
            errors.append(
                f"Description exceeds 160 characters ({len(metadata.description)})"
            )

        # Validate canonical URL format
        if metadata.canonical and not metadata.canonical.startswith(
            ("http://", "https://")
        ):
            errors.append("Canonical URL must be an absolute URL")

        if errors:
            return Failure("; ".join(errors))

        return Success(metadata)