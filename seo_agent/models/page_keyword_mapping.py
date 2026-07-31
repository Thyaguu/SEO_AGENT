"""Domain models for AI Page-Keyword Semantic Matching.

Contains representations for assignments of Primary and Secondary keywords
to discovered website pages, along with confidence scores, AI reasoning,
and unassigned keyword actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from seo_agent.models.seo_input import NormalizedSEOEntry


@dataclass
class PageKeywordAssignment:
    """Assignment of Primary and Secondary keywords to an existing website page.

    Attributes:
        page_route: URL route or page path (e.g. "/index.html", "/about").
        file_path: Absolute or relative physical file path.
        primary_keyword: Assigned primary keyword record.
        secondary_keywords: Tuple of exactly 2 assigned secondary keyword records.
        confidence_score: Confidence score (0.0 to 1.0) for this assignment.
        ai_reasoning: Explanation of why this primary + secondary assignment fits this page.
    """

    page_route: str
    file_path: str
    primary_keyword: NormalizedSEOEntry
    secondary_keywords: tuple[NormalizedSEOEntry, NormalizedSEOEntry]
    confidence_score: float = 0.95
    ai_reasoning: str = ""


@dataclass
class UnassignedKeywordAction:
    """Action for a keyword that was not assigned as primary to any existing page.

    Attributes:
        keyword_record: Unassigned keyword record.
        action: "generate_seo_page" or "defer".
        target_slug: Proposed slug if generating a new landing page.
        reasoning: Explanation for decision.
    """

    keyword_record: NormalizedSEOEntry
    action: str
    target_slug: str | None = None
    reasoning: str = ""


@dataclass
class KeywordMatchingResult:
    """Overall result of the AI Page-Keyword Semantic Matching Engine.

    Attributes:
        assignments: List of PageKeywordAssignment objects (1 per page).
        unassigned_actions: List of UnassignedKeywordAction objects for unmapped keywords.
    """

    assignments: list[PageKeywordAssignment] = field(default_factory=list)
    unassigned_actions: list[UnassignedKeywordAction] = field(default_factory=list)
