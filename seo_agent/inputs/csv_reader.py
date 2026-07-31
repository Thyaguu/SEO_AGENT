"""CSV Reader for SEO Agent Keyword Intelligence datasets.

Parses external CSV files containing keyword intelligence attributes (search volume, intent,
priority scores, H2 outlines, LSI keywords, and proposed metadata) into NormalizedSEOEntry objects.
The CSV reader does NOT require page identifier columns (url/page_path).
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

# Keyword column aliases
KEYWORD_COLUMNS = {
    "keyword", "term", "seedkeyword", "topic", "phrase", "name", "targetkeyword"
}

COLUMN_MAP = {
    "keyword": "keyword",
    "term": "keyword",
    "seedkeyword": "keyword",
    "topic": "keyword",
    "phrase": "keyword",
    "name": "keyword",
    "targetkeyword": "keyword",

    "searchvolume": "search_volume",
    "volume": "search_volume",
    "monthlysearches": "search_volume",

    "competition": "competition",
    "difficulty": "competition",
    "keyworddifficulty": "competition",
    "kd": "competition",

    "searchintent": "search_intent",
    "intent": "search_intent",
    "userintent": "search_intent",

    "contenttype": "content_type",
    "recommendedcontenttype": "content_type",
    "type": "content_type",

    "contentpriorityscore": "content_priority_score",
    "priorityscore": "content_priority_score",
    "priority": "content_priority_score",

    "aiopportunityscore": "ai_opportunity_score",
    "opportunityscore": "ai_opportunity_score",

    "rankingfeasibility": "ranking_feasibility",
    "feasibility": "ranking_feasibility",

    "seometatitle": "meta_title",
    "metatitle": "meta_title",
    "title": "meta_title",
    "pagetitle": "meta_title",

    "seometadescription": "meta_description",
    "metadescription": "meta_description",
    "description": "meta_description",
    "pagedescription": "meta_description",

    "h2outlines": "h2_outlines",
    "h2": "h2_outlines",
    "headings": "h2_outlines",
    "outline": "h2_outlines",

    "lsikeywords": "lsi_keywords",
    "secondarykeywords": "lsi_keywords",
    "lsikeyword": "lsi_keywords",

    "pagepath": "page_path",
    "path": "page_path",
    "route": "page_path",
    "url": "page_path",
    "page": "page_path",
}


def _normalize_key(key: str) -> str:
    return key.lower().replace("_", "").replace("-", "").replace(" ", "").strip()


def _parse_float(val: Any, default: float = 0.0) -> float:
    try:
        s = str(val).strip().rstrip("%")
        return float(s)
    except Exception:
        return default


def _parse_int(val: Any, default: int = 0) -> int:
    try:
        s = str(val).strip().replace(",", "")
        return int(float(s))
    except Exception:
        return default


class CSVSEOInputReader(BaseSEOInputReader):
    """Parses Keyword Intelligence CSV input datasets."""

    def read(self, source: str | Path | dict[str, Any] | list[Any]) -> Result[SEOInputCollection, str]:
        """Read CSV file path or raw CSV string and return normalized SEOInputCollection."""
        csv_content = ""
        source_path_str: str | None = None

        if isinstance(source, (str, Path)):
            src_str = str(source)
            if len(src_str) < 4096 and not ("\n" in src_str or "," in src_str):
                path_obj = Path(src_str)
                if path_obj.exists() and path_obj.is_file():
                    source_path_str = str(path_obj)
                    try:
                        csv_content = path_obj.read_text(encoding="utf-8")
                    except Exception as e:
                        return Failure(f"Failed to read CSV file '{path_obj}': {e}")
                else:
                    return Failure(f"CSV file not found: {source}")
            else:
                csv_content = src_str
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
            has_keyword_col = False

            for original_col in reader.fieldnames:
                norm_key = _normalize_key(original_col)
                if norm_key in COLUMN_MAP:
                    mapped_field = COLUMN_MAP[norm_key]
                    header_map[original_col] = mapped_field
                    if norm_key in KEYWORD_COLUMNS or mapped_field == "keyword":
                        has_keyword_col = True
                else:
                    if "keyword" in norm_key and not any(s in norm_key for s in ("score", "volume", "difficulty", "density", "count")):
                        header_map[original_col] = "keyword"
                        has_keyword_col = True
                    else:
                        header_map[original_col] = original_col

            if not has_keyword_col:
                for original_col in reader.fieldnames:
                    norm_k = _normalize_key(original_col)
                    if not any(s in norm_k for s in ("score", "volume", "difficulty", "density", "count", "id", "num")):
                        header_map[original_col] = "keyword"
                        has_keyword_col = True
                        logger.info(f"Fallback heuristic selected column '{original_col}' as keyword column")
                        break

            if not has_keyword_col and reader.fieldnames:
                # Force first column as keyword column as ultimate fallback
                first_col = reader.fieldnames[0]
                header_map[first_col] = "keyword"
                has_keyword_col = True

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
                    entry_data[mapped_col] = str_val

                kw_term = entry_data.get("keyword") or raw_record.get("keyword") or raw_record.get("term")
                if not kw_term or not str(kw_term).strip():
                    logger.warning(f"CSV Row {row_idx} skipped: missing keyword term")
                    skipped_count += 1
                    continue

                # Process list fields
                h2_list: list[str] = []
                if "h2_outlines" in entry_data and isinstance(entry_data["h2_outlines"], str):
                    h2_raw = entry_data["h2_outlines"]
                    h2_list = [h.strip() for h in h2_raw.replace(";", "|").replace("\n", "|").split("|") if h.strip()]

                lsi_list: list[str] = []
                if "lsi_keywords" in entry_data and isinstance(entry_data["lsi_keywords"], str):
                    lsi_raw = entry_data["lsi_keywords"]
                    lsi_list = [k.strip() for k in lsi_raw.replace(";", ",").split(",") if k.strip()]

                entry = NormalizedSEOEntry(
                    keyword=str(kw_term).strip(),
                    search_volume=_parse_int(entry_data.get("search_volume", 0)),
                    competition=_parse_float(entry_data.get("competition", 0.0)),
                    search_intent=str(entry_data.get("search_intent") or "informational").lower(),
                    content_type=str(entry_data.get("content_type") or "page").lower(),
                    content_priority_score=_parse_float(entry_data.get("content_priority_score", 0.0)),
                    ai_opportunity_score=_parse_float(entry_data.get("ai_opportunity_score", 0.0)),
                    ranking_feasibility=_parse_float(entry_data.get("ranking_feasibility", 0.0)),
                    meta_title=entry_data.get("meta_title"),
                    meta_description=entry_data.get("meta_description"),
                    h2_outlines=h2_list,
                    lsi_keywords=lsi_list,
                    page_path=entry_data.get("page_path"),
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
            logger.error(f"Error parsing Keyword Intelligence CSV: {e}")
            return Failure(f"Error parsing Keyword Intelligence CSV: {e}")
