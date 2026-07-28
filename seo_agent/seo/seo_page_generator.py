"""SEO landing page generation service.

This module provides functionality for generating SEO-optimized landing
pages based on approved execution results. It creates new HTML pages with
proper metadata, structured data, and SEO best practices.

The generator creates pages that are ready for search engine indexing
with proper title tags, meta descriptions, Open Graph tags, and
structured data.

Usage:
    generator = SEOPageGenerator(container)
    result = await generator.generate_page(execution_result, output_path)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from seo_agent.core.exceptions import SEOAgentError
from seo_agent.core.logging import get_logger
from seo_agent.core.result import Failure, Result, Success
from seo_agent.models.seo import (
    JsonLdData,
    Metadata,
    OpenGraphData,
    SEOPage,
    StructuredData,
    TwitterCardData,
)
from seo_agent.models.task import ExecutionResult

if TYPE_CHECKING:
    from seo_agent.core.dependency_injection import Container

logger = get_logger(__name__)


class PageGenerationError(SEOAgentError):
    """Raised when page generation fails."""
    pass


class SEOPageGenerator:
    """Service for generating SEO-optimized landing pages.

    This service creates new HTML pages optimized for search engines
    based on approved execution results. Each generated page includes
    proper SEO metadata, structured data, and semantic HTML structure.

    Attributes:
        container: Dependency injection container.
        _output_directory: Directory for generated pages.
    """

    DEFAULT_TEMPLATE = """<!DOCTYPE html>
<html lang="{language}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="{description}">
    {canonical_tag}
    <meta name="robots" content="{robots}">
    {keywords_tag}
    {og_tags}
    {twitter_tags}
    {structured_data}
</head>
<body>
{content}
</body>
</html>"""

    def __init__(
        self,
        container: Container,
        output_directory: Path | None = None,
    ) -> None:
        """Initialize the SEO page generator.

        Args:
            container: Dependency injection container.
            output_directory: Optional directory for generated pages.
        """
        self._container = container
        self._output_directory = output_directory or Path("seo")
        self._template = self.DEFAULT_TEMPLATE

    def set_output_directory(self, output_directory: Path) -> None:
        """Set the output directory for generated pages.

        Args:
            output_directory: Path to the output directory.
        """
        self._output_directory = output_directory
        self._output_directory.mkdir(parents=True, exist_ok=True)

    def set_template(self, template: str) -> None:
        """Set a custom HTML template for page generation.

        Args:
            template: Custom HTML template string.
        """
        self._template = template

    def generate_page(
        self,
        execution_result: ExecutionResult,
        output_path: Path | None = None,
        metadata: Metadata | None = None,
    ) -> Result[SEOPage, str]:
        """Generate an SEO-optimized landing page.

        Args:
            execution_result: Approved execution result with content.
            output_path: Optional path for the output file.
            metadata: Optional metadata to override defaults.

        Returns:
            Success with generated SEOPage if generation succeeds.
            Failure with error message if generation fails.
        """
        try:
            # Validate execution result
            if not execution_result.seo_pages_created:
                return Failure("No SEO pages in execution result")

            # Get the first SEO page from execution result
            seo_page_data = execution_result.seo_pages_created[0]

            # Use provided metadata or create from execution result
            page_metadata = metadata or self._create_metadata_from_result(
                seo_page_data, execution_result
            )

            # Determine output path
            if output_path is None:
                filename = self._sanitize_filename(seo_page_data.title)
                output_path = self._output_directory / f"{filename}.html"
            else:
                output_path = output_path

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Generate HTML content
            html_content = self._generate_html(
                seo_page_data.title,
                page_metadata,
                seo_page_data.content,
                seo_page_data.language or "en",
            )

            # Write the file
            output_path.write_text(html_content, encoding="utf-8")

            # Create SEOPage model
            result_page = SEOPage(
                slug=output_path.stem,
                title=seo_page_data.title,
                description=page_metadata.description if page_metadata else "",
                h1=seo_page_data.title,
                metadata=page_metadata,
                route_path=f"/seo/{output_path.name}",
                file_path=str(output_path),
            )

            logger.info(f"Generated SEO page: {output_path}")
            return Success(result_page)

        except Exception as e:
            error_msg = f"Failed to generate page: {e}"
            logger.error(error_msg)
            return Failure(error_msg)

    def generate_pages(
        self,
        execution_results: list[ExecutionResult],
        output_directory: Path | None = None,
    ) -> Result[list[SEOPage], str]:
        """Generate multiple SEO-optimized landing pages.

        Args:
            execution_results: List of approved execution results.
            output_directory: Optional directory for generated pages.

        Returns:
            Success with list of generated SEOPages.
            Failure with error message if generation fails.
        """
        if output_directory:
            self._output_directory = output_directory

        generated_pages: list[SEOPage] = []
        errors: list[str] = []

        for result in execution_results:
            page_result = self.generate_page(result)
            if page_result.is_success():
                generated_pages.append(page_result.value)
            else:
                errors.append(page_result.error or "Unknown error")

        if errors:
            logger.warning(f"Errors during batch generation: {errors}")

        return Success(generated_pages)

    def _create_metadata_from_result(
        self,
        seo_page_data: dict[str, Any],
        execution_result: ExecutionResult,
    ) -> Metadata:
        """Create Metadata from execution result.

        Args:
            seo_page_data: SEO page data from execution result.
            execution_result: The full execution result.

        Returns:
            Created Metadata object.
        """
        title = seo_page_data.get("title", "Untitled Page")
        description = seo_page_data.get(
            "description",
            seo_page_data.get("meta_description", "")
        )

        # Create Open Graph data
        og = OpenGraphData(
            title=title,
            description=description,
            url=seo_page_data.get("url", ""),
            type=seo_page_data.get("og_type", "website"),
            image=seo_page_data.get("og_image", ""),
            site_name=seo_page_data.get("site_name", ""),
        )

        # Create Twitter Card data
        twitter = TwitterCardData(
            card="summary_large_image",
            title=title,
            description=description,
            image=seo_page_data.get("twitter_image", ""),
            site=seo_page_data.get("twitter_site", ""),
        )

        # Create structured data
        structured_data = []
        if seo_page_data.get("schema_type"):
            sd = StructuredData(
                schema_type=seo_page_data["schema_type"],
                properties=seo_page_data.get("schema_properties", {}),
            )
            structured_data.append(sd)

        return Metadata(
            title=title,
            description=description,
            canonical_url=seo_page_data.get("canonical_url", ""),
            robots=seo_page_data.get("robots", "index, follow"),
            keywords=seo_page_data.get("keywords", []),
            og=og,
            twitter=twitter,
            structured_data=structured_data,
        )

    def _generate_html(
        self,
        title: str,
        metadata: Metadata,
        content: str,
        language: str = "en",
    ) -> str:
        """Generate HTML content with SEO metadata.

        Args:
            title: Page title.
            metadata: SEO metadata.
            content: Page content.
            language: Page language code.

        Returns:
            Generated HTML string.
        """
        # Build canonical tag
        canonical_tag = ""
        if metadata.canonical:
            canonical_tag = f'<link rel="canonical" href="{metadata.canonical}">'

        # Build keywords tag
        keywords_tag = ""
        if metadata.keywords:
            keywords = ", ".join(metadata.keywords)
            keywords_tag = f'<meta name="keywords" content="{keywords}">'

        # Build Open Graph tags
        og_tags = ""
        if metadata.og:
            og = metadata.og
            if og.title:
                og_tags += f'    <meta property="og:title" content="{og.title}">\n'
            if og.description:
                og_tags += f'    <meta property="og:description" content="{og.description}">\n'
            if og.image:
                og_tags += f'    <meta property="og:image" content="{og.image}">\n'
            if og.url:
                og_tags += f'    <meta property="og:url" content="{og.url}">\n'
            if og.type:
                og_tags += f'    <meta property="og:type" content="{og.type}">\n'
            if og.site_name:
                og_tags += f'    <meta property="og:site_name" content="{og.site_name}">\n'

        # Build Twitter Card tags
        twitter_tags = ""
        if metadata.twitter:
            twitter = metadata.twitter
            twitter_tags += f'    <meta name="twitter:card" content="{twitter.card}">\n'
            if twitter.title:
                twitter_tags += f'    <meta name="twitter:title" content="{twitter.title}">\n'
            if twitter.description:
                twitter_tags += f'    <meta name="twitter:description" content="{twitter.description}">\n'
            if twitter.image:
                twitter_tags += f'    <meta name="twitter:image" content="{twitter.image}">\n'
            if twitter.site:
                twitter_tags += f'    <meta name="twitter:site" content="{twitter.site}">\n'

        # Build structured data
        structured_data = ""
        if metadata.structured_data:
            import json
            for sd in metadata.structured_data:
                if sd.raw_json:
                    structured_data += (
                        f'    <script type="application/ld+json">\n'
                        f'    {sd.raw_json}\n'
                        f'    </script>\n'
                    )
                else:
                    jsonld = {
                        "@context": "https://schema.org",
                        "@type": sd.schema_type,
                        **sd.properties,
                    }
                    structured_data += (
                        f'    <script type="application/ld+json">\n'
                        f'    {json.dumps(jsonld, indent=4)}\n'
                        f'    </script>\n'
                    )

        # Format content with proper indentation
        formatted_content = self._format_content(content)

        # Build final HTML
        html = self._template.format(
            language=language,
            title=title,
            description=metadata.description,
            canonical_tag=canonical_tag,
            robots=metadata.robots or "index, follow",
            keywords_tag=keywords_tag,
            og_tags=og_tags,
            twitter_tags=twitter_tags,
            structured_data=structured_data,
            content=formatted_content,
        )

        return html

    def _format_content(self, content: str) -> str:
        """Format HTML content with proper indentation.

        Args:
            content: Raw content string.

        Returns:
            Formatted content with proper indentation.
        """
        lines = content.split("\n")
        formatted_lines = []
        for line in lines:
            formatted_lines.append(f"    {line}")
        return "\n".join(formatted_lines)

    def _sanitize_filename(self, title: str) -> str:
        """Sanitize title for use as filename.

        Args:
            title: Page title.

        Returns:
            Sanitized filename string.
        """
        import re

        # Convert to lowercase
        filename = title.lower()

        # Replace spaces with hyphens
        filename = filename.replace(" ", "-")

        # Remove special characters
        filename = re.sub(r"[^a-z0-9\-]", "", filename)

        # Remove multiple consecutive hyphens
        filename = re.sub(r"-+", "-", filename)

        # Limit length
        if len(filename) > 50:
            filename = filename[:50].rstrip("-")

        return filename or "page"

    def validate_page(self, page: SEOPage) -> Result[SEOPage, str]:
        """Validate a generated SEO page.

        Args:
            page: SEOPage to validate.

        Returns:
            Success with validated page if valid.
            Failure with validation error if invalid.
        """
        errors: list[str] = []

        # Validate title
        if len(page.title) > 60:
            errors.append(
                f"Title exceeds 60 characters ({len(page.title)})"
            )

        # Validate description
        if page.metadata and len(page.metadata.description) > 160:
            errors.append(
                f"Description exceeds 160 characters "
                f"({len(page.metadata.description)})"
            )

        # Validate file exists
        if not Path(page.file_path).exists():
            errors.append(f"Page file does not exist: {page.file_path}")

        if errors:
            return Failure("; ".join(errors))

        return Success(page)