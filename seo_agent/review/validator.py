"""Code/content validation.

This module provides validation functionality for reviewing execution
results against project rules, SEO best practices, and safety constraints.

The validator is completely read-only and never modifies repository files.

Usage:
    validator = ReviewValidator(container)
    result = await validator.validate(execution_result, repository_info)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from seo_agent.core.exceptions import ReviewError, ValidationError
from seo_agent.core.result import Failure, Result, Success

if TYPE_CHECKING:
    from seo_agent.models.repository import RepositoryInfo
    from seo_agent.models.seo import Metadata, SEOPage
    from seo_agent.models.task import ExecutionResult

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues.

    CRITICAL: Must be fixed before approval (e.g., broken links, security issues).
    ERROR: Should be fixed (e.g., duplicate metadata, missing canonical).
    WARNING: Recommended to fix (e.g., missing OG tags, suboptimal keywords).
    INFO: Informational (e.g., suggestions for improvement).
    """

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationCategory(Enum):
    """Categories of validation issues.

    METADATA: Issues with SEO metadata (titles, descriptions, etc.).
    STRUCTURED_DATA: Issues with JSON-LD and structured data.
    INTERNAL_LINKING: Issues with internal links.
    SITEMAP: Issues with sitemap.xml.
    ROBOTS: Issues with robots.txt.
    REPOSITORY_SAFETY: Issues with file/directory modifications.
    SEO_QUALITY: Issues with SEO best practices.
    HUMAN_VISIBILITY: Issues with visible content modifications.
    BRAND_RELEVANCE: Issues with content relevance.
    DUPLICATES: Duplicate content issues.
    """

    METADATA = "metadata"
    STRUCTURED_DATA = "structured_data"
    INTERNAL_LINKING = "internal_linking"
    SITEMAP = "sitemap"
    ROBOTS = "robots"
    REPOSITORY_SAFETY = "repository_safety"
    SEO_QUALITY = "seo_quality"
    HUMAN_VISIBILITY = "human_visibility"
    BRAND_RELEVANCE = "brand_relevance"
    DUPLICATES = "duplicates"


@dataclass(frozen=True)
class ValidationIssue:
    """Represents a single validation issue.

    Attributes:
        issue_id: Unique identifier for the issue.
        severity: How severe the issue is.
        category: Category of the issue.
        message: Human-readable description of the issue.
        file_path: Optional file where issue was found.
        line_number: Optional line number where issue was found.
        suggestion: Optional suggestion for fixing the issue.
        context: Additional context about the issue.
    """

    issue_id: str
    severity: ValidationSeverity
    category: ValidationCategory
    message: str
    file_path: str | None = None
    line_number: int | None = None
    suggestion: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert issue to dictionary representation."""
        return {
            "issue_id": self.issue_id,
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "suggestion": self.suggestion,
            "context": self.context,
        }


@dataclass
class ValidationResult:
    """Result of validation operation.

    Attributes:
        is_valid: Whether validation passed.
        issues: List of validation issues found.
        validated_files: Number of files validated.
        validated_pages: Number of pages validated.
        validation_duration_seconds: Time taken for validation.
    """

    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    validated_files: int = 0
    validated_pages: int = 0
    validation_duration_seconds: float = 0.0

    @property
    def critical_issues(self) -> list[ValidationIssue]:
        """Get all critical severity issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.CRITICAL]

    @property
    def error_issues(self) -> list[ValidationIssue]:
        """Get all error severity issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warning_issues(self) -> list[ValidationIssue]:
        """Get all warning severity issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def info_issues(self) -> list[ValidationIssue]:
        """Get all info severity issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.INFO]

    @property
    def has_blocking_issues(self) -> bool:
        """Check if there are any blocking issues (critical or error)."""
        return bool(self.critical_issues or self.error_issues)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "is_valid": self.is_valid,
            "issues": [i.to_dict() for i in self.issues],
            "validated_files": self.validated_files,
            "validated_pages": self.validated_pages,
            "validation_duration_seconds": self.validation_duration_seconds,
            "critical_count": len(self.critical_issues),
            "error_count": len(self.error_issues),
            "warning_count": len(self.warning_issues),
            "info_count": len(self.info_issues),
        }


class MetadataValidator:
    """Validates SEO metadata for pages.

    This validator checks metadata quality including titles, descriptions,
    canonical URLs, and keyword usage.
    """

    # Recommended character limits
    TITLE_MAX_LENGTH = 60
    DESCRIPTION_MAX_LENGTH = 160

    # Patterns for detecting issues
    KEYWORD_STUFFING_PATTERN = re.compile(
        r"(" + "|".join([re.escape(w) for w in [
            "buy now", "click here", "free money", "limited time",
            "act now", "order now", "sign up free", "winner",
            "guaranteed", "no obligation", "risk free"
        ]]) + r")",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        """Initialize the metadata validator."""
        self._issue_counter = 0

    def _generate_issue_id(self) -> str:
        """Generate unique issue ID."""
        self._issue_counter += 1
        return f"meta_{self._issue_counter}"

    def validate_title(
        self,
        title: str | None,
        file_path: str | None = None,
    ) -> list[ValidationIssue]:
        """Validate a page title.

        Args:
            title: The title to validate.
            file_path: Optional file path for context.

        Returns:
            List of validation issues found.
        """
        issues = []

        if not title:
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.METADATA,
                message="Missing page title",
                file_path=file_path,
                suggestion="Add a descriptive, keyword-rich title under 60 characters.",
            ))
            return issues

        # Check length
        if len(title) > self.TITLE_MAX_LENGTH:
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.METADATA,
                message=f"Title exceeds recommended length ({len(title)} > {self.TITLE_MAX_LENGTH} chars)",
                file_path=file_path,
                suggestion=f"Keep title under {self.TITLE_MAX_LENGTH} characters for better SERP display.",
                context={"length": len(title), "max_length": self.TITLE_MAX_LENGTH},
            ))

        # Check for keyword stuffing indicators
        if self.KEYWORD_STUFFING_PATTERN.search(title):
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.SEO_QUALITY,
                message="Title contains suspicious promotional phrases",
                file_path=file_path,
                suggestion="Remove promotional phrases and focus on descriptive content.",
            ))

        return issues

    def validate_description(
        self,
        description: str | None,
        file_path: str | None = None,
    ) -> list[ValidationIssue]:
        """Validate a meta description.

        Args:
            description: The description to validate.
            file_path: Optional file path for context.

        Returns:
            List of validation issues found.
        """
        issues = []

        if not description:
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.METADATA,
                message="Missing meta description",
                file_path=file_path,
                suggestion="Add a unique, descriptive meta description under 160 characters.",
            ))
            return issues

        # Check length
        if len(description) > self.DESCRIPTION_MAX_LENGTH:
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.METADATA,
                message=f"Description exceeds recommended length ({len(description)} > {self.DESCRIPTION_MAX_LENGTH} chars)",
                file_path=file_path,
                suggestion=f"Keep description under {self.DESCRIPTION_MAX_LENGTH} characters.",
                context={"length": len(description), "max_length": self.DESCRIPTION_MAX_LENGTH},
            ))

        # Check for keyword stuffing indicators
        if self.KEYWORD_STUFFING_PATTERN.search(description):
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.SEO_QUALITY,
                message="Description contains suspicious promotional phrases",
                file_path=file_path,
                suggestion="Remove promotional phrases and focus on descriptive content.",
            ))

        return issues

    def validate_canonical_url(
        self,
        canonical_url: str | None,
        file_path: str | None = None,
    ) -> list[ValidationIssue]:
        """Validate a canonical URL.

        Args:
            canonical_url: The canonical URL to validate.
            file_path: Optional file path for context.

        Returns:
            List of validation issues found.
        """
        issues = []

        if not canonical_url:
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.METADATA,
                message="Missing canonical URL",
                file_path=file_path,
                suggestion="Add a canonical URL to prevent duplicate content issues.",
            ))
            return issues

        # Basic URL format validation
        if not canonical_url.startswith(("http://", "https://")):
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.METADATA,
                message="Canonical URL must be an absolute URL starting with http:// or https://",
                file_path=file_path,
                suggestion="Use an absolute URL format for canonical tags.",
            ))

        return issues

    def validate_metadata(
        self,
        metadata: Metadata,
        file_path: str | None = None,
    ) -> list[ValidationIssue]:
        """Validate complete metadata for a page.

        Args:
            metadata: The metadata to validate.
            file_path: Optional file path for context.

        Returns:
            List of validation issues found.
        """
        issues = []

        # Validate individual fields
        issues.extend(self.validate_title(metadata.title, file_path))
        issues.extend(self.validate_description(metadata.description, file_path))
        issues.extend(self.validate_canonical_url(metadata.canonical, file_path))

        # Validate keywords
        if not metadata.primary_keyword and not metadata.keywords:
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.SEO_QUALITY,
                message="No primary keyword or keywords defined",
                file_path=file_path,
                suggestion="Define a primary keyword and optional secondary keywords.",
            ))

        return issues


class StructuredDataValidator:
    """Validates structured data (JSON-LD) for pages."""

    VALID_SCHEMA_TYPES = {
        "Article", "BlogPosting", "NewsArticle", "WebPage",
        "WebSite", "Organization", "Person", "LocalBusiness",
        "Product", "FAQPage", "HowTo", "Recipe", "Video",
        "Event", "BreadcrumbList", "ItemList", "AggregateRating",
    }

    def __init__(self) -> None:
        """Initialize the structured data validator."""
        self._issue_counter = 1000  # Offset to avoid ID conflicts

    def _generate_issue_id(self) -> str:
        """Generate unique issue ID."""
        self._issue_counter += 1
        return f"sd_{self._issue_counter}"

    def validate_schema_type(
        self,
        schema_type: str,
        file_path: str | None = None,
    ) -> list[ValidationIssue]:
        """Validate a schema.org type.

        Args:
            schema_type: The schema type to validate.
            file_path: Optional file path for context.

        Returns:
            List of validation issues found.
        """
        issues = []

        if schema_type not in self.VALID_SCHEMA_TYPES:
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.STRUCTURED_DATA,
                message=f"Unknown or uncommon schema type: {schema_type}",
                file_path=file_path,
                suggestion=f"Consider using a more common schema type. Valid types include: {', '.join(sorted(self.VALID_SCHEMA_TYPES))}",
                context={"schema_type": schema_type},
            ))

        return issues

    def validate_structured_data(
        self,
        structured_data: tuple,
        file_path: str | None = None,
    ) -> list[ValidationIssue]:
        """Validate structured data entries.

        Args:
            structured_data: Tuple of structured data entries.
            file_path: Optional file path for context.

        Returns:
            List of validation issues found.
        """
        issues = []

        if not structured_data:
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.INFO,
                category=ValidationCategory.STRUCTURED_DATA,
                message="No structured data found",
                file_path=file_path,
                suggestion="Consider adding relevant structured data (e.g., FAQPage, Article) for rich search results.",
            ))
            return issues

        # Validate each schema type
        for sd in structured_data:
            if hasattr(sd, "schema_type"):
                issues.extend(self.validate_schema_type(sd.schema_type, file_path))

        return issues


class OpenGraphValidator:
    """Validates Open Graph meta tags."""

    def __init__(self) -> None:
        """Initialize the Open Graph validator."""
        self._issue_counter = 2000

    def _generate_issue_id(self) -> str:
        """Generate unique issue ID."""
        self._issue_counter += 1
        return f"og_{self._issue_counter}"

    def validate_og_tags(
        self,
        og_data: Any,
        file_path: str | None = None,
    ) -> list[ValidationIssue]:
        """Validate Open Graph data.

        Args:
            og_data: Open Graph data to validate.
            file_path: Optional file path for context.

        Returns:
            List of validation issues found.
        """
        issues = []

        if not og_data:
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.METADATA,
                message="No Open Graph tags found",
                file_path=file_path,
                suggestion="Add Open Graph tags for better social sharing (og:title, og:description, og:image).",
            ))
            return issues

        # Check for essential OG tags
        if hasattr(og_data, "title") and not og_data.title:
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.METADATA,
                message="Missing og:title",
                file_path=file_path,
                suggestion="Add og:title for social sharing.",
            ))

        if hasattr(og_data, "description") and not og_data.description:
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.METADATA,
                message="Missing og:description",
                file_path=file_path,
                suggestion="Add og:description for social sharing.",
            ))

        if hasattr(og_data, "image") and not og_data.image:
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.INFO,
                category=ValidationCategory.METADATA,
                message="Missing og:image",
                file_path=file_path,
                suggestion="Add og:image for better social media engagement.",
            ))

        return issues


class TwitterCardValidator:
    """Validates Twitter Card meta tags."""

    VALID_CARD_TYPES = {"summary", "summary_large_image", "app", "player"}

    def __init__(self) -> None:
        """Initialize the Twitter Card validator."""
        self._issue_counter = 3000

    def _generate_issue_id(self) -> str:
        """Generate unique issue ID."""
        self._issue_counter += 1
        return f"tw_{self._issue_counter}"

    def validate_twitter_tags(
        self,
        twitter_data: Any,
        file_path: str | None = None,
    ) -> list[ValidationIssue]:
        """Validate Twitter Card data.

        Args:
            twitter_data: Twitter Card data to validate.
            file_path: Optional file path for context.

        Returns:
            List of validation issues found.
        """
        issues = []

        if not twitter_data:
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.INFO,
                category=ValidationCategory.METADATA,
                message="No Twitter Card tags found",
                file_path=file_path,
                suggestion="Add Twitter Card tags for better Twitter sharing (twitter:card, twitter:title, twitter:description).",
            ))
            return issues

        # Check card type
        if hasattr(twitter_data, "card"):
            if twitter_data.card not in self.VALID_CARD_TYPES:
                issues.append(ValidationIssue(
                    issue_id=self._generate_issue_id(),
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.METADATA,
                    message=f"Invalid Twitter Card type: {twitter_data.card}",
                    file_path=file_path,
                    suggestion=f"Use one of the valid card types: {', '.join(self.VALID_CARD_TYPES)}",
                ))

        return issues


class SEODirectoryValidator:
    """Validates SEO directory constraints.

    Ensures all generated SEO pages are within the /seo directory
    and the page limit is not exceeded.
    """

    MAX_SEO_PAGES = 10

    def __init__(self) -> None:
        """Initialize the SEO directory validator."""
        self._issue_counter = 4000

    def _generate_issue_id(self) -> str:
        """Generate unique issue ID."""
        self._issue_counter += 1
        return f"dir_{self._issue_counter}"

    def validate_seo_directory(
        self,
        seo_pages: list[SEOPage],
        file_paths: list[str],
    ) -> list[ValidationIssue]:
        """Validate SEO directory constraints.

        Args:
            seo_pages: List of generated SEO pages.
            file_paths: List of all modified file paths.

        Returns:
            List of validation issues found.
        """
        issues = []

        # Check for files outside /seo directory
        for file_path in file_paths:
            if "/seo/" not in file_path and file_path.endswith((".html", ".jsx", ".tsx", ".vue", ".svelte")):
                # Only flag if it's a new page (not an existing app page)
                if not any(seo.file_path == file_path for seo in seo_pages):
                    issues.append(ValidationIssue(
                        issue_id=self._generate_issue_id(),
                        severity=ValidationSeverity.CRITICAL,
                        category=ValidationCategory.REPOSITORY_SAFETY,
                        message=f"New page created outside /seo directory: {file_path}",
                        file_path=file_path,
                        suggestion="All generated SEO pages must be created within the /seo directory.",
                    ))

        # Check page limit
        if len(seo_pages) > self.MAX_SEO_PAGES:
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.CRITICAL,
                category=ValidationCategory.REPOSITORY_SAFETY,
                message=f"SEO page limit exceeded: {len(seo_pages)} > {self.MAX_SEO_PAGES}",
                suggestion=f"Remove {len(seo_pages) - self.MAX_SEO_PAGES} existing SEO pages before adding new ones.",
                context={"page_count": len(seo_pages), "limit": self.MAX_SEO_PAGES},
            ))

        return issues


class DuplicateValidator:
    """Validates for duplicate content issues."""

    def __init__(self) -> None:
        """Initialize the duplicate validator."""
        self._issue_counter = 5000

    def _generate_issue_id(self) -> str:
        """Generate unique issue ID."""
        self._issue_counter += 1
        return f"dup_{self._issue_counter}"

    def validate_no_duplicates(
        self,
        titles: list[str],
        descriptions: list[str],
    ) -> list[ValidationIssue]:
        """Check for duplicate titles and descriptions.

        Args:
            titles: List of page titles.
            descriptions: List of page descriptions.

        Returns:
            List of validation issues found.
        """
        issues = []

        # Find duplicate titles
        seen_titles: dict[str, list[int]] = {}
        for idx, title in enumerate(titles):
            if title:
                normalized = title.lower().strip()
                if normalized not in seen_titles:
                    seen_titles[normalized] = []
                seen_titles[normalized].append(idx)

        for title, indices in seen_titles.items():
            if len(indices) > 1:
                issues.append(ValidationIssue(
                    issue_id=self._generate_issue_id(),
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.DUPLICATES,
                    message=f"Duplicate title found across {len(indices)} pages: '{title}'",
                    suggestion="Ensure each page has a unique title.",
                    context={"title": title, "page_indices": indices},
                ))

        # Find duplicate descriptions
        seen_descriptions: dict[str, list[int]] = {}
        for idx, desc in enumerate(descriptions):
            if desc:
                normalized = desc.lower().strip()
                if normalized not in seen_descriptions:
                    seen_descriptions[normalized] = []
                seen_descriptions[normalized].append(idx)

        for desc, indices in seen_descriptions.items():
            if len(indices) > 1:
                issues.append(ValidationIssue(
                    issue_id=self._generate_issue_id(),
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.DUPLICATES,
                    message=f"Duplicate description found across {len(indices)} pages",
                    suggestion="Ensure each page has a unique meta description.",
                    context={"page_indices": indices},
                ))

        return issues


class SitemapValidator:
    """Validates sitemap.xml content."""

    def __init__(self) -> None:
        """Initialize the sitemap validator."""
        self._issue_counter = 6000

    def _generate_issue_id(self) -> str:
        """Generate unique issue ID."""
        self._issue_counter += 1
        return f"sm_{self._issue_counter}"

    def validate_sitemap_content(
        self,
        sitemap_content: str | None,
        expected_urls: list[str],
    ) -> list[ValidationIssue]:
        """Validate sitemap.xml content.

        Args:
            sitemap_content: Raw sitemap content.
            expected_urls: URLs that should be in the sitemap.

        Returns:
            List of validation issues found.
        """
        issues = []

        if not sitemap_content:
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.SITEMAP,
                message="No sitemap.xml found or empty",
                suggestion="Create or update sitemap.xml with all page URLs.",
            ))
            return issues

        # Check for basic sitemap structure
        if "<urlset" not in sitemap_content and "<sitemapindex" not in sitemap_content:
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.SITEMAP,
                message="Invalid sitemap structure",
                suggestion="Ensure sitemap.xml uses proper <urlset> or <sitemapindex> structure.",
            ))

        # Check for SEO page URLs
        for url in expected_urls:
            if "/seo/" in url and url not in sitemap_content:
                issues.append(ValidationIssue(
                    issue_id=self._generate_issue_id(),
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.SITEMAP,
                    message=f"SEO page URL missing from sitemap: {url}",
                    suggestion="Add the SEO page URL to sitemap.xml.",
                    context={"missing_url": url},
                ))

        return issues


class RobotsValidator:
    """Validates robots.txt content."""

    def __init__(self) -> None:
        """Initialize the robots.txt validator."""
        self._issue_counter = 7000

    def _generate_issue_id(self) -> str:
        """Generate unique issue ID."""
        self._issue_counter += 1
        return f"rb_{self._issue_counter}"

    def validate_robots_content(
        self,
        robots_content: str | None,
        sitemap_url: str | None,
    ) -> list[ValidationIssue]:
        """Validate robots.txt content.

        Args:
            robots_content: Raw robots.txt content.
            sitemap_url: Expected sitemap URL.

        Returns:
            List of validation issues found.
        """
        issues = []

        if not robots_content:
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.INFO,
                category=ValidationCategory.ROBOTS,
                message="No robots.txt found",
                suggestion="Consider creating robots.txt for proper crawler access control.",
            ))
            return issues

        # Check for sitemap reference
        if sitemap_url and "sitemap" not in robots_content.lower():
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.ROBOTS,
                message="Sitemap URL not found in robots.txt",
                suggestion="Add 'Sitemap: <url>' directive to robots.txt.",
            ))

        # Check for overly restrictive rules
        if "disallow: /" in robots_content.lower():
            issues.append(ValidationIssue(
                issue_id=self._generate_issue_id(),
                severity=ValidationSeverity.CRITICAL,
                category=ValidationCategory.ROBOTS,
                message="robots.txt blocks all crawlers (Disallow: /)",
                suggestion="Review robots.txt to ensure SEO pages are crawlable.",
            ))

        return issues


class ReviewValidator:
    """Main validator for review operations.

    This class orchestrates all validation checks and produces
    a comprehensive ValidationResult.
    """

    def __init__(
        self,
        metadata_validator: MetadataValidator | None = None,
        structured_data_validator: StructuredDataValidator | None = None,
        og_validator: OpenGraphValidator | None = None,
        twitter_validator: TwitterCardValidator | None = None,
        seo_directory_validator: SEODirectoryValidator | None = None,
        duplicate_validator: DuplicateValidator | None = None,
        sitemap_validator: SitemapValidator | None = None,
        robots_validator: RobotsValidator | None = None,
    ) -> None:
        """Initialize the review validator.

        Args:
            metadata_validator: Validator for SEO metadata.
            structured_data_validator: Validator for structured data.
            og_validator: Validator for Open Graph tags.
            twitter_validator: Validator for Twitter Cards.
            seo_directory_validator: Validator for SEO directory.
            duplicate_validator: Validator for duplicates.
            sitemap_validator: Validator for sitemap.
            robots_validator: Validator for robots.txt.
        """
        self.metadata_validator = metadata_validator or MetadataValidator()
        self.structured_data_validator = structured_data_validator or StructuredDataValidator()
        self.og_validator = og_validator or OpenGraphValidator()
        self.twitter_validator = twitter_validator or TwitterCardValidator()
        self.seo_directory_validator = seo_directory_validator or SEODirectoryValidator()
        self.duplicate_validator = duplicate_validator or DuplicateValidator()
        self.sitemap_validator = sitemap_validator or SitemapValidator()
        self.robots_validator = robots_validator or RobotsValidator()

    def validate_execution_result(
        self,
        execution_result: ExecutionResult,
        repository_info: RepositoryInfo,
    ) -> ValidationResult:
        """Validate execution result against project rules.

        Args:
            execution_result: The execution result to validate.
            repository_info: Repository information for context.

        Returns:
            ValidationResult with all issues found.
        """
        import time
        start_time = time.time()

        all_issues: list[ValidationIssue] = []
        validated_files = 0
        validated_pages = 0

        # Collect all modified file paths
        modified_files: list[str] = []
        if hasattr(execution_result, "modified_files"):
            modified_files.extend(execution_result.modified_files)
        if hasattr(execution_result, "created_files"):
            modified_files.extend(execution_result.created_files)

        # Validate SEO pages
        seo_pages: list[SEOPage] = []
        if hasattr(execution_result, "seo_pages"):
            seo_pages = list(execution_result.seo_pages)

        # Validate SEO directory constraints
        all_issues.extend(
            self.seo_directory_validator.validate_seo_directory(seo_pages, modified_files)
        )

        # Validate metadata for each page
        titles: list[str] = []
        descriptions: list[str] = []

        for page in seo_pages:
            validated_pages += 1

            # Validate metadata
            all_issues.extend(
                self.metadata_validator.validate_metadata(page.metadata, page.file_path)
            )

            # Validate structured data
            all_issues.extend(
                self.structured_data_validator.validate_structured_data(
                    page.metadata.structured_data,
                    page.file_path,
                )
            )

            # Validate Open Graph
            all_issues.extend(
                self.og_validator.validate_og_tags(page.metadata.og, page.file_path)
            )

            # Validate Twitter Cards
            all_issues.extend(
                self.twitter_validator.validate_twitter_tags(page.metadata.twitter, page.file_path)
            )

            # Collect for duplicate checking
            titles.append(page.metadata.title)
            descriptions.append(page.metadata.description)

        # Check for duplicates
        all_issues.extend(self.duplicate_validator.validate_no_duplicates(titles, descriptions))

        # Validate sitemap
        sitemap_content: str | None = None
        if hasattr(execution_result, "sitemap_content"):
            sitemap_content = execution_result.sitemap_content

        expected_urls = [page.metadata.canonical for page in seo_pages if page.metadata.canonical]
        all_issues.extend(
            self.sitemap_validator.validate_sitemap_content(sitemap_content, expected_urls)
        )

        # Validate robots.txt
        robots_content: str | None = None
        if hasattr(execution_result, "robots_content"):
            robots_content = execution_result.robots_content

        sitemap_url = f"{repository_info.base_url}/sitemap.xml" if hasattr(repository_info, "base_url") else None
        all_issues.extend(
            self.robots_validator.validate_robots_content(robots_content, sitemap_url)
        )

        # Count validated files
        validated_files = len(modified_files)

        # Determine if validation passed
        is_valid = not any(
            issue.severity in (ValidationSeverity.CRITICAL, ValidationSeverity.ERROR)
            for issue in all_issues
        )

        duration = time.time() - start_time

        return ValidationResult(
            is_valid=is_valid,
            issues=all_issues,
            validated_files=validated_files,
            validated_pages=validated_pages,
            validation_duration_seconds=duration,
        )