"""Abstract Base Class for SEO Input Readers.

Defines the contract for external SEO data sources (CSV, JSON, n8n payloads).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from seo_agent.core.result import Result
from seo_agent.models.seo_input import SEOInputCollection


class BaseSEOInputReader(ABC):
    """Abstract base class for reading and normalizing external SEO input data."""

    @abstractmethod
    def read(self, source: str | Path | dict[str, Any] | list[Any]) -> Result[SEOInputCollection, str]:
        """Read and normalize external SEO data into an SEOInputCollection.

        Args:
            source: File path, CSV content string, or dictionary/list payload.

        Returns:
            Result containing SEOInputCollection on success, or failure message on error.
        """
        pass
