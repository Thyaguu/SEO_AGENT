"""SEO operations package.

This package provides SEO optimization services for the SEO Agent framework.
It includes tools for metadata optimization, page generation, sitemap management,
and robots.txt configuration.

Services:
    - MetadataOptimizer: Updates page metadata (title, meta, OG, Twitter, JSON-LD)
    - SEOPageGenerator: Generates SEO landing pages from ExecutionResult
    - SitemapService: Creates and updates sitemap.xml files
    - RobotsService: Manages robots.txt configuration

Example:
    from seo_agent.seo import MetadataOptimizer, SEOPageGenerator
    from seo_agent.seo import SitemapService, RobotsService
    from seo_agent.core.dependency_injection import Container

    container = Container()
    optimizer = MetadataOptimizer(container)
    generator = SEOPageGenerator(container)
    sitemap = SitemapService(container)
    robots = RobotsService(container)
"""

from seo_agent.seo.metadata_optimizer import MetadataOptimizer
from seo_agent.seo.seo_page_generator import SEOPageGenerator
from seo_agent.seo.sitemap import SitemapService
from seo_agent.seo.robots import RobotsService
from seo_agent.seo.applier import ApprovedChangesApplier, ApplicationSummary

__all__ = [
    "MetadataOptimizer",
    "SEOPageGenerator",
    "SitemapService",
    "RobotsService",
    "ApprovedChangesApplier",
    "ApplicationSummary",
]