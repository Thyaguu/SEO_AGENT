"""CSV Reader for SEO Agent input data.

Parses external CSV files containing page SEO attributes into normalized domain models.
The CSV reader is the sole component aware of CSV column headers.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from pathlib import Path
from typing import Any

from seo_agent.core.result import Failure, Result, Success
from seo_agent.inputs.base import BaseSEOInputReader
from seo_agent.models.seo_input import NormalizedSEOEntry, SEOInputCollection

logger = logging.getLogger(__name__)

# Column aliases mapping (case-insensitive, stripped of underscores/spaces)
IDENTIFIER_COLUMNS = {
    "url", "pageurl", "targeturl", "link",
    "pagepath", "path", "route", "filepath", "file", "filename", "page"
}

COLUMN_MAP = {
    "url": "url",
    "pageurl": "url",
    "targeturl": "url",
    "link": "url",
    
    "pagepath": "page_path",
    "path": "page_path",
    "route": "page_path",
    "filepath": "page_path",
    "file": "page_path",
    "filename": "page_path",
    "page": "page_path",

    "title": "title",
    "metatitle": "title",
    "pagetitle": "title",

    "description": "description",
    "metadescription": "description",
    "pagedescription": "description",

    "canonical": "canonical",
    "canonicalurl": "canonical",

    "keywords": "keywords",
    "targetkeywords": "keywords",
    "seedkeywords": "keywords",

    "h1": "h1",
    "h1heading": "h1",
    "heading": "h1",

    "ogtitle": "og_title",
    "ogdescription": "og_description",
    "ogimage": "og_image",

    "twittercard": "twitter_card",
    "twittertitle": "twitter_title",
    "twitterdescription": "twitter_description",
    "twitterimage": "twitter_image",

    "structureddata": "structured_data",
    "jsonld": "structured_data",
    "schema": "structured_data",

    "internallinks": "internal_link_suggestions",
    "internallinksuggestions": "internal_link_suggestions",
    "links": "internal_link_suggestions",
}


def _normalize_key(key: str) -> str:
    return key.lower().replace("_", "").replace("-", "").replace(" ", "").strip()


class CSVSEOInputReader(BaseSEOInputReader):
    """Parses and normalizes CSV input files containing SEO recommendations."""

    def read(self, source: str | Path | dict[str, Any] | list[Any]) -> Result[SEOInputCollection, str]:
        """Read CSV file path or raw CSV string and return normalized SEOInputCollection."""
        csv_content = ""
        source_path_str: str | None = None

        if isinstance(source, (str, Path)):
            path_obj = Path(source)
            if path_obj.exists() and path_obj.is_file():
                source_path_str = str(path_obj)
                try:
                    csv_content = path_obj.read_text(encoding="utf-8")
                except Exception as e:
                    return Failure(f"Failed to read CSV file '{path_obj}': {e}")
            elif isinstance(source, str) and ("\n" in source or "," in source):
                csv_content = source
            else:
                return Failure(f"CSV file not found: {source}")
        else:
            return Failure(f"Unsupported CSV source type: {type(source)}")

        if not csv_content.strip():
            return Failure("CSV content is empty")

        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            if not reader.fieldnames:
                return Failure("CSV file has no header row")

            # Check column normalization
            header_map: dict[str, str] = {}
            has_identifier = False

            for original_col in reader.fieldnames:
                norm_key = _normalize_key(original_col)
                if norm_key in COLUMN_MAP:
                    mapped_field = COLUMN_MAP[norm_key]
                    header_map[original_col] = mapped_field
                    if norm_key in IDENTIFIER_COLUMNS:
                        has_identifier = True
                else:
                    header_map[original_col] = original_col

            if not has_identifier:
                return Failure(
                    "CSV missing required page identifier column (must contain at least one of: 'url', 'page_path', 'route', 'file_path')"
                )

            records: list[NormalizedSEOEntry] = []
            skipped_count = 0

            for row_idx, row in enumerate(reader, start=2):
                if not row or not any(str(v).strip() for v in row.values()):
                    skipped_count += 1
                    continue

                entry_data: dict[str, Any] = {}
                raw_record: dict[str, Any] = {}

                for orig_col, val in row.items():
                    if val is None:
                        continue
                    str_val = str(val).strip()
                    raw_record[orig_col] = str_val
                    
                    mapped_col = header_map.get(orig_col, orig_col)
                    if mapped_col in NormalizedSEOEntry.__dataclass_fields__:
                        entry_data[mapped_col] = str_val

                # Post-process list/dict fields
                if "keywords" in entry_data and isinstance(entry_data["keywords"], str):
                    kw_str = entry_data["keywords"]
                    entry_data["keywords"] = [k.strip() for k in kw_str.replace(";", ",").split(",") if k.strip()]

                if "internal_link_suggestions" in entry_data and isinstance(entry_data["internal_link_suggestions"], str):
                    links_str = entry_data["internal_link_suggestions"]
                    entry_data["internal_link_suggestions"] = [
                        l.strip() for l in links_str.replace("|", ",").replace("\n", ",").split(",") if l.strip()
                    ]

                if "structured_data" in entry_data and isinstance(entry_data["structured_data"], str):
                    sd_str = entry_data["structured_data"]
                    if sd_str.startswith("{") or sd_str.startswith("["):
                        try:
                            entry_data["structured_data"] = json.loads(sd_str)
                        except json.JSONDecodeError:
                            pass

                # Require at least url or page_path
                if not entry_data.get("url") and not entry_data.get("page_path"):
                    logger.warning(f"CSV Row {row_idx} skipped: missing both 'url' and 'page_path'")
                    skipped_count += 1
                    continue

                entry = NormalizedSEOEntry(
                    url=entry_data.get("url"),
                    page_path=entry_data.get("page_path"),
                    title=entry_data.get("title"),
                    description=entry_data.get("description"),
                    canonical=entry_data.get("canonical"),
                    keywords=entry_data.get("keywords", []),
                    h1=entry_data.get("h1"),
                    og_title=entry_data.get("og_title"),
                    og_description=entry_data.get("og_description"),
                    og_image=entry_data.get("og_image"),
                    twitter_card=entry_data.get("twitter_card"),
                    twitter_title=entry_data.get("twitter_title"),
                    twitter_description=entry_data.get("twitter_description"),
                    twitter_image=entry_data.get("twitter_image"),
                    structured_data=entry_data.get("structured_data"),
                    internal_link_suggestions=entry_data.get("internal_link_suggestions", []),
                    raw_data=raw_record,
                )
                records.append(entry)

            collection = SEOInputCollection(
                source_type="csv",
                source_path=source_path_str,
                records=records,
                records_loaded=len(records),
                skipped_records=skipped_count,
            )
            return Success(collection)

        except Exception as e:
            logger.error(f"Error parsing CSV input: {e}")
            return Failure(f"Error parsing CSV input: {e}")
