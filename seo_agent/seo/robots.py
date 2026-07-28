"""robots.txt management service.

This module provides functionality for creating and updating robots.txt
files. It preserves existing directives and appends sitemap location
while maintaining proper robots.txt format.

The robots service follows the Zero Disturbance Policy: it only modifies
the robots.txt file and never touches any other project files.

Usage:
    robots_service = RobotsService(container)
    result = await robots_service.update_robots(sitemap_url)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from seo_agent.core.exceptions import SEOAgentError
from seo_agent.core.logging import get_logger
from seo_agent.core.result import Failure, Result, Success

if TYPE_CHECKING:
    from seo_agent.core.dependency_injection import Container

logger = get_logger(__name__)


class RobotsError(SEOAgentError):
    """Raised when robots.txt operations fail."""
    pass


class DirectiveType(Enum):
    """Type of robots.txt directive."""
    ALLOW = "Allow"
    DISALLOW = "Disallow"
    CRAWL_DELAY = "Crawl-delay"


@dataclass
class RobotsDirective:
    """Represents a robots.txt directive.

    Attributes:
        user_agent: The user-agent the directive applies to.
        directive_type: Type of directive (ALLOW, DISALLOW, CRAWL_DELAY).
        path: The path the directive applies to.
        priority: Priority of the directive (higher = checked first).
    """
    user_agent: str
    directive_type: DirectiveType
    path: str
    priority: int = 0


class RobotsService:
    """Service for managing robots.txt files.

    This service creates and updates robots.txt files, preserving
    existing directives and adding sitemap location. It supports
    standard robots.txt format including wildcards.

    Attributes:
        container: Dependency injection container.
        _robots_path: Path to the robots.txt file.
    """

    def __init__(
        self,
        container: Container,
        robots_path: Path | None = None,
    ) -> None:
        """Initialize the robots service.

        Args:
            container: Dependency injection container.
            robots_path: Optional path to robots.txt.
        """
        self._container = container
        self._robots_path = robots_path or Path("robots.txt")

    def set_robots_path(self, robots_path: Path) -> None:
        """Set the robots.txt file path.

        Args:
            robots_path: Path to the robots.txt file.
        """
        self._robots_path = robots_path

    def create_robots(
        self,
        sitemap_url: str | None = None,
        default_user_agent: str = "*",
    ) -> Result[Path, str]:
        """Create a new robots.txt file.

        Args:
            sitemap_url: Optional sitemap URL to include.
            default_user_agent: Default user-agent for directives.

        Returns:
            Success with robots.txt path if creation succeeds.
            Failure with error message if creation fails.
        """
        try:
            directives = [
                RobotsDirective(
                    user_agent=default_user_agent,
                    directive_type=DirectiveType.ALLOW,
                    path="/",
                    priority=1,
                ),
            ]

            content = self._directives_to_text(directives, sitemap_url)

            self._robots_path.write_text(content, encoding="utf-8")

            logger.info(f"Created robots.txt: {self._robots_path}")
            return Success(self._robots_path)

        except Exception as e:
            error_msg = f"Failed to create robots.txt: {e}"
            logger.error(error_msg)
            return Failure(error_msg)

    def update_robots(
        self,
        sitemap_url: str | None = None,
        preserve_existing: bool = True,
    ) -> Result[Path, str]:
        """Update an existing robots.txt file.

        This method preserves existing directives and adds sitemap location.

        Args:
            sitemap_url: Sitemap URL to add.
            preserve_existing: If True, preserve existing directives.

        Returns:
            Success with robots.txt path if update succeeds.
            Failure with error message if update fails.
        """
        try:
            existing_directives: list[RobotsDirective] = []
            existing_sitemap: str | None = None

            if preserve_existing and self._robots_path.exists():
                existing_directives, existing_sitemap = (
                    self._parse_existing_robots()
                )

            # Generate content
            content = self._directives_to_text(
                existing_directives,
                sitemap_url or existing_sitemap,
            )

            # Write robots.txt
            self._robots_path.write_text(content, encoding="utf-8")

            logger.info(f"Updated robots.txt: {self._robots_path}")
            return Success(self._robots_path)

        except Exception as e:
            error_msg = f"Failed to update robots.txt: {e}"
            logger.error(error_msg)
            return Failure(error_msg)

    def add_directive(
        self,
        user_agent: str,
        path: str,
        directive_type: DirectiveType = DirectiveType.DISALLOW,
    ) -> Result[Path, str]:
        """Add a directive to robots.txt.

        Args:
            user_agent: User-agent for the directive.
            path: Path pattern for the directive.
            directive_type: Type of directive.

        Returns:
            Success with robots.txt path if addition succeeds.
            Failure with error message if addition fails.
        """
        try:
            existing_directives, existing_sitemap = ([], None)

            if self._robots_path.exists():
                existing_directives, existing_sitemap = (
                    self._parse_existing_robots()
                )

            # Add new directive
            new_directive = RobotsDirective(
                user_agent=user_agent,
                directive_type=directive_type,
                path=path,
                priority=0,
            )
            existing_directives.append(new_directive)

            # Generate content
            content = self._directives_to_text(existing_directives, existing_sitemap)

            # Write robots.txt
            self._robots_path.write_text(content, encoding="utf-8")

            logger.info(f"Added directive to robots.txt: {directive_type.value} {path}")
            return Success(self._robots_path)

        except Exception as e:
            error_msg = f"Failed to add directive: {e}"
            logger.error(error_msg)
            return Failure(error_msg)

    def remove_directive(
        self,
        user_agent: str,
        path: str,
    ) -> Result[Path, str]:
        """Remove a directive from robots.txt.

        Args:
            user_agent: User-agent of the directive.
            path: Path of the directive.

        Returns:
            Success with robots.txt path if removal succeeds.
            Failure with error message if removal fails.
        """
        try:
            if not self._robots_path.exists():
                return Failure("robots.txt does not exist")

            existing_directives, existing_sitemap = (
                self._parse_existing_robots()
            )

            # Filter out the directive to remove
            remaining_directives = [
                d for d in existing_directives
                if not (d.user_agent == user_agent and d.path == path)
            ]

            # Generate content
            content = self._directives_to_text(remaining_directives, existing_sitemap)

            # Write robots.txt
            self._robots_path.write_text(content, encoding="utf-8")

            logger.info(f"Removed directive from robots.txt: {path}")
            return Success(self._robots_path)

        except Exception as e:
            error_msg = f"Failed to remove directive: {e}"
            logger.error(error_msg)
            return Failure(error_msg)

    def _directives_to_text(
        self,
        directives: list[RobotsDirective],
        sitemap_url: str | None,
    ) -> str:
        """Convert directives to robots.txt text.

        Args:
            directives: List of robots directives.
            sitemap_url: Optional sitemap URL.

        Returns:
            robots.txt content string.
        """
        lines: list[str] = []

        # Group directives by user-agent
        by_user_agent: dict[str, list[RobotsDirective]] = {}
        for directive in directives:
            if directive.user_agent not in by_user_agent:
                by_user_agent[directive.user_agent] = []
            by_user_agent[directive.user_agent].append(directive)

        # Write directives grouped by user-agent
        for user_agent, agent_directives in by_user_agent.items():
            lines.append(f"User-agent: {user_agent}")

            # Sort by priority (higher first)
            sorted_directives = sorted(
                agent_directives,
                key=lambda d: d.priority,
                reverse=True,
            )

            for directive in sorted_directives:
                lines.append(
                    f"{directive.directive_type.value}: {directive.path}"
                )

            lines.append("")  # Empty line between user-agent blocks

        # Add sitemap directive
        if sitemap_url:
            lines.append(f"Sitemap: {sitemap_url}")

        return "\n".join(lines).strip() + "\n"

    def _parse_existing_robots(
        self,
    ) -> tuple[list[RobotsDirective], str | None]:
        """Parse existing robots.txt file.

        Returns:
            Tuple of (directives list, sitemap URL or None).
        """
        import re

        directives: list[RobotsDirective] = []
        sitemap_url: str | None = None
        current_user_agent: str | None = None

        content = self._robots_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        for line in lines:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse User-agent
            user_agent_match = re.match(r"User-agent:\s*(.+)", line, re.IGNORECASE)
            if user_agent_match:
                current_user_agent = user_agent_match.group(1).strip()
                continue

            # Parse Sitemap
            sitemap_match = re.match(r"Sitemap:\s*(.+)", line, re.IGNORECASE)
            if sitemap_match:
                sitemap_url = sitemap_match.group(1).strip()
                continue

            # Parse Allow/Disallow
            if current_user_agent:
                allow_match = re.match(
                    r"Allow:\s*(.+)",
                    line,
                    re.IGNORECASE,
                )
                if allow_match:
                    directive = RobotsDirective(
                        user_agent=current_user_agent,
                        directive_type=DirectiveType.ALLOW,
                        path=allow_match.group(1).strip(),
                        priority=1,
                    )
                    directives.append(directive)
                    continue

                disallow_match = re.match(
                    r"Disallow:\s*(.+)",
                    line,
                    re.IGNORECASE,
                )
                if disallow_match:
                    directive = RobotsDirective(
                        user_agent=current_user_agent,
                        directive_type=DirectiveType.DISALLOW,
                        path=disallow_match.group(1).strip(),
                        priority=0,
                    )
                    directives.append(directive)
                    continue

                crawl_delay_match = re.match(
                    r"Crawl-delay:\s*(.+)",
                    line,
                    re.IGNORECASE,
                )
                if crawl_delay_match:
                    directive = RobotsDirective(
                        user_agent=current_user_agent,
                        directive_type=DirectiveType.CRAWL_DELAY,
                        path=crawl_delay_match.group(1).strip(),
                        priority=0,
                    )
                    directives.append(directive)
                    continue

        return directives, sitemap_url

    def validate_robots(self, robots_path: Path | None = None) -> Result[bool, str]:
        """Validate a robots.txt file.

        Args:
            robots_path: Optional path to robots.txt to validate.

        Returns:
            Success with True if valid.
            Failure with validation error if invalid.
        """
        path = robots_path or self._robots_path

        if not path.exists():
            return Failure(f"robots.txt not found: {path}")

        try:
            content = path.read_text(encoding="utf-8")

            # Check for User-agent directive
            if "User-agent:" not in content:
                return Failure("Missing User-agent directive")

            # Check for valid directives
            valid_directives = {"Allow:", "Disallow:", "Sitemap:", "Crawl-delay:"}
            has_valid = False
            for line in content.split("\n"):
                line = line.strip()
                for directive in valid_directives:
                    if line.startswith(directive):
                        has_valid = True
                        break

            if not has_valid:
                logger.warning("No Allow/Disallow directives found")

            return Success(True)

        except Exception as e:
            return Failure(f"robots.txt validation failed: {e}")