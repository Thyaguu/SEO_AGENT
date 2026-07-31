"""JSON / n8n Reader for SEO Agent input data.

Parses external JSON files or dictionary/list payloads (such as n8n webhooks)
into identical NormalizedSEOEntry domain models.
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
    """Parses and normalizes JSON / n8n payload input data."""

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
            url = item.get("url") or item.get("page_url")
            page_path = item.get("page_path") or item.get("path") or item.get("route") or item.get("file_path")

            if not url and not page_path:
                skipped_count += 1
                continue

            kws = item.get("keywords") or item.get("seed_keywords") or []
            if isinstance(kws, str):
                kws = [k.strip() for k in kws.replace(";", ",").split(",") if k.strip()]

            links = item.get("internal_link_suggestions") or item.get("internal_links") or []
            if isinstance(links, str):
                links = [l.strip() for l in links.replace("|", ",").replace("\n", ",").split(",") if l.strip()]

            entry = NormalizedSEOEntry(
                url=url,
                page_path=page_path,
                title=item.get("title") or item.get("meta_title"),
                description=item.get("description") or item.get("meta_description"),
                canonical=item.get("canonical") or item.get("canonical_url"),
                keywords=kws if isinstance(kws, list) else [],
                h1=item.get("h1"),
                og_title=item.get("og_title"),
                og_description=item.get("og_description"),
                og_image=item.get("og_image"),
                twitter_card=item.get("twitter_card"),
                twitter_title=item.get("twitter_title"),
                twitter_description=item.get("twitter_description"),
                twitter_image=item.get("twitter_image"),
                structured_data=item.get("structured_data") or item.get("json_ld"),
                internal_link_suggestions=links if isinstance(links, list) else [],
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
