"""
SEO configuration module.

Defines settings specific to SEO operations and page generation.
"""

from pydantic import Field, field_validator

from .base import BaseConfig


class SEOSettings(BaseConfig):
    """Settings for SEO operations."""

    model_config = BaseConfig.model_config | {"env_prefix": "SEO_"}

    page_limit: int = Field(
        default=10,
        ge=1,
        description="Maximum number of SEO pages to generate per execution",
    )
    output_directory: str = Field(
        default="seo",
        description="Directory name for generated SEO pages",
    )
    sitemap_filename: str = Field(
        default="sitemap.xml",
        description="Filename for the sitemap",
    )
    robots_filename: str = Field(
        default="robots.txt",
        description="Filename for robots.txt",
    )

    @field_validator("output_directory", mode="before")
    @classmethod
    def validate_output_directory(cls, v: str) -> str:
        """Ensure output directory name is valid."""
        if not v or v.strip() == "":
            return "seo"
        return v.strip()