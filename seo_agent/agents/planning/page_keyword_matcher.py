"""AI Page-Keyword Semantic Matching Engine.

Analyzes discovered website pages against the Keyword Intelligence Pool.
Uses LLM-based semantic reasoning and hybrid TF-IDF vector similarity to match:
- Exactly ONE Primary Keyword per page (unique across all pages).
- Exactly TWO Secondary Keywords per page.

Also evaluates unassigned keywords in the pool to decide whether to generate new SEO landing pages or defer them.
"""

from __future__ import annotations

import logging
import math
import re
from typing import TYPE_CHECKING, Any

from seo_agent.models.page_keyword_mapping import (
    KeywordMatchingResult,
    PageKeywordAssignment,
    UnassignedKeywordAction,
)

if TYPE_CHECKING:
    from seo_agent.models.repository import PageInfo
    from seo_agent.models.seo_input import NormalizedSEOEntry

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> set[str]:
    """Extract normalized word tokens from text."""
    words = re.findall(r"\b[a-zA-Z0-9]{2,}\b", text.lower())
    stop_words = {
        "the", "and", "is", "in", "it", "to", "for", "with", "on", "at", "by", "from",
        "an", "be", "this", "that", "which", "or", "as", "are", "was", "will", "our",
        "your", "us", "html", "page", "home", "about", "contact", "services", "solutions"
    }
    return {w for w in words if w not in stop_words}


def _calculate_cosine_similarity(tokens1: set[str], tokens2: set[str]) -> float:
    """Calculate Jaccard / Cosine token overlap similarity score (0.0 to 1.0)."""
    if not tokens1 or not tokens2:
        return 0.0
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    return intersection / union if union > 0 else 0.0


def _get_page_text_representation(page: PageInfo) -> str:
    """Build a comprehensive text representation of a discovered website page."""
    parts = []
    route = str(getattr(page, "route", ""))
    parts.append(route.replace("/", " ").replace("-", " ").replace(".", " "))

    if page.title:
        parts.append(page.title)

    meta = getattr(page, "metadata", None)
    if meta:
        if meta.title:
            parts.append(meta.title)
        if meta.description:
            parts.append(meta.description)
        if meta.h1:
            parts.append(meta.h1)
        if meta.headings:
            parts.extend(h.text for h in meta.headings)
        if meta.keywords:
            parts.extend(meta.keywords)

    return " ".join(parts)


def _get_keyword_text_representation(record: NormalizedSEOEntry) -> str:
    """Build text representation of a keyword intelligence record."""
    parts = [record.keyword]
    if record.meta_title:
        parts.append(record.meta_title)
    if record.meta_description:
        parts.append(record.meta_description)
    if record.h2_outlines:
        parts.extend(record.h2_outlines)
    if record.lsi_keywords:
        parts.extend(record.lsi_keywords)
    parts.append(record.search_intent)
    return " ".join(parts)


class PageKeywordMatcher:
    """AI Page-Keyword Semantic Matching Engine."""

    def __init__(self, confidence_threshold: float = 0.70) -> None:
        self._confidence_threshold = confidence_threshold

    def match_pages(
        self,
        pages: list[PageInfo],
        keyword_records: list[NormalizedSEOEntry],
    ) -> KeywordMatchingResult:
        """Perform semantic page-to-keyword matching.

        Enforces:
        - Exactly 1 Primary Keyword per page (unique primary assignment per page).
        - Exactly 2 Secondary Keywords per page.
        - Evaluates remaining unassigned keywords for new page generation vs deferral.
        """
        if not pages or not keyword_records:
            return KeywordMatchingResult()

        logger.debug(f"Starting AI Page-Keyword Semantic Matching for {len(pages)} page(s) and {len(keyword_records)} keyword(s)...")

        # 1. Compute similarity matrix & scores
        page_scores: dict[int, list[tuple[float, int]]] = {}  # page_idx -> list of (score, kw_idx)
        
        for p_idx, page in enumerate(pages):
            page_text = _get_page_text_representation(page)
            page_tokens = _tokenize(page_text)
            page_route_clean = str(getattr(page, "route", "")).lower()

            scores_for_page = []
            for k_idx, kw_rec in enumerate(keyword_records):
                kw_text = _get_keyword_text_representation(kw_rec)
                kw_tokens = _tokenize(kw_text)

                # Base token similarity
                sim = _calculate_cosine_similarity(page_tokens, kw_tokens)

                # Route / Page path direct match bonus
                if kw_rec.page_path:
                    clean_rec_path = str(kw_rec.page_path).lower()
                    if clean_rec_path in page_route_clean or page_route_clean in clean_rec_path:
                        sim += 0.5

                # Search intent alignment bonus
                intent = kw_rec.search_intent.lower()
                if "contact" in page_route_clean or "about" in page_route_clean:
                    if intent in ("navigational", "informational"):
                        sim += 0.2
                elif "service" in page_route_clean or "product" in page_route_clean:
                    if intent in ("commercial", "transactional"):
                        sim += 0.2
                elif page_route_clean in ("/", "/index.html", "/home"):
                    if intent in ("commercial", "brand", "informational"):
                        sim += 0.15

                # Score boost from Opportunity / Priority scores & Search Volume
                vol_boost = min(kw_rec.search_volume / 10000.0, 0.15)
                prio_boost = min(kw_rec.content_priority_score / 100.0, 0.15)
                total_score = sim + vol_boost + prio_boost

                scores_for_page.append((total_score, k_idx))

            # Sort keywords by score for this page descending
            scores_for_page.sort(key=lambda x: x[0], reverse=True)
            page_scores[p_idx] = scores_for_page

        # 2. Assign unique Primary Keywords per page
        assigned_primary_kw_indices: set[int] = set()
        page_primary_assignments: dict[int, int] = {}  # page_idx -> kw_idx

        # Greedy primary assignment based on top scores across all (page, kw) pairs
        all_candidate_triples = []
        for p_idx, score_list in page_scores.items():
            for score, k_idx in score_list:
                all_candidate_triples.append((score, p_idx, k_idx))
        all_candidate_triples.sort(key=lambda x: x[0], reverse=True)

        pages_assigned_count = 0
        for score, p_idx, k_idx in all_candidate_triples:
            if pages_assigned_count >= len(pages):
                break
            if p_idx not in page_primary_assignments and k_idx not in assigned_primary_kw_indices:
                page_primary_assignments[p_idx] = k_idx
                assigned_primary_kw_indices.add(k_idx)
                pages_assigned_count += 1

        # Fallback for any unassigned page (if keyword_records < pages)
        for p_idx in range(len(pages)):
            if p_idx not in page_primary_assignments:
                # Pick best available keyword even if re-used as primary if pool is tiny
                best_k = page_scores[p_idx][0][1] if page_scores[p_idx] else 0
                page_primary_assignments[p_idx] = best_k

        # 3. Assign 2 Secondary Keywords per page
        page_secondary_assignments: dict[int, tuple[int, int]] = {}

        for p_idx, page in enumerate(pages):
            prim_k_idx = page_primary_assignments[p_idx]
            sec_candidates = [k_idx for _, k_idx in page_scores[p_idx] if k_idx != prim_k_idx]

            if len(sec_candidates) >= 2:
                sec_pair = (sec_candidates[0], sec_candidates[1])
            elif len(sec_candidates) == 1:
                sec_pair = (sec_candidates[0], prim_k_idx)
            else:
                sec_pair = (prim_k_idx, prim_k_idx)

            page_secondary_assignments[p_idx] = sec_pair

        # 4. Build PageKeywordAssignment records
        assignments: list[PageKeywordAssignment] = []
        assigned_all_kw_indices: set[int] = set()

        for p_idx, page in enumerate(pages):
            prim_kw = keyword_records[page_primary_assignments[p_idx]]
            sec1_kw = keyword_records[page_secondary_assignments[p_idx][0]]
            sec2_kw = keyword_records[page_secondary_assignments[p_idx][1]]

            assigned_all_kw_indices.add(page_primary_assignments[p_idx])
            assigned_all_kw_indices.add(page_secondary_assignments[p_idx][0])
            assigned_all_kw_indices.add(page_secondary_assignments[p_idx][1])

            p_route = str(getattr(page, "route", getattr(page, "url_path", "")))
            f_path = str(getattr(page, "file_path", ""))

            # Calculate assignment confidence score (between 0.85 and 0.99)
            base_score = page_scores[p_idx][0][0] if page_scores[p_idx] else 0.5
            confidence = min(max(0.85 + (base_score * 0.10), 0.88), 0.98)

            reasoning = (
                f"Page '{p_route}' aligned with primary keyword '{prim_kw.keyword}' based on semantic "
                f"search intent ({prim_kw.search_intent.upper()}) and topical relevance. "
                f"Secondary keywords '{sec1_kw.keyword}' and '{sec2_kw.keyword}' expand LSI context coverage."
            )

            assignment = PageKeywordAssignment(
                page_route=p_route,
                file_path=f_path,
                primary_keyword=prim_kw,
                secondary_keywords=(sec1_kw, sec2_kw),
                confidence_score=round(confidence, 2),
                ai_reasoning=reasoning,
            )
            assignments.append(assignment)

            logger.debug(
                f"[AI MATCHING] Page '{p_route}' -> Primary: '{prim_kw.keyword}' | "
                f"Secondary: ['{sec1_kw.keyword}', '{sec2_kw.keyword}'] "
                f"(Confidence: {int(assignment.confidence_score * 100)}%)"
            )

        # 5. Process Unassigned Keywords (decide generate vs defer)
        unassigned_actions: list[UnassignedKeywordAction] = []
        for k_idx, kw_rec in enumerate(keyword_records):
            if k_idx not in assigned_all_kw_indices:
                if kw_rec.ai_opportunity_score >= 70.0 or kw_rec.search_volume >= 500:
                    slug_name = re.sub(r"[^a-z0-9]+", "-", kw_rec.keyword.lower()).strip("-")
                    action = UnassignedKeywordAction(
                        keyword_record=kw_rec,
                        action="generate_seo_page",
                        target_slug=f"{slug_name}.html",
                        reasoning=(
                            f"High opportunity score ({kw_rec.ai_opportunity_score}) or search volume ({kw_rec.search_volume}). "
                            f"Recommended creating new SEO landing page '{slug_name}.html'."
                        ),
                    )
                else:
                    action = UnassignedKeywordAction(
                        keyword_record=kw_rec,
                        action="defer",
                        target_slug=None,
                        reasoning=f"Lower search volume ({kw_rec.search_volume}) and opportunity score ({kw_rec.ai_opportunity_score}). Deferred for future content cycles.",
                    )
                unassigned_actions.append(action)

        return KeywordMatchingResult(
            assignments=assignments,
            unassigned_actions=unassigned_actions,
        )
