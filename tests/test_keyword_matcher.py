"""Unit tests for AI Page-Keyword Semantic Matching Engine and Keyword Intelligence CSV Reader."""

import pytest
from pathlib import Path
from seo_agent.inputs.csv_reader import CSVSEOInputReader
from seo_agent.agents.planning.page_keyword_matcher import PageKeywordMatcher
from seo_agent.models.repository import PageInfo
from seo_agent.models.seo import Metadata


def test_csv_reader_keyword_intelligence(tmp_path: Path):
    csv_file = tmp_path / "seo_intelligence.csv"
    csv_file.write_text(
        "Keyword,Search Volume,Competition,Search Intent,SEO Meta Title,SEO Meta Description,H2 Outlines,LSI Keywords,AI Opportunity Score,Content Priority Score\n"
        "Recruitment Software,12000,0.45,commercial,Enterprise Recruitment Software | TechNova,Best recruitment software for modern HR teams.,Features|Pricing|Integrations,\"ATS Software, Hiring Automation\",92,95\n"
        "ATS Software,8500,0.50,commercial,Applicant Tracking System | TechNova,Streamline hiring with TechNova ATS.,Overview|Workflow,\"Recruitment Software, Candidate Screening\",88,90\n"
        "Talent Acquisition,5400,0.30,informational,Talent Acquisition Strategies | TechNova,Guide to enterprise talent acquisition.,Strategy|Metrics,\"Hiring Software, Resume Screening\",80,85\n"
        "AI Interviews,3200,0.25,commercial,AI Video Interviewing Tool | TechNova,Automate candidate screening with AI interviews.,AI Screening|Live Demos,\"Hiring Software, Candidate Screening\",85,80\n"
        "Candidate Screening,2100,0.20,informational,Automated Candidate Screening Guide,How to screen candidates faster with AI.,Best Practices|Tools,\"Resume Screening, ATS\",75,70\n",
        encoding="utf-8"
    )

    reader = CSVSEOInputReader()
    res = reader.read(csv_file)

    assert res.is_success()
    collection = res.value
    assert collection.source_type == "csv"
    assert collection.records_loaded == 5
    assert collection.records[0].keyword == "Recruitment Software"
    assert collection.records[0].search_volume == 12000
    assert collection.records[0].search_intent == "commercial"
    assert "Features" in collection.records[0].h2_outlines


def test_page_keyword_matcher_assignments():
    pages = [
        PageInfo(file_path=Path("/repo/index.html"), route="/index.html", title="Home - TechNova Recruitment & Hiring"),
        PageInfo(file_path=Path("/repo/about.html"), route="/about.html", title="About TechNova Solutions - Talent Acquisition Experts"),
        PageInfo(file_path=Path("/repo/services.html"), route="/services.html", title="AI Recruitment & Hiring Services"),
        PageInfo(file_path=Path("/repo/contact.html"), route="/contact.html", title="Contact Us - AI Interviews & Demos"),
    ]

    reader = CSVSEOInputReader()
    csv_text = (
        "Keyword,Search Volume,Competition,Search Intent,SEO Meta Title,SEO Meta Description,H2 Outlines,LSI Keywords,AI Opportunity Score,Content Priority Score\n"
        "Recruitment Software,12000,0.45,commercial,Enterprise Recruitment Software,Best software for hiring.,Features|Pricing,\"ATS Software, Hiring Software\",92,95\n"
        "ATS Software,8500,0.50,commercial,Applicant Tracking System,Streamline hiring.,Overview|Workflow,\"Recruitment Software, Candidate Screening\",88,90\n"
        "Hiring Software,6200,0.40,commercial,Hiring Software Platform,Manage applicants easily.,Tools|Solutions,\"ATS Software, Recruitment Software\",85,85\n"
        "Talent Acquisition,5400,0.30,informational,Talent Acquisition Strategies,Guide to talent acquisition.,Strategy|Metrics,\"Resume Screening, Candidate Screening\",80,85\n"
        "Resume Screening,3100,0.25,informational,Resume Screening Best Practices,Screen resumes fast.,Methods|Automation,\"Candidate Screening, Talent Acquisition\",75,75\n"
        "AI Recruitment,9500,0.35,commercial,AI Recruitment Services,Transform recruitment with AI.,Solutions|AI Tools,\"AI Hiring, Hiring Automation\",90,92\n"
        "AI Hiring,4200,0.30,commercial,AI Hiring Solutions,Automate recruitment process.,Benefits|Features,\"AI Recruitment, Hiring Automation\",82,80\n"
        "AI Interviews,3200,0.25,commercial,AI Video Interviewing Tool,Schedule AI interviews.,AI Screening|Live Demos,\"Candidate Screening, Hiring Software\",85,80\n"
        "Candidate Screening,2100,0.20,informational,Automated Candidate Screening,How to screen candidates.,Best Practices|Tools,\"Resume Screening, ATS\",75,70\n"
        "Unassigned High Volume Keyword,25000,0.60,commercial,Massive SEO Landing Page,Target high volume term.,Overview|Guide,\"SEO Landing Page\",98,99\n"
    )
    col = reader.read(csv_text).value

    matcher = PageKeywordMatcher()
    result = matcher.match_pages(pages, col.records)

    assert len(result.assignments) == 4

    # Verify every page receives 1 Primary Keyword and 2 Secondary Keywords
    primary_keywords_set = set()
    for ass in result.assignments:
        assert ass.primary_keyword is not None
        assert len(ass.secondary_keywords) == 2
        assert ass.confidence_score >= 0.80
        assert len(ass.ai_reasoning) > 0
        primary_keywords_set.add(ass.primary_keyword.keyword)

    # Primary keywords must be unique per page across the repository
    assert len(primary_keywords_set) == 4

    # Verify unassigned keywords handling (High volume keyword triggers generate_seo_page)
    gen_actions = [a for a in result.unassigned_actions if a.action == "generate_seo_page"]
    assert len(gen_actions) >= 1
    slugs = [a.target_slug for a in gen_actions if a.target_slug]
    assert any("unassigned-high-volume-keyword.html" in s for s in slugs)
