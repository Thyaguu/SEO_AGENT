"""Framework detection service.

This module provides functionality to detect the frontend framework
and routing strategy used in a repository.

Supported frameworks:
- Static HTML
- React (CRA, Vite)
- Next.js (App Router & Pages Router)
- Vue / Nuxt
- Angular
- Astro
- Svelte / SvelteKit
- Remix
- Gatsby
- Laravel Blade
- Django
- Flask
- Express.js

Usage:
    from seo_agent.repository.framework_detector import FrameworkDetector

    detector = FrameworkDetector()
    result = detector.detect("/path/to/repo")
    if result.is_success():
        framework = result.value
        print(f"Detected: {framework.framework_type.value}")
"""

from pathlib import Path
from typing import TYPE_CHECKING

from seo_agent.core.logging import get_logger
from seo_agent.core.result import Result, success, Failure
from seo_agent.models.repository import (
    FrameworkInfo,
    FrameworkType,
    RoutingStrategy,
    RepositoryInfo,
)


# Framework detection patterns
FRAMEWORK_INDICATORS: dict[FrameworkType, tuple[str, ...]] = {
    FrameworkType.NEXT_JS: (
        "next.config.js",
        "next.config.mjs",
        "next.config.ts",
        ".next",
        "next-env.d.ts",
    ),
    FrameworkType.REACT: (
        "package.json",  # Will check for react/react-dom
        "vite.config.js",
        "vite.config.ts",
        "vite.config.mjs",
        "webpack.config.js",
        "webpack.config.ts",
    ),
    FrameworkType.VUE: (
        "vue.config.js",
        "nuxt.config.js",
        "nuxt.config.ts",
        ".nuxt",
    ),
    FrameworkType.ANGULAR: (
        "angular.json",
        "ngsw-config.json",
    ),
    FrameworkType.ASTRO: (
        "astro.config.mjs",
        "astro.config.js",
        "astro.config.ts",
    ),
    FrameworkType.SVELTE: (
        "svelte.config.js",
        "svelte.config.ts",
        "vite.config.js",  # SvelteKit uses vite
    ),
    FrameworkType.REMIX: (
        "remix.config.js",
        "remix.config.ts",
    ),
    FrameworkType.GATSBY: (
        "gatsby-config.js",
        "gatsby-config.ts",
        ".gatsby",
    ),
    FrameworkType.LARAVEL_BLADE: (
        "artisan",
        "composer.json",  # Will check for laravel/framework
    ),
    FrameworkType.DJANGO: (
        "manage.py",
        "settings.py",
    ),
    FrameworkType.FLASK: (
        "app.py",
        "wsgi.py",
    ),
    FrameworkType.EXPRESS: (
        "package.json",  # Will check for express
        "server.js",
        "app.js",
    ),
}

# Routing strategy indicators
ROUTING_PATTERNS: dict[RoutingStrategy, tuple[str, ...]] = {
    RoutingStrategy.FILE_BASED: (
        "pages/",
        "src/pages/",
        "app/",
        "src/app/",
    ),
    RoutingStrategy.DYNAMIC: (
        "[id]",
        "[slug]",
        "[...path]",
        "[[...slug]]",
        ":id",
        ":slug",
    ),
    RoutingStrategy.API_ROUTES: (
        "api/",
        "pages/api/",
        "app/api/",
        "src/pages/api/",
    ),
}


class FrameworkDetector:
    """Detects the frontend framework and routing strategy.

    This class analyzes repository files to determine the framework
    being used and its routing strategy.

    Attributes:
        _logger: Logger instance for the detector.

    Example:
        detector = FrameworkDetector()
        result = detector.detect("/path/to/repo")
        if result.is_success():
            print(result.value.framework_type)
    """

    def __init__(self) -> None:
        """Initialize the framework detector."""
        self._logger = get_logger(__name__)

    def detect(
        self,
        repository_path: str | Path,
        repository_info: "RepositoryInfo | None" = None,
    ) -> Result[FrameworkInfo, str]:
        """Detect the framework and routing strategy.

        Args:
            repository_path: Path to the repository root.
            repository_info: Optional existing repository info with scanned files.

        Returns:
            Result containing FrameworkInfo on success, error on failure.
        """
        root = Path(repository_path).resolve()

        if not root.exists():
            return Result.failure(f"Repository path does not exist: {root}")

        self._logger.info(f"Detecting framework at {root}")

        try:
            # Detect framework type
            framework_type = self._detect_framework_type(root)

            # Detect routing strategy
            routing_strategy = self._detect_routing_strategy(root, framework_type)

            # Get additional metadata
            metadata = self._extract_framework_metadata(root, framework_type)

            framework_info = FrameworkInfo(
                framework_type=framework_type,
                routing_strategy=routing_strategy,
                version=metadata.get("version"),
                build_command=metadata.get("build_command"),
                output_directory=metadata.get("output_dir"),
            )

            self._logger.info(f"Framework detected: {framework_type.value} with {routing_strategy.value} routing")

            return success(framework_info)

        except Exception as e:
            self._logger.error("framework_detection_failed", exc_info=e)
            return Result.failure(f"Failed to detect framework: {e}")

    def _detect_framework_type(self, root: Path) -> FrameworkType:
        """Detect the framework type from repository files.

        Args:
            root: Repository root path.

        Returns:
            Detected FrameworkType.
        """
        # Check for Next.js first (most specific)
        if self._has_framework_indicators(root, FrameworkType.NEXT_JS):
            # Check if it's App Router or Pages Router
            if (root / "app").exists():
                return FrameworkType.NEXT_JS
            return FrameworkType.NEXT_JS

        # Check for Nuxt before Vue (Nuxt extends Vue)
        if self._has_framework_indicators(root, FrameworkType.NUXT):
            return FrameworkType.NUXT

        # Check for SvelteKit before Svelte
        if self._has_framework_indicators(root, FrameworkType.SVELTE):
            if (root / "src" / "routes").exists() or (root / "routes").exists():
                return FrameworkType.SVELTE
            return FrameworkType.SVELTE

        # Check other frameworks
        framework_checks = [
            FrameworkType.ANGULAR,
            FrameworkType.ASTRO,
            FrameworkType.GATSBY,
            FrameworkType.REMIX,
            FrameworkType.VUE,
            FrameworkType.REACT,
            FrameworkType.LARAVEL_BLADE,
            FrameworkType.DJANGO,
            FrameworkType.FLASK,
            FrameworkType.EXPRESS,
        ]

        for framework_type in framework_checks:
            if self._has_framework_indicators(root, framework_type):
                # Verify with package.json for JS frameworks
                if framework_type in (
                    FrameworkType.REACT,
                    FrameworkType.EXPRESS,
                ):
                    if self._verify_package_json_framework(root, framework_type):
                        return framework_type
                elif framework_type == FrameworkType.LARAVEL:
                    if self._verify_laravel(root):
                        return framework_type
                else:
                    return framework_type

        # Check for static HTML
        if self._is_static_html_site(root):
            return FrameworkType.STATIC_HTML

        return FrameworkType.UNKNOWN

    def _has_framework_indicators(
        self,
        root: Path,
        framework_type: FrameworkType,
    ) -> bool:
        """Check if repository has indicators for a framework.

        Args:
            root: Repository root path.
            framework_type: Framework type to check.

        Returns:
            True if framework indicators are present.
        """
        indicators = FRAMEWORK_INDICATORS.get(framework_type, ())

        for indicator in indicators:
            if (root / indicator).exists():
                return True

        return False

    def _verify_package_json_framework(
        self,
        root: Path,
        framework_type: FrameworkType,
    ) -> bool:
        """Verify framework from package.json dependencies.

        Args:
            root: Repository root path.
            framework_type: Expected framework type.

        Returns:
            True if package.json confirms the framework.
        """
        import json

        package_json = root / "package.json"
        if not package_json.exists():
            return False

        try:
            with open(package_json, encoding="utf-8") as f:
                data = json.load(f)

            deps = {
                **data.get("dependencies", {}),
                **data.get("devDependencies", {}),
            }

            if framework_type == FrameworkType.REACT:
                return "react" in deps or "react-dom" in deps
            elif framework_type == FrameworkType.EXPRESS:
                return "express" in deps
            elif framework_type == FrameworkType.NUXT:
                return "nuxt" in deps
            elif framework_type == FrameworkType.SVELTE:
                return "svelte" in deps
            elif framework_type == FrameworkType.SVELTE_KIT:
                return "@sveltejs/kit" in deps

        except (json.JSONDecodeError, OSError):
            pass

        return False

    def _verify_laravel(self, root: Path) -> bool:
        """Verify Laravel framework from composer.json.

        Args:
            root: Repository root path.

        Returns:
            True if composer.json confirms Laravel.
        """
        import json

        composer_json = root / "composer.json"
        if not composer_json.exists():
            return False

        try:
            with open(composer_json, encoding="utf-8") as f:
                data = json.load(f)

            deps = {
                **data.get("require", {}),
                **data.get("require-dev", {}),
            }

            return "laravel/framework" in deps

        except (json.JSONDecodeError, OSError):
            pass

        return False

    def _is_static_html_site(self, root: Path) -> bool:
        """Check if repository is a static HTML site.

        Args:
            root: Repository root path.

        Returns:
            True if site appears to be static HTML.
        """
        html_files = list(root.glob("*.html"))
        return len(html_files) > 0

    def _detect_routing_strategy(
        self,
        root: Path,
        framework_type: FrameworkType,
    ) -> RoutingStrategy:
        """Detect the routing strategy used.

        Args:
            root: Repository root path.
            framework_type: Detected framework type.

        Returns:
            Detected RoutingStrategy.
        """
        # Check for file-based routing patterns
        for pattern in ROUTING_PATTERNS[RoutingStrategy.FILE_BASED]:
            if (root / pattern).exists():
                # Determine if it's App Router or Pages Router
                if pattern == "app/" and (root / "app").exists():
                    return RoutingStrategy.FILE_BASED
                elif pattern == "pages/" and (root / "pages").exists():
                    return RoutingStrategy.FILE_BASED
                return RoutingStrategy.FILE_BASED

        # Check for dynamic routing
        for pattern in ROUTING_PATTERNS[RoutingStrategy.DYNAMIC]:
            for path in root.rglob(f"*{pattern}*"):
                if path.is_file() and path.suffix in (".js", ".jsx", ".ts", ".tsx", ".vue"):
                    return RoutingStrategy.DYNAMIC

        # Check for API routes
        for pattern in ROUTING_PATTERNS[RoutingStrategy.API_ROUTES]:
            if (root / pattern).exists():
                return RoutingStrategy.API_ROUTES

        # Framework-specific defaults
        if framework_type == FrameworkType.NEXT_JS:
            return RoutingStrategy.FILE_BASED
        elif framework_type == FrameworkType.ANGULAR:
            return RoutingStrategy.CONFIG_BASED
        elif framework_type in (FrameworkType.DJANGO, FrameworkType.FLASK):
            return RoutingStrategy.DYNAMIC

        return RoutingStrategy.UNKNOWN

    def _extract_framework_metadata(
        self,
        root: Path,
        framework_type: FrameworkType,
    ) -> dict[str, str | None]:
        """Extract framework-specific metadata.

        Args:
            root: Repository root path.
            framework_type: Detected framework type.

        Returns:
            Dictionary with metadata fields.
        """
        metadata: dict[str, str | None] = {
            "version": None,
            "build_command": None,
            "output_dir": None,
        }

        # Extract version from package.json
        package_json = root / "package.json"
        if package_json.exists():
            import json
            try:
                with open(package_json, encoding="utf-8") as f:
                    data = json.load(f)
                    metadata["version"] = data.get("version")
            except (json.JSONDecodeError, OSError):
                pass

        # Framework-specific build/output info
        if framework_type == FrameworkType.NEXT_JS:
            metadata["output_dir"] = ".next"
            metadata["build_command"] = "npm run build"
        elif framework_type == FrameworkType.VITE:
            metadata["output_dir"] = "dist"
            metadata["build_command"] = "npm run build"
        elif framework_type == FrameworkType.ANGULAR:
            metadata["output_dir"] = "dist"
            metadata["build_command"] = "ng build"

        return metadata