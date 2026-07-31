"""JSON / n8n Reader for SEO Agent Keyword Intelligence datasets.

Parses external JSON files or payload items into NormalizedSEOEntry objects.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from seo_agent.core.result import Failure, Result, Success
from seo_agent.inputs.base import BaseSEOInputReader
from seo_agent.models.seo_input import NormalizedSEOEntry, SEOInputCollection

logger = logging.getLogger(__name__)


class JSONSEOInputReader(BaseSEOInputReader):
    """Parses and normalizes JSON Keyword Intelligence input data."""

    def read(self, source: str | Path | dict[str, Any] | list[Any]) -> Result[SEOInputCollection, str]:
        """Read JSON file, string, or list/dict payload and return normalized SEOInputCollection."""
        raw_items: list[dict[str, Any]] = []
        source_path_str: str | None = None

        if isinstance(source, (str, Path)):
            path_obj = Path(source)
            if path_obj.exists() and path_obj.is_file():
                source_path_str = str(path_obj)
                try:
                    content = path_obj.read_text(encoding="utf-8")
                    parsed = json.loads(content)
                except Exception as e:
                    return Failure(f"Failed to read JSON file '{path_obj}': {e}")
            else:
                try:
                    parsed = json.loads(str(source))
                except Exception as e:
                    return Failure(f"Failed to parse JSON string: {e}")
        else:
            parsed = source

        if isinstance(parsed, dict):
            if "records" in parsed and isinstance(parsed["records"], list):
                raw_items = parsed["records"]
            elif "items" in parsed and isinstance(parsed["items"], list):
                raw_items = parsed["items"]
            else:
                raw_items = [parsed]
        elif isinstance(parsed, list):
            raw_items = [item for item in parsed if isinstance(item, dict)]
        else:
            return Failure(f"Invalid JSON payload structure: expected list or dict, got {type(parsed)}")

        records: list[NormalizedSEOEntry] = []
        skipped_count = 0

        for item in raw_items:
            kw_term = item.get("keyword") or item.get("term") or item.get("seed_keyword") or item.get("topic")
            if not kw_term or not str(kw_term).strip():
                skipped_count += 1
                continue

            h2s = item.get("h2_outlines") or item.get("h2") or []
            if isinstance(h2s, str):
                h2s = [h.strip() for h in h2s.replace(";", "|").replace("\n", "|").split("|") if h.strip()]

            lsis = item.get("lsi_keywords") or item.get("secondary_keywords") or []
            if isinstance(lsis, str):
                lsis = [k.strip() for k in lsis.replace(";", ",").split(",") if k.strip()]

            entry = NormalizedSEOEntry(
                keyword=str(kw_term).strip(),
                search_volume=int(item.get("search_volume") or item.get("volume") or 0),
                competition=float(item.get("competition") or item.get("difficulty") or 0.0),
                search_intent=str(item.get("search_intent") or item.get("intent") or "informational").lower(),
                content_type=str(item.get("content_type") or "page").lower(),
                content_priority_score=float(item.get("content_priority_score") or item.get("priority_score") or 0.0),
                ai_opportunity_score=float(item.get("ai_opportunity_score") or item.get("opportunity_score") or 0.0),
                ranking_feasibility=float(item.get("ranking_feasibility") or item.get("feasibility") or 0.0),
                meta_title=item.get("meta_title") or item.get("seo_meta_title") or item.get("title"),
                meta_description=item.get("meta_description") or item.get("seo_meta_description") or item.get("description"),
                h2_outlines=h2s if isinstance(h2s, list) else [],
                lsi_keywords=lsis if isinstance(lsis, list) else [],
                page_path=item.get("page_path") or item.get("path") or item.get("url"),
                raw_data=item,
            )
            records.append(entry)

        collection = SEOInputCollection(
            source_type="json",
            source_path=source_path_str,
            records=records,
            records_loaded=len(records),
            skipped_records=skipped_count,
        )
        return Success(collection)
