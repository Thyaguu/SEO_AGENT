"""Unit tests for MetadataParser structured data extraction."""

from seo_agent.repository.metadata_parser import MetadataParser
from seo_agent.models.seo import StructuredData


def test_extract_structured_data_success():
    parser = MetadataParser()
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "Test Article"
        }
        </script>
    </head>
    <body></body>
    </html>
    """
    result = parser.parse_content(html, "/test")
    assert result.is_success()
    metadata = result.unwrap()
    assert metadata.structured_data == ("Article",)


def test_extract_structured_data_direct_call():
    parser = MetadataParser()
    html = """
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "TechNova"
    }
    </script>
    """
    structured_data_list = parser._extract_structured_data(html)
    assert len(structured_data_list) == 1
    assert isinstance(structured_data_list[0], StructuredData)
    assert structured_data_list[0].schema_type == "Organization"
    assert structured_data_list[0].properties == {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "TechNova",
    }
