"""Change analysis.

This module provides diff analysis functionality for comparing the original
repository state with the execution result, producing classified changes.

The diff analyzer is completely read-only and never modifies repository files.

Usage:
    analyzer = DiffAnalyzer(container)
    analysis = await analyzer.analyze(execution_result, original_state)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from seo_agent.models.repository import RepositoryInfo
    from seo_agent.models.task import ExecutionResult

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Classification of changes made to files.

    CREATED: New file was created.
    MODIFIED: Existing file was modified.
    DELETED: File was deleted.
    UNCHANGED: No change to file.
    """

    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNCHANGED = "unchanged"


class ChangeCategory(Enum):
    """Categories for classifying changes.

    SEO_PAGE: Changes to SEO pages (expected, allowed).
    SITEMAP: Changes to sitemap.xml.
    ROBOTS: Changes to robots.txt.
    CONFIGURATION: Changes to configuration files.
    SOURCE_CODE: Changes to application source code.
    DEPENDENCIES: Changes to package files.
    BUILD_CONFIG: Changes to build configuration.
    DOCUMENTATION: Changes to documentation files.
    ASSETS: Changes to static assets.
    UNKNOWN: Unclassified changes.
    """

    SEO_PAGE = "seo_page"
    SITEMAP = "sitemap"
    ROBOTS = "robots"
    CONFIGURATION = "configuration"
    SOURCE_CODE = "source_code"
    DEPENDENCIES = "dependencies"
    BUILD_CONFIG = "build_config"
    DOCUMENTATION = "documentation"
    ASSETS = "assets"
    UNKNOWN = "unknown"


class ChangeSeverity(Enum):
    """Severity of changes for review purposes.

    SAFE: Expected changes, no concern.
    ACCEPTABLE: Minor changes, acceptable with review.
    WARNING: Changes that should be reviewed.
    BLOCKING: Changes that must be reviewed and approved.
    """

    SAFE = "safe"
    ACCEPTABLE = "acceptable"
    WARNING = "warning"
    BLOCKING = "blocking"


@dataclass(frozen=True)
class FileChange:
    """Represents a change to a single file.

    Attributes:
        file_path: Path to the changed file.
        change_type: Type of change (created, modified, deleted).
        category: Category of the change.
        severity: Severity of the change.
        lines_added: Number of lines added.
        lines_removed: Number of lines removed.
        description: Human-readable description of the change.
        is_within_seo_directory: Whether the file is within /seo directory.
    """

    file_path: str
    change_type: ChangeType
    category: ChangeCategory
    severity: ChangeSeverity
    lines_added: int = 0
    lines_removed: int = 0
    description: str = ""
    is_within_seo_directory: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "file_path": self.file_path,
            "change_type": self.change_type.value,
            "category": self.category.value,
            "severity": self.severity.value,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "description": self.description,
            "is_within_seo_directory": self.is_within_seo_directory,
        }


@dataclass
class DiffAnalysis:
    """Result of diff analysis between original and modified state.

    Attributes:
        total_files_changed: Total number of files changed.
        created_files: List of created file changes.
        modified_files: List of modified file changes.
        deleted_files: List of deleted file changes.
        seo_page_changes: List of changes to SEO pages.
        blocking_changes: List of blocking changes that need review.
        warning_changes: List of warning-level changes.
        is_within_safety_bounds: Whether changes are within acceptable limits.
        analysis_summary: Human-readable summary of changes.
    """

    total_files_changed: int = 0
    created_files: list[FileChange] = field(default_factory=list)
    modified_files: list[FileChange] = field(default_factory=list)
    deleted_files: list[FileChange] = field(default_factory=list)
    seo_page_changes: list[FileChange] = field(default_factory=list)
    blocking_changes: list[FileChange] = field(default_factory=list)
    warning_changes: list[FileChange] = field(default_factory=list)
    is_within_safety_bounds: bool = True
    analysis_summary: str = ""

    @property
    def all_changes(self) -> list[FileChange]:
        """Get all changes combined."""
        return self.created_files + self.modified_files + self.deleted_files

    @property
    def has_seo_pages(self) -> bool:
        """Check if any SEO pages were changed."""
        return len(self.seo_page_changes) > 0

    @property
    def has_blocking_changes(self) -> bool:
        """Check if there are any blocking changes."""
        return len(self.blocking_changes) > 0

    @property
    def has_warning_changes(self) -> bool:
        """Check if there are any warning changes."""
        return len(self.warning_changes) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_files_changed": self.total_files_changed,
            "created_files": [c.to_dict() for c in self.created_files],
            "modified_files": [c.to_dict() for c in self.modified_files],
            "deleted_files": [c.to_dict() for c in self.deleted_files],
            "seo_page_changes": [c.to_dict() for c in self.seo_page_changes],
            "blocking_changes": [c.to_dict() for c in self.blocking_changes],
            "warning_changes": [c.to_dict() for c in self.warning_changes],
            "is_within_safety_bounds": self.is_within_safety_bounds,
            "analysis_summary": self.analysis_summary,
        }


class FileClassifier:
    """Classifies files based on their path and content."""

    # Patterns for SEO-related files
    SEO_PATTERNS = ["/seo/", "/SEO/"]
    SITEMAP_PATTERNS = ["sitemap", "Sitemap", "SITEMAP"]
    ROBOTS_PATTERNS = ["robots.txt", "robots.txt"]

    # Patterns for potentially blocking changes
    DEPENDENCY_PATTERNS = [
        "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
        "requirements.txt", "Pipfile", "Pipfile.lock", "poetry.lock",
        "Gemfile", "Gemfile.lock", "Cargo.toml", "go.mod", "go.sum",
        "composer.json", "composer.lock",
    ]
    BUILD_CONFIG_PATTERNS = [
        "webpack.config", "vite.config", "rollup.config", "esbuild.config",
        "tsconfig", "babel.config", ".babelrc", "jest.config", "vitest.config",
        "next.config", "nuxt.config", "gatsby-config", "astro.config",
        ".github/workflows", "dockerfile", "docker-compose",
    ]
    SOURCE_CODE_PATTERNS = [
        ".ts", ".tsx", ".js", ".jsx", ".py", ".java", ".go", ".rs",
        ".rb", ".php", ".cs", ".cpp", ".c", ".h", ".swift", ".kt",
    ]
    CONFIG_PATTERNS = [
        ".env", ".env.local", ".env.production", "config.", "settings.",
        ".eslintrc", ".prettierrc", ".editorconfig",
    ]
    DOCUMENTATION_PATTERNS = [
        "README", "readme", "CHANGELOG", "CONTRIBUTING", "LICENSE",
        "docs/", ".md", ".rst",
    ]
    ASSET_PATTERNS = [
        ".css", ".scss", ".sass", ".less", ".svg", ".png", ".jpg",
        ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2", ".ttf",
    ]

    def classify_file(self, file_path: str) -> ChangeCategory:
        """Classify a file into a change category.

        Args:
            file_path: Path to the file.

        Returns:
            Category of the file.
        """
        file_lower = file_path.lower()

        # Check for SEO pages first
        if any(pattern in file_path for pattern in self.SEO_PATTERNS):
            return ChangeCategory.SEO_PAGE

        # Check for sitemap
        if any(pattern in file_path for pattern in self.SITEMAP_PATTERNS):
            return ChangeCategory.SITEMAP

        # Check for robots.txt
        if any(pattern in file_path for pattern in self.ROBOTS_PATTERNS):
            return ChangeCategory.ROBOTS

        # Check for dependencies
        if any(pattern in file_path for pattern in self.DEPENDENCY_PATTERNS):
            return ChangeCategory.DEPENDENCIES

        # Check for build config
        if any(pattern in file_path for pattern in self.BUILD_CONFIG_PATTERNS):
            return ChangeCategory.BUILD_CONFIG

        # Check for source code
        if any(pattern in file_path for pattern in self.SOURCE_CODE_PATTERNS):
            return ChangeCategory.SOURCE_CODE

        # Check for configuration
        if any(pattern in file_path for pattern in self.CONFIG_PATTERNS):
            return ChangeCategory.CONFIGURATION

        # Check for documentation
        if any(pattern in file_path for pattern in self.DOCUMENTATION_PATTERNS):
            return ChangeCategory.DOCUMENTATION

        # Check for assets
        if any(pattern in file_path for pattern in self.ASSET_PATTERNS):
            return ChangeCategory.ASSETS

        return ChangeCategory.UNKNOWN

    def determine_severity(
        self,
        category: ChangeCategory,
        change_type: ChangeType,
    ) -> ChangeSeverity:
        """Determine the severity of a change.

        Args:
            category: Category of the change.
            change_type: Type of change.

        Returns:
            Severity level of the change.
        """
        # SEO pages are generally safe if within /seo directory
        if category == ChangeCategory.SEO_PAGE:
            return ChangeSeverity.SAFE

        # Sitemap and robots are acceptable
        if category in (ChangeCategory.SITEMAP, ChangeCategory.ROBOTS):
            return ChangeSeverity.ACCEPTABLE

        # Dependencies are blocking
        if category == ChangeCategory.DEPENDENCIES:
            return ChangeSeverity.BLOCKING

        # Build config changes are blocking
        if category == ChangeCategory.BUILD_CONFIG:
            return ChangeSeverity.BLOCKING

        # Source code changes are warnings
        if category == ChangeCategory.SOURCE_CODE:
            return ChangeSeverity.WARNING

        # Configuration changes are blocking
        if category == ChangeCategory.CONFIGURATION:
            return ChangeSeverity.BLOCKING

        # Deletions are warnings
        if change_type == ChangeType.DELETED:
            return ChangeSeverity.WARNING

        # Documentation and assets are acceptable
        if category in (ChangeCategory.DOCUMENTATION, ChangeCategory.ASSETS):
            return ChangeSeverity.ACCEPTABLE

        return ChangeSeverity.WARNING

    def is_seo_directory(self, file_path: str) -> bool:
        """Check if file is within SEO directory.

        Args:
            file_path: Path to check.

        Returns:
            True if within /seo directory.
        """
        return any(pattern in file_path for pattern in self.SEO_PATTERNS)


class DiffAnalyzer:
    """Analyzes differences between original and modified repository state.

    This class compares the original repository state with the execution
    result and produces a DiffAnalysis with classified changes.
    """

    def __init__(
        self,
        file_classifier: FileClassifier | None = None,
    ) -> None:
        """Initialize the diff analyzer.

        Args:
            file_classifier: Classifier for categorizing files.
        """
        self.file_classifier = file_classifier or FileClassifier()

    def analyze(
        self,
        execution_result: ExecutionResult,
        original_state: RepositoryInfo,
    ) -> DiffAnalysis:
        """Analyze changes between original and modified state.

        Args:
            execution_result: The execution result with changes.
            original_state: The original repository state.

        Returns:
            DiffAnalysis with classified changes.
        """
        created_files: list[FileChange] = []
        modified_files: list[FileChange] = []
        deleted_files: list[FileChange] = []
        seo_page_changes: list[FileChange] = []
        blocking_changes: list[FileChange] = []
        warning_changes: list[FileChange] = []

        # Process created files
        created_paths: list[str] = []
        if hasattr(execution_result, "created_files"):
            created_paths = list(execution_result.created_files)

        for file_path in created_paths:
            category = self.file_classifier.classify_file(file_path)
            severity = self.file_classifier.determine_severity(category, ChangeType.CREATED)
            is_seo_dir = self.file_classifier.is_seo_directory(file_path)

            change = FileChange(
                file_path=file_path,
                change_type=ChangeType.CREATED,
                category=category,
                severity=severity,
                is_within_seo_directory=is_seo_dir,
                description=f"New file created: {file_path}",
            )
            created_files.append(change)

            if category == ChangeCategory.SEO_PAGE:
                seo_page_changes.append(change)
            if severity == ChangeSeverity.BLOCKING:
                blocking_changes.append(change)
            elif severity == ChangeSeverity.WARNING:
                warning_changes.append(change)

        # Process modified files
        modified_paths: list[str] = []
        if hasattr(execution_result, "modified_files"):
            modified_paths = list(execution_result.modified_files)

        for file_path in modified_paths:
            category = self.file_classifier.classify_file(file_path)
            severity = self.file_classifier.determine_severity(category, ChangeType.MODIFIED)
            is_seo_dir = self.file_classifier.is_seo_directory(file_path)

            change = FileChange(
                file_path=file_path,
                change_type=ChangeType.MODIFIED,
                category=category,
                severity=severity,
                is_within_seo_directory=is_seo_dir,
                description=f"File modified: {file_path}",
            )
            modified_files.append(change)

            if category == ChangeCategory.SEO_PAGE:
                seo_page_changes.append(change)
            if severity == ChangeSeverity.BLOCKING:
                blocking_changes.append(change)
            elif severity == ChangeSeverity.WARNING:
                warning_changes.append(change)

        # Process deleted files
        deleted_paths: list[str] = []
        if hasattr(execution_result, "deleted_files"):
            deleted_paths = list(execution_result.deleted_files)

        for file_path in deleted_paths:
            category = self.file_classifier.classify_file(file_path)
            severity = self.file_classifier.determine_severity(category, ChangeType.DELETED)
            is_seo_dir = self.file_classifier.is_seo_directory(file_path)

            change = FileChange(
                file_path=file_path,
                change_type=ChangeType.DELETED,
                category=category,
                severity=severity,
                is_within_seo_directory=is_seo_dir,
                description=f"File deleted: {file_path}",
            )
            deleted_files.append(change)

            if severity == ChangeSeverity.BLOCKING:
                blocking_changes.append(change)
            elif severity == ChangeSeverity.WARNING:
                warning_changes.append(change)

        # Determine if within safety bounds
        is_within_safety_bounds = len(blocking_changes) == 0

        # Generate summary
        summary = self._generate_summary(
            created=len(created_files),
            modified=len(modified_files),
            deleted=len(deleted_files),
            seo_pages=len(seo_page_changes),
            blocking=len(blocking_changes),
            warnings=len(warning_changes),
        )

        return DiffAnalysis(
            total_files_changed=len(created_files) + len(modified_files) + len(deleted_files),
            created_files=created_files,
            modified_files=modified_files,
            deleted_files=deleted_files,
            seo_page_changes=seo_page_changes,
            blocking_changes=blocking_changes,
            warning_changes=warning_changes,
            is_within_safety_bounds=is_within_safety_bounds,
            analysis_summary=summary,
        )

    def _generate_summary(
        self,
        created: int,
        modified: int,
        deleted: int,
        seo_pages: int,
        blocking: int,
        warnings: int,
    ) -> str:
        """Generate human-readable summary of changes.

        Args:
            created: Number of created files.
            modified: Number of modified files.
            deleted: Number of deleted files.
            seo_pages: Number of SEO page changes.
            blocking: Number of blocking changes.
            warnings: Number of warning changes.

        Returns:
            Summary string.
        """
        parts = []

        if created:
            parts.append(f"{created} file(s) created")
        if modified:
            parts.append(f"{modified} file(s) modified")
        if deleted:
            parts.append(f"{deleted} file(s) deleted")

        if seo_pages:
            parts.append(f"{seo_pages} SEO page(s) changed")

        if blocking:
            parts.append(f"{blocking} blocking change(s) require(s) review")

        if warnings:
            parts.append(f"{warnings} warning(s) for review")

        if not parts:
            return "No changes detected."

        return "; ".join(parts)