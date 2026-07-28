"""Page discovery service.

This module provides functionality to discover pages/routes
across different frameworks and routing strategies.

Supported routing strategies:
- File-based routing (Next.js, Nuxt, SvelteKit, Astro)
- Pages router (Next.js pages/, Gatsby)
- Dynamic routes ([id], [slug], [...path])
- API routes
- Code-based routing (Django, Flask, Express)

Usage:
    from seo_agent.repository.page_discovery import PageDiscovery

    discovery = PageDiscovery()
    result = discovery.discover_pages("/path/to/repo")
    if result.is_success():
        pages = result.value
        for page in pages:
            print(f"{page.url_path} - {page.title}")
"""

from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from seo_agent.core.logging import get_logger
from seo_agent.core.result import Result, success, Failure
from seo_agent.models.repository import (
    DiscoveredPage,
    FrameworkType,
    RoutingStrategy,
    PageType,
    RepositoryInfo,
)

if TYPE_CHECKING:
    from seo_agent.models.seo import FrameworkInfo


class PageDiscovery:
    """Discovers pages/routes in a repository.

    This class analyzes the repository structure to find all
    discoverable pages based on the routing strategy.

    Attributes:
        _logger: Logger instance for the discovery service.

    Example:
        discovery = PageDiscovery()
        result = discovery.discover_pages("/path/to/repo")
        if result.is_success():
            for page in result.value:
                print(page.url_path)
    """

    def __init__(self) -> None:
        """Initialize the page discovery service."""
        self._logger = get_logger(__name__)

    def discover_pages(
        self,
        repository_path: str | Path,
        repository_info: "RepositoryInfo | None" = None,
        framework_info: "FrameworkInfo | None" = None,
    ) -> Result[list[DiscoveredPage], str]:
        """Discover all pages in the repository.

        Args:
            repository_path: Path to the repository root.
            repository_info: Optional existing repository info with scanned files.
            framework_info: Optional framework info for targeted discovery.

        Returns:
            Result containing list of DiscoveredPage on success.
        """
        root = Path(repository_path).resolve()

        if not root.exists():
            return Result.failure(f"Repository path does not exist: {root}")

        self._logger.info(f"discovering_pages: path={root}")

        try:
            pages: list[DiscoveredPage] = []

            # Determine routing strategy
            routing_strategy = self._get_routing_strategy(
                root, framework_info, repository_info
            )

            # Discover pages based on routing strategy
            if routing_strategy == RoutingStrategy.FILE_BASED:
                pages = self._discover_file_based_pages(root)
            elif routing_strategy == RoutingStrategy.DYNAMIC:
                # Check if this is a code-based framework (Django/Flask)
                if framework_info and framework_info.framework_type in (
                    FrameworkType.DJANGO,
                    FrameworkType.FLASK,
                ):
                    pages = self._discover_code_based_routes(root)
                else:
                    pages = self._discover_dynamic_pages(root)
            elif routing_strategy == RoutingStrategy.API_ROUTES:
                pages = self._discover_api_routes(root)
            else:
                # Fallback: scan for common patterns
                pages = self._discover_all_pages(root)

            self._logger.info(f"pages_discovered: {len(pages)} pages")
            return success(pages)

        except Exception as e:
            self._logger.error(f"page_discovery_failed: {e}", exc_info=e)
            return Result.failure(f"Failed to discover pages: {e}")

    def _get_routing_strategy(
        self,
        root: Path,
        framework_info: "FrameworkInfo | None",
        repository_info: "RepositoryInfo | None",
    ) -> RoutingStrategy:
        """Determine the routing strategy from available info.

        Args:
            root: Repository root path.
            framework_info: Framework info if available.
            repository_info: Repository info if available.

        Returns:
            Detected RoutingStrategy.
        """
        if framework_info and framework_info.routing_strategy:
            return framework_info.routing_strategy

        # Detect from directory structure
        if (root / "app").exists():
            return RoutingStrategy.FILE_BASED
        if (root / "pages").exists():
            return RoutingStrategy.FILE_BASED
        if (root / "src" / "pages").exists():
            return RoutingStrategy.FILE_BASED
        if (root / "src" / "app").exists():
            return RoutingStrategy.FILE_BASED

        # Check for dynamic route patterns
        for pattern in ("[", "{"):
            if any(root.rglob(f"*{pattern}*")):
                return RoutingStrategy.DYNAMIC

        return RoutingStrategy.UNKNOWN

    def _discover_file_based_pages(self, root: Path) -> list[DiscoveredPage]:
        """Discover pages from file-based routing structure.

        Args:
            root: Repository root path.

        Returns:
            List of discovered pages.
        """
        pages: list[DiscoveredPage] = []
        seen_paths: set[str] = set()

        # Check for Next.js App Router (app/ directory)
        app_dir = root / "app"
        if app_dir.exists():
            pages.extend(self._scan_app_directory(app_dir, seen_paths))

        # Check for Pages Router (pages/ directory)
        pages_dir = root / "pages"
        if pages_dir.exists():
            pages.extend(self._scan_pages_directory(pages_dir, seen_paths))

        # Check for src/pages
        src_pages_dir = root / "src" / "pages"
        if src_pages_dir.exists():
            pages.extend(self._scan_pages_directory(src_pages_dir, seen_paths))

        # Check for src/app (SvelteKit, etc.)
        src_app_dir = root / "src" / "app"
        if src_app_dir.exists() and not pages:
            pages.extend(self._scan_app_directory(src_app_dir, seen_paths))

        return pages

    def _scan_app_directory(
        self,
        directory: Path,
        seen_paths: set[str],
    ) -> list[DiscoveredPage]:
        """Recursively scan an app directory for pages.

        Args:
            directory: Directory to scan.
            seen_paths: Set of already seen paths to avoid duplicates.

        Returns:
            List of discovered pages.
        """
        pages: list[DiscoveredPage] = []

        for item in directory.iterdir():
            if item.name.startswith("."):
                continue
            if item.name.startswith("_"):
                continue

            if item.is_file():
                # Check for page files
                if item.suffix in (".tsx", ".ts", ".jsx", ".js"):
                    if item.stem == "page":
                        # page.tsx -> /
                        route_path = self._get_route_path_from_app(item, directory)
                        if route_path and route_path not in seen_paths:
                            seen_paths.add(route_path)
                            pages.append(self._create_page_from_file(item, route_path))
                    elif item.stem != "layout" and item.stem != "not-found":
                        # other files like loading.tsx, error.tsx are not pages
                        pass

            elif item.is_dir():
                # Check for nested page.tsx
                nested_page = item / "page.tsx"
                if nested_page.exists():
                    route_path = self._get_route_path_from_app(nested_page, directory)
                    if route_path and route_path not in seen_paths:
                        seen_paths.add(route_path)
                        pages.append(self._create_page_from_file(nested_page, route_path))

                # Recurse into layout directories
                if not item.name.startswith("(") and not item.name.startswith("["):
                    pages.extend(self._scan_app_directory(item, seen_paths))

        return pages

    def _get_route_path_from_app(self, page_file: Path, root: Path) -> str:
        """Convert a page file path to a route path.

        Args:
            page_file: Path to the page file.
            root: Root app directory.

        Returns:
            Route path string.
        """
        try:
            relative = page_file.relative_to(root)
            parts = list(relative.parts)

            # Remove page.tsx
            if parts[-1] == "page.tsx" or parts[-1] == "page.jsx" or parts[-1] == "page.js":
                parts = parts[:-1]
            elif parts[-1].startswith("page."):
                parts = parts[:-1]

            if not parts:
                return "/"

            # Convert route segments
            path_parts: list[str] = []
            for part in parts:
                if part == "layout" or part.startswith("_"):
                    continue
                if part.startswith("["):
                    path_parts.append(part)
                else:
                    path_parts.append(part)

            if not path_parts:
                return "/"

            return "/" + "/".join(path_parts)

        except ValueError:
            return "/"

    def _scan_pages_directory(
        self,
        directory: Path,
        seen_paths: set[str],
    ) -> list[DiscoveredPage]:
        """Scan a pages directory for page files.

        Args:
            directory: Directory to scan.
            seen_paths: Set of already seen paths.

        Returns:
            List of discovered pages.
        """
        pages: list[DiscoveredPage] = []

        for item in directory.rglob("*"):
            if item.is_file() and item.suffix in (".tsx", ".ts", ".jsx", ".js"):
                # Skip non-page files
                if item.stem in ("_app", "_document", "_error"):
                    continue

                route_path = self._get_route_path_from_pages(item, directory)
                if route_path and route_path not in seen_paths:
                    seen_paths.add(route_path)
                    pages.append(self._create_page_from_file(item, route_path))

        return pages

    def _get_route_path_from_pages(self, page_file: Path, root: Path) -> str:
        """Convert a pages directory file to a route path.

        Args:
            page_file: Path to the page file.
            root: Root pages directory.

        Returns:
            Route path string.
        """
        try:
            relative = page_file.relative_to(root)
            parts = list(relative.parts)

            # Remove file extension
            filename = parts[-1]
            if "." in filename:
                filename = filename.rsplit(".", 1)[0]

            # Handle special pages
            if filename == "index":
                parts[-1] = ""
            elif filename.startswith("["):
                parts[-1] = filename
            else:
                parts[-1] = filename

            # Build path
            path = "/" + "/".join(p for p in parts if p)
            return path if path else "/"

        except ValueError:
            return "/"

    def _create_page_from_file(
        self,
        file_path: Path,
        route_path: str,
    ) -> DiscoveredPage:
        """Create a DiscoveredPage from a file path.

        Args:
            file_path: Path to the page file.
            route_path: Computed route path.

        Returns:
            DiscoveredPage instance.
        """
        # Determine page type
        page_type = self._determine_page_type(route_path, file_path)

        return DiscoveredPage(
            url_path=route_path,
            file_path=str(file_path),
            page_type=page_type,
            title=None,  # Will be extracted by metadata parser
            has_dynamic_params="[" in route_path or "{" in route_path,
        )

    def _determine_page_type(
        self,
        route_path: str,
        file_path: Path,
    ) -> PageType:
        """Determine the type of page based on route.

        Args:
            route_path: URL route path.
            file_path: File path.

        Returns:
            PageType enum value.
        """
        if route_path == "/":
            return PageType.HOMEPAGE
        if route_path.startswith("/api/"):
            return PageType.API_ROUTE
        if route_path.startswith("/blog/"):
            return PageType.BLOG_POST
        if route_path.startswith("/products/"):
            return PageType.PRODUCT
        if route_path.startswith("/category/"):
            return PageType.CATEGORY
        if route_path.startswith("/tag/"):
            return PageType.TAG
        if route_path.startswith("/auth/") or route_path == "/login" or route_path == "/register":
            return PageType.AUTH
        if route_path.startswith("/admin/"):
            return PageType.ADMIN
        if route_path.startswith("/dashboard/"):
            return PageType.DASHBOARD
        if route_path.startswith("/checkout/"):
            return PageType.CHECKOUT
        if route_path.startswith("/account/"):
            return PageType.ACCOUNT
        if route_path.startswith("/search/"):
            return PageType.SEARCH

        return PageType.GENERAL

    def _discover_dynamic_pages(self, root: Path) -> list[DiscoveredPage]:
        """Discover pages with dynamic route parameters.

        Args:
            root: Repository root path.

        Returns:
            List of discovered pages with dynamic routes.
        """
        pages: list[DiscoveredPage] = []
        seen_paths: set[str] = set()

        # Find files with dynamic segments
        for pattern in ["*.tsx", "*.ts", "*.jsx", "*.js"]:
            for file_path in root.rglob(pattern):
                if self._is_page_file(file_path):
                    route_path = self._extract_dynamic_route(file_path, root)
                    if route_path and route_path not in seen_paths:
                        seen_paths.add(route_path)
                        pages.append(self._create_page_from_file(file_path, route_path))

        return pages

    def _extract_dynamic_route(self, file_path: Path, root: Path) -> str | None:
        """Extract route path including dynamic segments.

        Args:
            file_path: Path to the page file.
            root: Repository root.

        Returns:
            Route path or None if not a page.
        """
        try:
            relative = file_path.relative_to(root)
            parts = []

            for part in relative.parts:
                if part.startswith("["):
                    parts.append(part)
                elif part.startswith("{"):
                    parts.append(part)
                elif part not in ("pages", "app", "src"):
                    parts.append(part)

            if not parts:
                return None

            filename = parts[-1]
            if "." in filename:
                filename = filename.rsplit(".", 1)[0]

            if filename == "index":
                parts = parts[:-1]
            elif filename not in ("layout", "loading", "error", "not-found"):
                parts[-1] = filename

            return "/" + "/".join(parts) if parts else "/"

        except ValueError:
            return None

    def _discover_api_routes(self, root: Path) -> list[DiscoveredPage]:
        """Discover API routes.

        Args:
            root: Repository root path.

        Returns:
            List of discovered API routes.
        """
        pages: list[DiscoveredPage] = []
        seen_paths: set[str] = set()

        # Look for api directories
        for api_dir in [root / "api", root / "pages" / "api", root / "app" / "api"]:
            if api_dir.exists():
                for file_path in api_dir.rglob("*"):
                    if file_path.is_file() and file_path.suffix in (".ts", ".js", ".tsx"):
                        route_path = self._get_api_route_path(file_path, api_dir)
                        if route_path and route_path not in seen_paths:
                            seen_paths.add(route_path)
                            pages.append(
                                DiscoveredPage(
                                    url_path=route_path,
                                    file_path=str(file_path),
                                    page_type=PageType.API_ROUTE,
                                    title=None,
                                    has_dynamic_params="[" in route_path,
                                )
                            )

        return pages

    def _get_api_route_path(self, file_path: Path, root: Path) -> str:
        """Get API route path from file.

        Args:
            file_path: Path to API route file.
            root: API directory root.

        Returns:
            API route path.
        """
        try:
            relative = file_path.relative_to(root)
            parts = list(relative.parts)

            filename = parts[-1]
            if "." in filename:
                filename = filename.rsplit(".", 1)[0]

            if filename == "index":
                parts[-1] = ""
            else:
                parts[-1] = filename

            return "/api/" + "/".join(p for p in parts if p)

        except ValueError:
            return "/api"

    def _discover_code_based_routes(self, root: Path) -> list[DiscoveredPage]:
        """Discover routes from code-based routing (Django, Flask, Express).

        Args:
            root: Repository root path.

        Returns:
            List of discovered pages.
        """
        pages: list[DiscoveredPage] = []
        seen_paths: set[str] = set()

        # Look for route definitions in Python/JS files
        route_patterns = ["urls.py", "views.py", "routes.js", "routes.ts", "app.js"]

        for pattern in route_patterns:
            for file_path in root.rglob(pattern):
                routes = self._parse_route_definitions(file_path)
                for route_path in routes:
                    if route_path not in seen_paths:
                        seen_paths.add(route_path)
                        pages.append(
                            DiscoveredPage(
                                url_path=route_path,
                                file_path=str(file_path),
                                page_type=PageType.GENERAL,
                                title=None,
                                has_dynamic_params="<" in route_path or ":" in route_path,
                            )
                        )

        return pages

    def _parse_route_definitions(self, file_path: Path) -> list[str]:
        """Parse route definitions from a file.

        Args:
            file_path: Path to route definitions file.

        Returns:
            List of route paths.
        """
        routes: list[str] = []

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Simple pattern matching for common route formats
            import re

            # Django url patterns
            django_pattern = r'path\(["\']([^"\']+)["\']'
            routes.extend(re.findall(django_pattern, content))

            # Flask/Express route decorators
            flask_pattern = r'@app\.route\(["\']([^"\']+)["\']'
            routes.extend(re.findall(flask_pattern, content))

            # Express router
            express_pattern = r'router\.(get|post|put|delete)\(["\']([^"\']+)["\']'
            routes.extend(m.group(2) for m in re.finditer(express_pattern, content))

        except OSError:
            pass

        return routes

    def _discover_all_pages(self, root: Path) -> list[DiscoveredPage]:
        """Fallback discovery for unknown routing strategies.

        Args:
            root: Repository root path.

        Returns:
            List of discovered pages.
        """
        pages: list[DiscoveredPage] = []
        seen_paths: set[str] = set()

        # Scan for HTML files
        for html_file in root.rglob("*.html"):
            if self._is_page_file(html_file):
                route_path = self._html_to_route_path(html_file, root)
                if route_path and route_path not in seen_paths:
                    seen_paths.add(route_path)
                    pages.append(
                        DiscoveredPage(
                            url_path=route_path,
                            file_path=str(html_file),
                            page_type=PageType.GENERAL,
                            title=None,
                            has_dynamic_params=False,
                        )
                    )

        return pages

    def _is_page_file(self, file_path: Path) -> bool:
        """Check if a file is likely a page file.

        Args:
            file_path: Path to check.

        Returns:
            True if file appears to be a page.
        """
        # Skip common non-page files
        skip_patterns = (
            "_app",
            "_document",
            "_error",
            "layout",
            "loading",
            "error",
            "not-found",
            "middleware",
            ".test.",
            ".spec.",
            "__tests__",
        )

        stem = file_path.stem
        return not any(pattern in stem for pattern in skip_patterns)

    def _html_to_route_path(self, html_file: Path, root: Path) -> str:
        """Convert HTML file path to route path.

        Args:
            html_file: Path to HTML file.
            root: Repository root.

        Returns:
            Route path.
        """
        try:
            relative = html_file.relative_to(root)
            parts = list(relative.parts)

            if parts[-1] == "index.html":
                parts[-1] = ""
            elif parts[-1].endswith(".html"):
                parts[-1] = parts[-1][:-5]

            path = "/" + "/".join(p for p in parts if p)
            return path if path else "/"

        except ValueError:
            return "/"

    def discover_sitemap(
        self,
        repository_path: str | Path,
    ) -> Result[list[str], str]:
        """Discover sitemap files in the repository.

        Args:
            repository_path: Path to the repository root.

        Returns:
            Result containing list of sitemap URLs.
        """
        root = Path(repository_path).resolve()
        sitemaps: list[str] = []

        # Look for sitemap files
        for sitemap in root.rglob("sitemap*.xml"):
            sitemaps.append(str(sitemap))

        # Look for sitemap in robots.txt
        robots_txt = root / "robots.txt"
        if robots_txt.exists():
            try:
                with open(robots_txt, encoding="utf-8") as f:
                    for line in f:
                        if line.lower().startswith("sitemap:"):
                            sitemap_url = line.split(":", 1)[1].strip()
                            if sitemap_url and sitemap_url not in sitemaps:
                                sitemaps.append(sitemap_url)
            except OSError:
                pass

        return success(sitemaps)