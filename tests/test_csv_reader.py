"""Unit tests for CSVSEOInputReader and JSONSEOInputReader."""

import pytest
from pathlib import Path
from seo_agent.inputs.csv_reader import CSVSEOInputReader
from seo_agent.inputs.json_reader import JSONSEOInputReader


def test_csv_reader_valid_content(tmp_path: Path):
    csv_file = tmp_path / "seo_data.csv"
    csv_file.write_text(
        "Keyword,Search Volume,Competition,Search Intent,SEO Meta Title,SEO Meta Description,Page Path\n"
        "AI Consulting,12000,0.45,commercial,About TechNova,Leading AI consulting firm,/about\n"
        "Enterprise Software,8500,0.50,commercial,Our Services,Enterprise software development,/services\n",
        encoding="utf-8"
    )

    reader = CSVSEOInputReader()
    res = reader.read(csv_file)

    assert res.is_success()
    collection = res.value
    assert collection.source_type == "csv"
    assert collection.records_loaded == 2
    assert collection.skipped_records == 0

    first = collection.records[0]
    assert first.keyword == "AI Consulting"
    assert first.search_volume == 12000
    assert first.meta_title == "About TechNova"
    assert first.meta_description == "Leading AI consulting firm"
    assert first.page_path == "/about"


def test_csv_reader_missing_keyword_column_fails(tmp_path: Path):
    csv_file = tmp_path / "invalid.csv"
    csv_file.write_text(
        "SEO Meta Title,SEO Meta Description\n"
        "About Page,Description Here\n",
        encoding="utf-8"
    )

    reader = CSVSEOInputReader()
    res = reader.read(csv_file)

    assert res.is_failure()
    assert "missing required keyword column" in res.get_error_or_none().lower()


def test_json_reader_valid_payload():
    json_data = [
        {
            "keyword": "AI Recruitment",
            "search_volume": 9500,
            "search_intent": "commercial",
            "meta_title": "Contact Us | TechNova",
            "meta_description": "Get in touch with TechNova Solutions.",
            "lsi_keywords": ["contact", "support"]
        }
    ]

    reader = JSONSEOInputReader()
    res = reader.read(json_data)

    assert res.is_success()
    collection = res.value
    assert collection.source_type == "json"
    assert collection.records_loaded == 1
    assert collection.records[0].keyword == "AI Recruitment"
    assert collection.records[0].search_volume == 9500
    assert collection.records[0].lsi_keywords == ["contact", "support"]
