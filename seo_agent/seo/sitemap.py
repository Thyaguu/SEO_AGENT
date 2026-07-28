"""Sitemap management service.

This module provides functionality for creating and updating sitemap.xml
files. It preserves existing sitemap entries and appends newly approved
SEO pages while maintaining proper XML structure.

The sitemap service follows the Zero Disturbance Policy: it only modifies
the sitemap file and never touches any other project files.

Usage:
    sitemap_service = SitemapService(container)
    result = await sitemap_service.update_sitemap(pages)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from seo_agent.core.exceptions import SEOAgentError
from seo_agent.core.logging import get_logger
from seo_agent.core.result import Failure, Result, Success
from seo_agent.models.seo import ChangeFrequency, SEOPage, SitemapEntry

if TYPE_CHECKING:
    from seo_agent.core.dependency_injection import Container

logger = get_logger(__name__)


class SitemapError(SEOAgentError):
    """Raised when sitemap operations fail."""
    pass


class SitemapService:
    """Service for managing sitemap.xml files.

    This service creates and updates sitemap.xml files, preserving
    existing entries and adding new SEO pages. It supports both XML
    sitemap format and sitemap index files.

    Attributes:
        container: Dependency injection container.
        _sitemap_path: Path to the sitemap.xml file.
    """

    SITEMAP_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{entries}
</urlset>"""

    ENTRY_TEMPLATE = """  <url>
    <loc>{loc}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
  </url>"""

    def __init__(
        self,
        container: Container,
        sitemap_path: Path | None = None,
    ) -> None:
        """Initialize the sitemap service.

        Args:
            container: Dependency injection container.
            sitemap_path: Optional path to sitemap.xml.
        """
        self._container = container
        self._sitemap_path = sitemap_path or Path("sitemap.xml")

    def set_sitemap_path(self, sitemap_path: Path) -> None:
        """Set the sitemap file path.

        Args:
            sitemap_path: Path to the sitemap.xml file.
        """
        self._sitemap_path = sitemap_path

    def create_sitemap(
        self,
        pages: list[SEOPage],
        base_url: str = "https://example.com",
    ) -> Result[Path, str]:
        """Create a new sitemap.xml file.

        Args:
            pages: List of SEO pages to include.
            base_url: Base URL for the site.

        Returns:
            Success with sitemap path if creation succeeds.
            Failure with error message if creation fails.
        """
        try:
            entries = self._generate_entries(pages, base_url)
            sitemap_content = self.SITEMAP_TEMPLATE.format(entries=entries)

            self._sitemap_path.write_text(sitemap_content, encoding="utf-8")

            logger.info(f"Created sitemap: {self._sitemap_path}")
            return Success(self._sitemap_path)

        except Exception as e:
            error_msg = f"Failed to create sitemap: {e}"
            logger.error(error_msg)
            return Failure(error_msg)

    def update_sitemap(
        self,
        pages: list[SEOPage],
        base_url: str = "https://example.com",
        preserve_existing: bool = True,
    ) -> Result[Path, str]:
        """Update an existing sitemap.xml file.

        This method preserves existing entries and adds new SEO pages.

        Args:
            pages: List of SEO pages to add.
            base_url: Base URL for the site.
            preserve_existing: If True, preserve existing entries.

        Returns:
            Success with sitemap path if update succeeds.
            Failure with error message if update fails.
        """
        try:
            existing_entries: list[SitemapEntry] = []

            if preserve_existing and self._sitemap_path.exists():
                existing_entries = self._parse_existing_sitemap()

            # Add new pages as entries
            new_entries = self._pages_to_entries(pages, base_url)

            # Merge entries (new entries override existing for same URL)
            all_entries = self._merge_entries(existing_entries, new_entries)

            # Generate sitemap content
            entries_xml = self._entries_to_xml(all_entries)
            sitemap_content = self.SITEMAP_TEMPLATE.format(entries=entries_xml)

            # Write sitemap
            self._sitemap_path.write_text(sitemap_content, encoding="utf-8")

            logger.info(f"Updated sitemap: {self._sitemap_path}")
            return Success(self._sitemap_path)

        except Exception as e:
            error_msg = f"Failed to update sitemap: {e}"
            logger.error(error_msg)
            return Failure(error_msg)

    def add_page(
        self,
        page: SEOPage,
        base_url: str = "https://example.com",
    ) -> Result[Path, str]:
        """Add a single page to the sitemap.

        Args:
            page: SEO page to add.
            base_url: Base URL for the site.

        Returns:
            Success with sitemap path if addition succeeds.
            Failure with error message if addition fails.
        """
        return self.update_sitemap([page], base_url, preserve_existing=True)

    def remove_page(
        self,
        page_url: str,
    ) -> Result[Path, str]:
        """Remove a page from the sitemap.

        Args:
            page_url: URL of the page to remove.

        Returns:
            Success with sitemap path if removal succeeds.
            Failure with error message if removal fails.
        """
        try:
            if not self._sitemap_path.exists():
                return Failure("Sitemap does not exist")

            existing_entries = self._parse_existing_sitemap()

            # Filter out the page to remove
            remaining_entries = [
                entry for entry in existing_entries
                if entry.loc != page_url
            ]

            # Generate sitemap content
            entries_xml = self._entries_to_xml(remaining_entries)
            sitemap_content = self.SITEMAP_TEMPLATE.format(entries=entries_xml)

            # Write sitemap
            self._sitemap_path.write_text(sitemap_content, encoding="utf-8")

            logger.info(f"Removed page from sitemap: {page_url}")
            return Success(self._sitemap_path)

        except Exception as e:
            error_msg = f"Failed to remove page from sitemap: {e}"
            logger.error(error_msg)
            return Failure(error_msg)

    def _generate_entries(
        self,
        pages: list[SEOPage],
        base_url: str,
    ) -> str:
        """Generate XML entries for pages.

        Args:
            pages: List of SEO pages.
            base_url: Base URL for the site.

        Returns:
            XML string of sitemap entries.
        """
        entries = self._pages_to_entries(pages, base_url)
        return self._entries_to_xml(entries)

    def _pages_to_entries(
        self,
        pages: list[SEOPage],
        base_url: str,
    ) -> list[SitemapEntry]:
        """Convert SEOPage objects to SitemapEntry objects.

        Args:
            pages: List of SEO pages.
            base_url: Base URL for the site.

        Returns:
            List of sitemap entries.
        """
        entries = []
        for page in pages:
            if not page.route_path:
                raise ValueError(f"SEOPage missing required route_path for sitemap entry: {page}")

            # Build full URL
            page_url = self._build_url(base_url, page.route_path)

            # Get priority from metadata if available
            priority = 0.5
            if page.metadata and page.metadata.structured_data:
                # Use schema type to determine priority
                schema_types = list(page.metadata.structured_data)
                if "WebPage" in schema_types or "Article" in schema_types:
                    priority = 0.8
                elif "Product" in schema_types:
                    priority = 0.9

            entry = SitemapEntry(
                url=page_url,
                last_modified=datetime.now(),
                change_frequency=ChangeFrequency.WEEKLY,
                priority=priority,
            )
            entries.append(entry)

        return entries

    def _build_url(self, base_url: str, path: Path) -> str:
        """Build full URL from base URL and path.

        Args:
            base_url: Base URL for the site.
            path: File path.

        Returns:
            Full URL string.
        """
        # Remove leading slash from path if present
        relative_path = str(path).lstrip("/")

        # Ensure base URL doesn't end with slash
        base = base_url.rstrip("/")

        return f"{base}/{relative_path}"

    def _merge_entries(
        self,
        existing: list[SitemapEntry],
        new: list[SitemapEntry],
    ) -> list[SitemapEntry]:
        """Merge existing and new entries.

        New entries override existing entries with the same URL.

        Args:
            existing: Existing sitemap entries.
            new: New sitemap entries to add.

        Returns:
            Merged list of entries.
        """
        # Create a dictionary for quick lookup
        entries_dict: dict[str, SitemapEntry] = {}

        # Add existing entries
        for entry in existing:
            entries_dict[entry.url] = entry

        # Add new entries (override existing)
        for entry in new:
            entries_dict[entry.url] = entry

        # Return sorted list
        return sorted(entries_dict.values(), key=lambda e: e.url)

    def _entries_to_xml(self, entries: list[SitemapEntry]) -> str:
        """Convert entries to XML string.

        Args:
            entries: List of sitemap entries.

        Returns:
            XML string of entries.
        """
        if not entries:
            return ""

        entry_xmls = []
        for entry in entries:
            lastmod_str = (
                entry.last_modified.strftime("%Y-%m-%d")
                if isinstance(entry.last_modified, datetime)
                else (entry.last_modified or datetime.now().strftime("%Y-%m-%d"))
            )
            entry_xml = self.ENTRY_TEMPLATE.format(
                loc=entry.url,
                lastmod=lastmod_str,
                changefreq=entry.change_frequency.value if hasattr(entry.change_frequency, "value") else str(entry.change_frequency),
                priority=f"{entry.priority:.1f}",
            )
            entry_xmls.append(entry_xml)

        return "\n".join(entry_xmls)

    def _parse_existing_sitemap(self) -> list[SitemapEntry]:
        """Parse existing sitemap.xml file.

        Returns:
            List of sitemap entries from existing file.
        """
        import re

        entries: list[SitemapEntry] = []
        content = self._sitemap_path.read_text(encoding="utf-8")

        # Pattern for URL entries
        url_pattern = re.compile(
            r"<url>\s*"
            r"<loc>(.*?)</loc>\s*"
            r"(?:<lastmod>(.*?)</lastmod>\s*)?"
            r"(?:<changefreq>(.*?)</changefreq>\s*)?"
            r"(?:<priority>(.*?)</priority>\s*)?"
            r"</url>",
            re.DOTALL,
        )

        for match in url_pattern.finditer(content):
            loc = match.group(1)
            lastmod_str = match.group(2)
            changefreq_str = match.group(3)
            priority_str = match.group(4)

            # Parse changefreq
            changefreq = ChangeFrequency.WEEKLY
            if changefreq_str:
                try:
                    changefreq = ChangeFrequency(changefreq_str)
                except ValueError:
                    changefreq = ChangeFrequency.WEEKLY

            # Parse priority
            priority = 0.5
            if priority_str:
                try:
                    priority = float(priority_str)
                except ValueError:
                    priority = 0.5

            last_modified = None
            if lastmod_str:
                try:
                    last_modified = datetime.strptime(lastmod_str.strip(), "%Y-%m-%d")
                except ValueError:
                    last_modified = None

            entry = SitemapEntry(
                url=loc,
                last_modified=last_modified,
                change_frequency=changefreq,
                priority=priority,
            )
            entries.append(entry)

        return entries

    def validate_sitemap(self, sitemap_path: Path | None = None) -> Result[bool, str]:
        """Validate a sitemap.xml file.

        Args:
            sitemap_path: Optional path to sitemap to validate.

        Returns:
            Success with True if valid.
            Failure with validation error if invalid.
        """
        path = sitemap_path or self._sitemap_path

        if not path.exists():
            return Failure(f"Sitemap not found: {path}")

        try:
            content = path.read_text(encoding="utf-8")

            # Check for required elements
            if '<?xml version="1.0" encoding="UTF-8"?>' not in content:
                return Failure("Missing XML declaration")

            if "<urlset" not in content:
                return Failure("Missing urlset element")

            if "</urlset>" not in content:
                return Failure("Missing closing urlset element")

            # Check for at least one URL
            if "<url>" not in content:
                logger.warning("Sitemap has no URL entries")

            return Success(True)

        except Exception as e:
            return Failure(f"Sitemap validation failed: {e}")