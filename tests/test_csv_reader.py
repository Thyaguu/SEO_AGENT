"""Unit tests for CSVSEOInputReader and JSONSEOInputReader."""

import pytest
from pathlib import Path
from seo_agent.inputs.csv_reader import CSVSEOInputReader
from seo_agent.inputs.json_reader import JSONSEOInputReader


def test_csv_reader_valid_content(tmp_path: Path):
    csv_file = tmp_path / "seo_data.csv"
    csv_file.write_text(
        "Page Path,Title,Meta Description,Canonical URL,Keywords,H1,OG Title,Twitter Card\n"
        "/about,About TechNova,Leading AI consulting firm,https://example.com/about,\"AI, consulting, cloud\",About Us,TechNova Solutions,summary_large_image\n"
        "/services,Our Services,Enterprise software development,https://example.com/services,\"services, software\",Our Services,TechNova Services,summary_large_image\n",
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
    assert first.page_path == "/about"
    assert first.title == "About TechNova"
    assert first.description == "Leading AI consulting firm"
    assert first.canonical == "https://example.com/about"
    assert first.keywords == ["AI", "consulting", "cloud"]
    assert first.h1 == "About Us"
    assert first.og_title == "TechNova Solutions"
    assert first.twitter_card == "summary_large_image"


def test_csv_reader_missing_identifier_fails(tmp_path: Path):
    csv_file = tmp_path / "invalid.csv"
    csv_file.write_text(
        "Title,Meta Description\n"
        "About Page,Description Here\n",
        encoding="utf-8"
    )

    reader = CSVSEOInputReader()
    res = reader.read(csv_file)

    assert res.is_failure()
    assert "missing required page identifier column" in res.get_error_or_none().lower()


def test_json_reader_valid_payload():
    json_data = [
        {
            "page_path": "/contact",
            "title": "Contact Us | TechNova",
            "description": "Get in touch with TechNova Solutions.",
            "keywords": ["contact", "support"],
            "og_title": "Contact TechNova"
        }
    ]

    reader = JSONSEOInputReader()
    res = reader.read(json_data)

    assert res.is_success()
    collection = res.value
    assert collection.source_type == "json"
    assert collection.records_loaded == 1
    assert collection.records[0].page_path == "/contact"
    assert collection.records[0].title == "Contact Us | TechNova"
    assert collection.records[0].keywords == ["contact", "support"]
