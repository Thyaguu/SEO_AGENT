"""Repository structure scanner.

This module provides functionality to scan a repository directory structure
and build a complete inventory of files and directories.

The scanner is read-only and does not modify any files. It uses pathlib
for all path operations and follows SOLID principles with single
responsibility for directory traversal.

Usage:
    from seo_agent.repository.scanner import RepositoryScanner

    scanner = RepositoryScanner()
    inventory = await scanner.scan("/path/to/repo")
"""

from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from seo_agent.core.logging import get_logger
from seo_agent.core.result import Failure, Result, success
from seo_agent.models.repository import (
    FileInfo,
    RepositoryInfo,
    RepositoryScanOptions,
    SitemapInfo,
    RobotsInfo,
    FrameworkInfo,
    FrameworkType,
    RoutingStrategy,
)
from seo_agent.models.seo import Metadata


# Default directories to ignore during scanning
DEFAULT_IGNORE_DIRS: frozenset[str] = frozenset({
    ".git",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".cache",
    "__pycache__",
    "venv",
    ".venv",
    "env",
    ".env",
    ".idea",
    ".vscode",
    ".DS_Store",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.dylib",
    ".egg-info",
    "eggs",
    "vendor",
    "tmp",
    "temp",
    ".sass-cache",
})

# Files that indicate SEO-related content
SEO_INDICATOR_FILES: tuple[str, ...] = (
    "sitemap.xml",
    "sitemap.json",
    "robots.txt",
    "sitemap_index.xml",
)

# Public asset directories
PUBLIC_DIR_PATTERNS: tuple[str, ...] = (
    "public",
    "static",
    "assets",
    "images",
    "img",
    "media",
    "uploads",
)


class RepositoryScanner:
    """Scans repository directory structure and builds inventory.

    This class is responsible for traversing a repository directory
    and collecting information about all files and directories.
    It is a read-only operation that does not modify any files.

    Attributes:
        _logger: Logger instance for the scanner.

    Example:
        scanner = RepositoryScanner()
        result = scanner.scan("/path/to/repo")
        if result.is_success():
            inventory = result.value
            print(f"Found {len(inventory.pages)} pages")
    """

    def __init__(self) -> None:
        """Initialize the repository scanner."""
        self._logger = get_logger(__name__)

    def scan(
        self,
        root_path: str | Path,
        options: RepositoryScanOptions | None = None,
    ) -> Result[RepositoryInfo, str]:
        """Scan the repository and build an inventory.

        Args:
            root_path: Path to the repository root directory.
            options: Optional scan configuration options.

        Returns:
            Result containing RepositoryInfo on success, error message on failure.
        """
        root = Path(root_path).resolve()

        if not root.exists():
            return Failure(f"Repository path does not exist: {root}")

        if not root.is_dir():
            return Failure(f"Path is not a directory: {root}")

        options = options or RepositoryScanOptions()

        self._logger.info(f"Starting_repository_scan: path={root}")

        try:
            # Scan files
            files = list(self._scan_files(root, options))
            self._logger.info(f"files_scanned: count={len(files)}")

            # Detect sitemap
            sitemap = self._detect_sitemap(root)

            # Detect robots.txt
            robots = self._detect_robots(root)

            # Detect public assets
            public_assets = self._detect_public_assets(root)

            # Build repository info with minimal framework info
            # Framework detection will be done by the framework detector
            framework_info = FrameworkInfo(
                framework_type=FrameworkType.UNKNOWN,
                routing_strategy=RoutingStrategy.UNKNOWN,
            )

            repository_info = RepositoryInfo(
                root_path=str(root),
                framework=framework_info,
                pages=(),  # Pages are discovered by page_discovery
                seo_pages=(),  # SEO pages are filtered from pages
                sitemap=sitemap,
                robots=robots,
                public_assets=tuple(public_assets),
                build_config={},
                analyzed_at=datetime.utcnow(),
            )

            self._logger.info(
                f"repository_scan_complete: files={len(files)}, "
                f"has_sitemap={sitemap.exists if sitemap else False}, "
                f"has_robots={robots.exists if robots else False}"
            )

            return success(repository_info)

        except OSError as e:
            self._logger.error(f"scan_os_error: {root} — {e}", exc_info=e)
            return Failure(f"OS error accessing repository: {root} — {e}")

        except PermissionError as e:
            self._logger.error(f"permission_denied: {root} — {e}", exc_info=e)
            return Failure(f"Permission denied accessing: {root} — {e}")

        except Exception as e:
            self._logger.error(f"scan_failed: {e}", exc_info=e)
            return Failure(f"Failed to scan repository: {e}")

    def _scan_files(
        self,
        root: Path,
        options: RepositoryScanOptions,
    ) -> Iterator[FileInfo]:
        """Recursively scan directory for files.

        Args:
            root: Root directory to scan.
            options: Scan configuration options.

        Yields:
            FileInfo for each discovered file.
        """
        exclude_patterns = set(options.exclude_patterns) | DEFAULT_IGNORE_DIRS

        for path in root.rglob("*"):
            # Skip if not a file
            if not path.is_file():
                continue

            # Check if path should be excluded
            if self._should_exclude(path, exclude_patterns, options):
                continue

            # Check depth limit
            if options.max_depth is not None:
                depth = len(path.relative_to(root).parts) - 1
                if depth > options.max_depth:
                    continue

            # Check extension filter
            if options.extensions:
                if path.suffix not in options.extensions:
                    continue

            # Build file info
            try:
                stat = path.stat()
                is_text = self._is_text_file(path)

                file_info = FileInfo(
                    path=str(path.relative_to(root)),
                    absolute_path=str(path),
                    size_bytes=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime),
                    is_text=is_text,
                    extension=path.suffix,
                    encoding="utf-8" if is_text else None,
                )
                yield file_info

            except (OSError, PermissionError) as e:
                self._logger.warning(
                    f"file_access_error: path={path}, error={e}"
                )
                continue

    def _should_exclude(
        self,
        path: Path,
        exclude_patterns: set[str],
        options: RepositoryScanOptions,
    ) -> bool:
        """Check if a path should be excluded from scanning.

        Args:
            path: Path to check.
            exclude_patterns: Set of patterns to exclude.
            options: Scan options.

        Returns:
            True if path should be excluded.
        """
        # Check if any parent directory is in exclude patterns
        for parent in path.parents:
            parent_name = parent.name
            if parent_name in exclude_patterns:
                return True

            # Check hidden files/directories
            if not options.include_hidden and parent_name.startswith("."):
                return True

        # Check hidden files
        if not options.include_hidden and path.name.startswith("."):
            return True

        # Check symlinks
        if path.is_symlink() and not options.follow_symlinks:
            return True

        return False

    def _is_text_file(self, path: Path) -> bool:
        """Determine if a file is a text file.

        Args:
            path: Path to check.

        Returns:
            True if file appears to be text.
        """
        text_extensions = {
            ".txt", ".md", ".rst", ".json", ".yaml", ".yml", ".toml",
            ".xml", ".html", ".htm", ".css", ".scss", ".sass", ".less",
            ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte",
            ".py", ".pyw", ".rb", ".php", ".java", ".kt", ".swift",
            ".c", ".cpp", ".h", ".hpp", ".cs", ".go", ".rs", ".sh",
            ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd",
            ".sql", ".graphql", ".gql", ".env", ".gitignore",
            ".dockerfile", ".editorconfig", ".prettierrc",
            ".eslintrc", ".babelrc", ".webpack",
        }

        if path.suffix.lower() in text_extensions:
            return True

        # Check for common text file names
        text_filenames = {
            "readme", "license", "changelog", "contributing",
            "authors", "maintainers", "makefile", "dockerfile",
        }
        if path.stem.lower() in text_filenames:
            return True

        return False

    def _detect_sitemap(self, root: Path) -> SitemapInfo | None:
        """Detect and parse sitemap.xml if present.

        Args:
            root: Repository root path.

        Returns:
            SitemapInfo if found, None otherwise.
        """
        sitemap_paths = [
            root / "sitemap.xml",
            root / "public" / "sitemap.xml",
            root / "static" / "sitemap.xml",
        ]

        for sitemap_path in sitemap_paths:
            if sitemap_path.exists():
                self._logger.info(f"sitemap_found: path={sitemap_path}")
                return SitemapInfo(
                    file_path=str(sitemap_path),
                    exists=True,
                    entries=(),
                    format="xml",
                )

        return SitemapInfo(
            file_path=str(root / "sitemap.xml"),
            exists=False,
            entries=(),
            format="xml",
        )

    def _detect_robots(self, root: Path) -> RobotsInfo | None:
        """Detect and parse robots.txt if present.

        Args:
            root: Repository root path.

        Returns:
            RobotsInfo if found, None otherwise.
        """
        robots_path = root / "robots.txt"

        if robots_path.exists():
            self._logger.info(f"robots_found: path={robots_path}")
            return RobotsInfo(
                file_path=str(robots_path),
                exists=True,
                rules=(),
            )

        return RobotsInfo(
            file_path=str(robots_path),
            exists=False,
            rules=(),
        )

    def _detect_public_assets(self, root: Path) -> list[str]:
        """Detect public asset directories.

        Args:
            root: Repository root path.

        Returns:
            List of relative paths to public asset directories.
        """
        public_dirs = []

        for pattern in PUBLIC_DIR_PATTERNS:
            for path in root.rglob(pattern):
                if path.is_dir() and not self._should_exclude(
                    path, DEFAULT_IGNORE_DIRS, RepositoryScanOptions()
                ):
                    public_dirs.append(str(path.relative_to(root)))

        return public_dirs